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
      payBillsSub: 'Upload and pay a bill',
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
      scannerPromoText: 'Launch a simulated automated attack campaign with TrendAI TMAS.',
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
      payBillsSub: 'Unggah dan bayar tagihan',
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
      scannerPromoText: 'Jalankan simulasi kampanye serangan otomatis dengan TrendAI TMAS.',
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
        <span class="promo-copy"><strong id="scanner-promo-title">Run an AI security scan</strong><small id="scanner-promo-text">Launch a simulated automated attack campaign with TrendAI TMAS.</small></span>
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
