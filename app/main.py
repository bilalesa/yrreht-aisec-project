from __future__ import annotations

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Literal, Optional

from fastapi import Body, FastAPI, File, Header, HTTPException, Request, UploadFile
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .config import REGION_BASE_URLS, RuntimeConfig, Settings
from .services import (
    AIGuardClient,
    BankLLM,
    FileSecurityService,
    GuardBlocked,
    GuardUnavailable,
    extract_user_prompt,
    make_temp_file,
    validate_scanner_token,
)

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger("visionone-bank-demo")

settings = Settings()
runtime = RuntimeConfig(settings)
guard = AIGuardClient(settings, runtime)
llm = BankLLM(settings)
file_security = FileSecurityService(settings)

app = FastAPI(
    title="BAM Bank Demo",
    description="Synthetic banking application for TrendAI Vision One AI Security demonstrations.",
    version="1.0.2",
    docs_url="/api/docs",
    redoc_url=None,
)
app.add_middleware(GZipMiddleware, minimum_size=1000)

STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=12000)
    guard_enabled: bool = True


class RuntimeSettingsRequest(BaseModel):
    api_key: Optional[str] = None
    region: Optional[str] = None
    application_name: Optional[str] = None
    force_demo_mode: Optional[bool] = None


class ScannerSimulationRequest(BaseModel):
    target: Literal["vulnerable", "protected"] = "vulnerable"
    objectives: list[str] = Field(default_factory=lambda: ["prompt-injection", "sensitive-data", "system-prompt"])


@app.get("/", include_in_schema=False)
async def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok", "service": "visionone-bank-demo", "version": "1.0.2"}


@app.get("/api/preflight")
async def application_preflight(request: Request) -> dict:
    cfg = runtime.snapshot()
    base = settings.public_base_url.rstrip("/") or str(request.base_url).rstrip("/")
    blockers: list[str] = []
    warnings: list[str] = []

    if settings.ai_guard_enabled and not cfg["configured"] and not cfg["force_demo_mode"]:
        blockers.append("AI Guard is enabled but TMV1_API_KEY is not configured")
    if cfg["force_demo_mode"]:
        warnings.append("AI Guard is using local demo mode; do not present this as live Vision One evidence")
    if settings.file_security_enabled and not (settings.file_security_api_key or settings.tmv1_api_key):
        if settings.file_security_demo_fallback:
            warnings.append("File Security SDK key is missing and local demo fallback is enabled")
        else:
            blockers.append("File Security is enabled but no SDK API key is configured")
    if settings.file_security_demo_fallback:
        warnings.append("File Security demo fallback is enabled; disable it for live validation")
    if not settings.ai_scanner_target_token:
        warnings.append("AI Scanner target bearer token is empty; endpoints are unauthenticated")
    if not settings.public_base_url:
        warnings.append("PUBLIC_BASE_URL is empty; generated scanner URLs depend on forwarded headers")
    if settings.file_storage_s3_bucket:
        warnings.append("Storage mode is configured; verify workload identity and s3:PutObject separately")

    return {
        "ready": not blockers,
        "blockers": blockers,
        "warnings": warnings,
        "effective": {
            "deploymentMode": "trend-hosted",
            "publicBaseUrl": base,
            "aiGuardRegion": cfg["region"],
            "aiGuardBaseUrl": cfg["base_url"],
            "fileSecurityRegion": settings.file_security_effective_region,
            "scannerAuthenticationRequired": bool(settings.ai_scanner_target_token),
        },
    }


@app.get("/api/settings")
async def get_settings(request: Request) -> dict:
    cfg = runtime.snapshot()
    base = settings.public_base_url.rstrip("/") or str(request.base_url).rstrip("/")
    return {
        "appName": settings.app_name,
        "aiGuard": {
            "deploymentMode": "trend-hosted",
            "enabled": settings.ai_guard_enabled,
            "configured": cfg["configured"],
            "region": cfg["region"],
            "applicationName": cfg["application_name"],
            "baseUrl": cfg["base_url"],
            "forceDemoMode": cfg["force_demo_mode"],
            "fallback": settings.ai_guard_fallback,
            "runtimeConfigurationAllowed": settings.allow_runtime_config,
        },
        "llm": {"configured": bool(settings.llm_chat_url), "model": settings.llm_model},
        "fileSecurity": {
            "enabled": settings.file_security_enabled,
            "sdkConfigured": bool(settings.file_security_api_key or settings.tmv1_api_key),
            "region": settings.file_security_effective_region,
            "storageConfigured": bool(settings.file_storage_s3_bucket),
            "maxUploadMb": settings.max_upload_mb,
        },
        "scanner": {
            "vulnerableEndpoint": f"{base}/api/ai/vulnerable/v1/chat/completions",
            "protectedEndpoint": f"{base}/api/ai/protected/v1/chat/completions",
            "authenticationRequired": bool(settings.ai_scanner_target_token),
        },
    }


@app.post("/api/settings")
async def update_settings(payload: RuntimeSettingsRequest) -> dict:
    if not settings.allow_runtime_config:
        raise HTTPException(status_code=403, detail="Runtime credential configuration is disabled. Use a Kubernetes Secret.")
    if payload.region and payload.region not in REGION_BASE_URLS:
        raise HTTPException(status_code=400, detail=f"Unsupported region: {payload.region}")
    runtime.update(
        api_key=payload.api_key,
        region=payload.region,
        application_name=payload.application_name,
        force_demo_mode=payload.force_demo_mode,
    )
    cfg = runtime.snapshot()
    return {"saved": True, "configured": cfg["configured"], "region": cfg["region"], "forceDemoMode": cfg["force_demo_mode"]}


