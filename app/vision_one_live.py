from __future__ import annotations

import asyncio
import json
import os
import re
import shutil
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
TARGET_BASE = os.getenv(
    "AI_SCANNER_TARGET_BASE_URL",
    "http://127.0.0.1:8080",
).rstrip("/")
RUNTIME_DIR = Path(
    os.getenv("AI_SCANNER_RUNTIME_DIR", "/tmp/bambank-aiscan")
)
MAX_SECONDS = int(os.getenv("AI_SCANNER_MAX_SECONDS", "900"))

JOBS: dict[str, dict] = {}
SCAN_LOCK = asyncio.Lock()
UPLOAD_ID_RE = re.compile(
    r"Successfully uploaded scan results.*?scanID=([0-9a-f-]{36})",
    re.IGNORECASE,
)
TMAS_ID_RE = re.compile(
    r"tmasScanID=([0-9a-f-]{36})",
    re.IGNORECASE,
)


class PromptMessage(BaseModel):
    role: Literal["user", "assistant", "system"] = "user"
    content: str = Field(min_length=1, max_length=12000)


class VisionOneLiveRequest(BaseModel):
    name: str = Field(
        default="BAM Bank custom prompt",
        min_length=2,
        max_length=500,
    )
    category: str = Field(
        default="Sensitive Data Disclosure",
        min_length=2,
        max_length=120,
    )
    evaluation_criteria: str = Field(
        min_length=2,
        max_length=4000,
    )
    tags: list[str] = Field(default_factory=list, max_length=20)
    messages: list[PromptMessage] = Field(min_length=1, max_length=20)
    target: Literal["vulnerable", "protected"] = "vulnerable"
    model_id: str = Field(
        default="visionone-bank-demo",
        min_length=1,
        max_length=200,
    )


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def yaml_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def clean_tag(value: str) -> str:
    return re.sub(
        r"[^A-Za-z0-9_.:/-]+",
        "-",
        value.strip(),
    ).strip("-")[:80]


def protected_adapter_url() -> str:
    return (
        f"{TARGET_BASE}/api/scanner/"
        "target/protected/v1/chat/completions"
    )


def target_url(target: str) -> str:
    if target == "protected":
        return protected_adapter_url()
    return (
        f"{TARGET_BASE}/api/ai/"
        "vulnerable/v1/chat/completions"
    )


def public_job(job: dict) -> dict:
    return {
        key: value
        for key, value in job.items()
        if key not in {"runtimeDir", "stdout", "stderr"}
    }


def write_custom_yaml(
    path: Path,
    payload: VisionOneLiveRequest,
) -> None:
    tags = [
        clean_tag(tag)
        for tag in payload.tags
        if clean_tag(tag)
    ] or ["bambank-custom-prompt"]

    tag_lines = "\n".join(
        f"      - {yaml_string(tag)}"
        for tag in tags
    )

    message_lines = []
    for message in payload.messages:
        message_lines.extend(
            [
                f"              - role: {message.role}",
                (
                    "                content: "
                    f"{yaml_string(message.content)}"
                ),
            ]
        )

    path.write_text(
        f'''version: "custom/1.0"

tags:
  - "bambank-vision-one-live"

prompts:
  - objective:
      category: {yaml_string(payload.category)}
      description: {yaml_string(payload.name)}

    tags:
{tag_lines}

    conversations:
      - tags:
          - "custom-prompt-studio"

        requests:
          - messages:
{chr(10).join(message_lines)}

    evaluator:
      type: "llm_judge"
      prompt: {yaml_string(payload.evaluation_criteria)}
''',
        encoding="utf-8",
    )


