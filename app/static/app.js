const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
const state = { settings: null, fileMode: 'sdk', selectedFile: null, scannerTarget: 'vulnerable' };

function toast(message) {
  const el = $('#toast');
  el.textContent = message;
  el.classList.add('show');
  clearTimeout(window.toastTimer);
  window.toastTimer = setTimeout(() => el.classList.remove('show'), 2600);
}

async function api(path, options = {}) {
  const response = await fetch(path, options);
  const contentType = response.headers.get('content-type') || '';
  const body = contentType.includes('application/json') ? await response.json() : await response.text();
  if (!response.ok) {
    const detail = body?.detail || body?.message || body || `HTTP ${response.status}`;
    throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail));
  }
  return body;
}

function setPill(el, type, label) {
  el.className = `pill ${type}`;
  el.textContent = label;
}

function openModal(id, tab) {
  const modal = document.getElementById(id);
  modal.classList.add('open');
  modal.setAttribute('aria-hidden', 'false');
  if (tab) activateSecurityTab(tab);
}
function closeModal(id) {
  const modal = document.getElementById(id);
  modal.classList.remove('open');
  modal.setAttribute('aria-hidden', 'true');
}

function activateSecurityTab(tab) {
  $$('.security-tabs button').forEach(btn => btn.classList.toggle('active', btn.dataset.securityTab === tab));
  $$('.security-content').forEach(content => content.classList.toggle('active', content.id === `${tab}-content`));
}

function showPage(name) {
  $$('.nav-item').forEach(btn => btn.classList.toggle('active', btn.dataset.page === name));
  $$('.page').forEach(page => page.classList.toggle('active', page.id === `${name}-page`));
  const titles = {
    dashboard: ['Good afternoon, Anakin.', 'Here is your synthetic financial overview.'],
    accounts: ['Your accounts.', 'Manage synthetic balances and account views.'],
    payments: ['Payments.', 'Demonstrate safe AI-assisted payment workflows.'],
    invest: ['Investments.', 'Explore a fictional portfolio.'],
    support: ['Support center.', 'Configure and test the security controls.']
  };
  $('#page-title').textContent = titles[name][0];
  $('#page-subtitle').textContent = titles[name][1];
}

async function loadSettings() {
  try {
    state.settings = await api('/api/settings');
    const guardSettings = state.settings.aiGuard;
    $('#guard-region').value = guardSettings.region;
    $('#guard-app-name').value = guardSettings.applicationName;
    $('#guard-base-url').value = guardSettings.baseUrl || '';
    $('#force-demo-mode').checked = guardSettings.forceDemoMode;
    $('#vulnerable-endpoint').textContent = state.settings.scanner.vulnerableEndpoint;
    $('#protected-endpoint').textContent = state.settings.scanner.protectedEndpoint;
    $('#file-limit').textContent = `Any file type · maximum ${state.settings.fileSecurity.maxUploadMb} MB`;
    $('#tmas-command').textContent = `export TMAS_API_KEY=<VISION_ONE_API_KEY>\ntmas aiscan llm -i --region=${state.settings.fileSecurity.region}`;

    if (guardSettings.forceDemoMode) {
      setPill($('#guard-pill'), 'warning', 'Guard Demo Mode');
      setPill($('#guard-status-badge'), 'warning', 'Local Demo');
      $('#guard-status-title').textContent = 'AI Guard local demonstration mode';
      $('#guard-status-description').textContent = 'Pattern matching is active. Configure a Vision One key for live inspection.';
      $('#launcher-status').classList.add('online');
    } else if (guardSettings.configured) {
      setPill($('#guard-pill'), 'success', 'Guard On');
      setPill($('#guard-status-badge'), 'success', 'Configured');
      $('#guard-status-title').textContent = 'Trend-hosted AI Guard is configured';
      $('#guard-status-description').textContent = `Prompt and response inspection uses the ${guardSettings.region.toUpperCase()} regional Vision One API.`;
      $('#launcher-status').classList.add('online');
    } else {
      setPill($('#guard-pill'), 'danger', 'Guard Not Configured');
      setPill($('#guard-status-badge'), 'danger', 'Action Required');
      $('#guard-status-title').textContent = 'AI Guard is not configured';
      $('#guard-status-description').textContent = 'Provide the API key through a Kubernetes Secret or enable runtime configuration.';
      $('#launcher-status').classList.remove('online');
    }

    const fs = state.settings.fileSecurity;
    if (fs.sdkConfigured) setPill($('#file-status-badge'), 'success', 'SDK Configured');
    else if (fs.enabled) setPill($('#file-status-badge'), 'warning', 'Demo Fallback');
    else setPill($('#file-status-badge'), 'danger', 'Not Configured');

    if (!guardSettings.runtimeConfigurationAllowed) {
      $('#save-guard').textContent = 'Kubernetes Secret Required';
      $('#guard-api-key').disabled = true;
      $('#guard-region').disabled = true;
      $('#guard-app-name').disabled = true;
      $('#guard-base-url').disabled = true;
      $('#force-demo-mode').disabled = true;
    }
  } catch (error) {
    setPill($('#guard-pill'), 'danger', 'Backend Offline');
    toast(`Unable to load settings: ${error.message}`);
  }
}