@app.post("/api/guard/test")
async def guard_test(payload: ChatRequest) -> dict:
    try:
        result = await guard.inspect_prompt(payload.message)
        return {"connected": True, "action": result.get("action", "allow"), "reasons": result.get("reasons", [])}
    except GuardBlocked as exc:
        return {"connected": True, "action": "block", "reasons": exc.details.get("reasons", [exc.reason])}
    except GuardUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.post("/api/chat")
async def chat(payload: ChatRequest) -> dict:
    try:
        if not payload.guard_enabled:
            unprotected_response = await llm.complete(payload.message, vulnerable=True)
            message = unprotected_response.get("choices", [{}])[0].get("message", {}).get("content", "")
            return {
                "status": "allowed",
                "message": message,
                "guard": {"enabled": False, "input": None, "output": None},
            }

        prompt_result = await guard.inspect_prompt(payload.message)
        safe_prompt = prompt_result.get("content", payload.message)
        llm_response = await llm.complete(safe_prompt, vulnerable=False)
        output_result = await guard.inspect_response(llm_response)
        return {
            "status": "allowed",
            "message": output_result.get("content", ""),
            "guard": {
                "enabled": True,
                "input": {"action": prompt_result.get("action", "allow"), "reasons": prompt_result.get("reasons", [])},
                "output": {"action": output_result.get("action", "allow"), "reasons": output_result.get("reasons", [])},
            },
        }
    except GuardBlocked as exc:
        return JSONResponse(
            status_code=400,
            content={"status": "blocked", "message": "Blocked by TrendAI Vision One AI Guard.", "reasons": exc.details.get("reasons") or [exc.reason]},
        )
    except GuardUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Chat request failed")
        raise HTTPException(status_code=502, detail=f"Chat backend error: {exc}") from exc


async def _scanner_completion(payload: dict, authorization: Optional[str], protected: bool) -> dict:
    try:
        validate_scanner_token(authorization, settings.ai_scanner_target_token)
    except PermissionError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    prompt = extract_user_prompt(payload)
    if not prompt:
        raise HTTPException(status_code=400, detail="No user prompt found in messages")

    if protected:
        try:
            prompt_result = await guard.inspect_prompt(prompt)
            response = await llm.complete(prompt_result.get("content", prompt), vulnerable=True)
            output_result = await guard.inspect_response(response)
            response["choices"][0]["message"]["content"] = output_result.get("content", "")
            return response
        except GuardBlocked as exc:
            raise HTTPException(status_code=400, detail={"error": "Blocked by AI Guard", "reasons": exc.details.get("reasons") or [exc.reason]}) from exc
        except GuardUnavailable as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    return await llm.complete(prompt, vulnerable=True)


@app.post("/api/ai/vulnerable/v1/chat/completions")
async def scanner_vulnerable(payload: dict = Body(...), authorization: Optional[str] = Header(default=None)) -> dict:
    return await _scanner_completion(payload, authorization, protected=False)


@app.post("/api/ai/protected/v1/chat/completions")
async def scanner_protected(payload: dict = Body(...), authorization: Optional[str] = Header(default=None)) -> dict:
    return await _scanner_completion(payload, authorization, protected=True)


@app.post("/api/scanner/simulate")
async def scanner_simulate(payload: ScannerSimulationRequest) -> dict:
    catalog = {
        "prompt-injection": ("Prompt Injection", "critical"),
        "sensitive-data": ("Sensitive Data Disclosure", "high"),
        "system-prompt": ("System Prompt Leakage", "high"),
        "jailbreak": ("Jailbreak Resistance", "medium"),
        "harmful-output": ("Harmful Output", "medium"),
        "agent-tools": ("Agent Tool Disclosure", "low"),
    }
    findings = []
    protected = payload.target == "protected"
    for index, objective in enumerate(payload.objectives):
        label, severity = catalog.get(objective, (objective.replace("-", " ").title(), "medium"))
        blocked = protected and objective in {"prompt-injection", "sensitive-data", "system-prompt", "jailbreak", "harmful-output"}
        findings.append(
            {
                "id": f"AIS-{index + 1:02d}",
                "objective": label,
                "severity": severity,
                "result": "blocked" if blocked else "successful",
                "framework": "OWASP LLM / MITRE ATLAS",
                "recommendation": "Keep AI Guard in both pre-call and post-call paths, then re-run TMAS for validation.",
            }
        )
        await asyncio.sleep(0.08)
    successful = sum(1 for item in findings if item["result"] == "successful")
    return {
        "target": payload.target,
        "total": len(findings),
        "successful": successful,
        "blocked": len(findings) - successful,
        "findings": findings,
        "simulated": True,
    }


@app.post("/api/files/scan")
async def scan_file(file: UploadFile = File(...), mode: Literal["sdk", "storage"] = "sdk") -> dict:
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing filename")
    content = await file.read(settings.max_upload_mb * 1024 * 1024 + 1)
    try:
        temp_path = make_temp_file(file.filename, content, settings.max_upload_mb * 1024 * 1024)
    except ValueError as exc:
        raise HTTPException(status_code=413, detail=str(exc)) from exc
    try:
        if mode == "storage":
            return await asyncio.to_thread(file_security.upload_to_storage, temp_path, file.filename)
        return await asyncio.to_thread(file_security.scan_and_store, temp_path, file.filename)
    except Exception as exc:
        temp_path.unlink(missing_ok=True)
        logger.exception("File scan failed")
        raise HTTPException(status_code=502, detail=f"File Security error: {exc}") from exc


@app.exception_handler(404)
async def spa_fallback(request: Request, exc: Exception):
    if request.url.path.startswith("/api/"):
        return JSONResponse(status_code=404, content={"detail": "Not found"})
    return FileResponse(STATIC_DIR / "index.html")