def write_config(
    path: Path,
    custom_name: str,
    payload: VisionOneLiveRequest,
) -> None:
    target_name = (
        "BAMBank Demo - AI Guard Protected"
        if payload.target == "protected"
        else "BAMBank Demo - Vulnerable"
    )

    path.write_text(
        f'''version: 2.9.0
name: BAMBank Vision One Live Custom Prompt
description: Live custom prompt scan launched from BAM Bank

target:
  endpoint: {yaml_string(target_url(payload.target))}
  name: {yaml_string(target_name)}
  custom:
    method: POST
    headers:
      Content-Type: application/json
    request:
      model: {yaml_string(payload.model_id)}
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


def normalize(
    data: dict,
    upload_id: Optional[str],
    tmas_id: Optional[str],
) -> dict:
    details = (
        data.get("details")
        if isinstance(data.get("details"), dict)
        else {}
    )
    raw_results = (
        data.get("evaluation_results")
        if isinstance(data.get("evaluation_results"), list)
        else []
    )

    results = []
    successful = 0

    for item in raw_results:
        if not isinstance(item, dict):
            continue

        outcome = str(
            item.get("attack_outcome", "")
        ).strip() or "completed"

        if outcome.lower() in {
            "successful",
            "success",
            "objective_met",
            "passed",
            "true",
        }:
            successful += 1

        results.append(
            {
                "resultId": item.get("result_id"),
                "objective": item.get("attack_objective"),
                "severity": item.get("severity"),
                "outcome": outcome,
                "evaluation": item.get("evaluation"),
                "judgeModel": item.get("judge_model"),
                "owasp": (
                    item.get("owasp")
                    if isinstance(item.get("owasp"), list)
                    else []
                ),
                "chatHistory": (
                    item.get("chat_history")
                    if isinstance(
                        item.get("chat_history"),
                        list,
                    )
                    else []
                ),
            }
        )

    return {
        "details": {
            "application": details.get("application"),
            "scanTime": details.get("scan_time"),
            "endpoint": details.get("endpoint"),
            "tmasScanId": (
                details.get("scan_id")
                or tmas_id
            ),
            "visionOneScanId": upload_id,
            "duration": details.get("scan_duration"),
        },
        "summary": {
            "total": len(results),
            "successful": successful,
            "blocked": max(
                0,
                len(results) - successful,
            ),
        },
        "results": results,
        "resultSource": "vision-one-ai-scanner",
        "visionOnePublished": True,
        "visionOneNote": (
            "The custom prompt was executed by TMAS and "
            "published to Trend Vision One AI Scanner."
        ),
    }


@router.post(
    "/target/protected/v1/chat/completions"
)
async def protected_target_adapter(
    body: dict = Body(...),
) -> dict:
    actual_url = (
        f"{TARGET_BASE}/api/ai/"
        "protected/v1/chat/completions"
    )

    async with httpx.AsyncClient(timeout=90) as client:
        response = await client.post(
            actual_url,
            json=body,
        )

    if response.is_success:
        return response.json()

    try:
        error_payload = response.json()
    except Exception:
        error_payload = {"detail": response.text}

    detail = error_payload.get(
        "detail",
        error_payload,
    )

    return {
        "id": (
            "chatcmpl-guard-"
            f"{uuid.uuid4().hex[:12]}"
        ),
        "object": "chat.completion",
        "created": int(
            datetime.now(
                timezone.utc,
            ).timestamp()
        ),
        "model": body.get(
            "model",
            "visionone-bank-demo",
        ),
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": (
                        "Blocked by Trend Vision One "
                        "AI Guard. "
                        + json.dumps(
                            detail,
                            ensure_ascii=False,
                        )
                    ),
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
        },
    }


async def run_live(
    job_id: str,
    payload: VisionOneLiveRequest,
) -> None:
    job = JOBS[job_id]
    folder = Path(job["runtimeDir"])

    try:
        async with SCAN_LOCK:
            job.update(
                status="preparing",
                stage="Generating custom prompt YAML",
                updatedAt=now(),
            )

            folder.mkdir(
                parents=True,
                exist_ok=False,
            )

            custom = folder / "custom-prompts.yaml"
            config = folder / "config.yaml"
            result = folder / "result.json"
            report = folder / "report.md"

            write_custom_yaml(custom, payload)
            write_config(
                config,
                custom.name,
                payload,
            )

            if not Path(TMAS_BINARY).is_file():
                raise RuntimeError(
                    "TMAS binary not found: "
                    f"{TMAS_BINARY}"
                )

            # BAM_V58_CREDENTIAL_PREFLIGHT
            readable_env_file = bool(
                TMAS_ENV_FILE
                and Path(TMAS_ENV_FILE).is_file()
                and os.access(TMAS_ENV_FILE, os.R_OK)
                and os.access(TMAS_ENV_FILE, os.R_OK)
            )
            if not os.getenv("TMAS_API_KEY") and not readable_env_file:
                raise RuntimeError(
                    "TMAS credential is unavailable. Configure "
                    "TMAS_API_KEY in the container environment."
                )

            command = [
                TMAS_BINARY,
                "aiscan",
                "llm",
                "--config",
                str(config),
                "--region",
                TMAS_REGION,
            ]

            if (
                TMAS_ENV_FILE
                and Path(TMAS_ENV_FILE).is_file()
                and os.access(TMAS_ENV_FILE, os.R_OK)
                and os.access(TMAS_ENV_FILE, os.R_OK)
            ):
                command.extend(
                    [
                        "--env-file",
                        TMAS_ENV_FILE,
                    ]
                )

            command.extend(
                [
                    "--yes",
                    "--output",
                    (
                        f"json={result},"
                        f"markdown={report}"
                    ),
                    "-v",
                ]
            )

            job.update(
                status="running",
                stage=(
                    "Running TMAS and publishing "
                    "to Vision One"
                ),
                updatedAt=now(),
            )

            process = (
                await asyncio.create_subprocess_exec(
                    *command,
                    cwd=str(folder),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
            )

            try:
                stdout_b, stderr_b = (
                    await asyncio.wait_for(
                        process.communicate(),
                        timeout=MAX_SECONDS,
                    )
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                raise RuntimeError(
                    "TMAS scan exceeded "
                    f"{MAX_SECONDS} seconds"
                )

            stdout = stdout_b.decode(
                errors="replace",
            )
            stderr = stderr_b.decode(
                errors="replace",
            )

            job["stdout"] = stdout
            job["stderr"] = stderr

            if process.returncode != 0:
                safe = (
                    stderr.strip().splitlines()[-1]
                    if stderr.strip()
                    else "TMAS scan failed"
                )
                raise RuntimeError(safe[:700])

            if not result.is_file():
                raise RuntimeError(
                    "TMAS completed without result.json"
                )

            combined = stdout + "\n" + stderr
            upload_match = UPLOAD_ID_RE.search(
                combined,
            )
            tmas_match = TMAS_ID_RE.search(
                combined,
            )

            normalized = normalize(
                json.loads(
                    result.read_text(
                        encoding="utf-8",
                    )
                ),
                (
                    upload_match.group(1)
                    if upload_match
                    else None
                ),
                (
                    tmas_match.group(1)
                    if tmas_match
                    else None
                ),
            )

            job.update(
                status="completed",
                stage="Published to Vision One",
                result=normalized,
                updatedAt=now(),
                completedAt=now(),
            )

    except Exception as exc:
        job.update(
            status="failed",
            stage="Scan failed",
            error=str(exc),
            updatedAt=now(),
            completedAt=now(),
        )


@router.post(
    "/vision-one-live",
    status_code=202,
)
async def vision_one_live(
    payload: VisionOneLiveRequest,
) -> dict:
    job_id = uuid.uuid4().hex
    job = {
        "jobId": job_id,
        "status": "queued",
        "stage": "Queued",
        "target": payload.target,
        "createdAt": now(),
        "updatedAt": now(),
        "runtimeDir": str(
            RUNTIME_DIR / job_id
        ),
        "result": None,
        "error": None,
    }

    JOBS[job_id] = job
    asyncio.create_task(
        run_live(
            job_id,
            payload,
        )
    )
    return public_job(job)


@router.get("/vision-one-live/jobs/{job_id}")
async def get_job(job_id: str) -> dict:
    job = JOBS.get(job_id)

    if not job:
        raise HTTPException(
            status_code=404,
            detail="AI Scanner job not found",
        )

    return public_job(job)
