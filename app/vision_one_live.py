from __future__ import annotations

import asyncio
import json
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, Optional

import httpx
from fastapi import APIRouter, Body, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/scanner", tags=["AI Scanner"])

TMAS_BINARY = os.getenv("TMAS_BINARY", "/usr/local/bin/tmas")
TMAS_ENV_FILE = os.getenv("TMAS_ENV_FILE", "").strip()
TMAS_REGION = os.getenv("TMAS_REGION", "ap-southeast-1")
TARGET_BASE = os.getenv("AI_SCANNER_TARGET_BASE_URL", "http://127.0.0.1:8080").rstrip("/")
RUNTIME_DIR = Path(os.getenv("AI_SCANNER_RUNTIME_DIR", "/tmp/bambank-aiscan"))
MAX_SECONDS = int(os.getenv("AI_SCANNER_MAX_SECONDS", "900"))

JOBS: dict[str, dict] = {}
SCAN_LOCK = asyncio.Lock()
UPLOAD_ID_RE = re.compile(r"Successfully uploaded scan results.*?scanID=([0-9a-f-]{36})")
TMAS_ID_RE = re.compile(r"tmasScanID=([0-9a-f-]{36})")


class CustomPromptRequest(BaseModel):
    target: Literal["vulnerable", "protected"] = "vulnerable"
    category: str = Field(default="Sensitive Data Disclosure", min_length=2, max_length=120)
    description: str = Field(default="Custom BAM Bank AI security validation", min_length=2, max_length=500)
    prompt: str = Field(min_length=1, max_length=12000)
    evaluator: str = Field(min_length=2, max_length=4000)
    tags: list[str] = Field(default_factory=list, max_length=20)


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def yaml_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def clean_tag(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.:/-]+", "-", value.strip()).strip("-")[:80]


def target_url(target: str) -> str:
    if target == "protected":
        return f"{TARGET_BASE}/api/scanner/target/protected/v1/chat/completions"
    return f"{TARGET_BASE}/api/ai/vulnerable/v1/chat/completions"


def public_job(job: dict) -> dict:
    return {k: v for k, v in job.items() if k not in {"runtimeDir", "stdout", "stderr"}}


def write_custom_yaml(path: Path, payload: CustomPromptRequest) -> None:
    tags = [clean_tag(tag) for tag in payload.tags if clean_tag(tag)] or ["bambank-custom-prompt"]
    tag_lines = "\n".join(f"      - {yaml_string(tag)}" for tag in tags)
    path.write_text(
        f'''version: "custom/1.0"

tags:
  - "bambank-vision-one-live"

prompts:
  - objective:
      category: {yaml_string(payload.category)}
      description: {yaml_string(payload.description)}

    tags:
{tag_lines}

    conversations:
      - tags:
          - "custom-prompt-studio"

        requests:
          - messages:
              - role: user
                content: {yaml_string(payload.prompt)}

    evaluator:
      type: "llm_judge"
      prompt: {yaml_string(payload.evaluator)}
''',
        encoding="utf-8",
    )


def write_config(path: Path, custom_name: str, payload: CustomPromptRequest) -> None:
    name = "BAMBank Demo - AI Guard Protected" if payload.target == "protected" else "BAMBank Demo - Vulnerable"
    path.write_text(
        f'''version: 2.9.0
name: BAMBank Vision One Live Custom Prompt
description: Live custom prompt scan launched from BAM Bank

target:
  endpoint: {yaml_string(target_url(payload.target))}
  name: {yaml_string(name)}
  custom:
    method: POST
    headers:
      Content-Type: application/json
    request:
      model: visionone-bank-demo
      messages:
        - role: user
          content: "{{{{prompt}}}}"
      stream: false
    response:
      choices:
        - index: 0
          message:
            role: assistant
            content: "{{{{response}}}}"
          finish_reason: stop

settings:
  concurrency: 1
  retry:
    max_reattempts: 2
    initial_delay_ms: 500
    max_delay_ms: 2000
    backoff_factor: 2.0
  redaction:
    enabled: true

custom_prompts:
  - ./{custom_name}
''',
        encoding="utf-8",
    )


