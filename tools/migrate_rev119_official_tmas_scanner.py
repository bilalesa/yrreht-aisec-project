#!/usr/bin/env python3
"""
TF Bank Rev 119 migration: make built-in AI Scanner Live mode run the
official TMAS job API, remove the misleading legacy live-validation route,
clean obsolete revision scripts, validate the source, and optionally deploy
the RC safely on port 18081.

Typical use from the repository root:

    python3 tools/migrate_rev119_official_tmas_scanner.py apply \
      --deploy-rc --commit --push

The script never touches production port 8081. Git updates must be made from
a feature branch and promoted to main through a pull request.
"""

from __future__ import annotations

import argparse
import datetime as dt
import importlib.util
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Iterable, Sequence

RELEASE_VERSION = "119.0.0"
FEATURE_BRANCH = "fix/rev119-official-ai-scanner"
COMMIT_MESSAGE = "fix: publish AI Scanner live runs through TMAS"

MAIN_PATH = Path("app/main.py")
SCANNER_UI_PATH = Path("app/static/bam-suite-v99.js")
BASE_UI_PATH = Path("app/static/app.js")
INDEX_PATH = Path("app/static/index.html")
TEST_PATH = Path("tests/test_api.py")

VERSIONED_TEXT_FILES = (
    Path("deploy/README.md"),
    Path("deploy/release.env.example"),
    Path("deploy/primary.env.example"),
    Path("deploy/backup.env.example"),
    Path("docker-compose.yaml"),
    Path("helm/visionone-bank-demo/values.yaml"),
)

OBSOLETE_PATCH_PATTERNS = (
    "scripts/apply_bam_revision_v*.sh",
    "scripts/apply_bam_revision_v*.py",
    "scripts/apply_rev*.py",
    "scripts/deploy-v14.sh",
    "apply_bam_revision_v*.sh",
    "apply_bam_revision_v*.py",
    "apply_rev*.py",
    "V14-LIVE-NOTES.md",
)

ALLOWED_CHANGED_PATHS = {
    str(MAIN_PATH),
    str(SCANNER_UI_PATH),
    str(BASE_UI_PATH),
    str(INDEX_PATH),
    str(TEST_PATH),
    *(str(path) for path in VERSIONED_TEXT_FILES),
    "tools/migrate_rev119_official_tmas_scanner.py",
}
ALLOWED_DELETED_PREFIXES = (
    "scripts/apply_bam_revision_v",
    "scripts/apply_rev",
    "scripts/deploy-v14.sh",
    "apply_bam_revision_v",
    "apply_rev",
    "V14-LIVE-NOTES.md",
)

REV119_MARKER = "TF_BANK_REV119_OFFICIAL_TMAS_SCANNER"

LEGACY_MAIN_PATTERN = re.compile(
    r"\nLIVE_SCANNER_PROMPTS = \{.*?"
    r"(?=\n@app\.post\(\"/api/files/scan\"\))",
    flags=re.S,
)

RUN_SCANNER_PATTERN = re.compile(
    r"  async function runScannerAssessment\(\) \{\n.*?\n  \}\n\n"
    r"  function renderTemplateLibrary\(\) \{",
    flags=re.S,
)

LEGACY_TEST_PATTERN = re.compile(
    r"\ndef test_live_scanner_executes_guard_path\(\) -> None:\n.*?"
    r"(?=\n\ndef test_client_context_shape\(\) -> None:)",
    flags=re.S,
)