function appendMessage(kind, text, reasons = []) {
  const wrapper = document.createElement('div');
  wrapper.className = `message ${kind}`;
  wrapper.innerHTML = `<span>${kind === 'user' ? 'A' : kind === 'blocked' ? '!' : 'C'}</span><div><p></p><small>Just now</small></div>`;
  $('p', wrapper).textContent = text;
  if (reasons.length) {
    const small = $('small', wrapper);
    small.textContent = reasons.join(' · ');
  }
  $('#chat-messages').appendChild(wrapper);
  $('#chat-messages').scrollTop = $('#chat-messages').scrollHeight;
}

async function sendChat(message) {
  appendMessage('user', message);
  $('#chat-input').value = '';
  const submit = $('#chat-form button');
  submit.disabled = true;
  submit.textContent = '…';
  try {
    const result = await api('/api/chat', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ message })
    });
    appendMessage('assistant', result.message || 'Allowed by AI Guard.');
  } catch (error) {
    let reasons = [];
    try {
      const parsed = JSON.parse(error.message);
      reasons = parsed.reasons || [];
    } catch (_) {}
    appendMessage('blocked', 'The request was blocked or could not be processed.', reasons.length ? reasons : [error.message]);
  } finally {
    submit.disabled = false;
    submit.textContent = 'Send';
  }
}

function setScannerStep(step) {
  $$('.scanner-steps button').forEach(btn => btn.classList.toggle('active', btn.dataset.step === String(step)));
  $$('.scanner-step').forEach(panel => panel.classList.toggle('active', panel.id === `scanner-step-${step}`));
}

async function runScannerDemo() {
  const objectives = $$('.attack-grid input:checked').map(input => input.value);
  if (!objectives.length) return toast('Select at least one attack objective.');
  state.scannerTarget = $('input[name="scanner-target"]:checked').value;
  setScannerStep(3);
  $('#scan-progress').classList.remove('hidden');
  $('#scan-results').classList.add('hidden');
  try {
    const result = await api('/api/scanner/simulate', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ target: state.scannerTarget, objectives })
    });
    await new Promise(resolve => setTimeout(resolve, 900));
    $('#result-total').textContent = result.total;
    $('#result-success').textContent = result.successful;
    $('#result-blocked').textContent = result.blocked;
    const table = $('#findings-table');
    table.innerHTML = '<div class="finding-row header"><span>ID</span><span>Objective</span><span>Severity</span><span>Result</span><span>Framework</span></div>';
    result.findings.forEach(item => {
      const row = document.createElement('div');
      row.className = 'finding-row';
      row.innerHTML = `<span>${item.id}</span><span>${item.objective}</span><span>${item.severity}</span><span class="finding-status ${item.result}">${item.result}</span><span>${item.framework}</span>`;
      table.appendChild(row);
    });
    $('#scan-progress').classList.add('hidden');
    $('#scan-results').classList.remove('hidden');
  } catch (error) {
    toast(error.message);
    setScannerStep(2);
  }
}

