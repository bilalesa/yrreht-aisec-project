const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
const state = { settings: null, fileMode: 'sdk', selectedFile: null, scannerTarget: 'vulnerable', guardEnabled: true };

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
  modal.classList.remove('open', 'banking-flow');
  modal.setAttribute('aria-hidden', 'true');
  resetSecurityHeader();
}

function setSecurityHeader(eyebrow, title, description) {
  $('#security-eyebrow').textContent = eyebrow;
  $('#security-title').textContent = title;
  $('#security-description').textContent = description;
}

function resetSecurityHeader() {
  setSecurityHeader(
    'PRESENTER LAB · AI APPLICATION SECURITY',
    'Presenter Security Lab',
    'Assessment, runtime enforcement, and malicious file prevention.'
  );
}

function openBillUpload() {
  const modal = $('#security-modal');
  modal.classList.add('banking-flow');
  setSecurityHeader(
    'PAYMENTS',
    'Upload a bill',
    'Your document is checked automatically before the payment workflow continues.'
  );
  openModal('security-modal', 'file');
}

function openPresenterLab(tab = 'guard') {
  $('#security-modal').classList.remove('banking-flow');
  resetSecurityHeader();
  openModal('security-modal', tab);
}

function activateSecurityTab(tab) {
  $$('.security-tabs button').forEach(btn => btn.classList.toggle('active', btn.dataset.securityTab === tab));
  $$('.security-content').forEach(content => content.classList.toggle('active', content.id === `${tab}-content`));
}

function showPage(name) {
  $$('.nav-item').forEach(btn => btn.classList.toggle('active', btn.dataset.page === name));
  $$('.page').forEach(page => page.classList.toggle('active', page.id === `${name}-page`));
  const titles = {
    dashboard: ['Good afternoon, Karim.', 'Here is your synthetic financial overview.'],
    accounts: ['Your accounts.', 'Manage synthetic balances and account views.'],
    payments: ['Payments.', 'Demonstrate safe AI-assisted payment workflows.'],
    invest: ['Investments.', 'Explore a fictional portfolio.'],
    support: ['Support center.', 'Get help with your BAM Bank account.']
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

    const available = guardSettings.forceDemoMode || guardSettings.configured;
    state.guardEnabled = available;
    $('#guard-toggle').checked = available;
    $('#guard-toggle').disabled = !available;
    $('#guard-mode-label').textContent = available
      ? 'Protected · prompts and responses inspected'
      : 'Protection unavailable';

    if (guardSettings.forceDemoMode) {
      setPill($('#guard-status-badge'), 'warning', 'Local Demo');
      $('#guard-status-title').textContent = 'AI Guard local demonstration mode';
      $('#guard-status-description').textContent = 'Pattern matching is active. Configure a Vision One key for live inspection.';
      $('#launcher-status').classList.add('online');
    } else if (guardSettings.configured) {
      setPill($('#guard-status-badge'), 'success', 'Configured');
      $('#guard-status-title').textContent = 'Trend-hosted AI Guard is configured';
      $('#guard-status-description').textContent = `Prompt and response inspection uses the ${guardSettings.region.toUpperCase()} regional Vision One API.`;
      $('#launcher-status').classList.add('online');
    } else {
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
  wrapper.innerHTML = `<span>${kind === 'user' ? 'A' : kind === 'blocked' ? '!' : 'B'}</span><div><p></p><small>Just now</small></div>`;
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
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ message, guard_enabled: state.guardEnabled })
    });
    appendMessage('assistant', result.message || (state.guardEnabled ? 'Allowed by AI Guard.' : 'Processed without AI Guard.'));
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
  const mode = state.scannerMode === 'live' ? 'live' : 'demo';
  const endpoint = mode === 'live'
    ? '/api/scanner/live'
    : '/api/scanner/simulate';

  setScannerStep(3);
  $('#scan-progress').classList.remove('hidden');
  $('#scan-results').classList.add('hidden');

  const progressText = $('#scan-progress p');
  if (progressText) {
    progressText.textContent = mode === 'live'
      ? 'Sending real validation prompts through the selected endpoint…'
      : 'Running simulated attack campaign…';
  }

  try {
    const result = await api(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        target: state.scannerTarget,
        objectives
      })
    });

    if (mode === 'demo') {
      await new Promise(resolve => setTimeout(resolve, 900));
    }

    $('#result-total').textContent = result.total;
    $('#result-success').textContent = result.successful;
    $('#result-blocked').textContent = result.blocked;

    const modeBadge = $('#scanner-result-mode');
    if (modeBadge) {
      modeBadge.textContent = mode === 'live'
        ? 'LIVE ENDPOINT VALIDATION'
        : 'DEMO SIMULATION';
      modeBadge.className = `scanner-result-mode ${mode}`;
    }

    const errorSummary = $('#scanner-result-errors');
    if (errorSummary) {
      const errors = Number(result.errors || 0);
      errorSummary.classList.toggle('hidden', errors === 0);
      errorSummary.textContent = errors
        ? `${errors} live request(s) could not complete. Review the error rows below.`
        : '';
    }

    const table = $('#findings-table');
    table.innerHTML = '<div class="finding-row header"><span>ID</span><span>Objective</span><span>Severity</span><span>Result</span><span>Framework</span></div>';

    result.findings.forEach(item => {
      const row = document.createElement('div');
      row.className = 'finding-row';
      row.title = item.detail || item.recommendation || '';
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
    const bankingFlow = $('#security-modal').classList.contains('banking-flow');
    const title = result.status === 'clean'
      ? (bankingFlow ? 'Document verified — ready to continue' : 'Clean — processing allowed')
      : result.status === 'quarantined'
        ? (bankingFlow ? 'Document rejected' : 'Malware detected — file quarantined')
        : 'Submitted for storage scanning';
    const message = result.status === 'clean'
      ? 'The uploaded document passed the safety check.'
      : result.status === 'quarantined'
        ? 'This document could not be processed safely.'
        : 'The document was submitted for verification.';
    el.innerHTML = bankingFlow
      ? `<h4>${title}</h4><p>${message}</p>`
      : `<h4>${title}</h4><p>${result.message || (result.scanError ? `Live SDK error; local fallback used: ${result.scanError}` : 'Vision One File Security completed the scan.')}</p><pre>${JSON.stringify(result.scan || result, null, 2)}</pre>`;
    el.classList.remove('hidden');
  } catch (error) {
    const el = $('#file-result');
    el.className = 'file-result quarantined';
    el.innerHTML = `<h4>Scan failed</h4><p>${error.message}</p>`;
    el.classList.remove('hidden');
  } finally {
    button.disabled = false;
    button.textContent = 'Verify & Continue';
  }
}