NEW_RUN_SCANNER_FUNCTION = r"""  async function runScannerAssessment() {
    if (state.scannerBusy) return;

    let endpoint;
    let body;
    let officialTmas = false;

    if (state.scannerSource === 'custom') {
      captureCustomPromptFields();
      const tags = customPromptTags();
      if (!String(state.customCategory || '').trim()) {
        state.scannerResult = { error: 'Enter an objective category.' };
        renderScanner();
        return;
      }
      if (!String(state.customDescription || '').trim()) {
        state.scannerResult = { error: 'Enter an objective description.' };
        renderScanner();
        return;
      }
      if (!String(state.customPrompt || '').trim()) {
        state.scannerResult = { error: 'Enter at least one user prompt.' };
        renderScanner();
        return;
      }
      if (!String(state.customEvaluator || '').trim()) {
        state.scannerResult = { error: 'Enter evaluation criteria.' };
        renderScanner();
        return;
      }
      if (!tags.length) {
        state.scannerResult = { error: 'Add at least one conversation tag.' };
        renderScanner();
        return;
      }
      endpoint = '/api/v99/scanner/custom';
      body = {
        mode: state.scannerMode,
        target: state.scannerTarget,
        category: state.customCategory,
        description: state.customDescription,
        prompt: state.customPrompt,
        assistant_prefill: state.customAssistantPrefill || null,
        follow_up: state.customFollowUp || null,
        evaluator: state.customEvaluator,
        tags,
      };
    } else {
      const objectives = [...q('#control-body').querySelectorAll('[data-scanner-objective]:checked')].map(input => input.value);
      if (!objectives.length) {
        state.scannerResult = { error: 'Select at least one test.' };
        renderScanner();
        return;
      }
      state.scannerObjectives = objectives;
      officialTmas = state.scannerMode === 'live';
      endpoint = officialTmas ? '/api/scanner/jobs' : '/api/scanner/simulate';
      body = officialTmas
        ? {
            mode: 'live',
            target: state.scannerTarget,
            objectives,
            techniques: ['None'],
            modifiers: ['None'],
            model_id: 'visionone-bank-demo',
            tenant_mode: 'default',
          }
        : {
            target: state.scannerTarget,
            objectives,
          };
    }

    state.scannerBusy = true;
    state.scannerResult = null;
    renderScanner();

    try {
      const response = await request(endpoint, {
        method: 'POST',
        body: JSON.stringify(body),
      });

      if (!officialTmas) {
        state.scannerResult = response;
      } else {
        const jobId = String(response?.jobId || '');
        if (!jobId) throw new Error('Vision One did not return a TMAS job ID.');

        let job = null;
        for (let attempt = 0; attempt < 420; attempt += 1) {
          job = await request(`/api/scanner/jobs/${encodeURIComponent(jobId)}`);
          if (job?.status === 'completed' || job?.status === 'failed') break;
          await new Promise(resolve => window.setTimeout(resolve, 1500));
        }

        if (!job || job.status !== 'completed') {
          const detail = job?.error
            || job?.failure?.message
            || 'The TMAS assessment did not complete within the expected time.';
          throw new Error(detail);
        }

        const summary = job.result || {};
        state.scannerResult = {
          ...summary,
          jobId: job.id || jobId,
          status: job.status,
          stage: job.stage,
          tenantMode: job.tenantMode,
          tenantRegion: job.tenantRegion,
          tenantLabel: summary.tenantLabel || 'Server-managed Vision One tenant',
          processLog: Array.isArray(job.logs) ? job.logs : [],
          consoleExpected: Boolean(summary.consoleExpected),
          visionOnePublished: Boolean(summary.consoleExpected),
        };
      }
    } catch (error) {
      state.scannerResult = { error: error.message };
    } finally {
      state.scannerBusy = false;
      renderScanner();
      q('#scanner-result-host')?.scrollIntoView({ behavior:'smooth', block:'nearest' });
    }
  }

  function renderTemplateLibrary() {"""

NEW_UI_COMPLETION_BLOCK = r"""    const live = state.scannerMode === 'live';
    const custom = result?.source === 'custom' || state.scannerSource === 'custom';
    const resultModeLabel = custom
      ? (live ? 'Application-path validation · no tenant record' : 'Custom prompts · demo')
      : (live ? 'Vision One live · TMAS' : 'Demo');
    const completionCopy = custom
      ? (live
        ? 'The exact custom payload used the real model path, but no Vision One tenant record was created.'
        : 'Custom prompt simulated locally · no tenant record.')
      : (live
        ? (result?.consoleExpected
          ? `Official TMAS assessment completed for ${result?.tenantLabel || 'the configured Vision One tenant'}.`
          : 'TMAS completed; verify the full report in the selected Vision One tenant.')
        : 'Completed locally · no tenant record.');"""

NEW_UI_RUN_BLOCK = r"""    const runTitle = state.scannerMode === 'live'
      ? (state.scannerSource === 'custom' ? 'Application-path validation' : 'Vision One live')
      : 'Demo';
    const runCopy = state.scannerSource === 'custom'
      ? (state.scannerMode === 'live'
        ? 'Runs the exact message sequence through the real model path. No tenant record is created; use the exported YAML for a TMAS tenant scan.'
        : 'Simulates the selected custom payload locally · no tenant record.')
      : (state.scannerMode === 'live'
        ? 'Runs the official TMAS campaign and publishes the report to the configured Vision One tenant.'
        : 'Runs locally · no tenant record.');"""

