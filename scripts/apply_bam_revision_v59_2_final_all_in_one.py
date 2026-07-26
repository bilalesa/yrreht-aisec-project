#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

VERSION = "2.2.5"
BRANCH = "bam-banking-ui"
IMAGE = "bambank-demo:v59-2"
CONTAINER = "bambank-demo-v59-2"
PORT = "8081"

ALLOWED_DIRTY_FILES = {
    "app/main.py",
    "app/vision_one_live.py",
    "app/static/index.html",
    "app/static/app.js",
    "app/static/styles.css",
}

V591_JS = '/* BAM_BANK_UI_REVISION_V59_1 */\n(() => {\n  if (window.__bamRevisionV591) return;\n  window.__bamRevisionV591 = true;\n\n  const hiddenPhrases = new Set([\n    \'file security ready\',\n    \'protected by file security\',\n    \'file security scanning enabled\',\n    \'dilindungi file security\',\n    \'pemindaian file security aktif\'\n  ]);\n\n  function normalize(value) {\n    return String(value || \'\')\n      .replace(/\\s+/g, \' \')\n      .trim()\n      .toLowerCase();\n  }\n\n  function hideFileSecurityLabels() {\n    document.querySelectorAll(\n      \'.file-security-badge,\' +\n      \'.file-security-ready,\' +\n      \'[data-file-security-ready]\'\n    ).forEach(node => {\n      node.classList.add(\'bam-file-ready-hidden-v59-1\');\n      node.setAttribute(\'aria-hidden\', \'true\');\n    });\n\n    document.querySelectorAll(\n      \'.quick-actions button em,\' +\n      \'.quick-actions button small,\' +\n      \'.quick-actions button span,\' +\n      \'.quick-actions button b\'\n    ).forEach(node => {\n      if (!hiddenPhrases.has(normalize(node.textContent))) return;\n      node.classList.add(\'bam-file-ready-hidden-v59-1\');\n      node.setAttribute(\'aria-hidden\', \'true\');\n    });\n  }\n\n  function scheduleLabelCleanup() {\n    [0, 120, 450, 1100].forEach(delay => {\n      window.setTimeout(hideFileSecurityLabels, delay);\n    });\n  }\n\n  document.querySelector(\'#language\')\n    ?.addEventListener(\'change\', scheduleLabelCleanup);\n\n  document.querySelector(\'#settings-language\')\n    ?.addEventListener(\'change\', scheduleLabelCleanup);\n\n  document.addEventListener(\'click\', event => {\n    if (\n      event.target instanceof Element &&\n      event.target.closest(\n        \'[data-open="file"],\' +\n        \'.quick-actions,\' +\n        \'[data-close="security-modal"]\'\n      )\n    ) {\n      scheduleLabelCleanup();\n    }\n  }, true);\n\n  scheduleLabelCleanup();\n})();\n'
V591_CSS = '/* BAM_BANK_UI_REVISION_V59_1 */\n.file-security-badge,\n.file-security-ready,\n[data-file-security-ready],\n.bam-file-ready-hidden-v59-1 {\n  display: none !important;\n  pointer-events: none !important;\n}\n'
V55_REPLACEMENT = "  // Revision 59.1: use finite result refreshes instead of a\n  // document-wide characterData observer.\n  function scheduleV55ResultRefresh() {\n    [0, 180, 550, 1200, 2500, 5000].forEach(delay => {\n      window.setTimeout(install, delay);\n    });\n  }\n\n  document.addEventListener('click', event => {\n    if (\n      event.target instanceof Element &&\n      event.target.closest('#cp-run')\n    ) {\n      scheduleV55ResultRefresh();\n    }\n  }, true);"
V57_REPLACEMENT = '  // Revision 59.1: controls are installed once and retried by\n  // the existing finite setTimeout calls below.'
V58_REPLACEMENT = '  // Revision 59.1: avoid observing class and disabled changes\n  // that are also written by install().'


def fail(message: str) -> None:
    raise SystemExit(f"ERROR: {message}")


def run(
    command: list[str],
    cwd: Path | None = None,
    *,
    check: bool = True,
    capture: bool = False,
) -> subprocess.CompletedProcess:
    print("+", " ".join(command))
    result = subprocess.run(
        command,
        cwd=str(cwd) if cwd else None,
        text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
    )

    if check and result.returncode != 0:
        if capture and result.stdout:
            print(result.stdout)
        if capture and result.stderr:
            print(result.stderr, file=sys.stderr)
        fail(f"Command failed with exit code {result.returncode}")

    return result


def require_command(name: str) -> None:
    if not shutil.which(name):
        fail(f"{name} is not installed")