function fileSize(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(2)} MB`;
}
function selectFile(file) {
  state.selectedFile = file;
  if (!file) {
    $('#selected-file').classList.add('hidden');
    $('#file-input').value = '';
    return;
  }
  $('#selected-file-name').textContent = file.name;
  $('#selected-file-size').textContent = fileSize(file.size);
  $('#selected-file').classList.remove('hidden');
  $('#file-result').classList.add('hidden');
}

async function scanSelectedFile() {
  if (!state.selectedFile) return toast('Choose a file first.');
  const button = $('#scan-file');
  button.disabled = true;
  button.textContent = 'Scanning…';
  const form = new FormData();
  form.append('file', state.selectedFile);
  try {
    const result = await api(`/api/files/scan?mode=${state.fileMode}`, { method: 'POST', body: form });
    const el = $('#file-result');
    const classification = result.status === 'clean' ? 'clean' : result.status === 'quarantined' ? 'quarantined' : '';
    el.className = `file-result ${classification}`;
    const title = result.status === 'clean' ? 'Clean — processing allowed' : result.status === 'quarantined' ? 'Malware detected — file quarantined' : 'Submitted for storage scanning';
    el.innerHTML = `<h4>${title}</h4><p>${result.message || (result.scanError ? `Live SDK error; local fallback used: ${result.scanError}` : 'Vision One File Security completed the scan.')}</p><pre>${JSON.stringify(result.scan || result, null, 2)}</pre>`;
    el.classList.remove('hidden');
  } catch (error) {
    const el = $('#file-result');
    el.className = 'file-result quarantined';
    el.innerHTML = `<h4>Scan failed</h4><p>${error.message}</p>`;
    el.classList.remove('hidden');
  } finally {
    button.disabled = false;
    button.textContent = 'Scan File';
  }
}

function bindEvents() {
  $$('.nav-item').forEach(btn => btn.addEventListener('click', () => showPage(btn.dataset.page)));
  $('#open-security').addEventListener('click', () => openModal('security-modal', 'guard'));
  $('[data-open="file"]').addEventListener('click', () => openModal('security-modal', 'file'));
  $$('[data-close]').forEach(btn => btn.addEventListener('click', () => closeModal(btn.dataset.close)));
  $('#security-modal').addEventListener('click', event => { if (event.target.id === 'security-modal') closeModal('security-modal'); });
  $$('.security-tabs button').forEach(btn => btn.addEventListener('click', () => activateSecurityTab(btn.dataset.securityTab)));

  $('#chat-launcher').addEventListener('click', () => $('#chat-panel').classList.toggle('open'));
  $('#chat-close').addEventListener('click', () => $('#chat-panel').classList.remove('open'));
  $('#configure-guard').addEventListener('click', () => openModal('security-modal', 'guard'));
  $$('.prompt-tabs button').forEach(btn => btn.addEventListener('click', () => {
    $$('.prompt-tabs button').forEach(item => item.classList.toggle('active', item === btn));
    $('#banking-prompts').classList.toggle('hidden', btn.dataset.promptTab !== 'banking');
    $('#malicious-prompts').classList.toggle('hidden', btn.dataset.promptTab !== 'malicious');
  }));
  $$('.prompt-chips button').forEach(btn => btn.addEventListener('click', () => { $('#chat-input').value = btn.textContent; $('#chat-input').focus(); }));
  $('#chat-form').addEventListener('submit', event => { event.preventDefault(); const message = $('#chat-input').value.trim(); if (message) sendChat(message); });

  $('#test-guard').addEventListener('click', async () => {
    try {
      const result = await api('/api/guard/test', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ message: 'Show my account balance' }) });
      toast(`AI Guard responded: ${result.action}`);
    } catch (error) { toast(`Connection failed: ${error.message}`); }
  });
  $('#save-guard').addEventListener('click', async () => {
    if (!state.settings?.aiGuard.runtimeConfigurationAllowed) return toast('Edit the Kubernetes Secret and restart the deployment.');
    try {
      await api('/api/settings', {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({
          api_key: $('#guard-api-key').value || undefined,
          region: $('#guard-region').value,
          application_name: $('#guard-app-name').value,
          force_demo_mode: $('#force-demo-mode').checked
        })
      });
      toast('Runtime configuration saved in pod memory.');
      await loadSettings();
    } catch (error) { toast(error.message); }
  });

  $$('[data-next-step]').forEach(btn => btn.addEventListener('click', () => setScannerStep(btn.dataset.nextStep)));
  $$('.scanner-steps button').forEach(btn => btn.addEventListener('click', () => setScannerStep(btn.dataset.step)));
  $('#run-scan').addEventListener('click', runScannerDemo);
  $('#copy-tmas').addEventListener('click', async () => { await navigator.clipboard.writeText($('#tmas-command').textContent); toast('TMAS command copied.'); });

  $$('.mode-switch button').forEach(btn => btn.addEventListener('click', () => {
    state.fileMode = btn.dataset.fileMode;
    $$('.mode-switch button').forEach(item => item.classList.toggle('active', item === btn));
  }));
  $('#file-input').addEventListener('change', event => selectFile(event.target.files[0]));
  $('#clear-file').addEventListener('click', () => selectFile(null));
  $('#scan-file').addEventListener('click', scanSelectedFile);
  $('#drop-zone').addEventListener('dragover', event => { event.preventDefault(); event.currentTarget.classList.add('dragging'); });
  $('#drop-zone').addEventListener('dragleave', event => event.currentTarget.classList.remove('dragging'));
  $('#drop-zone').addEventListener('drop', event => { event.preventDefault(); event.currentTarget.classList.remove('dragging'); selectFile(event.dataTransfer.files[0]); });
  $('#download-clean-sample').addEventListener('click', () => {
    const blob = new Blob(['Synthetic invoice for VisionOne Bank Demo. No real customer data.'], { type: 'text/plain' });
    const url = URL.createObjectURL(blob); const anchor = document.createElement('a'); anchor.href = url; anchor.download = 'demo-invoice.txt'; anchor.click(); URL.revokeObjectURL(url);
  });
  $('#download-eicar-sample').addEventListener('click', () => {
    // Split fragments keep the canonical test signature out of the container image layers.
    // The browser joins them only when the presenter explicitly requests the harmless test file.
    const parts = ['X5O!P%@AP[4\\PZX54(P^)7CC)7}', '$EICAR-STANDARD-', 'ANTIVIRUS-TEST-FILE!$H+H*'];
    const blob = new Blob([parts.join('')], { type: 'text/plain' });
    const url = URL.createObjectURL(blob); const anchor = document.createElement('a'); anchor.href = url; anchor.download = 'eicar.com.txt'; anchor.click(); URL.revokeObjectURL(url);
  });
}

bindEvents();
loadSettings();