NEW_TEST = r"""
def test_rev119_ui_uses_official_tmas_job_api() -> None:
    script = (
        Path(__file__).parents[1]
        / "app"
        / "static"
        / "bam-suite-v99.js"
    ).read_text(encoding="utf-8")

    assert "/api/scanner/jobs" in script
    assert "/api/scanner/live" not in script
    assert "Vision One live · TMAS" in script
"""


class MigrationError(RuntimeError):
    pass


def run(
    args: Sequence[str],
    *,
    cwd: Path,
    check: bool = True,
    capture: bool = False,
) -> subprocess.CompletedProcess[str]:
    print("+", " ".join(str(item) for item in args))
    return subprocess.run(
        list(args),
        cwd=cwd,
        check=check,
        text=True,
        capture_output=capture,
    )


def git(repo: Path, *args: str, capture: bool = True) -> str:
    result = run(("git", *args), cwd=repo, capture=capture)
    return result.stdout.strip() if capture else ""


def require_repo(repo: Path) -> None:
    if not (repo / ".git").exists():
        raise MigrationError(f"Not a Git repository: {repo}")
    for relative in (MAIN_PATH, SCANNER_UI_PATH, BASE_UI_PATH, INDEX_PATH, TEST_PATH):
        if not (repo / relative).is_file():
            raise MigrationError(f"Required file is missing: {relative}")


def replace_exact(
    text: str,
    old: str,
    new: str,
    *,
    label: str,
    expected: int = 1,
) -> str:
    count = text.count(old)
    if count != expected:
        raise MigrationError(
            f"{label}: expected {expected} occurrence(s), found {count}"
        )
    return text.replace(old, new)


def regex_replace_once(
    text: str,
    pattern: re.Pattern[str],
    replacement: str,
    *,
    label: str,
) -> str:
    updated, count = pattern.subn(replacement, text, count=1)
    if count != 1:
        raise MigrationError(f"{label}: expected one matching block, found {count}")
    return updated


def backup_files(repo: Path, paths: Iterable[Path]) -> Path:
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d-%H%M%S")
    backup_root = Path.home() / f"tfbank-local-archive-{stamp}" / "rev119"
    for relative in paths:
        source = repo / relative
        if not source.exists():
            continue
        destination = backup_root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    print(f"Backup: {backup_root}")
    return backup_root


def write_if_changed(path: Path, text: str) -> bool:
    current = path.read_text(encoding="utf-8")
    if current == text:
        return False
    path.write_text(text, encoding="utf-8")
    print(f"UPDATED: {path}")
    return True


def patch_main(repo: Path) -> None:
    path = repo / MAIN_PATH
    text = path.read_text(encoding="utf-8")

    if REV119_MARKER not in text:
        text = regex_replace_once(
            text,
            LEGACY_MAIN_PATTERN,
            (
                "\n# TF_BANK_REV119_LEGACY_SCANNER_REMOVED\n"
                "# Built-in live scans now use the asynchronous TMAS job API.\n"
            ),
            label="remove legacy /api/scanner/live implementation",
        )

        old_comment = (
            "# BAM_BANK_UI_REVISION_V31\n"
            "# Real TMAS AI Scanner jobs. The legacy /api/scanner/live endpoint remains\n"
            "# available for compatibility, but the v31 UI no longer presents it as a\n"
            "# Trend Vision One live scan because it only validates the endpoint directly.\n"
        )
        new_comment = (
            f"# {REV119_MARKER}\n"
            "# Real TMAS AI Scanner jobs. Built-in live UI runs through /api/scanner/jobs.\n"
            "# Custom prompt live validation remains an application-path test and does not\n"
            "# create a Vision One tenant record.\n"
        )
        text = replace_exact(
            text,
            old_comment,
            new_comment,
            label="replace legacy scanner comment",
        )

    if '"/api/scanner/live"' in text or "'/api/scanner/live'" in text:
        raise MigrationError("app/main.py still contains the legacy scanner route")

    write_if_changed(path, text)