def section_bounds(
    text: str,
    marker: str,
    next_marker: str | None,
) -> tuple[int, int]:
    start = text.find(marker)
    if start < 0:
        fail(f"Required JavaScript marker was not found: {marker}")

    if next_marker:
        end = text.find(next_marker, start + len(marker))
        if end < 0:
            end = len(text)
    else:
        end = len(text)

    return start, end


def remove_section_observer(
    text: str,
    marker: str,
    next_marker: str | None,
    replacement: str,
    label: str,
) -> str:
    start, end = section_bounds(text, marker, next_marker)
    section = text[start:end]

    if "new MutationObserver" not in section:
        print(f"{label}: observer is already removed")
        return text

    pattern = re.compile(
        r"\n\s*const\s+observer\s*=\s*new\s+MutationObserver"
        r"\([\s\S]*?"
        r"\n\s*observer\.observe\([\s\S]*?\);\s*",
        re.MULTILINE,
    )

    updated, count = pattern.subn(
        "\n" + replacement.strip("\n") + "\n",
        section,
        count=1,
    )

    if count != 1:
        fail(
            f"{label}: unable to remove the existing observer. "
            "The source layout is different from the expected Revision 58 state."
        )

    return text[:start] + updated + text[end:]


def patch_event_loops(js_text: str) -> str:
    js_text = remove_section_observer(
        js_text,
        "/* BAM_BANK_UI_REVISION_V55 */",
        "/* BAM_BANK_UI_REVISION_V57 */",
        V55_REPLACEMENT,
        "Revision 55",
    )

    js_text = remove_section_observer(
        js_text,
        "/* BAM_BANK_UI_REVISION_V57 */",
        "/* BAM_BANK_UI_REVISION_V58 */",
        V57_REPLACEMENT,
        "Revision 57",
    )

    v58_next = (
        "/* BAM_BANK_UI_REVISION_V59_1 */"
        if "/* BAM_BANK_UI_REVISION_V59_1 */" in js_text
        else None
    )

    js_text = remove_section_observer(
        js_text,
        "/* BAM_BANK_UI_REVISION_V58 */",
        v58_next,
        V58_REPLACEMENT,
        "Revision 58",
    )

    return js_text


def patch_sources(root: Path) -> None:
    main = root / "app" / "main.py"
    live = root / "app" / "vision_one_live.py"
    index = root / "app" / "static" / "index.html"
    js = root / "app" / "static" / "app.js"
    css = root / "app" / "static" / "styles.css"

    for path in (main, live, index, js, css):
        if not path.is_file():
            fail(f"Required file not found: {path}")

    main_text = main.read_text(encoding="utf-8")
    main_text = re.sub(
        r'version="[0-9.]+"',
        f'version="{VERSION}"',
        main_text,
        count=1,
    )
    main_text = re.sub(
        r'"version":\s*"[0-9.]+"',
        f'"version": "{VERSION}"',
        main_text,
        count=1,
    )
    main.write_text(main_text, encoding="utf-8")

    index_text = index.read_text(encoding="utf-8")
    for asset in ("styles.css", "app.js", "favicon.svg"):
        index_text = re.sub(
            rf"/static/{re.escape(asset)}\?v=[0-9.]+",
            f"/static/{asset}?v={VERSION}",
            index_text,
        )

    if "<!-- BAM_BANK_UI_REVISION_V59_1 -->" not in index_text:
        marker_candidates = (
            "<!-- BAM_BANK_UI_REVISION_V59 -->",
            "<!-- BAM_BANK_UI_REVISION_V58 -->",
            "<!-- BAM_BANK_UI_REVISION_V57 -->",
        )

        inserted = False
        for marker in marker_candidates:
            if marker in index_text:
                index_text = index_text.replace(
                    marker,
                    "<!-- BAM_BANK_UI_REVISION_V59_1 -->\n  " + marker,
                    1,
                )
                inserted = True
                break

        if not inserted:
            index_text = index_text.replace(
                "</body>",
                "  <!-- BAM_BANK_UI_REVISION_V59_1 -->\n</body>",
                1,
            )

    index.write_text(index_text, encoding="utf-8")

    js_text = js.read_text(encoding="utf-8")
    js_text = patch_event_loops(js_text)

    if "/* BAM_BANK_UI_REVISION_V59_1 */" not in js_text:
        js_text = js_text.rstrip() + "\n\n" + V591_JS.strip() + "\n"

    js.write_text(js_text, encoding="utf-8")

    css_text = css.read_text(encoding="utf-8")

    if "/* BAM_BANK_UI_REVISION_V59_1 */" not in css_text:
        css_text = css_text.rstrip() + "\n\n" + V591_CSS.strip() + "\n"

    css.write_text(css_text, encoding="utf-8")