function bindEvents() {
  $$('.nav-item').forEach(btn => btn.addEventListener('click', () => showPage(btn.dataset.page)));
  $('[data-open="file"]').addEventListener('click', openBillUpload);
  $$('[data-close]').forEach(btn => btn.addEventListener('click', () => closeModal(btn.dataset.close)));
  $('#security-modal').addEventListener('click', event => { if (event.target.id === 'security-modal') closeModal('security-modal'); });
  $$('.security-tabs button').forEach(btn => btn.addEventListener('click', () => activateSecurityTab(btn.dataset.securityTab)));

  $('#chat-launcher').addEventListener('click', () => $('#chat-panel').classList.toggle('open'));
  $('#chat-close').addEventListener('click', () => $('#chat-panel').classList.remove('open'));
  $('#guard-toggle').addEventListener('change', event => {
    state.guardEnabled = event.target.checked;
    $('#guard-mode-label').textContent = state.guardEnabled
      ? 'Protected · prompts and responses inspected'
      : 'Unprotected demo · direct model response';
    toast(state.guardEnabled ? 'AI Guard protection enabled.' : 'AI Guard disabled for comparison.');
  });
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
          force_demo_mode: $('#force-demo-mode').checked,
          prompt_injection_detection: $('#guard-policy-prompt-injection')?.checked ?? true,
          jailbreak_detection: $('#guard-policy-jailbreak')?.checked ?? true,
          harmful_content_detection: $('#guard-policy-harmful')?.checked ?? true,
          pii_detection: $('#guard-policy-pii')?.checked ?? true
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
    const blob = new Blob(['Synthetic invoice for BAM Bank. No real customer data.'], { type: 'text/plain' });
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


function randomInt(min, max) {
  return Math.floor(Math.random() * (max - min + 1)) + min;
}

function formatRupiah(value) {
  return new Intl.NumberFormat('id-ID', {
    style: 'currency',
    currency: 'IDR',
    maximumFractionDigits: 0
  }).format(value).replace(/\s/g, '');
}

function randomizeDashboard() {
  const savings = randomInt(280_000_000, 520_000_000);
  const investments = randomInt(430_000_000, 850_000_000);
  const credit = randomInt(150_000_000, 300_000_000);
  const total = savings + investments + randomInt(80_000_000, 180_000_000);

  $('#total-balance').textContent = formatRupiah(total);
  $('#savings-balance').textContent = formatRupiah(savings);
  $('#investment-balance').textContent = formatRupiah(investments);
  $('#credit-line').textContent = formatRupiah(credit);
  $('#monthly-gain').textContent = `▲ +${formatRupiah(randomInt(8_000_000, 35_000_000))}`;
  $('#savings-growth').textContent = `+${(Math.random() * 2.4 + 0.8).toFixed(1)}%`;
  $('#investment-return').textContent = `+${(Math.random() * 5.5 + 1.5).toFixed(1)}%`;
  $('#credit-used').textContent = `${randomInt(10, 38)}%`;

  const amounts = [
    -randomInt(450_000, 1_800_000),
    randomInt(35_000_000, 75_000_000),
    -randomInt(45_000, 180_000),
    -randomInt(120_000, 260_000),
    -randomInt(350_000, 950_000)
  ];

  $$('.transaction > b').forEach((element, index) => {
    const amount = amounts[index];
    element.textContent = `${amount >= 0 ? '+' : '−'}${formatRupiah(Math.abs(amount))}`;
  });
}

function exposePresenterLabFromUrl() {
  const params = new URLSearchParams(window.location.search);
  if (params.get('presenter') === '1' || window.location.hash === '#security-lab') {
    openPresenterLab('guard');
  }
}

bindEvents();
randomizeDashboard();
loadSettings();
exposePresenterLabFromUrl();


/* BAM_BANK_UI_REVISION_V2 */
(() => {
  const q = selector => document.querySelector(selector);
  const qa = selector => [...document.querySelectorAll(selector)];

  const translations = {
    en: {
      navDashboard: 'Dashboard',
      navAccounts: 'Accounts',
      navPayments: 'Payments',
      navInvest: 'Invest',
      navSupport: 'Support',
      scanner: 'AI Scanner',
      digitalBanking: 'DIGITAL BANKING',
      dashboardTitle: 'Good afternoon, Karim.',
      dashboardSubtitle: 'Here is your synthetic financial overview.',
      accountsTitle: 'Your accounts.',
      accountsSubtitle: 'Review balances, cards, and recent activity.',
      paymentsTitle: 'Payments.',
      paymentsSubtitle: 'Send money and pay bills securely.',
      investTitle: 'Investments.',
      investSubtitle: 'Explore your synthetic portfolio.',
      supportTitle: 'Support center.',
      supportSubtitle: 'Get help with your BAM Bank account.',
      language: 'Language',
      payBills: 'Pay Bills',
      payBillsSub: 'Protected document upload',
      sendMoney: 'Send Money',
      sendMoneySub: 'Demo transfer flow',
      topUp: 'Top Up',
      topUpSub: 'Add demo funds',
      invest: 'Invest',
      investSub: 'Explore portfolios',
      newAccount: 'New Account',
      newAccountSub: 'Open a demo account',
      totalBalance: 'Total Portfolio Balance',
      savings: 'Savings',
      investments: 'Investments',
      creditLine: 'Credit Line',
      thisMonth: 'This month',
      monthlyGrowth: 'Monthly growth',
      portfolioReturn: 'Portfolio return',
      used: 'Used',
      activity: 'ACTIVITY',
      recentTransactions: 'Recent Transactions',
      viewAll: 'View all →',
      analytics: 'ANALYTICS',
      spending: 'Spending · June',
      details: 'Details →',
      cardHolder: 'CARD HOLDER',
      validThru: 'VALID THRU',
      alwaysAvailable: 'Always available',
      bankingQueries: 'Banking Queries',
      maliciousPrompts: 'Malicious Prompts',
      send: 'Send',
      chatPlaceholder: 'Ask about your demo account…',
      protected: 'Protected · prompts and responses inspected',
      unprotected: 'Unprotected demo · direct model response',
      settings: 'Settings',
      preferences: 'Preferences',
      settingsLanguage: 'Display language',
      showPromos: 'Show demo shortcuts',
      refreshData: 'Refresh dashboard data',
      refreshButton: 'Refresh now',
      close: 'Close',
      refreshedToast: 'Dashboard balances refreshed.',
      scannerPromoTitle: 'Run an AI security scan',
      scannerPromoText: 'Run an AI Scanner assessment against the configured application target.',
      scannerPromoAction: 'Try it →',
      guardPromoTitle: 'Test AI Guard in real time',
      guardPromoText: 'Try a banking question or malicious prompt and see AI Guard react.',
      guardPromoAction: 'Explore →',
      accountsHeading: 'Account overview',
      accountsBody: 'Review balances, cards, and recent account activity.',
      paymentsHeading: 'Send money and pay bills',
      paymentsBody: 'Prepare synthetic transfers, upload invoices, and review payment history. No real payment is executed.',
      investHeading: 'Your portfolio',
      investBody: 'Explore synthetic investment products and portfolio performance.',
      supportHeading: 'How can we help?',
      supportBody: 'Get assistance with cards, payments, account access, and document submission.'
    },
    id: {
      navDashboard: 'Dasbor',
      navAccounts: 'Rekening',
      navPayments: 'Pembayaran',
      navInvest: 'Investasi',
      navSupport: 'Bantuan',
      scanner: 'AI Scanner',
      digitalBanking: 'PERBANKAN DIGITAL',
      dashboardTitle: 'Selamat sore, Karim.',
      dashboardSubtitle: 'Berikut ringkasan keuangan sintetis Anda.',
      accountsTitle: 'Rekening Anda.',
      accountsSubtitle: 'Lihat saldo, kartu, dan aktivitas terbaru.',
      paymentsTitle: 'Pembayaran.',
      paymentsSubtitle: 'Kirim uang dan bayar tagihan dengan aman.',
      investTitle: 'Investasi.',
      investSubtitle: 'Jelajahi portofolio sintetis Anda.',
      supportTitle: 'Pusat bantuan.',
      supportSubtitle: 'Dapatkan bantuan untuk rekening BAM Bank Anda.',
      language: 'Bahasa',
      payBills: 'Bayar Tagihan',
      payBillsSub: 'Unggah dokumen dengan perlindungan',
      sendMoney: 'Kirim Uang',
      sendMoneySub: 'Simulasi alur transfer',
      topUp: 'Isi Saldo',
      topUpSub: 'Tambahkan dana demo',
      invest: 'Investasi',
      investSub: 'Jelajahi portofolio',
      newAccount: 'Rekening Baru',
      newAccountSub: 'Buka rekening demo',
      totalBalance: 'Total Saldo Portofolio',
      savings: 'Tabungan',
      investments: 'Investasi',
      creditLine: 'Batas Kredit',
      thisMonth: 'Bulan ini',
      monthlyGrowth: 'Pertumbuhan bulanan',
      portfolioReturn: 'Imbal hasil portofolio',
      used: 'Terpakai',
      activity: 'AKTIVITAS',
      recentTransactions: 'Transaksi Terbaru',
      viewAll: 'Lihat semua →',
      analytics: 'ANALISIS',
      spending: 'Pengeluaran · Juni',
      details: 'Detail →',
      cardHolder: 'PEMEGANG KARTU',
      validThru: 'BERLAKU HINGGA',
      alwaysAvailable: 'Selalu tersedia',
      bankingQueries: 'Pertanyaan Perbankan',
      maliciousPrompts: 'Prompt Berbahaya',
      send: 'Kirim',
      chatPlaceholder: 'Tanyakan tentang rekening demo Anda…',
      protected: 'Terlindungi · prompt dan respons diperiksa',
      unprotected: 'Demo tanpa perlindungan · respons langsung model',
      settings: 'Pengaturan',
      preferences: 'Preferensi',
      settingsLanguage: 'Bahasa tampilan',
      showPromos: 'Tampilkan pintasan demo',
      refreshData: 'Perbarui data dasbor',
      refreshButton: 'Perbarui sekarang',
      close: 'Tutup',
      refreshedToast: 'Saldo dasbor berhasil diperbarui.',
      scannerPromoTitle: 'Jalankan pemindaian keamanan AI',
      scannerPromoText: 'Jalankan assessment AI Scanner terhadap target aplikasi yang dikonfigurasi.',
      scannerPromoAction: 'Coba →',
      guardPromoTitle: 'Uji AI Guard secara real-time',
      guardPromoText: 'Coba pertanyaan perbankan atau prompt berbahaya untuk melihat AI Guard bereaksi.',
      guardPromoAction: 'Jelajahi →',
      accountsHeading: 'Ringkasan rekening',
      accountsBody: 'Lihat saldo, kartu, dan aktivitas rekening terbaru.',
      paymentsHeading: 'Kirim uang dan bayar tagihan',
      paymentsBody: 'Siapkan transfer sintetis, unggah tagihan, dan lihat riwayat pembayaran. Tidak ada pembayaran nyata.',
      investHeading: 'Portofolio Anda',
      investBody: 'Jelajahi produk investasi sintetis dan kinerja portofolio.',
      supportHeading: 'Apa yang dapat kami bantu?',
      supportBody: 'Dapatkan bantuan terkait kartu, pembayaran, akses rekening, dan pengiriman dokumen.'
    }
  };

  let currentLanguage = localStorage.getItem('bam-language') === 'id' ? 'id' : 'en';

  function setNodeText(selector, value) {
    const element = q(selector);
    if (element) element.textContent = value;
  }

  function setIconButtonText(selector, value) {
    const button = q(selector);
    if (!button) return;
    const icon = button.querySelector('span');
    button.innerHTML = `${icon ? icon.outerHTML : ''}${value}`;
  }

  function updateSpendingLabel(index, value) {
    const item = qa('.spending-panel li')[index];
    if (!item) return;
    const percentage = item.querySelector('b');
    const dot = item.querySelector('i');
    item.innerHTML = '';
    if (dot) item.appendChild(dot);
    item.append(document.createTextNode(value + ' '));
    if (percentage) item.appendChild(percentage);
  }

  function updateActivePageTitle(lang) {
    const copy = translations[lang];
    const activePage = q('.page.active');
    const page = activePage ? activePage.id.replace('-page', '') : 'dashboard';
    const map = {
      dashboard: [copy.dashboardTitle, copy.dashboardSubtitle],
      accounts: [copy.accountsTitle, copy.accountsSubtitle],
      payments: [copy.paymentsTitle, copy.paymentsSubtitle],
      invest: [copy.investTitle, copy.investSubtitle],
      support: [copy.supportTitle, copy.supportSubtitle]
    };
    const selected = map[page] || map.dashboard;
    setNodeText('#page-title', selected[0]);
    setNodeText('#page-subtitle', selected[1]);
  }

  function applyLanguage(lang) {
    currentLanguage = lang;
    localStorage.setItem('bam-language', lang);
    document.documentElement.lang = lang === 'id' ? 'id' : 'en';
    const copy = translations[lang];

    setIconButtonText('.nav-item[data-page="dashboard"]', copy.navDashboard);
    setIconButtonText('.nav-item[data-page="accounts"]', copy.navAccounts);
    setIconButtonText('.nav-item[data-page="payments"]', copy.navPayments);
    setIconButtonText('.nav-item[data-page="invest"]', copy.navInvest);
    setIconButtonText('.nav-item[data-page="support"]', copy.navSupport);
    setIconButtonText('#open-ai-scanner', copy.scanner);

    setNodeText('.topbar .eyebrow', copy.digitalBanking);
    updateActivePageTitle(lang);
    setNodeText('.language > span', copy.language);

    const quickActions = qa('.quick-actions button');
    const quickCopy = [
      [copy.payBills, copy.payBillsSub],
      [copy.sendMoney, copy.sendMoneySub],
      [copy.topUp, copy.topUpSub],
      [copy.invest, copy.investSub],
      [copy.newAccount, copy.newAccountSub]
    ];
    quickActions.forEach((button, index) => {
      const values = quickCopy[index];
      if (!values) return;
      const title = button.querySelector('strong');
      const subtitle = button.querySelector('small');
      if (title) title.textContent = values[0];
      if (subtitle) subtitle.textContent = values[1];
    });

    const metrics = qa('.metrics-grid .metric-card');
    const metricCopy = [
      [copy.totalBalance, copy.thisMonth],
      [copy.savings, copy.monthlyGrowth],
      [copy.investments, copy.portfolioReturn],
      [copy.creditLine, copy.used]
    ];
    metrics.forEach((card, index) => {
      const values = metricCopy[index];
      if (!values) return;
      const label = card.querySelector(':scope > span');
      const footer = card.querySelector(':scope > div small');
      if (label) label.textContent = values[0];
      if (footer) footer.textContent = values[1];
    });

    setNodeText('.transactions-panel .eyebrow', copy.activity);
    setNodeText('.transactions-panel h2', copy.recentTransactions);
    setNodeText('.transactions-panel .text-button', copy.viewAll);
    setNodeText('.spending-panel .eyebrow', copy.analytics);
    setNodeText('.spending-panel h2', copy.spending);
    setNodeText('.spending-panel .text-button', copy.details);

    const cardLabels = qa('.bank-card-bottom small');
    if (cardLabels[0]) cardLabels[0].textContent = copy.cardHolder;
    if (cardLabels[1]) cardLabels[1].textContent = copy.validThru;

    const spendingLabels = lang === 'id'
      ? ['Perumahan', 'Belanja Bahan Pokok', 'Makan', 'Hiburan', 'Lainnya']
      : ['Housing', 'Groceries', 'Dining', 'Entertainment', 'Other'];
    spendingLabels.forEach((label, index) => updateSpendingLabel(index, label));

    setNodeText('#accounts-page h2', copy.accountsHeading);
    setNodeText('#accounts-page article > p:last-child', copy.accountsBody);
    setNodeText('#payments-page h2', copy.paymentsHeading);
    setNodeText('#payments-page article > p:last-child', copy.paymentsBody);
    setNodeText('#invest-page h2', copy.investHeading);
    setNodeText('#invest-page article > p:last-child', copy.investBody);
    setNodeText('#support-page h2', copy.supportHeading);
    setNodeText('#support-page article > p:last-child', copy.supportBody);

    setNodeText('#chat-panel header small', copy.alwaysAvailable);
    setNodeText('[data-prompt-tab="banking"]', copy.bankingQueries);
    setNodeText('[data-prompt-tab="malicious"]', copy.maliciousPrompts);
    const chatInput = q('#chat-input');
    if (chatInput) chatInput.placeholder = copy.chatPlaceholder;
    setNodeText('#chat-form button[type="submit"]', copy.send);
    setNodeText('#guard-mode-label', state.guardEnabled ? copy.protected : copy.unprotected);

    setNodeText('#settings-title', copy.settings);
    setNodeText('#settings-subtitle', copy.preferences);
    setNodeText('#settings-language-label', copy.settingsLanguage);
    setNodeText('#settings-promos-label', copy.showPromos);
    setNodeText('#settings-refresh-label', copy.refreshData);
    setNodeText('#settings-refresh', copy.refreshButton);
    setNodeText('#settings-close', copy.close);

    setNodeText('#scanner-promo-title', copy.scannerPromoTitle);
    setNodeText('#scanner-promo-text', copy.scannerPromoText);
    setNodeText('#scanner-promo-action', copy.scannerPromoAction);
    setNodeText('#guard-promo-title', copy.guardPromoTitle);
    setNodeText('#guard-promo-text', copy.guardPromoText);
    setNodeText('#guard-promo-action', copy.guardPromoAction);

    const topLanguage = q('#language');
    if (topLanguage) topLanguage.selectedIndex = lang === 'id' ? 1 : 0;
    const settingsLanguage = q('#settings-language');
    if (settingsLanguage) settingsLanguage.value = lang;
  }

  function installScannerNavigation() {
    const nav = q('.nav-list');
    if (!nav || q('#open-ai-scanner')) return;
    const button = document.createElement('button');
    button.className = 'nav-item ai-scanner-nav';
    button.id = 'open-ai-scanner';
    button.type = 'button';
    button.innerHTML = '<span>⌗</span>AI Scanner';
    button.addEventListener('click', () => openPresenterLab('scanner'));
    nav.appendChild(button);
  }

  function installSettings() {
    const actions = q('.top-actions');
    if (!actions || q('#settings-button')) return;

    const existingIcon = actions.querySelector('.icon-button');
    const button = document.createElement('button');
    button.className = 'icon-button settings-button';
    button.id = 'settings-button';
    button.type = 'button';
    button.setAttribute('aria-label', 'Settings');
    button.setAttribute('aria-expanded', 'false');
    button.innerHTML = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M9.7 3.2 10.2 2h3.6l.5 1.2 1.4.6 1.2-.5 2.5 2.5-.5 1.2.6 1.4 1.2.5v3.6l-1.2.5-.6 1.4.5 1.2-2.5 2.5-1.2-.5-1.4.6-.5 1.2h-3.6l-.5-1.2-1.4-.6-1.2.5-2.5-2.5.5-1.2-.6-1.4-1.2-.5V8.9l1.2-.5.6-1.4-.5-1.2 2.5-2.5 1.2.5 1.4-.6Zm2.3 5.4a3.4 3.4 0 1 0 0 6.8 3.4 3.4 0 0 0 0-6.8Z" fill="currentColor"/></svg>';
    actions.insertBefore(button, existingIcon || null);

    const panel = document.createElement('section');
    panel.className = 'settings-popover';
    panel.id = 'settings-popover';
    panel.setAttribute('aria-hidden', 'true');
    panel.innerHTML = `
      <header>
        <div><strong id="settings-title">Settings</strong><small id="settings-subtitle">Preferences</small></div>
        <button type="button" id="settings-close" aria-label="Close settings">Close</button>
      </header>
      <label class="settings-field">
        <span id="settings-language-label">Display language</span>
        <select id="settings-language">
          <option value="en">English</option>
          <option value="id">Bahasa Indonesia</option>
        </select>
      </label>
      <label class="settings-toggle">
        <span id="settings-promos-label">Show demo shortcuts</span>
        <input id="settings-promos" type="checkbox" checked />
      </label>
      <div class="settings-refresh">
        <span id="settings-refresh-label">Refresh dashboard data</span>
        <button type="button" id="settings-refresh">Refresh now</button>
      </div>`;
    actions.appendChild(panel);

    const close = () => {
      panel.classList.remove('open');
      panel.setAttribute('aria-hidden', 'true');
      button.setAttribute('aria-expanded', 'false');
    };
    const toggle = event => {
      event.stopPropagation();
      const open = !panel.classList.contains('open');
      panel.classList.toggle('open', open);
      panel.setAttribute('aria-hidden', open ? 'false' : 'true');
      button.setAttribute('aria-expanded', open ? 'true' : 'false');
    };

    button.addEventListener('click', toggle);
    q('#settings-close').addEventListener('click', close);
    panel.addEventListener('click', event => event.stopPropagation());
    document.addEventListener('click', close);

    q('#settings-language').addEventListener('change', event => applyLanguage(event.target.value));
    q('#settings-promos').addEventListener('change', event => {
      const promos = q('#demo-promos');
      if (promos) promos.classList.toggle('disabled', !event.target.checked);
    });
    q('#settings-refresh').addEventListener('click', () => {
      randomizeDashboard();
      toast(translations[currentLanguage].refreshedToast);
    });
  }

  function installPromos() {
    if (q('#demo-promos')) return;
    const promos = document.createElement('aside');
    promos.className = 'demo-promos';
    promos.id = 'demo-promos';
    promos.setAttribute('aria-label', 'AI security demo shortcuts');
    promos.innerHTML = `
      <button type="button" class="demo-promo scanner-promo" id="scanner-promo">
        <span class="promo-symbol">S</span>
        <span class="promo-copy"><strong id="scanner-promo-title">Run an AI security scan</strong><small id="scanner-promo-text">Run an AI Scanner assessment against the configured application target.</small></span>
        <span class="promo-action" id="scanner-promo-action">Try it →</span>
      </button>
      <button type="button" class="demo-promo guard-promo" id="guard-promo">
        <span class="promo-symbol">G</span>
        <span class="promo-copy"><strong id="guard-promo-title">Test AI Guard in real time</strong><small id="guard-promo-text">Try a banking question or malicious prompt and see AI Guard react.</small></span>
        <span class="promo-action" id="guard-promo-action">Explore →</span>
      </button>`;
    document.body.appendChild(promos);

    q('#scanner-promo').addEventListener('click', () => openPresenterLab('scanner'));
    q('#guard-promo').addEventListener('click', () => {
      q('#chat-panel')?.classList.add('open');
      q('[data-prompt-tab="malicious"]')?.click();
    });
    window.setTimeout(() => promos.classList.add('show'), 650);
  }

  function bindLanguageControls() {
    const topLanguage = q('#language');
    if (topLanguage) {
      topLanguage.addEventListener('change', event => {
        const lang = event.target.selectedIndex === 1 ? 'id' : 'en';
        applyLanguage(lang);
      });
    }

    qa('.nav-item[data-page]').forEach(button => {
      button.addEventListener('click', () => {
        window.setTimeout(() => updateActivePageTitle(currentLanguage), 0);
      });
    });

    q('#guard-toggle')?.addEventListener('change', () => {
      window.setTimeout(() => applyLanguage(currentLanguage), 0);
    });
  }

  installScannerNavigation();
  installSettings();
  installPromos();
  bindLanguageControls();
  applyLanguage(currentLanguage);
  window.setTimeout(() => applyLanguage(currentLanguage), 900);
})();


/* BAM_BANK_UI_REVISION_V4 */
(() => {
  const q = selector => document.querySelector(selector);
  const qa = selector => [...document.querySelectorAll(selector)];

  const modalBackdrop = q('#security-modal');
  const modal = q('#security-modal .security-modal');
  const guardContent = q('#guard-content');

  if (!modalBackdrop || !modal || !guardContent) return;

  const removeLegacySettingsPopover = () => {
    q('#settings-popover')?.remove();
  };

  const cleanSettingsButton = () => {
    const oldButton = q('#settings-button');
    if (!oldButton) return null;

    const newButton = oldButton.cloneNode(true);
    oldButton.replaceWith(newButton);
    newButton.setAttribute('aria-label', 'AI Application Security Configuration');
    newButton.setAttribute('title', 'AI Application Security Configuration');
    return newButton;
  };

  const ensureDrawerMarkup = () => {
    if (!q('#guard-drawer-credentials-label')) {
      const credentials = document.createElement('p');
      credentials.className = 'drawer-section-label';
      credentials.id = 'guard-drawer-credentials-label';
      credentials.textContent = 'VISION ONE CREDENTIALS';
      q('#guard-content .two-column-form')?.before(credentials);
    }

    if (!q('#guard-drawer-policy-label')) {
      const policy = document.createElement('p');
      policy.className = 'drawer-section-label';
      policy.id = 'guard-drawer-policy-label';
      policy.textContent = 'AI GUARD POLICY';
      q('#guard-content .policy-grid')?.before(policy);
    }

    if (!q('#guard-drawer-runtime-label')) {
      const runtime = document.createElement('p');
      runtime.className = 'drawer-section-label';
      runtime.id = 'guard-drawer-runtime-label';
      runtime.textContent = 'DEMO BEHAVIOR';
      q('#guard-content .toggle-line')?.before(runtime);
    }

    const form = q('#guard-content .two-column-form');
    if (!form) return;

    const labels = [...form.querySelectorAll(':scope > label')];
    const credentialLabel = labels.find(label => label.contains(q('#guard-api-key')));
    const regionLabel = labels.find(label => label.contains(q('#guard-region')));
    const appLabel = labels.find(label => label.contains(q('#guard-app-name')));
    const endpointLabel = labels.find(label => label.contains(q('#guard-base-url')));

    if (credentialLabel) {
      credentialLabel.childNodes[0].textContent = 'API Key';
      credentialLabel.classList.add('drawer-field', 'drawer-field-full');
      const input = q('#guard-api-key');
      input.type = 'password';
      input.value = '';
      input.placeholder = 'Using server default — enter here to override';
      input.removeAttribute('readonly');

      if (!credentialLabel.querySelector('.drawer-help')) {
        const help = document.createElement('small');
        help.className = 'drawer-help';
        help.textContent = 'Leave blank to use the API key configured on the server.';
        credentialLabel.appendChild(help);
      }
    }

    if (regionLabel) {
      regionLabel.childNodes[0].textContent = 'Region';
      regionLabel.classList.add('drawer-field');
    }

    if (appLabel) {
      appLabel.childNodes[0].textContent = 'Guard ID / App Name';
      appLabel.classList.add('drawer-field', 'drawer-field-full');
      q('#guard-app-name').placeholder = 'e.g. bam-bank-assistant';

      if (!appLabel.querySelector('.drawer-help')) {
        const help = document.createElement('small');
        help.className = 'drawer-help';
        help.textContent = 'Identifies this application in the Vision One dashboard.';
        appLabel.appendChild(help);
      }
    }

    if (endpointLabel) {
      endpointLabel.childNodes[0].textContent = 'AI Guard Endpoint';
      endpointLabel.classList.add('drawer-field', 'drawer-field-full');

      if (!endpointLabel.querySelector('.drawer-help')) {
        const help = document.createElement('small');
        help.className = 'drawer-help';
        help.textContent = 'The effective Trend-hosted endpoint for the selected region.';
        endpointLabel.appendChild(help);
      }
    }

    if (!q('#guard-api-version')) {
      const apiVersionLabel = document.createElement('label');
      apiVersionLabel.className = 'drawer-field';
      apiVersionLabel.innerHTML = `
        API Version
        <select id="guard-api-version" disabled>
          <option value="v3.0">v3.0</option>
        </select>`;
      regionLabel?.insertAdjacentElement('afterend', apiVersionLabel);
    }

    if (!q('#scanner-judge-endpoint')) {
      const scannerLabel = document.createElement('label');
      scannerLabel.className = 'drawer-field drawer-field-full';
      scannerLabel.innerHTML = `
        AI Scanner Judge Endpoint
        <input id="scanner-judge-endpoint" readonly aria-readonly="true"
          placeholder="Trend-hosted TMAS judge" />
        <small class="drawer-help">
          Uses the Trend-hosted TMAS judge unless a self-hosted judge is configured externally.
        </small>`;
      endpointLabel?.insertAdjacentElement('afterend', scannerLabel);
    }

    qa('#guard-content .policy-grid label').forEach(label => {
      label.classList.add('drawer-policy-item');
    });

    const toggle = q('#guard-content .toggle-line');
    if (toggle) toggle.classList.add('drawer-demo-card');

    const actionRow = q('#guard-content .action-row');
    if (actionRow) actionRow.classList.add('drawer-actions');

    const statusHero = q('#guard-content .status-hero');
    if (statusHero) statusHero.classList.add('drawer-status');

    q('#guard-content .code-note')?.classList.add('drawer-code-note');
  };

  const updateDrawerState = () => {
    const settings = window.state?.settings || state?.settings;
    const guardSettings = settings?.aiGuard;

    const scannerJudge = q('#scanner-judge-endpoint');
    if (scannerJudge) {
      scannerJudge.value = 'Managed by Trend-hosted TMAS';
    }

    const apiKeyInput = q('#guard-api-key');
    const saveButton = q('#save-guard');
    const allowed = Boolean(guardSettings?.runtimeConfigurationAllowed);

    if (apiKeyInput) {
      apiKeyInput.disabled = !allowed;
      apiKeyInput.placeholder = allowed
        ? 'Using server default — enter here to override'
        : 'Managed by Kubernetes Secret';
    }

    if (saveButton && !allowed) {
      saveButton.disabled = true;
      saveButton.textContent = 'Managed by Kubernetes Secret';
    } else if (saveButton) {
      saveButton.disabled = false;
      saveButton.textContent = 'Save & Enable';
    }

    const badge = q('#guard-status-badge');
    if (badge && guardSettings?.configured) {
      badge.textContent = 'Live';
      badge.className = 'pill success';
    }
  };

  const enterSettingsDrawer = () => {
    removeLegacySettingsPopover();
    ensureDrawerMarkup();

    modalBackdrop.classList.add('settings-drawer-mode');
    modal.classList.add('settings-drawer-mode');

    if (typeof activateSecurityTab === 'function') {
      activateSecurityTab('guard');
    }

    q('#security-eyebrow').textContent = 'VISION ONE · AI APPLICATION SECURITY';
    q('#security-title').textContent = 'AI Application Security Configuration';
    q('#security-description').textContent = 'Configure TrendAI Vision One AI Guard and scanner connectivity.';

    if (typeof openModal === 'function') {
      openModal('security-modal', 'guard');
    } else {
      modalBackdrop.classList.add('open');
      modalBackdrop.setAttribute('aria-hidden', 'false');
    }

    window.setTimeout(updateDrawerState, 0);
  };

  const exitSettingsDrawer = () => {
    modalBackdrop.classList.remove('settings-drawer-mode');
    modal.classList.remove('settings-drawer-mode');
  };

  removeLegacySettingsPopover();
  ensureDrawerMarkup();

  const settingsButton = cleanSettingsButton();
  settingsButton?.addEventListener('click', event => {
    event.preventDefault();
    event.stopPropagation();
    enterSettingsDrawer();
  });

  qa('#open-ai-scanner, #scanner-promo, .security-tabs button').forEach(element => {
    element.addEventListener('click', exitSettingsDrawer, true);
  });

  qa('[data-close="security-modal"]').forEach(button => {
    button.addEventListener('click', exitSettingsDrawer);
  });

  modalBackdrop.addEventListener('click', event => {
    if (event.target === modalBackdrop) exitSettingsDrawer();
  });

  // v9: drawer cleanup is handled by explicit close events.

  window.setTimeout(updateDrawerState, 900);
})();


/* BAM_BANK_UI_REVISION_V6 */
(() => {
  const chatPanel = document.querySelector('#chat-panel');
  const chatLauncher = document.querySelector('#chat-launcher');
  const demoPromos = document.querySelector('#demo-promos');

  if (!chatPanel || !chatLauncher || !demoPromos) return;

  const syncBamskyUi = () => {
    const isOpen = chatPanel.classList.contains('open');

    demoPromos.classList.toggle('chat-open', isOpen);

    chatLauncher.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
    chatLauncher.setAttribute(
      'aria-label',
      isOpen ? 'Close Bamsky banking assistant' : 'Open Bamsky banking assistant'
    );
  };

  new MutationObserver(syncBamskyUi).observe(chatPanel, {
    attributes: true,
    attributeFilter: ['class']
  });

  syncBamskyUi();
})();


/* BAM_BANK_UI_REVISION_V8 */
(() => {
  const q = (selector, root = document) => root.querySelector(selector);

  const heroCopy = {
    en: {
      eyebrow: 'BAM PRIVATE DIGITAL BANKING',
      title: 'Your money, beautifully in motion.',
      body: 'A clearer view of spending, saving, and intelligent protection—built for everyday decisions.',
      ask: 'Ask Bamsky',
      security: 'Security center',
      protected: 'AI Guard protected',
      scanner: 'AI Scanner assessment ready',
      cardLabel: 'Smart balance',
      cardValue: 'Rp142.850.000',
      cardStatus: 'Protected in real time',
      trendLabel: 'Monthly momentum',
      trendValue: '+12.4%',
      trendText: 'across your synthetic portfolio'
    },
    id: {
      eyebrow: 'PERBANKAN DIGITAL PRIVAT BAM',
      title: 'Keuangan Anda, bergerak lebih cerdas.',
      body: 'Pantau pengeluaran, tabungan, dan perlindungan cerdas dalam satu pengalaman yang lebih jernih.',
      ask: 'Tanya Bamsky',
      security: 'Pusat keamanan',
      protected: 'Dilindungi AI Guard',
      scanner: 'AI Scanner siap untuk assessment',
      cardLabel: 'Saldo cerdas',
      cardValue: 'Rp142.850.000',
      cardStatus: 'Terlindungi secara real-time',
      trendLabel: 'Momentum bulanan',
      trendValue: '+12,4%',
      trendText: 'pada portofolio sintetis Anda'
    }
  };

  const currentLanguage = () =>
    localStorage.getItem('bam-language') === 'id' ||
    document.documentElement.lang === 'id'
      ? 'id'
      : 'en';

  function installSettingsIcon() {
    const button = q('#settings-button');
    if (!button) return;

    button.innerHTML = `
      <svg class="settings-gear-icon" viewBox="0 0 24 24"
        aria-hidden="true" focusable="false">
        <circle cx="12" cy="12" r="3.2"></circle>
        <path d="M19.2 13.4c.08-.46.12-.93.12-1.4s-.04-.94-.12-1.4l2-1.57-2.03-3.52-2.49 1a7.7 7.7 0 0 0-2.42-1.4L13.88 2.4H9.8l-.38 2.71A7.7 7.7 0 0 0 7 6.51l-2.49-1-2.03 3.52 2 1.57c-.08.46-.12.93-.12 1.4s.04.94.12 1.4l-2 1.57 2.03 3.52 2.49-1a7.7 7.7 0 0 0 2.42 1.4l.38 2.71h4.08l.38-2.71a7.7 7.7 0 0 0 2.42-1.4l2.49 1 2.03-3.52-2-1.57Z"></path>
      </svg>`;

    button.setAttribute('aria-label', 'AI Application Security Configuration');
    button.setAttribute('title', 'AI Application Security Configuration');
  }

  function installHero() {
    const dashboard = q('#dashboard-page');
    const quickActions = q('#dashboard-page .quick-actions');
    if (!dashboard || !quickActions || q('#bam-experience-hero')) return;

    const hero = document.createElement('section');
    hero.id = 'bam-experience-hero';
    hero.className = 'bam-experience-hero';
    hero.innerHTML = `
      <div class="bam-hero-copy">
        <div class="bam-hero-eyebrow">
          <span class="bam-pulse-dot"></span>
          <span id="bam-hero-eyebrow"></span>
        </div>
        <h2 id="bam-hero-title"></h2>
        <p id="bam-hero-body"></p>

        <div class="bam-hero-actions">
          <button type="button" class="bam-hero-primary" id="bam-hero-chat">
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path d="M5.8 5.2h12.4A2.8 2.8 0 0 1 21 8v7.2a2.8 2.8 0 0 1-2.8 2.8H11l-5.8 3v-3.2A2.8 2.8 0 0 1 3 15.2V8a2.8 2.8 0 0 1 2.8-2.8Z"></path>
            </svg>
            <span id="bam-hero-ask"></span>
          </button>
          <button type="button" class="bam-hero-secondary" id="bam-hero-security">
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path d="M12 2.8 19 5.6v5.7c0 4.4-2.8 8.2-7 9.9-4.2-1.7-7-5.5-7-9.9V5.6l7-2.8Z"></path>
              <path d="m9.1 12 1.8 1.8 4.2-4.2"></path>
            </svg>
            <span id="bam-hero-security-label"></span>
          </button>
        </div>

        <div class="bam-trust-row">
          <span><i class="bam-status-dot bam-status-green"></i><b id="bam-trust-guard"></b></span>
          <span><i class="bam-status-dot bam-status-cyan"></i><b id="bam-trust-scanner"></b></span>
        </div>
      </div>

      <div class="bam-hero-visual" aria-hidden="true">
        <div class="bam-aurora bam-aurora-one"></div>
        <div class="bam-aurora bam-aurora-two"></div>

        <svg class="bam-orbit-art" viewBox="0 0 520 380" focusable="false">
          <defs>
            <linearGradient id="bamOrbitGradient" x1="0" y1="0" x2="1" y2="1">
              <stop offset="0" stop-color="#8EF0D0"/>
              <stop offset=".52" stop-color="#7DB6FF"/>
              <stop offset="1" stop-color="#B09CFF"/>
            </linearGradient>
            <linearGradient id="bamLineGradient" x1="0" y1="1" x2="1" y2="0">
              <stop offset="0" stop-color="#7DE7C4"/>
              <stop offset="1" stop-color="#90A8FF"/>
            </linearGradient>
          </defs>
          <ellipse cx="300" cy="198" rx="176" ry="112" fill="none"
            stroke="url(#bamOrbitGradient)" stroke-width="1.4" opacity=".48"
            transform="rotate(-18 300 198)"/>
          <ellipse cx="300" cy="198" rx="132" ry="82" fill="none"
            stroke="#D4E4FF" stroke-width="1" opacity=".32"
            transform="rotate(19 300 198)"/>
          <circle cx="300" cy="198" r="72" fill="#FFFFFF" fill-opacity=".08"
            stroke="#FFFFFF" stroke-opacity=".22"/>
          <circle cx="300" cy="198" r="54" fill="url(#bamOrbitGradient)" fill-opacity=".15"/>
          <path d="M162 247 C215 235 238 198 276 206 C319 215 334 162 376 171 C404 177 417 151 449 132"
            fill="none" stroke="url(#bamLineGradient)" stroke-width="6" stroke-linecap="round"/>
          <path d="M162 247 C215 235 238 198 276 206 C319 215 334 162 376 171 C404 177 417 151 449 132"
            fill="none" stroke="#FFFFFF" stroke-opacity=".25" stroke-width="1.3"/>
          <circle cx="162" cy="247" r="7" fill="#8EF0D0"/>
          <circle cx="276" cy="206" r="7" fill="#A5BEFF"/>
          <circle cx="376" cy="171" r="7" fill="#A898FF"/>
          <circle cx="449" cy="132" r="8" fill="#FFFFFF"/>
          <path d="M282 180 300 172l18 8v15c0 13-7.4 24-18 29-10.6-5-18-16-18-29v-15Z"
            fill="#FFFFFF" fill-opacity=".94"/>
          <path d="m292 197 6 6 11-13" fill="none" stroke="#315EFB"
            stroke-width="5" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>

        <div class="bam-float-card bam-balance-card">
          <span id="bam-visual-card-label"></span>
          <strong id="bam-visual-card-value"></strong>
          <small id="bam-visual-card-status"></small>
        </div>

        <div class="bam-float-card bam-insight-card">
          <span id="bam-visual-trend-label"></span>
          <strong id="bam-visual-trend-value"></strong>
          <small id="bam-visual-trend-text"></small>
        </div>
      </div>`;

    dashboard.insertBefore(hero, quickActions);

    q('#bam-hero-chat')?.addEventListener('click', () => {
      q('#chat-panel')?.classList.add('open');
    });

    q('#bam-hero-security')?.addEventListener('click', () => {
      q('#settings-button')?.click();
    });
  }

  function syncHeroLanguage() {
    const text = heroCopy[currentLanguage()];
    const values = {
      '#bam-hero-eyebrow': text.eyebrow,
      '#bam-hero-title': text.title,
      '#bam-hero-body': text.body,
      '#bam-hero-ask': text.ask,
      '#bam-hero-security-label': text.security,
      '#bam-trust-guard': text.protected,
      '#bam-trust-scanner': text.scanner,
      '#bam-visual-card-label': text.cardLabel,
      '#bam-visual-card-value': text.cardValue,
      '#bam-visual-card-status': text.cardStatus,
      '#bam-visual-trend-label': text.trendLabel,
      '#bam-visual-trend-value': text.trendValue,
      '#bam-visual-trend-text': text.trendText
    };

    Object.entries(values).forEach(([selector, value]) => {
      const node = q(selector);
      if (node) node.textContent = value;
    });
  }

  function installOverlayBehavior() {
    const chatPanel = q('#chat-panel');
    const securityBackdrop = q('#security-modal');
    const demoPromos = q('#demo-promos');
    if (!demoPromos) return;

    const sync = () => {
      const chatOpen = Boolean(chatPanel?.classList.contains('open'));
      const securityOpen = Boolean(securityBackdrop?.classList.contains('open'));
      demoPromos.classList.toggle(
        'assistant-or-security-open',
        chatOpen || securityOpen
      );
    };

    if (chatPanel) {
      new MutationObserver(sync).observe(chatPanel, {
        attributes: true,
        attributeFilter: ['class']
      });
    }

    if (securityBackdrop) {
      new MutationObserver(sync).observe(securityBackdrop, {
        attributes: true,
        attributeFilter: ['class']
      });
    }

    sync();
  }

  function bindLanguageSync() {
    q('#language')?.addEventListener('change', () => {
      window.setTimeout(syncHeroLanguage, 0);
    });
    q('#settings-language')?.addEventListener('change', () => {
      window.setTimeout(syncHeroLanguage, 0);
    });
    new MutationObserver(syncHeroLanguage).observe(document.documentElement, {
      attributes: true,
      attributeFilter: ['lang']
    });
  }

  installSettingsIcon();
  installHero();
  syncHeroLanguage();
  installOverlayBehavior();
  bindLanguageSync();
})();


/* BAM_BANK_UI_REVISION_V9 */
(() => {
  const q = (selector, root = document) => root.querySelector(selector);
  const qa = (selector, root = document) => [...root.querySelectorAll(selector)];

  const securityBackdrop = q('#security-modal');
  const securityModal = q('#security-modal .security-modal');

  function safeCloseSecurity(event) {
    event?.preventDefault();
    event?.stopPropagation();
    event?.stopImmediatePropagation?.();

    securityBackdrop?.classList.remove('open', 'settings-drawer-mode');
    securityBackdrop?.setAttribute('aria-hidden', 'true');
    securityModal?.classList.remove('settings-drawer-mode');
    document.body.classList.remove('security-overlay-open');
  }

  function installSafeClose() {
    const oldClose = q('[data-close="security-modal"]');
    if (oldClose) {
      const newClose = oldClose.cloneNode(true);
      oldClose.replaceWith(newClose);
      newClose.addEventListener('click', safeCloseSecurity, true);
    }

    securityBackdrop?.addEventListener('click', event => {
      if (event.target === securityBackdrop) {
        safeCloseSecurity(event);
      }
    }, true);

    document.addEventListener('keydown', event => {
      if (
        event.key === 'Escape' &&
        securityBackdrop?.classList.contains('open')
      ) {
        safeCloseSecurity(event);
      }
    });

    q('#settings-button')?.addEventListener('click', () => {
      document.body.classList.add('security-overlay-open');
      window.setTimeout(syncGuardControls, 0);
    });
  }

  function installPolicyIds() {
    const policyInputs = qa('#guard-content .policy-grid input[type="checkbox"]');
    const definitions = [
      ['guard-policy-prompt-injection', 'Prompt Injection'],
      ['guard-policy-jailbreak', 'Jailbreak'],
      ['guard-policy-harmful', 'Harmful Content'],
      ['guard-policy-pii', 'PII Redaction']
    ];

    policyInputs.forEach((input, index) => {
      const definition = definitions[index];
      if (!definition) return;

      input.id = definition[0];
      const label = input.closest('label');
      if (label) {
        label.setAttribute('for', definition[0]);
        label.classList.add('editable-policy');
      }
    });

    const policyGrid = q('#guard-content .policy-grid');
    if (policyGrid && !q('#guard-policy-note')) {
      const note = document.createElement('p');
      note.id = 'guard-policy-note';
      note.className = 'guard-policy-note';
      note.textContent = 'Selected policies control local Force Demo Mode. Live Trend-hosted enforcement continues to follow the policy configured in Vision One.';
      policyGrid.insertAdjacentElement('afterend', note);
    }

    const demoToggle = q('#force-demo-mode');
    const demoCard = demoToggle?.closest('label');
    if (demoCard) {
      const title = demoCard.querySelector('span');
      const help = demoCard.querySelector('small');
      if (title) title.textContent = 'Force Demo Mode';
      if (help) {
        help.textContent = 'Use local policy matching instead of the live API. Ideal for offline presentation and connectivity testing.';
      }
    }
  }

  async function syncGuardControls() {
    installPolicyIds();

    let settings = state.settings;
    try {
      settings = await api('/api/settings');
      state.settings = settings;
    } catch (_) {
      // Keep the most recently loaded state when refresh fails.
    }

    const guardSettings = settings?.aiGuard || {};
    const allowed = Boolean(guardSettings.runtimeConfigurationAllowed);
    const policies = guardSettings.policies || {};

    const editableSelectors = [
      '#guard-api-key',
      '#guard-region',
      '#guard-app-name',
      '#force-demo-mode',
      '#guard-policy-prompt-injection',
      '#guard-policy-jailbreak',
      '#guard-policy-harmful',
      '#guard-policy-pii'
    ];

    editableSelectors.forEach(selector => {
      const control = q(selector);
      if (control) control.disabled = !allowed;
    });

    const values = {
      '#guard-policy-prompt-injection': policies.promptInjection ?? true,
      '#guard-policy-jailbreak': policies.jailbreak ?? true,
      '#guard-policy-harmful': policies.harmfulContent ?? true,
      '#guard-policy-pii': policies.pii ?? true
    };

    Object.entries(values).forEach(([selector, checked]) => {
      const input = q(selector);
      if (input) input.checked = Boolean(checked);
    });

    const demoToggle = q('#force-demo-mode');
    if (demoToggle) {
      demoToggle.checked = Boolean(guardSettings.forceDemoMode);
    }

    const saveButton = q('#save-guard');
    if (saveButton) {
      saveButton.disabled = !allowed;
      saveButton.textContent = allowed
        ? 'Save & Enable'
        : 'Managed by Kubernetes Secret';
    }

    const note = q('#guard-policy-note');
    if (note) {
      note.dataset.locked = allowed ? 'false' : 'true';
      if (!allowed) {
        note.textContent = 'Runtime editing is disabled by the server. Start the container with ALLOW_RUNTIME_CONFIG=true to edit and save these controls.';
      }
    }
  }

  function installScannerModeSwitch() {
    const scannerContent = q('#scanner-content');
    if (!scannerContent || q('#scanner-execution-mode')) return;

    state.scannerMode = 'demo';

    const switcher = document.createElement('section');
    switcher.id = 'scanner-execution-mode';
    switcher.className = 'scanner-execution-mode';
    switcher.innerHTML = `
      <div class="scanner-mode-tabs" role="tablist" aria-label="AI Scanner execution mode">
        <button type="button" class="active" data-scanner-mode="demo" role="tab" aria-selected="true">Demo</button>
        <button type="button" data-scanner-mode="live" role="tab" aria-selected="false">Live</button>
      </div>
      <div class="scanner-mode-copy">
        <strong id="scanner-mode-title">Demo Mode</strong>
        <span id="scanner-mode-description">Simulated campaign with deterministic results and no external scan execution.</span>
      </div>`;

    const steps = q('.scanner-steps', scannerContent);
    scannerContent.insertBefore(switcher, steps || scannerContent.firstChild);

    const stepTwo = q('#scanner-step-2');
    if (stepTwo && !q('#scanner-live-guidance')) {
      const guidance = document.createElement('div');
      guidance.id = 'scanner-live-guidance';
      guidance.className = 'scanner-live-guidance hidden';
      guidance.innerHTML = `
        <strong>Live endpoint validation</strong>
        <p>This sends actual adversarial prompts through the selected application path. Use the TMAS command below for the complete Vision One AI Scanner campaign and report.</p>`;
      stepTwo.insertBefore(guidance, stepTwo.firstChild);
    }

    const results = q('#scan-results');
    if (results && !q('#scanner-result-mode')) {
      const header = document.createElement('div');
      header.className = 'scanner-result-header';
      header.innerHTML = `
        <span id="scanner-result-mode" class="scanner-result-mode demo">DEMO SIMULATION</span>
        <p id="scanner-result-errors" class="scanner-result-errors hidden"></p>`;
      results.insertBefore(header, results.firstChild);
    }

    const setMode = mode => {
      state.scannerMode = mode;

      qa('[data-scanner-mode]', switcher).forEach(button => {
        const active = button.dataset.scannerMode === mode;
        button.classList.toggle('active', active);
        button.setAttribute('aria-selected', active ? 'true' : 'false');
      });

      const live = mode === 'live';
      q('#scanner-mode-title').textContent = live
        ? 'Live Mode'
        : 'Demo Mode';
      q('#scanner-mode-description').textContent = live
        ? 'Runs real prompts through the configured LLM and AI Guard path. Full TMAS execution remains available through the generated command.'
        : 'Simulated campaign with deterministic results and no external scan execution.';

      q('#scanner-live-guidance')?.classList.toggle('hidden', !live);

      const runButton = q('#run-scan');
      if (runButton) {
        runButton.textContent = live
          ? 'Run Live Validation'
          : 'Run Demo Scan';
      }

      const commandTitle = q('.tmas-command p');
      if (commandTitle) {
        commandTitle.textContent = live
          ? 'Full TMAS live assessment command'
          : 'TMAS command for a real assessment';
      }
    };

    qa('[data-scanner-mode]', switcher).forEach(button => {
      button.addEventListener('click', () => {
        setMode(button.dataset.scannerMode);
      });
    });

    setMode('demo');
  }

  installSafeClose();
  installPolicyIds();
  installScannerModeSwitch();

  q('#settings-button')?.addEventListener('click', () => {
    window.setTimeout(syncGuardControls, 20);
  });

  q('#save-guard')?.addEventListener('click', () => {
    window.setTimeout(syncGuardControls, 450);
  });

  window.setTimeout(syncGuardControls, 100);
  window.setTimeout(syncGuardControls, 900);
})();


/* BAM_BANK_UI_REVISION_V10 */
(() => {
  const q = (selector, root = document) => root.querySelector(selector);
  const qa = (selector, root = document) => [...root.querySelectorAll(selector)];

  const uiState = { transactions: [], activePage: 'dashboard' };

  function currentLanguage() {
    return localStorage.getItem('bam-language') === 'id' ||
      document.documentElement.lang === 'id' ? 'id' : 'en';
  }

  function cloneForCleanEvents(selector) {
    const node = q(selector);
    if (!node) return null;
    const clone = node.cloneNode(true);
    node.replaceWith(clone);
    return clone;
  }

  function closeSidebar() {
    document.body.classList.remove('sidebar-is-open');
    q('#sidebar-toggle')?.setAttribute('aria-expanded', 'false');
    q('#sidebar-backdrop')?.setAttribute('aria-hidden', 'true');
  }

  function openSidebar() {
    document.body.classList.add('sidebar-is-open');
    q('#sidebar-toggle')?.setAttribute('aria-expanded', 'true');
    q('#sidebar-backdrop')?.setAttribute('aria-hidden', 'false');
  }

  function installSidebarController() {
    const sidebar = q('.sidebar');
    const topbar = q('.topbar');
    if (!sidebar || !topbar) return;

    if (!q('#sidebar-toggle')) {
      const toggle = document.createElement('button');
      toggle.type = 'button';
      toggle.id = 'sidebar-toggle';
      toggle.className = 'sidebar-toggle';
      toggle.setAttribute('aria-label', 'Show or hide navigation');
      toggle.setAttribute('aria-expanded', 'false');
      toggle.innerHTML = `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 7h16M4 12h16M4 17h16"></path></svg>`;
      topbar.insertBefore(toggle, topbar.firstChild);
      toggle.addEventListener('click', event => {
        event.preventDefault();
        document.body.classList.contains('sidebar-is-open') ? closeSidebar() : openSidebar();
      });
    }

    if (!q('#sidebar-close')) {
      const close = document.createElement('button');
      close.type = 'button';
      close.id = 'sidebar-close';
      close.className = 'sidebar-close';
      close.setAttribute('aria-label', 'Close navigation');
      close.innerHTML = `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m6 6 12 12M18 6 6 18"></path></svg>`;
      sidebar.appendChild(close);
      close.addEventListener('click', closeSidebar);
    }

    if (!q('#sidebar-backdrop')) {
      const backdrop = document.createElement('button');
      backdrop.type = 'button';
      backdrop.id = 'sidebar-backdrop';
      backdrop.className = 'sidebar-backdrop';
      backdrop.setAttribute('aria-label', 'Close navigation');
      backdrop.setAttribute('aria-hidden', 'true');
      document.body.appendChild(backdrop);
      backdrop.addEventListener('click', closeSidebar);
    }

    closeSidebar();
  }

  function greetingForHour(hour, language) {
    if (language === 'id') {
      if (hour < 11) return 'Selamat pagi';
      if (hour < 15) return 'Selamat siang';
      if (hour < 18) return 'Selamat sore';
      return 'Selamat malam';
    }
    if (hour < 12) return 'Good morning';
    if (hour < 18) return 'Good afternoon';
    return 'Good evening';
  }

  function updateSimpleHeader(page = uiState.activePage) {
    uiState.activePage = page || 'dashboard';
    const language = currentLanguage();
    const title = q('#page-title');
    if (!title) return;

    const pageTitles = language === 'id'
      ? { accounts: 'Rekening', payments: 'Pembayaran', invest: 'Investasi', support: 'Bantuan' }
      : { accounts: 'Accounts', payments: 'Payments', invest: 'Investments', support: 'Support' };

    const nextText = uiState.activePage === 'dashboard'
      ? `${greetingForHour(new Date().getHours(), language)}, Karim.`
      : pageTitles[uiState.activePage] || pageTitles.accounts;

    if (title.textContent !== nextText) title.textContent = nextText;
  }

  function formatTime(date, language) {
    const now = new Date();
    const sameDay = date.toDateString() === now.toDateString();
    const yesterday = new Date(now);
    yesterday.setDate(now.getDate() - 1);
    const wasYesterday = date.toDateString() === yesterday.toDateString();
    const time = new Intl.DateTimeFormat(
      language === 'id' ? 'id-ID' : 'en-GB',
      { hour: '2-digit', minute: '2-digit' }
    ).format(date);

    if (sameDay) return language === 'id' ? `Hari ini, ${time}` : `Today, ${time}`;
    if (wasYesterday) return language === 'id' ? `Kemarin, ${time}` : `Yesterday, ${time}`;
    return new Intl.DateTimeFormat(
      language === 'id' ? 'id-ID' : 'en-GB',
      { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' }
    ).format(date);
  }

  function formatRupiah(amount, positive) {
    const formatted = new Intl.NumberFormat('id-ID', {
      style: 'currency',
      currency: 'IDR',
      maximumFractionDigits: 0
    }).format(Math.abs(amount));
    return `${positive ? '+' : '−'}${formatted}`;
  }

  function generateTransactions() {
    const merchants = [
      { icon: 'RA', name: 'Ruang Asa Coffee', en: 'Dining', id: 'Makan', min: 38000, max: 128000 },
      { icon: 'NS', name: 'Nusantara Rail', en: 'Transport', id: 'Transportasi', min: 75000, max: 420000 },
      { icon: 'AL', name: 'Awan Lokal Market', en: 'Groceries', id: 'Belanja Harian', min: 165000, max: 890000 },
      { icon: 'SK', name: 'Saku Kreatif Studio', en: 'Digital service', id: 'Layanan Digital', min: 99000, max: 575000 },
      { icon: 'HB', name: 'Hutan Biru Living', en: 'Home & living', id: 'Rumah & Gaya Hidup', min: 245000, max: 1450000 },
      { icon: 'KL', name: 'Kelana Airlines', en: 'Travel', id: 'Perjalanan', min: 985000, max: 3850000 },
      { icon: 'SE', name: 'Sehat Everyday', en: 'Health', id: 'Kesehatan', min: 125000, max: 780000 },
      { icon: 'PC', name: 'Pijar Cloud', en: 'Cloud subscription', id: 'Langganan Cloud', min: 149000, max: 650000 },
      { icon: 'BT', name: 'Bumi Terang Energy', en: 'Utilities', id: 'Utilitas', min: 325000, max: 1250000 },
      { icon: 'AM', name: 'Arunika Mobility', en: 'Ride service', id: 'Transportasi Online', min: 28000, max: 235000 },
      { icon: 'MP', name: 'Mitra Pangan Lab', en: 'Food delivery', id: 'Pesan Makanan', min: 72000, max: 365000 },
      { icon: 'RF', name: 'Rupa Film Club', en: 'Entertainment', id: 'Hiburan', min: 59000, max: 225000 },
      { icon: 'NX', name: 'Nexora Payroll', en: 'Income', id: 'Pendapatan', min: 18500000, max: 27500000, income: true },
      { icon: 'BI', name: 'BAM Investment Yield', en: 'Investment return', id: 'Imbal Hasil Investasi', min: 850000, max: 3200000, income: true },
      { icon: 'DP', name: 'Dana Pintar Cashback', en: 'Cashback', id: 'Cashback', min: 45000, max: 450000, income: true }
    ];
    const selected = [...merchants].sort(() => Math.random() - 0.5).slice(0, 5);
    uiState.transactions = selected.map((item, index) => {
      const amount = Math.round(item.min + Math.random() * (item.max - item.min));
      const hoursAgo = index === 0 ? Math.random() * 4 : 4 + Math.random() * 92;
      return { ...item, amount, date: new Date(Date.now() - hoursAgo * 60 * 60 * 1000) };
    }).sort((a, b) => b.date - a.date);
  }

  function renderTransactions() {
    const list = q('.transaction-list');
    if (!list) return;
    if (!uiState.transactions.length) generateTransactions();
    const language = currentLanguage();
    list.innerHTML = '';

    uiState.transactions.forEach(item => {
      const row = document.createElement('div');
      row.className = 'transaction bam-random-transaction';
      const icon = document.createElement('span');
      icon.className = 'transaction-icon';
      icon.textContent = item.icon;
      const copy = document.createElement('div');
      const merchant = document.createElement('strong');
      merchant.textContent = item.name;
      const detail = document.createElement('small');
      detail.textContent = `${formatTime(item.date, language)} · ${language === 'id' ? item.id : item.en}`;
      copy.append(merchant, detail);
      const amount = document.createElement('b');
      amount.className = item.income ? 'positive' : 'negative';
      amount.textContent = formatRupiah(item.amount, Boolean(item.income));
      row.append(icon, copy, amount);
      list.appendChild(row);
    });
  }

  function installMastercardBrand() {
    const brand = q('.bank-card-top span:last-child');
    const number = q('.bank-card > strong');
    if (!brand) return;
    brand.className = 'mastercard-brand';
    brand.setAttribute('aria-label', 'Mastercard');
    brand.innerHTML = `
      <svg class="mastercard-symbol" viewBox="0 0 76 48" aria-hidden="true">
        <circle cx="28" cy="24" r="20" fill="#EB001B"></circle>
        <circle cx="48" cy="24" r="20" fill="#F79E1B"></circle>
        <path d="M38 8.9a20 20 0 0 1 0 30.2A20 20 0 0 1 38 8.9Z" fill="#FF5F00"></path>
      </svg>
      <span class="mastercard-wordmark">mastercard</span>`;
    if (number) number.textContent = '5454 •••• •••• 7842';
  }

  async function updateSecurityLanguage() {
    const language = currentLanguage();
    const payButton = qa('.quick-actions button').find(button => {
      const title = button.querySelector('strong')?.textContent.toLowerCase() || '';
      return title.includes('pay bills') || title.includes('bayar tagihan');
    }) || qa('.quick-actions button')[0];

    if (payButton) {
      payButton.classList.add('pay-bills-secured');
      let badge = q('.file-security-badge', payButton);
      if (!badge) {
        badge = document.createElement('em');
        badge.className = 'file-security-badge';
        payButton.appendChild(badge);
      }
      const subtitle = payButton.querySelector('small');
      if (subtitle) {
        subtitle.textContent = language === 'id'
          ? 'Unggah tagihan untuk dipindai sebelum diproses'
          : 'Upload a bill for scanning before processing';
      }

      let configured = Boolean(state.settings?.fileSecurity?.sdkConfigured);
      let enabled = Boolean(state.settings?.fileSecurity?.enabled);
      try {
        if (!state.settings) state.settings = await api('/api/settings');
        configured = Boolean(state.settings?.fileSecurity?.sdkConfigured);
        enabled = Boolean(state.settings?.fileSecurity?.enabled);
      } catch (_) {}

      badge.textContent = language === 'id'
        ? configured ? 'Dilindungi File Security' : enabled ? 'Pemindaian File Security aktif' : 'Perlindungan file belum aktif'
        : configured ? 'Protected by File Security' : enabled ? 'File Security scanning enabled' : 'File protection not enabled';
    }

    const scannerTrust = q('#bam-trust-scanner');
    if (scannerTrust) {
      scannerTrust.textContent = language === 'id'
        ? 'AI Scanner siap untuk assessment'
        : 'AI Scanner assessment ready';
    }
  }

  function removeDrawerMode() {
    q('#security-modal')?.classList.remove('settings-drawer-mode');
    q('#security-modal .security-modal')?.classList.remove('settings-drawer-mode');
  }

  function setSecurityHeading(settingsMode) {
    const eyebrow = q('#security-eyebrow') || q('#security-modal .modal-header .eyebrow');
    const title = q('#security-title') || q('#security-modal .modal-header h2');
    const description = q('#security-description') || q('#security-modal .modal-header div > p:last-child');

    if (settingsMode) {
      if (eyebrow) eyebrow.textContent = 'VISION ONE · AI APPLICATION SECURITY';
      if (title) title.textContent = 'AI Application Security Configuration';
      if (description) description.textContent = 'Configure TrendAI Vision One AI Guard and scanner connectivity.';
    } else {
      if (eyebrow) eyebrow.textContent = 'VISION ONE · AI APPLICATION SECURITY';
      if (title) title.textContent = 'AI Application Security';
      if (description) description.textContent = 'Assessment, runtime enforcement, and malicious file prevention.';
    }
  }

  async function refreshGuardControls() {
    try {
      const settings = await api('/api/settings');
      state.settings = settings;
      const guard = settings.aiGuard || {};
      const allowed = Boolean(guard.runtimeConfigurationAllowed);
      const policies = guard.policies || {};

      [
        '#guard-api-key', '#guard-region', '#guard-app-name', '#force-demo-mode',
        '#guard-policy-prompt-injection', '#guard-policy-jailbreak',
        '#guard-policy-harmful', '#guard-policy-pii'
      ].forEach(selector => {
        const control = q(selector);
        if (control) control.disabled = !allowed;
      });

      const policyValues = {
        '#guard-policy-prompt-injection': policies.promptInjection ?? true,
        '#guard-policy-jailbreak': policies.jailbreak ?? true,
        '#guard-policy-harmful': policies.harmfulContent ?? true,
        '#guard-policy-pii': policies.pii ?? true
      };
      Object.entries(policyValues).forEach(([selector, value]) => {
        const control = q(selector);
        if (control) control.checked = Boolean(value);
      });

      const demo = q('#force-demo-mode');
      if (demo) demo.checked = Boolean(guard.forceDemoMode);
      const save = q('#save-guard');
      if (save) {
        save.disabled = !allowed;
        save.textContent = allowed ? 'Save & Enable' : 'Managed by Kubernetes Secret';
      }
    } catch (error) {
      toast(`Unable to refresh settings: ${error.message}`);
    }
  }

  function closeSecurity() {
    const backdrop = q('#security-modal');
    backdrop?.classList.remove('open', 'settings-drawer-mode');
    backdrop?.setAttribute('aria-hidden', 'true');
    q('#security-modal .security-modal')?.classList.remove('settings-drawer-mode');
    document.body.classList.remove('security-overlay-open');
  }

  function openSecurity(tab, settingsMode = false) {
    const backdrop = q('#security-modal');
    const modal = q('#security-modal .security-modal');
    if (!backdrop || !modal) return;

    backdrop.classList.toggle('settings-drawer-mode', settingsMode);
    modal.classList.toggle('settings-drawer-mode', settingsMode);
    setSecurityHeading(settingsMode);
    activateSecurityTab(tab);
    backdrop.classList.add('open');
    backdrop.setAttribute('aria-hidden', 'false');
    document.body.classList.add('security-overlay-open');
    if (settingsMode) refreshGuardControls();
  }

  function installStableInteractions() {
    const navButtons = qa('.nav-item[data-page]').map(button => {
      const clone = button.cloneNode(true);
      button.replaceWith(clone);
      return clone;
    });

    navButtons.forEach(button => {
      button.addEventListener('click', event => {
        event.preventDefault();
        const page = button.dataset.page;
        if (!page) return;
        showPage(page);
        uiState.activePage = page;
        updateSimpleHeader(page);
        if (page === 'dashboard') renderTransactions();
        closeSidebar();
      });
    });

    cloneForCleanEvents('#open-ai-scanner')?.addEventListener('click', event => {
      event.preventDefault();
      openSecurity('scanner', false);
      closeSidebar();
    });

    cloneForCleanEvents('#settings-button')?.addEventListener('click', event => {
      event.preventDefault();
      openSecurity('guard', true);
    });

    cloneForCleanEvents('[data-close="security-modal"]')?.addEventListener('click', event => {
      event.preventDefault();
      event.stopPropagation();
      closeSecurity();
    });

    qa('.security-tabs button').forEach(button => {
      const clone = button.cloneNode(true);
      button.replaceWith(clone);
      clone.addEventListener('click', event => {
        event.preventDefault();
        removeDrawerMode();
        setSecurityHeading(false);
        activateSecurityTab(clone.dataset.securityTab);
      });
    });

    cloneForCleanEvents('#chat-launcher')?.addEventListener('click', event => {
      event.preventDefault();
      q('#chat-panel')?.classList.toggle('open');
    });

    cloneForCleanEvents('#chat-close')?.addEventListener('click', event => {
      event.preventDefault();
      q('#chat-panel')?.classList.remove('open');
    });

    cloneForCleanEvents('#configure-guard')?.addEventListener('click', event => {
      event.preventDefault();
      openSecurity('guard', true);
    });

    cloneForCleanEvents('#bam-hero-chat')?.addEventListener('click', event => {
      event.preventDefault();
      q('#chat-panel')?.classList.add('open');
    });

    cloneForCleanEvents('#bam-hero-security')?.addEventListener('click', event => {
      event.preventDefault();
      openSecurity('guard', true);
    });

    cloneForCleanEvents('#scanner-promo')?.addEventListener('click', event => {
      event.preventDefault();
      openSecurity('scanner', false);
    });

    cloneForCleanEvents('#guard-promo')?.addEventListener('click', event => {
      event.preventDefault();
      q('#chat-panel')?.classList.add('open');
      q('[data-prompt-tab="malicious"]')?.click();
    });

    const payButton = qa('.quick-actions button').find(button => {
      const text = button.querySelector('strong')?.textContent.toLowerCase() || '';
      return text.includes('pay bills') || text.includes('bayar tagihan');
    }) || qa('.quick-actions button')[0];

    if (payButton) {
      const cleanPay = payButton.cloneNode(true);
      payButton.replaceWith(cleanPay);
      cleanPay.addEventListener('click', event => {
        event.preventDefault();
        openSecurity('file', false);
      });
    }

    const backdrop = q('#security-modal');
    backdrop?.addEventListener('click', event => {
      if (event.target === backdrop) closeSecurity();
    }, true);

    document.addEventListener('keydown', event => {
      if (event.key === 'Escape') {
        closeSecurity();
        q('#chat-panel')?.classList.remove('open');
        closeSidebar();
      }
    });

    q('#settings-refresh')?.addEventListener('click', () => {
      generateTransactions();
      renderTransactions();
    });

    q('#language')?.addEventListener('change', () => {
      window.setTimeout(() => {
        updateSimpleHeader(uiState.activePage);
        renderTransactions();
        updateSecurityLanguage();
      }, 0);
    });

    q('#settings-language')?.addEventListener('change', () => {
      window.setTimeout(() => {
        updateSimpleHeader(uiState.activePage);
        renderTransactions();
        updateSecurityLanguage();
      }, 0);
    });
  }

  installSidebarController();
  installMastercardBrand();
  generateTransactions();
  renderTransactions();
  installStableInteractions();
  updateSimpleHeader('dashboard');
  updateSecurityLanguage();
  window.setInterval(() => updateSimpleHeader(uiState.activePage), 60000);
})();


/* BAM_BANK_UI_REVISION_V11 */
(() => {
  const q = (selector, root = document) => root.querySelector(selector);
  const qa = (selector, root = document) => [...root.querySelectorAll(selector)];

  const actionIcons = [
    {
      className: 'action-pay-bills',
      svg: `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M7 3.5h8.5L19 7v13.5H7z"></path><path d="M15.5 3.5V7H19M10 11h6M10 14h6"></path><path d="m10 17 1.35 1.35L14 15.7"></path></svg>`
    },
    {
      className: 'action-send-money',
      svg: `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 12.5 20 4l-5.3 16-3.15-6.05L4 12.5Z"></path><path d="m11.55 13.95 4.2-4.15"></path></svg>`
    },
    {
      className: 'action-top-up',
      svg: `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 7.5h14.5A1.5 1.5 0 0 1 20 9v9.5H5.5A1.5 1.5 0 0 1 4 17V7.5Z"></path><path d="M4 7.5 15.5 4v3.5M15.5 12v5M13 14.5h5"></path></svg>`
    },
    {
      className: 'action-invest',
      svg: `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 19.5h16M6 16l4.1-4.1 3 2.7L19 8.5"></path><path d="M15.5 8.5H19V12"></path><circle cx="6" cy="16" r="1"></circle><circle cx="10.1" cy="11.9" r="1"></circle><circle cx="13.1" cy="14.6" r="1"></circle></svg>`
    },
    {
      className: 'action-new-account',
      svg: `<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="3.5" y="5" width="17" height="14" rx="2.5"></rect><circle cx="9" cy="11" r="2.1"></circle><path d="M5.8 16c.8-1.7 1.9-2.5 3.2-2.5s2.4.8 3.2 2.5M15 10.5h3.5M16.75 8.75v3.5"></path></svg>`
    }
  ];

  qa('#dashboard-page .quick-actions button')
    .slice(0, actionIcons.length)
    .forEach((button, index) => {
      const iconHost = q(':scope > span', button);
      if (!iconHost) return;
      button.classList.add('bam-product-action', actionIcons[index].className);
      iconHost.classList.add('bam-product-action-icon');
      iconHost.innerHTML = actionIcons[index].svg;
    });

  const trustRow = q('#bam-experience-hero .bam-trust-row');
  if (trustRow && !q('#bam-demo-credit')) {
    const credit = document.createElement('div');
    credit.id = 'bam-demo-credit';
    credit.className = 'bam-demo-credit';
    credit.innerHTML = `<span class="bam-credit-monogram">TF</span><span class="bam-credit-copy"><small>A concept demo by</small><strong>Therry Fohan</strong></span>`;
    trustRow.insertAdjacentElement('afterend', credit);
  }
})();


/* BAM_BANK_UI_REVISION_V12 */
(() => {
  const q = (selector, root = document) => root.querySelector(selector);
  const qa = (selector, root = document) => [...root.querySelectorAll(selector)];

  const coverage = [
    {
      value: 'sensitive-data',
      title: 'Sensitive Data Disclosure',
      detail: 'Tests whether protected or confidential data can be extracted.',
      checked: true
    },
    {
      value: 'system-prompt',
      title: 'System Prompt Leakage',
      detail: 'Attempts to reveal hidden instructions and system context.',
      checked: true
    },
    {
      value: 'malicious-code',
      title: 'Malicious Code Generation',
      detail: 'Evaluates whether the model produces harmful executable guidance.'
    },
    {
      value: 'model-discovery',
      title: 'Discover ML Model Family',
      detail: 'Attempts to identify model family and deployment details.'
    },
    {
      value: 'hallucinated-software',
      title: 'Hallucinated Software Entities',
      detail: 'Checks for invented packages, libraries, or dependencies.'
    },
    {
      value: 'agent-tools',
      title: 'Agent Tool Definition Leakage',
      detail: 'Tests whether private tools, parameters, or schemas are exposed.'
    },
    {
      value: 'indirect-prompt-injection',
      title: 'Indirect Prompt Injection',
      detail: 'Tests malicious instructions embedded in retrieved content.',
      checked: true
    },
    {
      value: 'resource-exhaustion',
      title: 'Resource Exhaustion via Prompt',
      detail: 'Checks resistance to excessive token or recursive output requests.'
    },
    {
      value: 'harmful-output',
      title: 'Harmful Content Generation',
      detail: 'Evaluates generation of unsafe or abusive content.'
    }
  ];

  function removeRedundantActions() {
    qa('.top-actions > button:not(#settings-button)').forEach(button => {
      button.remove();
    });

    q('#bam-hero-security')?.remove();

    const heroActions = q('#bam-experience-hero .bam-hero-actions');
    heroActions?.classList.add('single-action');
  }

  function flagEmoji(countryCode) {
    if (!countryCode || !/^[A-Z]{2}$/i.test(countryCode)) return '🌐';
    return countryCode
      .toUpperCase()
      .split('')
      .map(character => String.fromCodePoint(127397 + character.charCodeAt(0)))
      .join('');
  }

  function countryName(countryCode, providedName) {
    if (providedName) return providedName;
    if (!countryCode) return null;
    try {
      return new Intl.DisplayNames(
        [document.documentElement.lang === 'id' ? 'id' : 'en'],
        { type: 'region' }
      ).of(countryCode.toUpperCase());
    } catch (_) {
      return countryCode.toUpperCase();
    }
  }

  function installAccessContext() {
    const title = q('#page-title');
    const host = title?.parentElement;
    if (!host || q('#bam-access-context')) return;

    const context = document.createElement('div');
    context.id = 'bam-access-context';
    context.className = 'bam-access-context';
    context.innerHTML = `
      <span class="bam-access-chip">
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <rect x="4" y="5.5" width="16" height="14" rx="2.5"></rect>
          <path d="M8 3.5v4M16 3.5v4M4 9.5h16"></path>
        </svg>
        <span id="bam-access-date">Loading local date…</span>
      </span>
      <span class="bam-access-chip">
        <span class="bam-country-flag" id="bam-country-flag">🌐</span>
        <span id="bam-access-network">Resolving visitor network…</span>
      </span>`;

    const subtitle = q('#page-subtitle');
    if (subtitle) subtitle.replaceWith(context);
    else title.insertAdjacentElement('afterend', context);

    updateLocalAccessDate();
    loadClientContext();
  }

  function updateLocalAccessDate() {
    const target = q('#bam-access-date');
    if (!target) return;

    const now = new Date();
    const indonesia =
      localStorage.getItem('bam-language') === 'id' ||
      document.documentElement.lang === 'id';
    const locale = indonesia ? 'id-ID' : 'en-GB';

    const date = new Intl.DateTimeFormat(locale, {
      weekday: 'long',
      day: 'numeric',
      month: 'long',
      year: 'numeric'
    }).format(now);

    const time = new Intl.DateTimeFormat(locale, {
      hour: '2-digit',
      minute: '2-digit',
      timeZoneName: 'short'
    }).format(now);

    target.textContent = `${date} · ${time}`;
  }

  async function loadClientContext() {
    const network = q('#bam-access-network');
    const flag = q('#bam-country-flag');
    if (!network || !flag) return;

    try {
      const result = await api('/api/client-context');
      const name = countryName(result.countryCode, result.country);
      flag.textContent = flagEmoji(result.countryCode);

      const ip = result.ip || 'IP unavailable';
      network.textContent = name ? `${ip} · ${name}` : ip;
      network.title = `Display source: ${result.source || 'unknown'}`;
    } catch (_) {
      flag.textContent = '🌐';
      network.textContent = 'Network context unavailable';
    }
  }

  function installCurrentScannerCoverage() {
    const grid = q('#scanner-step-2 .attack-grid');
    if (!grid) return;

    grid.innerHTML = coverage.map(item => `
      <label class="attack-option updated-coverage">
        <input type="checkbox" value="${item.value}" ${item.checked ? 'checked' : ''} />
        <span>
          <strong>${item.title}</strong>
          <small>${item.detail}</small>
        </span>
      </label>`).join('');

    let reference = q('#scanner-coverage-reference');
    if (!reference) {
      reference = document.createElement('section');
      reference.id = 'scanner-coverage-reference';
      reference.className = 'scanner-coverage-reference';
      grid.insertAdjacentElement('afterend', reference);
    }

    reference.innerHTML = `
      <div>
        <strong>Current AI Scanner coverage reference</strong>
        <span>9 built-in categories aligned with the current public documentation.</span>
      </div>
      <div class="scanner-capability-tags">
        <span>Custom prompts</span>
        <span>Multi-turn conversations</span>
        <span>CVSS tags</span>
        <span>OWASP mapping</span>
        <span>MITRE ATLAS mapping</span>
      </div>
      <p>This interface runs representative demo or live endpoint checks. Use the generated TMAS configuration for the full judge-based assessment and custom-prompt workflow.</p>`;
  }

  function installGuardCoverageReference() {
    const status = q('#guard-content .status-hero');
    if (!status || q('#guard-official-coverage')) return;

    const coverageCard = document.createElement('section');
    coverageCard.id = 'guard-official-coverage';
    coverageCard.className = 'guard-official-coverage';
    coverageCard.innerHTML = `
      <div>
        <span class="guard-coverage-kicker">LIVE POLICY REFERENCE</span>
        <strong>Moderate security level recommended</strong>
        <p>AI Guard evaluates prompt attacks, harmful content, and sensitive information. Local demo checkboxes below only tune the offline fallback behavior.</p>
      </div>
      <div class="guard-coverage-tags">
        <span>Prompt attacks</span>
        <span>Harmful content</span>
        <span>Sensitive information</span>
      </div>`;

    status.insertAdjacentElement('afterend', coverageCard);

    const replacements = [
      ['#guard-policy-prompt-injection', 'Prompt attacks'],
      ['#guard-policy-jailbreak', 'Jailbreak patterns'],
      ['#guard-policy-harmful', 'Harmful content'],
      ['#guard-policy-pii', 'Sensitive information / PII']
    ];

    replacements.forEach(([selector, label]) => {
      const input = q(selector);
      const host = input?.closest('label');
      if (!host) return;
      const textNodes = [...host.childNodes].filter(node => node.nodeType === Node.TEXT_NODE);
      if (textNodes.length) textNodes[textNodes.length - 1].textContent = ` ${label}`;
    });
  }

  function syncAccessLanguage() {
    updateLocalAccessDate();
    loadClientContext();
  }

  removeRedundantActions();
  installAccessContext();
  installCurrentScannerCoverage();
  installGuardCoverageReference();

  q('#language')?.addEventListener('change', () => {
    window.setTimeout(syncAccessLanguage, 0);
  });
  q('#settings-language')?.addEventListener('change', () => {
    window.setTimeout(syncAccessLanguage, 0);
  });

  window.setInterval(updateLocalAccessDate, 60000);
})();


/* BAM_BANK_UI_REVISION_V13 */
(() => {
  const q = (selector, root = document) => root.querySelector(selector);

  function currentLanguage() {
    return localStorage.getItem('bam-language') === 'id' ||
      document.documentElement.lang === 'id' ? 'id' : 'en';
  }

  const copy = {
    en: {
      eyebrow: 'AI SECURITY LAB',
      title: 'Validate the AI experience',
      body: 'Run an assessment or compare protected responses without covering the dashboard.',
      scannerTitle: 'AI Scanner',
      scannerBody: 'Assess exposure',
      guardTitle: 'AI Guard',
      guardBody: 'Test protection'
    },
    id: {
      eyebrow: 'LAB KEAMANAN AI',
      title: 'Validasi pengalaman AI',
      body: 'Jalankan assessment atau bandingkan respons terlindungi tanpa menutupi dashboard.',
      scannerTitle: 'AI Scanner',
      scannerBody: 'Uji paparan',
      guardTitle: 'AI Guard',
      guardBody: 'Uji perlindungan'
    }
  };

  function removeSmartBalance() {
    q('.bam-balance-card')?.remove();
  }

  function openScanner() {
    const scannerNav = q('#open-ai-scanner');
    if (scannerNav) {
      scannerNav.click();
      return;
    }

    q('#security-modal')?.classList.add('open');
    q('[data-security-tab="scanner"]')?.click();
  }

  function openGuardTest() {
    const chatPanel = q('#chat-panel');
    chatPanel?.classList.add('open');
    q('[data-prompt-tab="malicious"]')?.click();
  }

  function syncSecurityLabCopy() {
    const text = copy[currentLanguage()];
    const values = {
      '#bam-lab-eyebrow': text.eyebrow,
      '#bam-lab-title': text.title,
      '#bam-lab-body': text.body,
      '#bam-lab-scanner-title': text.scannerTitle,
      '#bam-lab-scanner-body': text.scannerBody,
      '#bam-lab-guard-title': text.guardTitle,
      '#bam-lab-guard-body': text.guardBody
    };

    Object.entries(values).forEach(([selector, value]) => {
      const node = q(selector);
      if (node) node.textContent = value;
    });
  }

  function installSecurityLabCard() {
    const promos = q('#demo-promos');
    const rightColumn = q('#dashboard-page .right-column');
    const bankCard = q('#dashboard-page .right-column .bank-card');

    if (!promos || !rightColumn) return false;

    if (!promos.classList.contains('bam-security-lab-card')) {
      promos.className = 'demo-promos bam-security-lab-card';
      promos.innerHTML = `
        <div class="bam-security-lab-heading">
          <span class="bam-security-lab-mark" aria-hidden="true">
            <svg viewBox="0 0 24 24" focusable="false">
              <path d="M12 3.2 19 6v5.5c0 4.3-2.8 7.9-7 9.5-4.2-1.6-7-5.2-7-9.5V6l7-2.8Z"></path>
              <path d="M8.3 12h2.2l1.2-3 1.8 6 1.2-3h1.2"></path>
            </svg>
          </span>
          <span class="bam-security-lab-copy">
            <small id="bam-lab-eyebrow"></small>
            <strong id="bam-lab-title"></strong>
            <span id="bam-lab-body"></span>
          </span>
        </div>

        <div class="bam-security-lab-actions">
          <button type="button" class="bam-lab-action scanner" id="scanner-promo">
            <span class="bam-lab-action-icon" aria-hidden="true">
              <svg viewBox="0 0 24 24" focusable="false">
                <circle cx="12" cy="12" r="7.5"></circle>
                <circle cx="12" cy="12" r="2.2"></circle>
                <path d="M12 2.8v3M12 18.2v3M2.8 12h3M18.2 12h3"></path>
              </svg>
            </span>
            <span>
              <strong id="bam-lab-scanner-title"></strong>
              <small id="bam-lab-scanner-body"></small>
            </span>
            <svg class="bam-lab-arrow" viewBox="0 0 24 24" aria-hidden="true">
              <path d="M8 12h8M13 8l4 4-4 4"></path>
            </svg>
          </button>

          <button type="button" class="bam-lab-action guard" id="guard-promo">
            <span class="bam-lab-action-icon" aria-hidden="true">
              <svg viewBox="0 0 24 24" focusable="false">
                <path d="M12 3.2 19 6v5.5c0 4.3-2.8 7.9-7 9.5-4.2-1.6-7-5.2-7-9.5V6l7-2.8Z"></path>
                <path d="m8.8 12 2 2 4.5-4.5"></path>
              </svg>
            </span>
            <span>
              <strong id="bam-lab-guard-title"></strong>
              <small id="bam-lab-guard-body"></small>
            </span>
            <svg class="bam-lab-arrow" viewBox="0 0 24 24" aria-hidden="true">
              <path d="M8 12h8M13 8l4 4-4 4"></path>
            </svg>
          </button>
        </div>`;

      q('#scanner-promo')?.addEventListener('click', event => {
        event.preventDefault();
        openScanner();
      });

      q('#guard-promo')?.addEventListener('click', event => {
        event.preventDefault();
        openGuardTest();
      });
    }

    if (bankCard?.nextSibling) {
      rightColumn.insertBefore(promos, bankCard.nextSibling);
    } else {
      rightColumn.appendChild(promos);
    }

    syncSecurityLabCopy();
    return true;
  }

  function initialise() {
    removeSmartBalance();

    if (!installSecurityLabCard()) {
      window.setTimeout(installSecurityLabCard, 180);
      window.setTimeout(installSecurityLabCard, 700);
    }
  }

  initialise();

  q('#language')?.addEventListener('change', () => {
    window.setTimeout(syncSecurityLabCopy, 0);
  });

  q('#settings-language')?.addEventListener('change', () => {
    window.setTimeout(syncSecurityLabCopy, 0);
  });

  new MutationObserver(syncSecurityLabCopy).observe(
    document.documentElement,
    {
      attributes: true,
      attributeFilter: ['lang']
    }
  );
})();