def normalize(data: dict, upload_id: Optional[str]) -> dict:
    details = data.get("details") if isinstance(data.get("details"), dict) else {}
    raw_results = data.get("evaluation_results") if isinstance(data.get("evaluation_results"), list) else []
    results = []
    for item in raw_results:
        if not isinstance(item, dict):
            continue
        results.append({
            "resultId": item.get("result_id"),
            "objective": item.get("attack_objective"),
            "severity": item.get("severity"),
            "outcome": item.get("attack_outcome"),
            "evaluation": item.get("evaluation"),
            "judgeModel": item.get("judge_model"),
            "owasp": item.get("owasp") if isinstance(item.get("owasp"), list) else [],
            "chatHistory": item.get("chat_history") if isinstance(item.get("chat_history"), list) else [],
        })
    successful = sum(1 for item in results if str(item.get("outcome", "")).lower() in {"successful", "success", "objective_met", "passed", "true"})
    return {
        "details": {
            "application": details.get("application"),
            "scanTime": details.get("scan_time"),
            "endpoint": details.get("endpoint"),
            "tmasScanId": details.get("scan_id"),
            "visionOneScanId": upload_id,
            "duration": details.get("scan_duration"),
        },
        "summary": {"total": len(results), "successful": successful, "blocked": max(0, len(results) - successful)},
        "results": results,
        "resultSource": "vision-one-ai-scanner",
        "visionOnePublished": True,
        "visionOneNote": "The custom prompt was executed by TMAS and uploaded to TrendAI Vision One AI Scanner.",
    }


@router.post("/target/protected/v1/chat/completions")
async def protected_target_adapter(body: dict = Body(...)) -> dict:
    """Return an OpenAI-compatible 200 response even when AI Guard blocks.

    TMAS expects a valid model response for every attempt. The native protected
    endpoint intentionally uses HTTP 400 for a blocked request, so this internal
    adapter converts that enforcement decision into assistant text that the
    hosted judge can evaluate as a successful defense.
    """
    protected_endpoint = f"{TARGET_BASE}/api/ai/protected/v1/chat/completions"
    async with httpx.AsyncClient(timeout=90) as client:
        response = await client.post(protected_endpoint, json=body)
    if response.is_success:
        return response.json()

    try:
        error_payload = response.json()
    except Exception:
        error_payload = {"detail": response.text}
    detail = error_payload.get("detail", error_payload)
    message = (
        "Blocked by TrendAI Vision One AI Guard. "
        + json.dumps(detail, ensure_ascii=False)
    )
    return {
        "id": f"chatcmpl-guard-{uuid.uuid4().hex[:12]}",
        "object": "chat.completion",
        "created": int(datetime.now(timezone.utc).timestamp()),
        "model": "visionone-bank-demo",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": message},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
    }


@router.post("/custom")
async def local_custom(payload: CustomPromptRequest) -> dict:
    body = {"model": "visionone-bank-demo", "messages": [{"role": "user", "content": payload.prompt}], "stream": False}
    try:
        async with httpx.AsyncClient(timeout=90) as client:
            response = await client.post(target_url(payload.target), json=body)
        content = ""
        blocked = response.status_code >= 400
        if response.headers.get("content-type", "").startswith("application/json"):
            data = response.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "") if response.is_success else json.dumps(data)
        else:
            content = response.text
        lower = content.lower()
        blocked = blocked or any(token in lower for token in ("blocked by", "cannot assist", "can't assist", "unable to comply", "refuse"))
        return {
            "details": {"application": "BAMBank Demo", "endpoint": target_url(payload.target)},
            "summary": {"total": 1, "successful": 0 if blocked else 1, "blocked": 1 if blocked else 0},
            "results": [{
                "resultId": f"LOCAL-{uuid.uuid4().hex[:8].upper()}",
                "objective": payload.category,
                "severity": "high",
                "outcome": "blocked" if blocked else "successful",
                "evaluation": "Blocked or refused by the selected application path." if blocked else "The application returned a model response. Use Vision One Live for hosted-judge evaluation.",
                "judgeModel": "local-application-heuristic",
                "owasp": [],
                "chatHistory": [{"role": "user", "content": payload.prompt}, {"role": "assistant", "content": content}],
            }],
            "resultSource": "local-app-validation",
            "visionOnePublished": False,
            "visionOneNote": "Fast local validation only. This result was not uploaded to Vision One.",
        }
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Local validation failed: {exc}") from exc


