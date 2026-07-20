from __future__ import annotations

import os
from dataclasses import dataclass, field
from threading import RLock
from typing import Optional


REGION_BASE_URLS = {
    "us": "https://api.xdr.trendmicro.com/v3.0/aiSecurity",
    "eu": "https://api.eu.xdr.trendmicro.com/v3.0/aiSecurity",
    "jp": "https://api.xdr.trendmicro.co.jp/v3.0/aiSecurity",
    "sg": "https://api.sg.xdr.trendmicro.com/v3.0/aiSecurity",
    "au": "https://api.au.xdr.trendmicro.com/v3.0/aiSecurity",
    "in": "https://api.in.xdr.trendmicro.com/v3.0/aiSecurity",
    "ca": "https://api.ca.xdr.trendmicro.com/v3.0/aiSecurity",
    "uk": "https://api.uk.xdr.trendmicro.com/v3.0/aiSecurity",
    "mea": "https://api.mea.xdr.trendmicro.com/v3.0/aiSecurity",
}

REGION_TO_AWS = {
    "us": "us-east-1",
    "eu": "eu-central-1",
    "jp": "ap-northeast-1",
    "sg": "ap-southeast-1",
    "au": "ap-southeast-2",
    "in": "ap-south-1",
    "ca": "ca-central-1",
    "uk": "eu-west-2",
    "mea": "me-central-1",
}


def _bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


@dataclass
class Settings:
    app_name: str = field(default_factory=lambda: os.getenv("APP_NAME", "BAM Bank Demo"))
    app_env: str = field(default_factory=lambda: os.getenv("APP_ENV", "demo"))
    public_base_url: str = field(default_factory=lambda: os.getenv("PUBLIC_BASE_URL", ""))
    data_dir: str = field(default_factory=lambda: os.getenv("DATA_DIR", "/data"))
    max_upload_mb: int = field(default_factory=lambda: _int("MAX_UPLOAD_MB", 10))

    tmv1_region: str = field(default_factory=lambda: os.getenv("TMV1_REGION", "sg").lower())
    tmv1_api_key: str = field(default_factory=lambda: os.getenv("TMV1_API_KEY", ""))
    tmv1_application_name: str = field(default_factory=lambda: os.getenv("TMV1_APPLICATION_NAME", "visionone-bank-demo"))
    ai_guard_enabled: bool = field(default_factory=lambda: _bool("AI_GUARD_ENABLED", True))
    ai_guard_fallback: str = field(default_factory=lambda: os.getenv("AI_GUARD_FALLBACK", "block").lower())
    ai_guard_mask_pii: bool = field(default_factory=lambda: _bool("AI_GUARD_MASK_PII", True))
    ai_guard_timeout_seconds: float = field(default_factory=lambda: float(os.getenv("AI_GUARD_TIMEOUT_SECONDS", "8")))
    force_demo_mode: bool = field(default_factory=lambda: _bool("FORCE_DEMO_MODE", False))
    allow_runtime_config: bool = field(default_factory=lambda: _bool("ALLOW_RUNTIME_CONFIG", False))

    llm_chat_url: str = field(default_factory=lambda: os.getenv("LLM_CHAT_URL", ""))
    llm_api_key: str = field(default_factory=lambda: os.getenv("LLM_API_KEY", ""))
    llm_model: str = field(default_factory=lambda: os.getenv("LLM_MODEL", "visionone-bank-demo"))
    llm_timeout_seconds: float = field(default_factory=lambda: float(os.getenv("LLM_TIMEOUT_SECONDS", "30")))

    file_security_enabled: bool = field(default_factory=lambda: _bool("FILE_SECURITY_ENABLED", True))
    file_security_api_key: str = field(default_factory=lambda: os.getenv("FILE_SECURITY_API_KEY", ""))
    file_security_region: str = field(default_factory=lambda: os.getenv("FILE_SECURITY_REGION", ""))
    file_security_pml: bool = field(default_factory=lambda: _bool("FILE_SECURITY_PML", True))
    file_security_demo_fallback: bool = field(default_factory=lambda: _bool("FILE_SECURITY_DEMO_FALLBACK", True))

    file_storage_s3_bucket: str = field(default_factory=lambda: os.getenv("FILE_STORAGE_S3_BUCKET", ""))
    file_storage_s3_prefix: str = field(default_factory=lambda: os.getenv("FILE_STORAGE_S3_PREFIX", "incoming/"))
    aws_region: str = field(default_factory=lambda: os.getenv("AWS_REGION", "ap-southeast-1"))

    ai_scanner_target_token: str = field(default_factory=lambda: os.getenv("AI_SCANNER_TARGET_TOKEN", ""))

    @property
    def file_security_effective_region(self) -> str:
        if self.file_security_region:
            return self.file_security_region
        return REGION_TO_AWS.get(self.tmv1_region, "ap-southeast-1")


class RuntimeConfig:
    """Ephemeral credential overrides for demos. Values are never returned to the browser."""

    def __init__(self, settings: Settings):
        self._lock = RLock()
        self._tmv1_api_key: Optional[str] = settings.tmv1_api_key or None
        self._region = settings.tmv1_region
        self._application_name = settings.tmv1_application_name
        self._force_demo_mode = settings.force_demo_mode

    def update(
        self,
        *,
        api_key: Optional[str] = None,
        region: Optional[str] = None,
        application_name: Optional[str] = None,
        force_demo_mode: Optional[bool] = None,
    ) -> None:
        with self._lock:
            if api_key is not None and api_key.strip():
                self._tmv1_api_key = api_key.strip()
            if region is not None and region in REGION_BASE_URLS:
                self._region = region
            if application_name is not None and application_name.strip():
                self._application_name = application_name.strip()
            if force_demo_mode is not None:
                self._force_demo_mode = force_demo_mode

    def snapshot(self) -> dict:
        with self._lock:
            base_url = REGION_BASE_URLS.get(self._region, REGION_BASE_URLS["sg"])
            return {
                "api_key": self._tmv1_api_key or "",
                "configured": bool(self._tmv1_api_key),
                "region": self._region,
                "application_name": self._application_name,
                "base_url": base_url.rstrip("/"),
                "force_demo_mode": self._force_demo_mode,
            }