def patch_scanner_ui(repo: Path) -> None:
    path = repo / SCANNER_UI_PATH
    text = path.read_text(encoding="utf-8")

    text = replace_exact(
        text,
        "const VERSION = '118.0.0';",
        f"const VERSION = '{RELEASE_VERSION}';",
        label="bump scanner UI version",
    ) if "const VERSION = '118.0.0';" in text else text

    if "Vision One live · TMAS" not in text:
        old_completion = r"""    const live = state.scannerMode === 'live';
    const custom = result?.source === 'custom' || state.scannerSource === 'custom';
    const completionCopy = custom
      ? (live ? 'Exact custom payload validated through the real model path.' : 'Custom prompt simulated locally · no tenant record.')
      : (live ? 'Completed through the live integration.' : 'Completed locally · no tenant record.');"""
        text = replace_exact(
            text,
            old_completion,
            NEW_UI_COMPLETION_BLOCK,
            label="replace scanner completion wording",
        )
        text = replace_exact(
            text,
            "<div><span>${custom ? 'Custom prompts · custom/1.0' : live ? 'Live validation' : 'Demo'}</span>",
            "<div><span>${resultModeLabel}</span>",
            label="replace scanner result mode label",
        )

    if "Runs the official TMAS campaign" not in text:
        old_run_block = r"""    const runTitle = state.scannerMode === 'live' ? 'Live validation' : 'Demo';
    const runCopy = state.scannerSource === 'custom'
      ? (state.scannerMode === 'live'
        ? 'Runs the exact message sequence through the configured real model path. Download YAML for a TMAS tenant scan.'
        : 'Simulates the selected custom payload locally · no tenant record.')
      : (state.scannerMode === 'live'
        ? 'Uses the configured live integration.'
        : 'Runs locally · no tenant record.');"""
        text = replace_exact(
            text,
            old_run_block,
            NEW_UI_RUN_BLOCK,
            label="replace scanner run wording",
        )
        text = replace_exact(
            text,
            ": (state.scannerMode === 'live' ? 'Run live assessment' : 'Run demo');",
            ": (state.scannerMode === 'live' ? 'Run Vision One assessment' : 'Run demo');",
            label="replace live scanner button",
        )
        text = replace_exact(
            text,
            '<button class="${state.scannerMode === \'live\' ? \'active\' : \'\'}" data-scanner-mode="live" type="button"><strong>Live validation</strong><small>Real model path</small></button>',
            '<button class="${state.scannerMode === \'live\' ? \'active\' : \'\'}" data-scanner-mode="live" type="button"><strong>Live</strong><small>${state.scannerSource === \'custom\' ? \'Real model path · no tenant record\' : \'TMAS tenant report\'}</small></button>',
            label="replace live mode card",
        )
        text = replace_exact(
            text,
            "${state.scannerBusy ? `<div class=\"inspection-progress\"><span></span><div><strong>Assessment running</strong><small>Live runs may take several minutes.</small></div></div>` : scannerResultMarkup(state.scannerResult)}",
            "${state.scannerBusy ? `<div class=\"inspection-progress\"><span></span><div><strong>Assessment running</strong><small>${state.scannerSource === 'custom' ? 'Application-path validation in progress.' : 'TMAS is running and will publish to Vision One.'}</small></div></div>` : scannerResultMarkup(state.scannerResult)}",
            label="replace scanner progress copy",
        )

    if "/api/scanner/live" in text or "officialTmas = false;" not in text:
        text = regex_replace_once(
            text,
            RUN_SCANNER_PATTERN,
            NEW_RUN_SCANNER_FUNCTION,
            label="replace scanner execution function",
        )

    if "/api/scanner/live" in text:
        raise MigrationError("UI still references the legacy /api/scanner/live route")
    if "/api/scanner/jobs" not in text:
        raise MigrationError("UI does not reference the official TMAS job API")

    write_if_changed(path, text)


def patch_base_ui(repo: Path) -> None:
    path = repo / BASE_UI_PATH
    text = path.read_text(encoding="utf-8")

    legacy = (
        "  const endpoint = mode === 'live'\n"
        "    ? '/api/scanner/live'\n"
        "    : '/api/scanner/simulate';"
    )
    safe = (
        "  if (mode === 'live') {\n"
        "    toast(\n"
        "      'Official TMAS workflow is initializing. ' +\n"
        "      'Retry the assessment.'\n"
        "    );\n"
        "    return;\n"
        "  }\n"
        "  const endpoint = '/api/scanner/simulate';"
    )

    if legacy in text:
        text = text.replace(legacy, safe, 1)

    if "/api/scanner/live" in text:
        raise MigrationError(
            "Base UI still references /api/scanner/live"
        )
    if "/api/scanner/jobs" not in text:
        raise MigrationError(
            "Base UI does not contain the official TMAS job flow"
        )

    write_if_changed(path, text)