def validate_dirty_state(root: Path) -> None:
    raw_status = run(
        [
            "git",
            "status",
            "--porcelain=v1",
            "--untracked-files=no",
        ],
        cwd=root,
        capture=True,
    ).stdout

    # Do not call .strip() here. A porcelain status line may begin
    # with a space, for example " M app/main.py". Removing that
    # leading space corrupts the first path into "pp/main.py".
    if not raw_status.strip():
        return

    dirty_files: set[str] = set()

    for raw_line in raw_status.splitlines():
        if not raw_line:
            continue

        # Porcelain v1 format is: XY<space>PATH.
        # Preserve leading status characters and remove exactly
        # the three-character prefix.
        if len(raw_line) >= 4 and raw_line[2] == " ":
            path = raw_line[3:]
        else:
            match = re.match(r"^.{2}\\s(.*)$", raw_line)
            if not match:
                fail(
                    "Unable to parse Git status entry safely: "
                    + repr(raw_line)
                )
            path = match.group(1)

        path = path.strip()

        if " -> " in path:
            path = path.split(" -> ", 1)[1]

        dirty_files.add(path)

    unexpected = dirty_files - ALLOWED_DIRTY_FILES

    if unexpected:
        fail(
            "Unexpected tracked changes are present: "
            + ", ".join(sorted(unexpected))
        )

    print(
        "Detected expected source changes from the interrupted revision; "
        "continuing safely."
    )


def validate_sources(root: Path) -> None:
    run(
        [
            sys.executable,
            "-m",
            "py_compile",
            "app/main.py",
            "app/vision_one_live.py",
        ],
        cwd=root,
    )

    run(["git", "diff", "--check"], cwd=root)

    js_path = root / "app" / "static" / "app.js"
    js_text = js_path.read_text(encoding="utf-8")

    for marker, next_marker, label in (
        (
            "/* BAM_BANK_UI_REVISION_V55 */",
            "/* BAM_BANK_UI_REVISION_V57 */",
            "Revision 55",
        ),
        (
            "/* BAM_BANK_UI_REVISION_V57 */",
            "/* BAM_BANK_UI_REVISION_V58 */",
            "Revision 57",
        ),
        (
            "/* BAM_BANK_UI_REVISION_V58 */",
            "/* BAM_BANK_UI_REVISION_V59_1 */",
            "Revision 58",
        ),
    ):
        start, end = section_bounds(js_text, marker, next_marker)
        section = js_text[start:end]
        if "new MutationObserver" in section:
            fail(f"{label} still contains a document observer")

    node = shutil.which("node")
    if node:
        run([node, "--check", "app/static/app.js"], cwd=root)
    else:
        print(
            "Node.js is unavailable locally; "
            "validating JavaScript with node:22-alpine."
        )
        run(
            [
                "docker",
                "run",
                "--rm",
                "-v",
                f"{root / 'app' / 'static'}:/work:ro",
                "node:22-alpine",
                "node",
                "--check",
                "/work/app.js",
            ],
            cwd=root,
        )


def read_health() -> dict | None:
    result = subprocess.run(
        [
            "curl",
            "-fsS",
            f"http://127.0.0.1:{PORT}/api/health",
        ],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )

    if result.returncode != 0:
        return None

    try:
        return json.loads(result.stdout)
    except Exception:
        return None


