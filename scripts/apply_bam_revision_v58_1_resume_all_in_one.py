#!/usr/bin/env python3
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

VERSION = "2.2.2"
BRANCH = "bam-banking-ui"
IMAGE = "bambank-demo:v58"
CONTAINER = "bambank-demo-v58"
PORT = "8081"
ALLOWED_DIRTY_FILES = {
    "app/main.py",
    "app/vision_one_live.py",
    "app/static/index.html",
    "app/static/app.js",
    "app/static/styles.css",
}
JS_PATCH = '/* BAM_BANK_UI_REVISION_V58 */\n(() => {\n  if (window.__bamRevisionV58) return;\n  window.__bamRevisionV58 = true;\n\n  const q = (selector, root = document) => root.querySelector(selector);\n  const qa = (selector, root = document) => [...root.querySelectorAll(selector)];\n  let syncingGuard = false;\n\n  const chatIcon = `\n    <svg viewBox="0 0 48 48" focusable="false">\n      <path class="bam-chat-bubble-v58"\n        d="M10.5 9.5h27a5 5 0 0 1 5 5v16a5 5 0 0 1-5 5H23l-10.5 6v-6.4a5 5 0 0 1-4-4.9V14.5a5 5 0 0 1 5-5Z"/>\n      <circle class="bam-chat-dot-v58 dot-one" cx="18" cy="23" r="2.2"/>\n      <circle class="bam-chat-dot-v58 dot-two" cx="24.5" cy="23" r="2.2"/>\n      <circle class="bam-chat-dot-v58 dot-three" cx="31" cy="23" r="2.2"/>\n      <path class="bam-chat-spark-v58"\n        d="M37 5.2c.45 2.7 2.05 4.3 4.75 4.75-2.7.45-4.3 2.05-4.75 4.75-.45-2.7-2.05-4.3-4.75-4.75C34.95 9.5 36.55 7.9 37 5.2Z"/>\n    </svg>`;\n\n  const guardIcon = `\n    <span class="bam-guard-icon-v58" aria-hidden="true">\n      <svg viewBox="0 0 24 24">\n        <path d="M12 3.2 19 6v5.1c0 4.6-2.9 7.8-7 9.4-4.1-1.6-7-4.8-7-9.4V6l7-2.8Z"/>\n        <path d="m8.8 12 2.1 2.1 4.5-4.7"/>\n      </svg>\n    </span>`;\n\n  function polishLauncher() {\n    const launcher = q(\'#chat-launcher\');\n    if (!launcher) return false;\n\n    if (!launcher.classList.contains(\'bam-chat-launcher-v58\')) {\n      launcher.classList.add(\'bam-chat-launcher-v58\');\n      launcher.setAttribute(\'aria-label\', \'Open BAM Assist\');\n      launcher.setAttribute(\'title\', \'Open BAM Assist\');\n      launcher.innerHTML = `\n        <span class="bam-chat-orb-v58" aria-hidden="true">${chatIcon}</span>\n        <span class="bam-chat-copy-v58">\n          <strong>BAM Assist</strong>\n          <small>Secure AI banking</small>\n        </span>\n        <span class="bam-chat-live-v58"><i></i>Online</span>\n        <i id="launcher-status"></i>`;\n    }\n\n    const avatar = q(\'#chat-panel .assistant-avatar, .assistant-avatar\');\n    if (avatar && !avatar.classList.contains(\'bam-chat-avatar-v58\')) {\n      avatar.classList.add(\'bam-chat-avatar-v58\');\n      avatar.innerHTML = chatIcon;\n    }\n    return true;\n  }\n\n  function findGuardRows() {\n    const rows = new Set();\n\n    const original = q(\'#guard-toggle\');\n    if (original) {\n      const row = original.closest(\n        \'.guard-banner,[class*="runtime"],[class*="control"],section,article,div\'\n      );\n      if (row) rows.add(row);\n    }\n\n    qa(\'strong,h2,h3,h4,span,div\').forEach(title => {\n      if ((title.textContent || \'\').trim() !== \'AI Guard\') return;\n      let row = title.closest(\n        \'[class*="runtime"],[class*="control"],[class*="guard"],section,article,div\'\n      );\n      while (row && !row.querySelector(\'input[type="checkbox"]\')) {\n        row = row.parentElement;\n      }\n      if (row) rows.add(row);\n    });\n\n    return [...rows];\n  }\n\n  function guardInputs() {\n    const inputs = new Set();\n    const original = q(\'#guard-toggle\');\n    if (original) inputs.add(original);\n\n    findGuardRows().forEach(row => {\n      qa(\'input[type="checkbox"]\', row).forEach(input => inputs.add(input));\n    });\n\n    qa(\n      \'input[type="checkbox"][data-runtime-control="guard"],\' +\n      \'input[type="checkbox"][id*="ai-guard"],\' +\n      \'input[type="checkbox"][id*="guard-toggle"]\'\n    ).forEach(input => inputs.add(input));\n\n    return [...inputs];\n  }\n\n  function updateGuardVisuals(enabled) {\n    findGuardRows().forEach(row => {\n      row.classList.add(\'bam-guard-row-v58\');\n      row.classList.toggle(\'is-enabled\', enabled);\n\n      qa(\'small,p\', row).forEach(node => {\n        const text = (node.textContent || \'\').trim().toLowerCase();\n        if (\n          text.includes(\'unprotected demo\') ||\n          text.includes(\'direct model response\') ||\n          text.includes(\'protected by\') ||\n          text.includes(\'runtime enforcement\')\n        ) {\n          node.textContent = enabled\n            ? \'Protected by Trend Vision One AI Guard\'\n            : \'Unprotected demo · direct model response\';\n        }\n      });\n\n      qa(\'.pill,[class*="badge"],[class*="status"]\').forEach(node => {\n        const text = (node.textContent || \'\').trim().toLowerCase();\n        if ([\'baseline\', \'protected\', \'enabled\', \'disabled\'].includes(text)) {\n          node.textContent = enabled ? \'Protected\' : \'Baseline\';\n          node.classList.toggle(\'is-protected\', enabled);\n        }\n      });\n    });\n\n    const label = q(\'#guard-mode-label\');\n    if (label) {\n      label.textContent = enabled\n        ? \'AI Guard protection enabled\'\n        : \'Unprotected demo · direct model response\';\n    }\n  }\n\n  function setGuardState(enabled, source = null) {\n    if (syncingGuard) return;\n    syncingGuard = true;\n\n    try {\n      const inputs = guardInputs();\n      inputs.forEach(input => {\n        input.disabled = false;\n        input.removeAttribute(\'disabled\');\n        input.setAttribute(\'aria-disabled\', \'false\');\n        input.checked = enabled;\n      });\n\n      if (typeof state === \'object\' && state) {\n        state.guardEnabled = enabled;\n      }\n\n      const original = q(\'#guard-toggle\');\n      if (original && source !== original) {\n        original.checked = enabled;\n        original.dispatchEvent(new Event(\'change\', { bubbles: true }));\n      }\n\n      updateGuardVisuals(enabled);\n    } finally {\n      syncingGuard = false;\n    }\n  }\n\n  function installGuard() {\n    const inputs = guardInputs();\n    if (!inputs.length) return false;\n\n    inputs.forEach(input => {\n      input.disabled = false;\n      input.removeAttribute(\'disabled\');\n      input.setAttribute(\'aria-disabled\', \'false\');\n\n      if (input.dataset.bamGuardV58Bound !== \'true\') {\n        input.dataset.bamGuardV58Bound = \'true\';\n        input.addEventListener(\'change\', event => {\n          if (!syncingGuard) {\n            setGuardState(Boolean(event.target.checked), event.target);\n          }\n        });\n      }\n    });\n\n    findGuardRows().forEach(row => {\n      row.classList.add(\'bam-guard-row-v58\');\n      qa(\'.bam-runtime-icon-v55\', row).forEach(icon => icon.remove());\n      if (q(\'.bam-guard-icon-v58\', row)) return;\n\n      const title = qa(\'strong,h2,h3,h4,span,div\', row)\n        .find(node => (node.textContent || \'\').trim() === \'AI Guard\');\n      if (!title) return;\n\n      const host = title.parentElement || title;\n      host.classList.add(\'bam-guard-copy-v58\');\n      host.insertAdjacentHTML(\'afterbegin\', guardIcon);\n    });\n\n    const original = q(\'#guard-toggle\');\n    updateGuardVisuals(original ? Boolean(original.checked) : inputs.some(input => input.checked));\n    return true;\n  }\n\n  function modeIcon(type) {\n    if (type === \'live\') {\n      return `\n        <span class="cp-mode-icon-v58 live" aria-hidden="true">\n          <svg viewBox="0 0 24 24">\n            <path d="M7 17.5h10a4 4 0 0 0 .5-7.97A5.7 5.7 0 0 0 6.65 8.1 4.8 4.8 0 0 0 7 17.5Z"/>\n            <path d="m9.5 13 2 2 3.7-4"/>\n          </svg>\n        </span>`;\n    }\n    return `\n      <span class="cp-mode-icon-v58 demo" aria-hidden="true">\n        <svg viewBox="0 0 24 24"><path d="M8 6.5 17 12l-9 5.5v-11Z"/></svg>\n      </span>`;\n  }\n\n  function polishModes() {\n    const studio = q(\'#cp-studio\');\n    const mode = q(\'#cp-live-mode-v57\');\n    if (!studio || !mode) return false;\n\n    let toolbar = q(\'#cp-execution-toolbar-v58\');\n    if (!toolbar) {\n      toolbar = document.createElement(\'section\');\n      toolbar.id = \'cp-execution-toolbar-v58\';\n      toolbar.className = \'cp-execution-toolbar-v58\';\n      toolbar.innerHTML = `\n        <div class="cp-execution-copy-v58">\n          <span>Execution mode</span>\n          <small>Choose a local preview or an official Vision One assessment.</small>\n        </div>`;\n      q(\':scope > header\', studio)?.insertAdjacentElement(\'afterend\', toolbar);\n    }\n\n    if (mode.parentElement !== toolbar) toolbar.appendChild(mode);\n    mode.classList.add(\'cp-live-mode-v58\');\n\n    const demo = q(\'[data-cp-execution="demo"]\', mode);\n    const live = q(\'[data-cp-execution="live"]\', mode);\n\n    if (demo && demo.dataset.bamModeV58 !== \'true\') {\n      demo.dataset.bamModeV58 = \'true\';\n      demo.innerHTML = `\n        ${modeIcon(\'demo\')}\n        <span><strong>Demo</strong><small>Test in app</small></span>`;\n    }\n\n    if (live && live.dataset.bamModeV58 !== \'true\') {\n      live.dataset.bamModeV58 = \'true\';\n      live.innerHTML = `\n        ${modeIcon(\'live\')}\n        <span><strong>Vision One Live</strong><small>TMAS · hosted judge</small></span>`;\n    }\n\n    const globalMode = q(\'#bam-scanner-mode-v31\');\n    globalMode?.classList.toggle(\n      \'bam-hide-global-mode-v58\',\n      !studio.classList.contains(\'hidden\')\n    );\n    return true;\n  }\n\n  function install() {\n    polishLauncher();\n    installGuard();\n    polishModes();\n  }\n\n  const observer = new MutationObserver(() => {\n    window.requestAnimationFrame(install);\n  });\n\n  observer.observe(document.documentElement, {\n    childList: true,\n    subtree: true,\n    attributes: true,\n    attributeFilter: [\'disabled\', \'class\']\n  });\n\n  document.addEventListener(\'click\', event => {\n    if (event.target.closest(\n      \'#chat-launcher,[data-cp-mode],[data-security-tab="scanner"],#cp-run\'\n    )) {\n      window.setTimeout(install, 0);\n      window.setTimeout(install, 220);\n    }\n  });\n\n  install();\n  [120, 400, 900, 1600].forEach(delay => window.setTimeout(install, delay));\n})();\n'
CSS_PATCH = '/* BAM_BANK_UI_REVISION_V58 */\n\n/* Balanced execution selector */\n#cp-studio > header{padding-right:0!important}\n\n.cp-execution-toolbar-v58{\n  display:flex;align-items:center;justify-content:space-between;gap:20px;\n  margin:16px 0;padding:14px 15px;border:1px solid #dfe6f1;\n  border-radius:14px;background:linear-gradient(135deg,#f8faff,#f2f6fc)\n}\n.cp-execution-copy-v58{min-width:190px}\n.cp-execution-copy-v58>span,.cp-execution-copy-v58>small{display:block}\n.cp-execution-copy-v58>span{color:#273b57;font-size:9px;font-weight:850}\n.cp-execution-copy-v58>small{margin-top:4px;color:#73839a;font-size:7.5px;line-height:1.45}\n\n#cp-live-mode-v57.cp-live-mode-v58{\n  position:static!important;top:auto!important;right:auto!important;\n  width:min(100%,430px)!important;min-width:390px;\n  display:grid!important;grid-template-columns:1fr 1fr;gap:5px!important;\n  margin:0!important;padding:5px!important;border:1px solid #d9e2ef!important;\n  border-radius:13px!important;background:#eaf0f8!important;\n  box-shadow:inset 0 1px 2px rgba(34,56,96,.05)\n}\n#cp-live-mode-v57.cp-live-mode-v58 button{\n  width:100%;min-height:51px!important;display:flex;align-items:center;\n  justify-content:flex-start;gap:10px;padding:8px 11px!important;\n  border:1px solid transparent!important;border-radius:10px!important;\n  background:transparent!important;color:#64758d!important;text-align:left;\n  transition:background .18s ease,border-color .18s ease,\n             box-shadow .18s ease,transform .18s ease\n}\n#cp-live-mode-v57.cp-live-mode-v58 button:hover{\n  transform:translateY(-1px);background:rgba(255,255,255,.62)!important\n}\n#cp-live-mode-v57.cp-live-mode-v58 button.active{\n  border-color:#c9d9f4!important;background:#fff!important;color:#213650!important;\n  box-shadow:0 6px 17px rgba(37,67,120,.11)!important\n}\n#cp-live-mode-v57.cp-live-mode-v58 button>span:last-child{\n  min-width:0;display:flex;flex-direction:column;gap:3px\n}\n#cp-live-mode-v57.cp-live-mode-v58 button strong{\n  color:inherit;font-size:8.5px;font-weight:850;white-space:nowrap\n}\n#cp-live-mode-v57.cp-live-mode-v58 button small{\n  color:#7b8ba0;font-size:6.8px;font-weight:650;white-space:nowrap\n}\n#cp-live-mode-v57.cp-live-mode-v58 button>i{display:none!important}\n\n.cp-mode-icon-v58{\n  width:31px;height:31px;display:grid;place-items:center;flex:none;\n  border-radius:9px;border:1px solid #d7e1ef;background:#f5f8fc;color:#5c718d\n}\n.cp-mode-icon-v58.live{border-color:#cfe8dd;background:#eaf8f1;color:#168052}\n.cp-mode-icon-v58 svg{\n  width:18px;height:18px;fill:none;stroke:currentColor;stroke-width:1.8;\n  stroke-linecap:round;stroke-linejoin:round\n}\n.cp-mode-icon-v58.demo svg path{fill:currentColor;stroke:none}\n.bam-hide-global-mode-v58{display:none!important}\n\n/* Animated, clearly recognizable chatbot launcher */\n#chat-launcher.bam-chat-launcher-v58{\n  isolation:isolate;right:24px!important;bottom:24px!important;width:auto!important;\n  min-width:204px!important;height:64px!important;display:flex!important;\n  align-items:center!important;justify-content:flex-start!important;gap:11px!important;\n  padding:7px 13px 7px 8px!important;overflow:visible!important;\n  border:1px solid rgba(255,255,255,.42)!important;border-radius:20px!important;\n  background:\n    radial-gradient(circle at 18% -20%,rgba(111,232,255,.78),transparent 39%),\n    linear-gradient(135deg,#0d2d78 0%,#145bd7 54%,#188dcc 100%)!important;\n  color:#fff!important;\n  box-shadow:0 18px 44px rgba(14,55,139,.38),\n             inset 0 1px 0 rgba(255,255,255,.25)!important;\n  animation:bam-launcher-float-v58 4s ease-in-out infinite;\n  transition:transform .2s ease,box-shadow .2s ease,filter .2s ease!important\n}\n#chat-launcher.bam-chat-launcher-v58::before{\n  content:"";position:absolute;z-index:-1;inset:-5px;border-radius:24px;\n  border:1px solid rgba(64,185,255,.28);opacity:.72;\n  animation:bam-launcher-ring-v58 2.8s ease-out infinite\n}\n#chat-launcher.bam-chat-launcher-v58::after{\n  content:"";position:absolute;inset:1px;border-radius:19px;pointer-events:none;\n  background:linear-gradient(105deg,transparent 22%,rgba(255,255,255,.2) 47%,transparent 70%);\n  transform:translateX(-130%);animation:bam-launcher-sheen-v58 5.6s ease-in-out infinite\n}\n#chat-launcher.bam-chat-launcher-v58:hover{\n  transform:translateY(-4px) scale(1.02)!important;filter:saturate(1.08) brightness(1.03);\n  box-shadow:0 23px 52px rgba(14,55,139,.46),\n             inset 0 1px 0 rgba(255,255,255,.3)!important\n}\n\n.bam-chat-orb-v58{\n  position:relative;width:47px;height:47px;display:grid;place-items:center;flex:none;\n  overflow:hidden;border:1px solid rgba(255,255,255,.32);border-radius:15px;\n  background:linear-gradient(145deg,rgba(255,255,255,.26),rgba(255,255,255,.09));\n  box-shadow:inset 0 1px 0 rgba(255,255,255,.28),0 8px 19px rgba(7,39,111,.2)\n}\n.bam-chat-orb-v58 svg{width:33px;height:33px;overflow:visible}\n.bam-chat-bubble-v58{\n  fill:none;stroke:#fff;stroke-width:2.15;stroke-linecap:round;stroke-linejoin:round\n}\n.bam-chat-dot-v58{fill:#fff;animation:bam-chat-dot-v58 1.8s ease-in-out infinite}\n.bam-chat-dot-v58.dot-two{animation-delay:.16s}\n.bam-chat-dot-v58.dot-three{animation-delay:.32s}\n.bam-chat-spark-v58{\n  fill:#dff9ff;transform-origin:37px 10px;\n  animation:bam-chat-spark-v58 2.4s ease-in-out infinite\n}\n.bam-chat-copy-v58{\n  min-width:92px;display:flex;flex-direction:column;align-items:flex-start;\n  gap:4px;line-height:1;text-align:left\n}\n.bam-chat-copy-v58 strong{color:#fff;font-size:11.5px;font-weight:850}\n.bam-chat-copy-v58 small{\n  color:#d8eaff;font-size:7.5px;font-weight:650;white-space:nowrap\n}\n.bam-chat-live-v58{\n  display:inline-flex;align-items:center;gap:5px;margin-left:auto;padding:5px 7px;\n  border:1px solid rgba(255,255,255,.18);border-radius:999px;\n  background:rgba(3,30,82,.2);color:#e8f7ff;font-size:6.5px;font-weight:800;\n  text-transform:uppercase\n}\n.bam-chat-live-v58 i{\n  position:static!important;width:6px!important;height:6px!important;border:0!important;\n  border-radius:50%;background:#4ce2a1!important;\n  box-shadow:0 0 0 3px rgba(76,226,161,.16)!important\n}\n#chat-launcher.bam-chat-launcher-v58>#launcher-status{\n  right:-2px!important;top:-2px!important;width:11px!important;height:11px!important;\n  border:2px solid #fff!important\n}\n\n.assistant-avatar.bam-chat-avatar-v58{\n  width:48px!important;height:48px!important;display:grid!important;\n  place-items:center!important;flex:none;overflow:visible!important;\n  border:1px solid rgba(255,255,255,.28)!important;border-radius:15px!important;\n  background:linear-gradient(145deg,#65dfff,#4e88ff 55%,#7159f1)!important;\n  box-shadow:0 9px 22px rgba(12,60,153,.28)!important\n}\n.assistant-avatar.bam-chat-avatar-v58::before,\n.assistant-avatar.bam-chat-avatar-v58::after{content:none!important}\n.assistant-avatar.bam-chat-avatar-v58 svg{width:31px;height:31px}\n\n/* AI Guard icon and usable switch */\n.bam-guard-copy-v58{display:flex!important;align-items:center!important;gap:13px!important}\n.bam-guard-icon-v58{\n  width:46px;height:46px;display:grid;place-items:center;flex:none;\n  border:1px solid #d9e5f4;border-radius:14px;\n  background:linear-gradient(145deg,#eff5ff,#e8f1ff);color:#2d68ce;\n  box-shadow:inset 0 1px 0 rgba(255,255,255,.85)\n}\n.bam-guard-row-v58.is-enabled .bam-guard-icon-v58{\n  border-color:#c8e9dc;background:linear-gradient(145deg,#e9faf2,#e2f5ec);\n  color:#168258\n}\n.bam-guard-icon-v58 svg{\n  width:23px;height:23px;fill:none;stroke:currentColor;stroke-width:1.8;\n  stroke-linecap:round;stroke-linejoin:round\n}\n.bam-guard-row-v58 input[type="checkbox"],\n.bam-guard-row-v58 input[type="checkbox"]:disabled{\n  pointer-events:auto!important;cursor:pointer!important;opacity:1!important\n}\n.bam-guard-row-v58 .is-protected{\n  border-color:#c8e9dc!important;background:#e8f8f0!important;color:#14764e!important\n}\n\n@keyframes bam-launcher-float-v58{\n  0%,100%{transform:translateY(0)}50%{transform:translateY(-5px)}\n}\n@keyframes bam-launcher-ring-v58{\n  0%{transform:scale(.96);opacity:.65}72%,100%{transform:scale(1.08);opacity:0}\n}\n@keyframes bam-launcher-sheen-v58{\n  0%,58%{transform:translateX(-130%)}77%,100%{transform:translateX(130%)}\n}\n@keyframes bam-chat-dot-v58{\n  0%,55%,100%{opacity:.46;transform:translateY(0)}\n  26%{opacity:1;transform:translateY(-2px)}\n}\n@keyframes bam-chat-spark-v58{\n  0%,100%{opacity:.7;transform:scale(.86) rotate(0deg)}\n  50%{opacity:1;transform:scale(1.12) rotate(12deg)}\n}\n\n@media(max-width:760px){\n  .cp-execution-toolbar-v58{align-items:stretch;flex-direction:column}\n  #cp-live-mode-v57.cp-live-mode-v58{width:100%!important;min-width:0}\n  #chat-launcher.bam-chat-launcher-v58{\n    width:62px!important;min-width:62px!important;height:62px!important;\n    padding:7px!important;justify-content:center!important\n  }\n  .bam-chat-copy-v58,.bam-chat-live-v58{display:none!important}\n}\n@media(prefers-reduced-motion:reduce){\n  #chat-launcher.bam-chat-launcher-v58,\n  #chat-launcher.bam-chat-launcher-v58::before,\n  #chat-launcher.bam-chat-launcher-v58::after,\n  .bam-chat-dot-v58,.bam-chat-spark-v58{animation:none!important}\n}\n'