def patch_tests(repo: Path) -> None:
    path = repo / TEST_PATH
    text = path.read_text(encoding="utf-8")
    block = re.compile(
        r"(?:def test_live_scanner_executes_guard_path|"
        r"def test_rev119_ui_uses_official_tmas_job_api)"
        r"\(\) -> None:\n.*?"
        r"(?=\n\ndef test_client_context_shape\(\) -> None:)",
        flags=re.S,
    )
    replacement = (
        "def test_rev119_ui_uses_official_tmas_job_api() -> None:\n"
        "    static_dir = Path(__file__).parents[1] / 'app' / 'static'\n"
        "    suite_script = (static_dir / 'bam-suite-v99.js').read_text(\n"
        "        encoding='utf-8'\n"
        "    )\n"
        "    base_script = (static_dir / 'app.js').read_text(\n"
        "        encoding='utf-8'\n"
        "    )\n\n"
        "    for script in (suite_script, base_script):\n"
        "        assert '/api/scanner/jobs' in script\n"
        "        assert '/api/scanner/live' not in script\n\n"
        "    assert 'Vision One live · TMAS' in suite_script"
    )
    text, count = block.subn(replacement, text, count=1)
    if count != 1:
        raise MigrationError(
            "Scanner regression-test block was not found"
        )
    write_if_changed(path, text)

def bump_versions(repo: Path) -> None:
    index_path = repo / INDEX_PATH
    index = index_path.read_text(encoding="utf-8")
    index = index.replace(
        "/static/bam-suite-v99.js?v=118.0.0",
        f"/static/bam-suite-v99.js?v={RELEASE_VERSION}",
    )
    index = re.sub(
        r'/static/app\.js\?v=[^"\']+',
        f"/static/app.js?v={RELEASE_VERSION}",
        index,
        count=1,
    )
    write_if_changed(index_path, index)

    for relative in VERSIONED_TEXT_FILES:
        path = repo / relative
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        updated = text.replace("118.0.0", RELEASE_VERSION)
        updated = updated.replace(
            "TF Bank Rev 118 Deployment",
            "TF Bank Rev 119 Deployment",
        )
        write_if_changed(path, updated)


def clean_obsolete_patch_files(repo: Path) -> list[Path]:
    removed: list[Path] = []
    current_script = Path(__file__).resolve()
    for pattern in OBSOLETE_PATCH_PATTERNS:
        for path in sorted(repo.glob(pattern)):
            if not path.is_file():
                continue
            if path.resolve() == current_script:
                continue
            path.unlink()
            removed.append(path.relative_to(repo))
            print(f"REMOVED obsolete patch artifact: {path.relative_to(repo)}")
    return removed


def validate_source(repo: Path) -> None:
    main_text = (repo / MAIN_PATH).read_text(encoding="utf-8")
    ui_text = (repo / SCANNER_UI_PATH).read_text(encoding="utf-8")
    base_ui_text = (repo / BASE_UI_PATH).read_text(encoding="utf-8")
    test_text = (repo / TEST_PATH).read_text(encoding="utf-8")

    required = {
        "main TMAS job API": '@app.post("/api/scanner/jobs")' in main_text,
        "legacy backend removed": "/api/scanner/live" not in main_text,
        "UI job creation": "'/api/scanner/jobs'" in ui_text,
        "UI job polling": "/api/scanner/jobs/${encodeURIComponent(jobId)}" in ui_text,
        "legacy suite UI removed": "/api/scanner/live" not in ui_text,
        "base UI job flow": "/api/scanner/jobs" in base_ui_text,
        "legacy base UI removed": "/api/scanner/live" not in base_ui_text,
        "truthful live label": "Vision One live · TMAS" in ui_text,
        "custom no-record label": "Application-path validation · no tenant record" in ui_text,
        "Rev119 regression test": "test_rev119_ui_uses_official_tmas_job_api" in test_text,
    }
    failures = [name for name, ok in required.items() if not ok]
    if failures:
        raise MigrationError("Validation failed: " + ", ".join(failures))

    py_files = [str(path.relative_to(repo)) for path in sorted((repo / "app").glob("*.py"))]
    run((sys.executable, "-m", "py_compile", *py_files), cwd=repo)

    if shutil.which("node"):
        run(("node", "--check", str(SCANNER_UI_PATH)), cwd=repo)
        run(("node", "--check", str(BASE_UI_PATH)), cwd=repo)
    else:
        print("SKIP: node is not installed; JavaScript syntax check unavailable")

    if importlib.util.find_spec("pytest") is not None:
        run((sys.executable, "-m", "pytest", "-q"), cwd=repo)
    else:
        print("SKIP: pytest is not installed on the host")

    git(repo, "diff", "--check", capture=False)
    print("PASS: source validation completed")