def deploy(root: Path) -> dict:
    run(
        [
            "docker",
            "build",
            "--no-cache",
            "-t",
            IMAGE,
            ".",
        ],
        cwd=root,
    )

    old_ids = run(
        [
            "docker",
            "ps",
            "-q",
            "--filter",
            f"publish={PORT}",
        ],
        cwd=root,
        capture=True,
    ).stdout.strip().split()

    for container_id in old_ids:
        run(
            ["docker", "rm", "-f", container_id],
            cwd=root,
            check=False,
        )

    for name in (
        "bambank-demo-v56",
        "bambank-demo-v57",
        "bambank-demo-v58",
        "bambank-demo-v59",
        "bambank-demo-restored",
        "visionone-bank-demo-test",
        CONTAINER,
    ):
        run(
            ["docker", "rm", "-f", name],
            cwd=root,
            check=False,
        )

    run(
        [
            "docker",
            "volume",
            "create",
            "bambank-demo-data",
        ],
        cwd=root,
        check=False,
    )

    run(
        [
            "docker",
            "run",
            "-d",
            "--name",
            CONTAINER,
            "--restart",
            "unless-stopped",
            "-p",
            f"{PORT}:8080",
            "--env-file",
            str(root / ".env"),
            "-e",
            "TMAS_BINARY=/usr/local/bin/tmas",
            "-e",
            "TMAS_ENV_FILE=",
            "-e",
            "TMAS_REGION=ap-southeast-1",
            "-e",
            "AI_SCANNER_TARGET_BASE_URL=http://127.0.0.1:8080",
            "-e",
            "AI_SCANNER_RUNTIME_DIR=/tmp/bambank-aiscan",
            "-e",
            "AI_SCANNER_MAX_SECONDS=900",
            "-v",
            "/usr/local/bin/tmas:/usr/local/bin/tmas:ro",
            "-v",
            "bambank-demo-data:/data",
            "--read-only",
            "--tmpfs",
            "/tmp:size=160m,mode=1777",
            "--security-opt",
            "no-new-privileges:true",
            IMAGE,
        ],
        cwd=root,
    )

    health = None

    for _ in range(45):
        health = read_health()
        if health and health.get("version") == VERSION:
            break
        time.sleep(1)

    if not health or health.get("version") != VERSION:
        run(
            [
                "docker",
                "logs",
                "--tail=140",
                CONTAINER,
            ],
            cwd=root,
            check=False,
        )
        fail(
            "Deployment validation failed; "
            f"health={health!r}"
        )

    run(
        [
            "docker",
            "exec",
            CONTAINER,
            "sh",
            "-lc",
            (
                'test -n "$TMAS_API_KEY" '
                '&& echo "TMAS_API_KEY=loaded" '
                "|| exit 1"
            ),
        ],
        cwd=root,
    )

    static_check = subprocess.run(
        [
            "curl",
            "-fsS",
            (
                f"http://127.0.0.1:{PORT}/static/"
                f"app.js?v={VERSION}"
            ),
        ],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    if (
        static_check.returncode != 0
        or "BAM_BANK_UI_REVISION_V59_1"
        not in static_check.stdout
    ):
        fail(
            "The deployed JavaScript does not contain "
            "the Revision 59.1 marker"
        )

    return health


def update_git(root: Path) -> None:
    scripts_dir = root / "scripts"
    scripts_dir.mkdir(exist_ok=True)

    installer_name = (
        "apply_bam_revision_v59_2_final_all_in_one.py"
    )
    installer = scripts_dir / installer_name

    shutil.copy2(
        Path(__file__).resolve(),
        installer,
    )
    installer.chmod(0o755)

    run(
        [
            "git",
            "add",
            "app/main.py",
            "app/vision_one_live.py",
            "app/static/index.html",
            "app/static/app.js",
            "app/static/styles.css",
        ],
        cwd=root,
    )

    run(
        [
            "git",
            "add",
            "-f",
            f"scripts/{installer_name}",
        ],
        cwd=root,
    )

    run(
        [
            "git",
            "diff",
            "--cached",
            "--check",
        ],
        cwd=root,
    )

    changed = (
        subprocess.run(
            [
                "git",
                "diff",
                "--cached",
                "--quiet",
            ],
            cwd=str(root),
        ).returncode
        != 0
    )

    if changed:
        run(
            [
                "git",
                "commit",
                "-m",
                (
                    "Fix BAM Bank UI hang and "
                    "hide file security status"
                ),
            ],
            cwd=root,
        )

    run(
        [
            "git",
            "push",
            "origin",
            BRANCH,
        ],
        cwd=root,
    )

    run(
        [
            "git",
            "branch",
            "--set-upstream-to",
            f"origin/{BRANCH}",
            BRANCH,
        ],
        cwd=root,
    )


def main() -> None:
    root = Path(
        sys.argv[1]
        if len(sys.argv) > 1
        else Path.home() / "visionone-bank-demo"
    ).expanduser().resolve()

    for command in (
        "git",
        "docker",
        "curl",
    ):
        require_command(command)

    if not (root / ".git").is_dir():
        fail(f"Git repository not found: {root}")

    if not (root / ".env").is_file():
        fail(f"Project .env not found: {root / '.env'}")

    if not Path("/usr/local/bin/tmas").is_file():
        fail(
            "TMAS binary not found: "
            "/usr/local/bin/tmas"
        )

    run(
        ["git", "fetch", "origin", "--prune"],
        cwd=root,
    )

    branch = run(
        ["git", "branch", "--show-current"],
        cwd=root,
        capture=True,
    ).stdout.strip()

    if branch != BRANCH:
        fail(
            f"Expected branch {BRANCH}, "
            f"current branch is {branch!r}"
        )

    validate_dirty_state(root)
    patch_sources(root)
    validate_sources(root)
    health = deploy(root)
    update_git(root)

    print()
    print("BAM Bank Revision 59.2 completed.")
    print(f"Version   : {VERSION}")
    print(f"Branch    : {BRANCH}")
    print(f"Container : {CONTAINER}")
    print(f"Health    : {health}")
    print()
    print("Fixed:")
    print(
        "  - Removed the recursive V55, V57, "
        "and V58 DOM observers"
    )
    print(
        "  - Restored normal clicks and "
        "page interaction"
    )
    print(
        '  - Hidden the redundant '
        '"File security ready" badge'
    )


if __name__ == "__main__":
    main()