def fail(message: str) -> None:
    raise SystemExit(f"ERROR: {message}")


def run(command: list[str], cwd: Path | None = None, check: bool = True, capture: bool = False):
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


def ensure_tmas_key(root: Path) -> None:
    env_path = root / ".env"
    if not env_path.is_file():
        fail(f"Project .env not found: {env_path}")

    current = env_path.read_text(encoding="utf-8")
    if re.search(r"(?m)^TMAS_API_KEY=", current):
        print("TMAS_API_KEY is already present in the project .env.")
        env_path.chmod(0o600)
        return

    source = Path.home() / ".tmas" / ".env"
    if not source.is_file():
        fail(f"TMAS_API_KEY is absent and {source} was not found")

    key_line = ""
    for line in source.read_text(encoding="utf-8").splitlines():
        if line.startswith("TMAS_API_KEY="):
            key_line = line

    if not key_line:
        fail(f"TMAS_API_KEY was not found in {source}")

    with env_path.open("a", encoding="utf-8") as handle:
        handle.write("\n" + key_line + "\n")

    env_path.chmod(0o600)
    print("TMAS_API_KEY copied into the gitignored project .env (value not displayed).")


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

    live_text = live.read_text(encoding="utf-8")
    live_text = live_text.replace(
        "and Path(TMAS_ENV_FILE).is_file()",
        "and Path(TMAS_ENV_FILE).is_file()\n"
        "                and os.access(TMAS_ENV_FILE, os.R_OK)",
    )

    credential_marker = "# BAM_V58_CREDENTIAL_PREFLIGHT"
    if credential_marker not in live_text:
        anchor = "            command = [\n                TMAS_BINARY,\n"
        replacement = (
            "            # BAM_V58_CREDENTIAL_PREFLIGHT\n"
            "            readable_env_file = bool(\n"
            "                TMAS_ENV_FILE\n"
            "                and Path(TMAS_ENV_FILE).is_file()\n"
            "                and os.access(TMAS_ENV_FILE, os.R_OK)\n"
            "            )\n"
            "            if not os.getenv(\"TMAS_API_KEY\") and not readable_env_file:\n"
            "                raise RuntimeError(\n"
            "                    \"TMAS credential is unavailable. Configure \"\n"
            "                    \"TMAS_API_KEY in the container environment.\"\n"
            "                )\n\n"
            "            command = [\n"
            "                TMAS_BINARY,\n"
        )
        if anchor not in live_text:
            fail("Unable to insert the TMAS credential preflight")
        live_text = live_text.replace(anchor, replacement, 1)

    live.write_text(live_text, encoding="utf-8")

    index_text = index.read_text(encoding="utf-8")
    for asset in ("styles.css", "app.js", "favicon.svg"):
        index_text = re.sub(
            rf"/static/{re.escape(asset)}\?v=[0-9.]+",
            f"/static/{asset}?v={VERSION}",
            index_text,
        )

    if "<!-- BAM_BANK_UI_REVISION_V58 -->" not in index_text:
        index_text = index_text.replace(
            "<!-- BAM_BANK_UI_REVISION_V57 -->",
            "<!-- BAM_BANK_UI_REVISION_V58 -->\n  "
            "<!-- BAM_BANK_UI_REVISION_V57 -->",
            1,
        )
    index.write_text(index_text, encoding="utf-8")

    js_text = js.read_text(encoding="utf-8")
    if "BAM_BANK_UI_REVISION_V58" not in js_text:
        js_text = js_text.rstrip() + "\n\n" + JS_PATCH.strip() + "\n"
    js.write_text(js_text, encoding="utf-8")

    css_text = css.read_text(encoding="utf-8")
    if "BAM_BANK_UI_REVISION_V58" not in css_text:
        css_text = css_text.rstrip() + "\n\n" + CSS_PATCH.strip() + "\n"
    css.write_text(css_text, encoding="utf-8")