def changed_paths(repo: Path) -> list[str]:
    result = run(
        (
            "git",
            "status",
            "--porcelain=v1",
            "--untracked-files=all",
        ),
        cwd=repo,
        capture=True,
    )
    output = result.stdout.rstrip("\n")
    paths: list[str] = []
    for line in output.splitlines():
        if not line:
            continue
        if len(line) < 4:
            raise MigrationError(
                f"Unexpected Git status entry: {line!r}"
            )
        raw = line[3:]
        if " -> " in raw:
            raw = raw.split(" -> ", 1)[1]
        paths.append(raw)
    return paths

def validate_change_scope(repo: Path) -> list[str]:
    paths = changed_paths(repo)
    unexpected = []
    for path in paths:
        if path in ALLOWED_CHANGED_PATHS:
            continue
        if path.startswith(ALLOWED_DELETED_PREFIXES):
            continue
        unexpected.append(path)
    if unexpected:
        raise MigrationError(
            "Unexpected working-tree changes: " + ", ".join(unexpected)
        )
    return paths


def ensure_feature_branch(repo: Path, branch: str) -> str:
    current = git(repo, "branch", "--show-current")
    if current == branch:
        return current
    if current in {"main", "bam-banking-ui"}:
        existing = subprocess.run(
            ("git", "show-ref", "--verify", "--quiet", f"refs/heads/{branch}"),
            cwd=repo,
            check=False,
        ).returncode == 0
        if existing:
            git(repo, "switch", branch, capture=False)
        else:
            git(repo, "switch", "-c", branch, capture=False)
        return branch
    raise MigrationError(
        f"Refusing to commit from unexpected branch {current!r}; "
        f"use {branch!r}"
    )


def commit_and_optionally_push(
    repo: Path,
    *,
    branch: str,
    push: bool,
) -> None:
    ensure_feature_branch(repo, branch)
    paths = validate_change_scope(repo)
    if not paths:
        print("No source changes to commit")
        return

    git(repo, "add", "--", *paths, capture=False)
    git(repo, "diff", "--cached", "--check", capture=False)
    git(repo, "commit", "-m", COMMIT_MESSAGE, capture=False)

    if push:
        git(repo, "push", "-u", "origin", branch, capture=False)
        print(f"PASS: pushed feature branch {branch}")


def docker(*args: str, cwd: Path, capture: bool = False) -> str:
    result = run(("docker", *args), cwd=cwd, capture=capture)
    return result.stdout.strip() if capture else ""


def wait_for_http(port: int, timeout_seconds: int = 120) -> None:
    url = f"http://127.0.0.1:{port}/api/health"
    deadline = time.monotonic() + timeout_seconds
    last_error = ""
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=3) as response:
                body = response.read().decode("utf-8", errors="replace")
                if response.status == 200 and '"status":"ok"' in body.replace(" ", ""):
                    print(f"PASS: health check succeeded on port {port}")
                    return
        except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
            last_error = str(exc)
        time.sleep(2)
    raise MigrationError(
        f"Health check failed on port {port}: {last_error or 'timeout'}"
    )