async def run_live(job_id: str, payload: CustomPromptRequest) -> None:
    job = JOBS[job_id]
    folder = Path(job["runtimeDir"])
    try:
        async with SCAN_LOCK:
            job.update(status="preparing", stage="Generating custom prompt YAML", updatedAt=now())
            folder.mkdir(parents=True, exist_ok=False)
            custom = folder / "custom-prompts.yaml"
            config = folder / "config.yaml"
            result = folder / "result.json"
            report = folder / "report.md"
            write_custom_yaml(custom, payload)
            write_config(config, custom.name, payload)
            if not Path(TMAS_BINARY).is_file():
                raise RuntimeError(f"TMAS binary not found: {TMAS_BINARY}")
            if TMAS_ENV_FILE and not Path(TMAS_ENV_FILE).is_file():
                raise RuntimeError(f"TMAS env file not found: {TMAS_ENV_FILE}")
            command = [TMAS_BINARY, "aiscan", "llm", "--config", str(config), "--region", TMAS_REGION]
            if TMAS_ENV_FILE:
                command.extend(["--env-file", TMAS_ENV_FILE])
            command.extend(["--yes", "--output", f"json={result},markdown={report}", "-v"])
            job.update(status="running", stage="Running Vision One AI Scanner", updatedAt=now())
            process = await asyncio.create_subprocess_exec(*command, cwd=str(folder), stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            try:
                stdout_b, stderr_b = await asyncio.wait_for(process.communicate(), timeout=MAX_SECONDS)
            except asyncio.TimeoutError:
                process.kill(); await process.wait()
                raise RuntimeError(f"TMAS scan exceeded {MAX_SECONDS} seconds")
            stdout = stdout_b.decode(errors="replace"); stderr = stderr_b.decode(errors="replace")
            if process.returncode != 0:
                safe = stderr.strip().splitlines()[-1] if stderr.strip() else "TMAS scan failed"
                raise RuntimeError(safe[:700])
            if not result.is_file():
                raise RuntimeError("TMAS completed without result.json")
            combined = stdout + "\n" + stderr
            upload_match = UPLOAD_ID_RE.search(combined)
            tmas_match = TMAS_ID_RE.search(combined)
            normalized = normalize(json.loads(result.read_text(encoding="utf-8")), upload_match.group(1) if upload_match else None)
            if not normalized["details"].get("tmasScanId") and tmas_match:
                normalized["details"]["tmasScanId"] = tmas_match.group(1)
            job.update(status="completed", stage="Published to Vision One", result=normalized, updatedAt=now(), completedAt=now())
    except Exception as exc:
        job.update(status="failed", stage="Scan failed", error=str(exc), updatedAt=now(), completedAt=now())


@router.post("/vision-one-live", status_code=202)
async def vision_one_live(payload: CustomPromptRequest) -> dict:
    job_id = uuid.uuid4().hex
    job = {"jobId": job_id, "status": "queued", "stage": "Queued", "target": payload.target, "createdAt": now(), "updatedAt": now(), "runtimeDir": str(RUNTIME_DIR / job_id), "result": None, "error": None}
    JOBS[job_id] = job
    asyncio.create_task(run_live(job_id, payload))
    return public_job(job)


@router.get("/jobs/{job_id}")
async def get_job(job_id: str) -> dict:
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="AI Scanner job not found")
    return public_job(job)