def validate_sources(root: Path) -> None:
    run(
        [sys.executable, "-m", "py_compile", "app/main.py", "app/vision_one_live.py"],
        cwd=root,
    )
    run(["git", "diff", "--check"], cwd=root)

    node = shutil.which("node")
    if node:
        run([node, "--check", "app/static/app.js"], cwd=root)
    else:
        print("Node.js is unavailable; JavaScript syntax validation skipped.")


def read_health() -> dict | None:
    result = subprocess.run(
        ["curl", "-fsS", f"http://127.0.0.1:{PORT}/api/health"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    if result.returncode != 0:
        return None

    import json

    try:
        return json.loads(result.stdout)
    except Exception:
        return None


def running_container_on_port(root: Path) -> str | None:
    result = run(
        ["docker", "ps", "-q", "--filter", f"publish={PORT}"],
        cwd=root,
        capture=True,
        check=False,
    )
    ids = result.stdout.strip().split()
    return ids[0] if ids else None


def container_has_tmas_key(root: Path, container_id: str) -> bool:
    result = subprocess.run(
        [
            "docker",
            "exec",
            container_id,
            "sh",
            "-lc",
            'test -n "$TMAS_API_KEY"',
        ],
        cwd=str(root),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return result.returncode == 0


def deploy(root: Path) -> dict:
    existing_health = read_health()
    existing_container = running_container_on_port(root)

    if (
        existing_health
        and existing_health.get("version") == VERSION
        and existing_container
        and container_has_tmas_key(root, existing_container)
    ):
        print(
            "Revision 58 container is already healthy; "
            "skipping duplicate rebuild and deployment."
        )
        run(
            [
                "docker",
                "exec",
                existing_container,
                "/usr/local/bin/tmas",
                "--version",
            ],
            cwd=root,
        )
        return existing_health

    run(["docker", "build", "--no-cache", "-t", IMAGE, "."], cwd=root)

    old_ids = run(
        ["docker", "ps", "-q", "--filter", f"publish={PORT}"],
        cwd=root,
        capture=True,
    ).stdout.strip().split()

    for container_id in old_ids:
        run(["docker", "rm", "-f", container_id], cwd=root, check=False)

    for name in (
        "bambank-demo-v56",
        "bambank-demo-v57",
        "bambank-demo-restored",
        "visionone-bank-demo-test",
        CONTAINER,
    ):
        run(["docker", "rm", "-f", name], cwd=root, check=False)

    run(
        ["docker", "volume", "create", "bambank-demo-data"],
        cwd=root,
        check=False,
    )

    command = [
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
    ]
    run(command, cwd=root)

    health = None
    for _ in range(45):
        health = read_health()
        if health and health.get("version") == VERSION:
            break
        time.sleep(1)

    if not health or health.get("version") != VERSION:
        run(
            ["docker", "logs", "--tail=120", CONTAINER],
            cwd=root,
            check=False,
        )
        fail(f"Deployment validation failed; health={health!r}")

    run(
        [
            "docker",
            "exec",
            CONTAINER,
            "sh",
            "-lc",
            'test -n "$TMAS_API_KEY" '
            '&& echo "TMAS_API_KEY=loaded" || exit 1',
        ],
        cwd=root,
    )
    run(
        [
            "docker",
            "exec",
            CONTAINER,
            "/usr/local/bin/tmas",
            "--version",
        ],
        cwd=root,
    )
    return health

def update_git(root: Path) -> None:
    scripts_dir = root / "scripts"
    scripts_dir.mkdir(exist_ok=True)
    target = (
        scripts_dir
        / "apply_bam_revision_v58_1_resume_all_in_one.py"
    )
    shutil.copy2(Path(__file__).resolve(), target)
    target.chmod(0o755)

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

    # scripts/ is intentionally ignored in this repository.
    # Force-add only this release installer.
    run(
        [
            "git",
            "add",
            "-f",
            "scripts/apply_bam_revision_v58_1_resume_all_in_one.py",
        ],
        cwd=root,
    )

    run(["git", "diff", "--cached", "--check"], cwd=root)

    changed = (
        subprocess.run(
            ["git", "diff", "--cached", "--quiet"],
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
                "Finalize BAM Bank v58 scanner and UI fixes",
            ],
            cwd=root,
        )

    run(["git", "push", "origin", BRANCH], cwd=root)
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
        sys.argv[1] if len(sys.argv) > 1 else Path.home() / "visionone-bank-demo"
    ).expanduser().resolve()

    for command in ("git", "docker", "curl"):
        require_command(command)

    if not (root / ".git").is_dir():
        fail(f"Git repository not found: {root}")
    if not Path("/usr/local/bin/tmas").is_file():
        fail("TMAS binary not found: /usr/local/bin/tmas")

    run(["git", "fetch", "origin", "--prune"], cwd=root)
    run(["git", "checkout", BRANCH], cwd=root)

    status = run(
        ["git", "status", "--porcelain", "--untracked-files=no"],
        cwd=root,
        capture=True,
    ).stdout.strip()

    if status:
        dirty_files = set()
        for line in status.splitlines():
            path = line[3:].strip()
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
            "Detected the already-applied Revision 58 source changes; "
            "resuming validation, Git commit, and push."
        )

    ensure_tmas_key(root)
    patch_sources(root)
    validate_sources(root)
    health = deploy(root)
    update_git(root)

    print()
    print("BAM Bank revision 58.1 finalization completed.")
    print(f"Version   : {VERSION}")
    print(f"Branch    : {BRANCH}")
    print(f"Container : {CONTAINER}")
    print(f"Health    : {health}")
    print()
    print("Fixed:")
    print("  - Vision One Live TMAS permission error")
    print("  - Balanced Demo / Vision One Live selector")
    print("  - Animated message-based BAM Assist launcher")
    print("  - Functional AI Guard toggle with matching icon")


if __name__ == "__main__":
    main()