def request_json(
    url: str,
    *,
    method: str = "GET",
    payload: dict | None = None,
    timeout: int = 15,
) -> dict:
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(
        url,
        data=data,
        headers=headers,
        method=method,
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise MigrationError(
            f"HTTP {exc.code} from {url}: {detail[:800]}"
        ) from exc
    except urllib.error.URLError as exc:
        raise MigrationError(f"Request failed for {url}: {exc}") from exc
    try:
        parsed = json.loads(body)
    except ValueError as exc:
        raise MigrationError(f"Non-JSON response from {url}") from exc
    if not isinstance(parsed, dict):
        raise MigrationError(f"Unexpected JSON shape from {url}")
    return parsed


def smoke_official_tmas(port: int, timeout_seconds: int = 660) -> dict:
    base = f"http://127.0.0.1:{port}"
    status = request_json(f"{base}/api/scanner/tmas/status")
    required = {
        "tmasInstalled": status.get("tmasInstalled"),
        "visionOneKeyConfigured": status.get("visionOneKeyConfigured"),
        "defaultTenantReady": status.get("defaultTenantReady"),
        "liveReady": status.get("liveReady"),
    }
    missing = [name for name, value in required.items() if not value]
    if missing:
        raise MigrationError(
            "Official TMAS smoke test is not ready: " + ", ".join(missing)
        )

    created = request_json(
        f"{base}/api/scanner/jobs",
        method="POST",
        payload={
            "mode": "live",
            "target": "vulnerable",
            "objectives": ["prompt-injection"],
            "techniques": ["None"],
            "modifiers": ["None"],
            "model_id": "visionone-bank-demo",
            "tenant_mode": "default",
        },
        timeout=30,
    )
    job_id = str(created.get("jobId") or "")
    if not job_id:
        raise MigrationError("Official TMAS smoke test did not return a job ID")

    print(f"TMAS smoke job: {job_id}")
    deadline = time.monotonic() + timeout_seconds
    job: dict = {}
    while time.monotonic() < deadline:
        job = request_json(f"{base}/api/scanner/jobs/{job_id}")
        state = str(job.get("status") or "")
        stage = str(job.get("stage") or "")
        print(f"TMAS smoke status={state} stage={stage}")
        if state in {"completed", "failed"}:
            break
        time.sleep(5)

    if job.get("status") != "completed":
        raise MigrationError(
            "Official TMAS smoke test failed: "
            + str(job.get("error") or job.get("failure") or "timeout")
        )

    result = job.get("result") if isinstance(job.get("result"), dict) else {}
    if not result.get("consoleExpected"):
        raise MigrationError(
            "TMAS completed but did not report consoleExpected=true"
        )

    print(
        "PASS: official TMAS smoke completed; "
        f"tenantMode={job.get('tenantMode')} "
        f"tenantRegion={job.get('tenantRegion')} "
        f"jobId={job_id}"
    )
    return job


def validate_env_file(path: Path) -> None:
    if not path.is_file():
        raise MigrationError(f"Environment file not found: {path}")
    mode = stat.S_IMODE(path.stat().st_mode)
    if mode & 0o077:
        raise MigrationError(
            f"Environment file must be mode 600 or 400, got {oct(mode)}: {path}"
        )


def run_container(
    repo: Path,
    *,
    name: str,
    image: str,
    env_file: Path,
    port: int,
    volume: str,
) -> None:
    docker(
        "run",
        "-d",
        "--name",
        name,
        "--restart",
        "unless-stopped",
        "--env-file",
        str(env_file),
        "-p",
        f"{port}:8080",
        "-v",
        f"{volume}:/data",
        "--read-only",
        "--tmpfs",
        "/tmp:rw,nosuid,nodev,noexec,size=160m,mode=1777",
        "--security-opt",
        "no-new-privileges:true",
        "--user",
        "10001:10001",
        image,
        cwd=repo,
    )


def deploy_rc(
    repo: Path,
    *,
    image: str,
    env_file: Path,
    target_port: int,
    verify_port: int,
    volume: str,
    new_container: str,
    current_container: str,
) -> None:
    if target_port == 8081 or verify_port == 8081:
        raise MigrationError("Production port 8081 is forbidden")
    if target_port == verify_port:
        raise MigrationError("Target and verification ports must differ")
    if not shutil.which("docker"):
        raise MigrationError("Docker is not installed")

    validate_env_file(env_file)
    docker("version", cwd=repo)
    docker("build", "--progress=plain", "--tag", image, ".", cwd=repo)

    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d%H%M%S")
    canary_name = f"{new_container}-canary-{stamp}"
    canary_volume = f"{new_container}-canary-data-{stamp}"
    rollback_name = f"{current_container}-rollback-{stamp}"

    docker("volume", "create", canary_volume, cwd=repo)
    try:
        run_container(
            repo,
            name=canary_name,
            image=image,
            env_file=env_file,
            port=verify_port,
            volume=canary_volume,
        )
        wait_for_http(verify_port)
    finally:
        subprocess.run(
            ("docker", "rm", "-f", canary_name),
            cwd=repo,
            check=False,
            text=True,
        )
        subprocess.run(
            ("docker", "volume", "rm", canary_volume),
            cwd=repo,
            check=False,
            text=True,
        )

    existing = subprocess.run(
        ("docker", "inspect", current_container),
        cwd=repo,
        check=False,
        text=True,
        capture_output=True,
    ).returncode == 0
    if not existing:
        raise MigrationError(
            f"Expected current RC container not found: {current_container}"
        )

    new_exists = subprocess.run(
        ("docker", "inspect", new_container),
        cwd=repo,
        check=False,
        text=True,
        capture_output=True,
    ).returncode == 0
    if new_exists:
        raise MigrationError(f"New container name already exists: {new_container}")

    docker("stop", current_container, cwd=repo)
    docker("rename", current_container, rollback_name, cwd=repo)

    try:
        run_container(
            repo,
            name=new_container,
            image=image,
            env_file=env_file,
            port=target_port,
            volume=volume,
        )
        wait_for_http(target_port)
    except Exception:
        subprocess.run(
            ("docker", "rm", "-f", new_container),
            cwd=repo,
            check=False,
            text=True,
        )
        docker("rename", rollback_name, current_container, cwd=repo)
        docker("start", current_container, cwd=repo)
        raise

    smoke_official_tmas(target_port)

    print(f"PASS: Rev 119 RC is running on port {target_port}")
    print(f"Rollback container retained (stopped): {rollback_name}")
    print("Production port 8081 was not touched")


def show_status(repo: Path) -> None:
    main_text = (repo / MAIN_PATH).read_text(encoding="utf-8")
    ui_text = (repo / SCANNER_UI_PATH).read_text(encoding="utf-8")
    base_ui_text = (repo / BASE_UI_PATH).read_text(encoding="utf-8")
    print(
        json.dumps(
            {
                "releaseVersion": RELEASE_VERSION,
                "backendOfficialJobApi": '@app.post("/api/scanner/jobs")' in main_text,
                "legacyBackendRoutePresent": "/api/scanner/live" in main_text,
                "uiUsesJobApi": (
                    "/api/scanner/jobs" in ui_text
                    and "/api/scanner/jobs" in base_ui_text
                ),
                "legacyUiRoutePresent": (
                    "/api/scanner/live" in ui_text
                    or "/api/scanner/live" in base_ui_text
                ),
                "rev119Marker": REV119_MARKER in main_text,
                "gitBranch": git(repo, "branch", "--show-current"),
                "workingTreeClean": not bool(git(repo, "status", "--porcelain")),
            },
            indent=2,
        )
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Apply and validate the TF Bank Rev 119 official TMAS scanner migration."
    )
    parser.add_argument("action", choices=("check", "apply"))
    parser.add_argument("--repo", default=".", help="Repository root")
    parser.add_argument("--branch", default=FEATURE_BRANCH)
    parser.add_argument("--commit", action="store_true")
    parser.add_argument("--push", action="store_true")
    parser.add_argument("--deploy-rc", action="store_true")
    parser.add_argument("--image", default="tfbank-demo:119.0.0-rc1")
    parser.add_argument(
        "--env-file",
        default=str(Path.home() / "tfbank-secrets" / "backup.env"),
    )
    parser.add_argument("--target-port", type=int, default=18081)
    parser.add_argument("--verify-port", type=int, default=18082)
    parser.add_argument("--volume", default="tfbank-rev118-rc-data")
    parser.add_argument("--new-container", default="tfbank-rev119-rc1")
    parser.add_argument("--current-container", default="tfbank-rev118-rc3")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo = Path(args.repo).expanduser().resolve()
    require_repo(repo)

    if args.push and not args.commit:
        raise MigrationError("--push requires --commit")

    if args.action == "check":
        show_status(repo)
        return 0

    files_to_backup = [
        MAIN_PATH,
        SCANNER_UI_PATH,
        BASE_UI_PATH,
        INDEX_PATH,
        TEST_PATH,
        *VERSIONED_TEXT_FILES,
    ]
    backup_files(repo, files_to_backup)

    patch_main(repo)
    patch_scanner_ui(repo)
    patch_base_ui(repo)
    patch_tests(repo)
    bump_versions(repo)
    clean_obsolete_patch_files(repo)
    validate_source(repo)
    validate_change_scope(repo)

    if args.deploy_rc:
        deploy_rc(
            repo,
            image=args.image,
            env_file=Path(args.env_file).expanduser().resolve(),
            target_port=args.target_port,
            verify_port=args.verify_port,
            volume=args.volume,
            new_container=args.new_container,
            current_container=args.current_container,
        )

    if args.commit:
        commit_and_optionally_push(
            repo,
            branch=args.branch,
            push=args.push,
        )

    show_status(repo)
    print("PASS: TF Bank Rev 119 migration completed")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except MigrationError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
