/**
 * RetentionIQ — Main Application JavaScript
 * Single-Page Application logic, API calls, page rendering.
 */

'use strict';

// ============================================================
// Constants & Config
// ============================================================

const API = {
  health:     '/api/health',
  meta:       '/api/meta',
  curves:     '/api/meta/curves',
  predict:    '/api/predict/',
  explain: {
    local:   '/api/explain/local',
    global:  '/api/explain/global',
    whatif:  '/api/explain/whatif',
    pdp:     (feature) => `/api/explain/pdp/${feature}`,
  },
  batch:         '/api/batch/upload',
  batchValidate: '/api/batch/validate',
  batchTemplate: '/api/batch/template',
  batchSample:   '/api/batch/sample',
  batchProfile:  '/api/batch/profile',
  batchRemap:    '/api/batch/remap',
  batchProcess:  '/api/batch/dynamic-process',
  batchExport:   (id) => `/api/batch/${id}/export`,
  customers: {
    list:    '/api/customers/',
    overview:'/api/customers/overview',
    export:  '/api/customers/export',
    detail:  (id) => `/api/customers/${id}`,
  },
  history: {
    list:    '/api/history/',
    save:    '/api/history/',
    detail:  (id) => `/api/history/${id}`,
    compare: (a,b) => `/api/history/compare/${a}/${b}`,
  },
  reports: {
    pdf:     '/api/reports/pdf',
    metrics: '/api/reports/metrics',
    csv:     '/api/customers/export',
  },
};

const FEATURES = [
  { key: 'age',                  label: 'Age',                   min: 18,  max: 100,  step: 1,   unit: 'yrs', integer: true  },
  { key: 'session_frequency',    label: 'Session Frequency',     min: 0,   max: 100,  step: 1,   unit: '/wk', integer: true  },
  { key: 'avg_session_minutes',  label: 'Avg Session Duration',  min: 0,   max: 180,  step: 0.5, unit: 'min', integer: false },
  { key: 'days_since_install',   label: 'Days Since Install',    min: 1,   max: 365,  step: 1,   unit: 'days',integer: true  },
  { key: 'notifications_clicked',label: 'Notifications Clicked', min: 0,   max: 100,  step: 1,   unit: '',    integer: true  },
  { key: 'crashes',              label: 'App Crashes',           min: 0,   max: 20,   step: 1,   unit: '',    integer: true  },
  { key: 'purchases',            label: 'In-App Purchases',      min: 0,   max: 50,   step: 1,   unit: '',    integer: true  },
];

const PAGES = [
  { id: 'overview',    label: 'Overview',          icon: 'home'    },
  { id: 'predict',     label: 'Predict',           icon: 'zap'     },
  { id: 'batch',       label: 'Batch Analysis',    icon: 'layers'  },
  { id: 'customers',   label: 'Customers',         icon: 'users'   },
  { id: 'explain',     label: 'Explainability Lab',icon: 'cpu'     },
  { id: 'history',     label: 'History & Compare', icon: 'clock'   },
  { id: 'reports',     label: 'Reports',           icon: 'file-text'},
  { id: 'about',       label: 'About & Limits',    icon: 'info'    },
];

// ============================================================
// SVG Icons (inline, no emoji)
// ============================================================

const ICONS = {
  home: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>`,
  zap: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>`,
  layers: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/></svg>`,
  users: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 00-3-3.87"/><path d="M16 3.13a4 4 0 010 7.75"/></svg>`,
  cpu: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="4" y="4" width="16" height="16" rx="2"/><rect x="9" y="9" width="6" height="6"/><line x1="9" y1="1" x2="9" y2="4"/><line x1="15" y1="1" x2="15" y2="4"/><line x1="9" y1="20" x2="9" y2="23"/><line x1="15" y1="20" x2="15" y2="23"/><line x1="20" y1="9" x2="23" y2="9"/><line x1="20" y1="14" x2="23" y2="14"/><line x1="1" y1="9" x2="4" y2="9"/><line x1="1" y1="14" x2="4" y2="14"/></svg>`,
  clock: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>`,
  'file-text': `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/></svg>`,
  info: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>`,
  search: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>`,
  chevronLeft: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"/></svg>`,
  chevronRight: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"/></svg>`,
  x: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>`,
  download: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>`,
  upload: `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="16 16 12 12 8 16"/><line x1="12" y1="12" x2="12" y2="21"/><path d="M20.39 18.39A5 5 0 0018 9h-1.26A8 8 0 103 16.3"/></svg>`,
  menu: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="18" x2="21" y2="18"/></svg>`,
  alertTriangle: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>`,
  checkCircle: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 11-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>`,
  save: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 21H5a2 2 0 01-2-2V5a2 2 0 012-2h11l5 5v11a2 2 0 01-2 2z"/><polyline points="17 21 17 13 7 13 7 21"/><polyline points="7 3 7 8 15 8"/></svg>`,
  externalLink: `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 13v6a2 2 0 01-2 2H5a2 2 0 01-2-2V8a2 2 0 012-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>`,
  'upload-cloud': `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="16 16 12 12 8 16"/><line x1="12" y1="12" x2="12" y2="21"/><path d="M20.39 18.39A5 5 0 0018 9h-1.26A8 8 0 103 16.3"/></svg>`,
  'bar-chart-2': `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>`,
  'check-circle': `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 11-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>`,
  'refresh-cw': `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/><path d="M3.51 9a9 9 0 0114.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0020.49 15"/></svg>`,
};

// ============================================================
// State
// ============================================================

const state = {
  currentPage: 'overview',
  sidebarCollapsed: false,
  globalExplanation: null,
  customersPage: 0,
  customersRisk: '',
  customersSearch: '',
  whatIfDebounceTimer: null,
  charts: {},
  lastPrediction: null,
  historyList: [],
  compareA: null,
  compareB: null,
};

// ============================================================
// API Helpers
// ============================================================

async function apiFetch(url, options = {}) {
  try {
    const resp = await fetch(url, {
      headers: { 'Content-Type': 'application/json' },
      ...options,
    });
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({ detail: resp.statusText }));
      throw new Error(err.detail || `HTTP ${resp.status}`);
    }
    return await resp.json();
  } catch (e) {
    throw e;
  }
}

async function apiPost(url, body) {
  return apiFetch(url, { method: 'POST', body: JSON.stringify(body) });
}

// ============================================================
// Rendering Utilities
// ============================================================

function icon(name, cls = '') {
  return `<span class="icon ${cls}" aria-hidden="true">${ICONS[name] || ''}</span>`;
}

function riskBadge(level) {
  const map = { High: 'high', Medium: 'medium', Low: 'low' };
  const cls = map[level] || 'low';
  return `<span class="risk-badge ${cls}"><span class="pulse-dot"></span>${level} Risk</span>`;
}

function fmtPct(v) { return v != null ? `${(v * 100).toFixed(1)}%` : '—'; }
function fmtProb(v) { return v != null ? `${(v * 100).toFixed(0)}%` : '—'; }
function fmtNum(v) { return v != null ? Number(v).toLocaleString() : '—'; }

/**
 * Escape a string for safe insertion into HTML to prevent XSS.
 * Used throughout the dynamic batch UI where user-supplied column names
 * and values are rendered into innerHTML.
 */
function escHtml(str) {
  if (str == null) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function synthAlert() {
  return `<div class="alert alert-synthetic">
    ${icon('alertTriangle')}
    <span><strong>Synthetic data only</strong> — demonstration model, not validated on real customers.</span>
  </div>`;
}

function countUpAnimation(el, target, suffix = '', decimals = 0) {
  if (!el) return;
  const duration = 900;
  const start = performance.now();
  const from = 0;
  function tick(now) {
    const elapsed = now - start;
    const progress = Math.min(elapsed / duration, 1);
    const ease = 1 - Math.pow(1 - progress, 3);
    const val = from + (target - from) * ease;
    el.textContent = decimals > 0
      ? val.toFixed(decimals) + suffix
      : Math.round(val) + suffix;
    if (progress < 1) requestAnimationFrame(tick);
    else el.textContent = target.toFixed(decimals) + suffix;
  }
  requestAnimationFrame(tick);
}

function destroyChart(key) {
  if (state.charts[key]) {
    state.charts[key].destroy();
    delete state.charts[key];
  }
}

// ============================================================
// Gauge SVG
// ============================================================

function buildGauge(probability, risk) {
  const pct = Math.max(0, Math.min(1, probability));
  const W = 200, H = 120;
  const cx = W / 2, cy = H - 10;
  const r = 80;
  // Arc goes from 180° to 0° (left to right)
  const startAngle = Math.PI;
  const endAngle = 0;
  const sweepAngle = (1 - pct) * Math.PI;  // how far from the left
  const fillAngle = pct * Math.PI;

  const polarX = (a) => cx + r * Math.cos(Math.PI - a);
  const polarY = (a) => cy - r * Math.sin(Math.PI - a);

  const trackStart = { x: cx - r, y: cy };
  const trackEnd   = { x: cx + r, y: cy };

  // Needle
  const needleAngle = Math.PI - pct * Math.PI;
  const nx = cx + (r - 12) * Math.cos(needleAngle);
  const ny = cy - (r - 12) * Math.sin(needleAngle);

  const fillColour = risk === 'High' ? '#DC2626' : risk === 'Medium' ? '#D97706' : '#059669';

  return `<svg class="gauge-svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}" role="img" aria-label="Retention probability gauge: ${fmtPct(probability)}">
    <!-- Track arc -->
    <path d="M ${cx - r} ${cy} A ${r} ${r} 0 0 1 ${cx + r} ${cy}"
          fill="none" stroke="#E8E8F0" stroke-width="14" stroke-linecap="round"/>
    <!-- Fill arc -->
    ${pct > 0 ? `<path d="M ${cx - r} ${cy} A ${r} ${r} 0 ${pct > 0.5 ? 1 : 0} 1 ${polarX(fillAngle)} ${polarY(fillAngle)}"
          fill="none" stroke="${fillColour}" stroke-width="14" stroke-linecap="round"
          style="transition: stroke-dasharray 0.8s ease; filter: drop-shadow(0 0 6px ${fillColour}44)"/>` : ''}
    <!-- Needle -->
    <line x1="${cx}" y1="${cy}" x2="${nx}" y2="${ny}"
          stroke="${fillColour}" stroke-width="3" stroke-linecap="round"
          style="transform-origin: ${cx}px ${cy}px; transition: transform 0.8s cubic-bezier(0.34,1.56,0.64,1)"/>
    <circle cx="${cx}" cy="${cy}" r="5" fill="${fillColour}"/>
    <!-- Tick labels -->
    <text x="${cx - r - 2}" y="${cy + 16}" font-size="9" fill="#9494B0" text-anchor="middle">0%</text>
    <text x="${cx + r + 2}" y="${cy + 16}" font-size="9" fill="#9494B0" text-anchor="middle">100%</text>
  </svg>`;
}

// ============================================================
// SHAP Waterfall Renderer
// ============================================================

function buildSHAPWaterfall(contribs, bias) {
  const maxAbs = Math.max(...Object.values(contribs).map(Math.abs), 0.01);
  const rows = Object.entries(contribs)
    .sort((a, b) => Math.abs(b[1]) - Math.abs(a[1]));

  const bars = rows.map(([feat, val]) => {
    const pct = (Math.abs(val) / maxAbs) * 100;
    const dir = val >= 0 ? 'positive' : 'negative';
    const label = FEATURES.find(f => f.key === feat)?.label || feat;
    const sign = val >= 0 ? '+' : '';
    // For positive: bar starts at center going right; for negative: going left
    const fillStyle = val >= 0
      ? `left: 50%; width: ${pct / 2}%;`
      : `left: ${50 - pct / 2}%; width: ${pct / 2}%;`;
    return `<div class="shap-bar-row fade-in-up">
      <span class="shap-bar-label">${label}</span>
      <div class="shap-bar-track">
        <div class="shap-bar-fill ${dir}" style="${fillStyle}"></div>
      </div>
      <span class="shap-bar-value ${val >= 0 ? 'text-accent' : ''}" style="color: ${val < 0 ? 'var(--risk-high)' : ''}">${sign}${val.toFixed(3)}</span>
    </div>`;
  }).join('');

  return `<div class="shap-bar-container">${bars}
    <div class="shap-bar-row" style="margin-top:8px;border-top:1px dashed var(--surface-border);padding-top:8px;">
      <span class="shap-bar-label" style="color:var(--text-muted);font-size:0.75rem;">Base value (bias)</span>
      <div class="shap-bar-track"></div>
      <span class="shap-bar-value text-muted">${bias.toFixed(3)}</span>
    </div>
  </div>`;
}

// ============================================================
// Navigation & Shell
// ============================================================

function buildShell() {
  document.getElementById('app').innerHTML = `
    <div class="app-shell" id="appShell">
      <!-- Top Bar -->
      <header class="topbar" role="banner">
        <div class="topbar-brand">
          <svg width="28" height="28" viewBox="0 0 32 32" fill="none">
            <rect width="32" height="32" rx="8" fill="url(#grad1)"/>
            <defs><linearGradient id="grad1" x1="0" y1="0" x2="32" y2="32"><stop offset="0%" stop-color="#4F46E5"/><stop offset="100%" stop-color="#7C3AED"/></linearGradient></defs>
            <path d="M8 22L14 14L18 18L22 10" stroke="white" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
            <circle cx="22" cy="10" r="2" fill="white"/>
          </svg>
          <span>RetentionIQ</span>
        </div>
        <div class="topbar-center">
          <div class="search-bar">
            <span class="search-icon">${icon('search')}</span>
            <input type="text" placeholder="Search customers or jump to page…" id="globalSearch"
                   aria-label="Global search" autocomplete="off"/>
            <span class="kbd-hint">Ctrl+K</span>
          </div>
        </div>
        <div class="topbar-right">
          <div class="model-badge" title="XGBoost v3.4.1 | n_est=50 | depth=3">XGBoost v1.0</div>
          <div class="synthetic-badge">${icon('alertTriangle')} Synthetic Data</div>
        </div>
      </header>

      <!-- Sidebar -->
      <nav class="sidebar" id="sidebar" role="navigation" aria-label="Main navigation">
        <div class="sidebar-toggle">
          <button id="sidebarToggle" aria-label="Toggle sidebar">${icon('menu')}</button>
        </div>
        <div class="nav-section">
          <div class="nav-section-label">Analytics</div>
          ${PAGES.slice(0, 4).map(p => navLink(p)).join('')}
        </div>
        <div class="nav-section" style="margin-top:8px;">
          <div class="nav-section-label">Insights</div>
          ${PAGES.slice(4).map(p => navLink(p)).join('')}
        </div>
      </nav>

      <!-- Main Content -->
      <main class="main-content" id="mainContent" role="main">
        <div id="pageContainer"></div>
      </main>
    </div>

    <!-- Customer Drawer -->
    <div class="drawer-overlay" id="drawerOverlay" role="presentation"></div>
    <aside class="drawer" id="customerDrawer" role="complementary" aria-label="Customer detail">
      <div class="drawer-header">
        <span class="drawer-title" id="drawerTitle">Customer Detail</span>
        <button class="drawer-close" id="drawerClose" aria-label="Close drawer">${icon('x')}</button>
      </div>
      <div id="drawerContent">Loading…</div>
    </aside>

    <!-- Command Palette -->
    <div class="modal-overlay" id="cmdOverlay" role="dialog" aria-modal="true" aria-label="Command palette">
      <div class="modal-box">
        <div class="modal-search">
          ${icon('search')}
          <input type="text" id="cmdInput" placeholder="Search pages, customers…" aria-label="Command palette search"/>
        </div>
        <div class="palette-list" id="paletteList"></div>
      </div>
    </div>
  `;

  // Wire events
  document.getElementById('sidebarToggle').addEventListener('click', toggleSidebar);
  document.getElementById('drawerOverlay').addEventListener('click', closeDrawer);
  document.getElementById('drawerClose').addEventListener('click', closeDrawer);
  document.getElementById('globalSearch').addEventListener('focus', openCmdPalette);
  document.getElementById('cmdOverlay').addEventListener('click', (e) => {
    if (e.target === e.currentTarget) closeCmdPalette();
  });
  document.getElementById('cmdInput').addEventListener('input', filterPalette);
  document.addEventListener('keydown', handleGlobalKeydown);

  // Nav links
  document.querySelectorAll('.nav-link').forEach(el => {
    el.addEventListener('click', () => navigateTo(el.dataset.page));
  });
}

function navLink(p) {
  return `<div class="nav-section">
    <button class="nav-link" data-page="${p.id}" id="nav-${p.id}"
            aria-current="${state.currentPage === p.id ? 'page' : 'false'}">
      ${icon(p.icon)}
      <span class="nav-link-text">${p.label}</span>
    </button>
  </div>`;
}

function updateNavActive() {
  document.querySelectorAll('.nav-link').forEach(el => {
    const active = el.dataset.page === state.currentPage;
    el.classList.toggle('active', active);
    el.setAttribute('aria-current', active ? 'page' : 'false');
  });
}

function toggleSidebar() {
  state.sidebarCollapsed = !state.sidebarCollapsed;
  document.getElementById('appShell').classList.toggle('sidebar-collapsed', state.sidebarCollapsed);
}

function navigateTo(page) {
  state.currentPage = page;
  updateNavActive();
  renderPage(page);
  window.history.pushState({}, '', `#${page}`);
  // Scroll to top
  document.getElementById('mainContent').scrollTo(0, 0);
}

// ============================================================
// Command Palette
// ============================================================

function openCmdPalette() {
  document.getElementById('cmdOverlay').classList.add('open');
  document.getElementById('cmdInput').value = '';
  filterPalette();
  setTimeout(() => document.getElementById('cmdInput').focus(), 50);
}

function closeCmdPalette() {
  document.getElementById('cmdOverlay').classList.remove('open');
  document.getElementById('globalSearch').blur();
}

function filterPalette() {
  const q = document.getElementById('cmdInput').value.toLowerCase();
  const list = document.getElementById('paletteList');
  const items = PAGES.filter(p => p.label.toLowerCase().includes(q) || p.id.includes(q));
  list.innerHTML = items.map((p, i) => `
    <div class="palette-item ${i === 0 ? 'selected' : ''}" data-page="${p.id}" tabindex="0">
      ${icon(p.icon)} <span>${p.label}</span>
    </div>
  `).join('') || `<div class="empty-state"><span class="text-muted" style="font-size:0.85rem">No results for "${q}"</span></div>`;

  list.querySelectorAll('.palette-item').forEach(el => {
    el.addEventListener('click', () => {
      navigateTo(el.dataset.page);
      closeCmdPalette();
    });
  });
}

function handleGlobalKeydown(e) {
  if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
    e.preventDefault();
    openCmdPalette();
  }
  if (e.key === 'Escape') {
    closeCmdPalette();
    closeDrawer();
  }
}

// ============================================================
// Drawer
// ============================================================

function openDrawer(title, contentHtml) {
  document.getElementById('drawerTitle').textContent = title;
  document.getElementById('drawerContent').innerHTML = contentHtml;
  document.getElementById('drawerOverlay').classList.add('open');
  document.getElementById('customerDrawer').classList.add('open');
}

function closeDrawer() {
  document.getElementById('drawerOverlay').classList.remove('open');
  document.getElementById('customerDrawer').classList.remove('open');
}

// ============================================================
// Page Routing
// ============================================================

async function renderPage(page) {
  const container = document.getElementById('pageContainer');
  container.innerHTML = `<div class="skeleton skeleton-chart" style="height:200px;margin-top:8px;"></div>`;
  
  const renderers = {
    overview:  renderOverview,
    predict:   renderPredict,
    batch:     renderBatch,
    customers: renderCustomers,
    explain:   renderExplain,
    history:   renderHistory,
    reports:   renderReports,
    about:     renderAbout,
  };
  
  try {
    await (renderers[page] || renderOverview)(container);
  } catch (err) {
    container.innerHTML = `<div class="alert alert-error">${icon('alertTriangle')} Error loading page: ${err.message}</div>`;
  }
}

// ============================================================
// PAGE: Overview
// ============================================================

async function renderOverview(container) {
  container.innerHTML = `
    <div class="page-header">
      <div class="breadcrumbs"><span class="crumb">RetentionIQ</span><span>›</span><span class="crumb">Overview</span></div>
      <h1 class="page-title">Overview</h1>
      <p class="page-subtitle">Real-time retention analytics dashboard</p>
    </div>
    ${synthAlert()}
    <div class="kpi-grid" id="kpiGrid">
      ${[1,2,3,4].map(() => '<div class="skeleton skeleton-kpi"></div>').join('')}
    </div>
    <div class="grid-2" style="margin-bottom:20px;">
      <div class="card">
        <div class="card-title">Risk Distribution</div>
        <div class="card-subtitle">Customers by retention risk tier</div>
        <canvas id="riskChart" height="200"></canvas>
      </div>
      <div class="card">
        <div class="card-title">Retention Probability</div>
        <div class="card-subtitle">Distribution across all scored customers</div>
        <canvas id="probChart" height="200"></canvas>
      </div>
    </div>
    <div class="card">
      <div class="card-title">Top At-Risk Customers</div>
      <div class="card-subtitle">Highest churn probability — requires immediate attention</div>
      <div id="atRiskList"></div>
    </div>
  `;

  // Fetch KPIs
  let stats;
  try {
    stats = await apiFetch(API.customers.overview);
  } catch (e) {
    stats = { total_customers: 0, high_risk: 0, medium_risk: 0, low_risk: 0, avg_retention_probability: null };
  }

  const total = stats.total_customers || 0;

  // KPI cards
  const kpiData = [
    { label: 'Total Customers', value: total, icon: 'users', cls: '' },
    { label: 'High Risk', value: stats.high_risk || 0, icon: 'alertTriangle', cls: 'high-risk' },
    { label: 'Medium Risk', value: stats.medium_risk || 0, icon: 'cpu', cls: 'medium-risk' },
    { label: 'Low Risk', value: stats.low_risk || 0, icon: 'checkCircle', cls: 'low-risk' },
  ];

  if (total === 0) {
    document.getElementById('kpiGrid').innerHTML = `
      <div class="kpi-card fade-in-up">
        <div class="kpi-icon">${icon('users')}</div>
        <div class="kpi-value" id="kpi-total">0</div>
        <div class="kpi-label">Total Customers</div>
      </div>
      <div class="kpi-card high-risk fade-in-up">
        <div class="kpi-value">0</div><div class="kpi-label">High Risk</div>
      </div>
      <div class="kpi-card medium-risk fade-in-up">
        <div class="kpi-value">0</div><div class="kpi-label">Medium Risk</div>
      </div>
      <div class="kpi-card low-risk fade-in-up">
        <div class="kpi-value">0</div><div class="kpi-label">Low Risk</div>
      </div>
    `;
  } else {
    document.getElementById('kpiGrid').innerHTML = kpiData.map((k, i) => `
      <div class="kpi-card ${k.cls} fade-in-up">
        <div class="kpi-icon">${icon(k.icon)}</div>
        <div class="kpi-value" id="kpi-${i}">0</div>
        <div class="kpi-label">${k.label}</div>
        ${k.cls === '' && stats.avg_retention_probability != null
          ? `<div class="kpi-delta positive">${fmtPct(stats.avg_retention_probability)} avg prob</div>` : ''}
      </div>
    `).join('');
    // Count-up animations
    kpiData.forEach((k, i) => {
      const el = document.getElementById(`kpi-${i}`);
      if (el) countUpAnimation(el, k.value);
    });
  }

  // Charts
  if (total > 0) {
    // Risk distribution doughnut
    destroyChart('risk');
    const riskCtx = document.getElementById('riskChart');
    if (riskCtx) {
      state.charts.risk = new Chart(riskCtx, {
        type: 'doughnut',
        data: {
          labels: ['High Risk (<40%)', 'Medium Risk (40-70%)', 'Low Risk (≥70%)'],
          datasets: [{
            data: [stats.high_risk || 0, stats.medium_risk || 0, stats.low_risk || 0],
            backgroundColor: ['#DC2626', '#D97706', '#059669'],
            borderWidth: 0,
            hoverOffset: 6,
          }],
        },
        options: {
          responsive: true,
          plugins: {
            legend: { position: 'bottom', labels: { padding: 16, font: { size: 12 } } },
            tooltip: { callbacks: { label: (c) => ` ${c.label}: ${c.raw} (${Math.round(c.raw/total*100)}%)` } },
          },
          animation: { animateRotate: true, duration: 800 },
        },
      });
    }

    // Retention Probability Histogram
    destroyChart('prob');
    const probCtx = document.getElementById('probChart');
    if (probCtx && stats.histogram) {
      state.charts.prob = new Chart(probCtx, {
        type: 'bar',
        data: {
          labels: stats.histogram.labels,
          datasets: [{
            label: 'Customers',
            data: stats.histogram.counts,
            backgroundColor: [
              '#DC2626', '#DC2626', '#DC2626', '#DC2626', // 0-40% High Risk
              '#D97706', '#D97706', '#D97706',             // 40-70% Medium Risk
              '#059669', '#059669', '#059669'              // 70-100% Low Risk
            ],
            borderRadius: 4,
          }],
        },
        options: {
          responsive: true,
          plugins: {
            legend: { display: false },
            tooltip: {
              callbacks: {
                title: (items) => `Retention Range: ${items[0].label}`,
                label: (item) => ` ${item.raw} customers (${Math.round(item.raw/total*100)}%)`,
              },
            },
          },
          scales: {
            x: { grid: { display: false }, title: { display: true, text: 'Retention Probability' } },
            y: { beginAtZero: true, title: { display: true, text: 'Count' }, ticks: { precision: 0 } },
          },
          animation: { duration: 700 },
        },
      });
    }

    // Top at-risk table
    try {
      const atRisk = await apiFetch(API.customers.list + '?risk=High&sort_by=probability&sort_dir=ASC&limit=8');
      const atRiskEl = document.getElementById('atRiskList');
      if (atRiskEl && atRisk.items.length > 0) {
        atRiskEl.innerHTML = `<div class="table-wrapper"><table>
          <thead><tr><th>ID</th><th>Customer</th><th>Probability</th><th>Risk</th><th>Crashes</th><th>Sessions/wk</th></tr></thead>
          <tbody>${atRisk.items.map(c => `
            <tr data-id="${c.id}" class="highlighted" style="cursor:pointer;">
              <td>${c.id}</td>
              <td>${c.customer_id || `User ${c.id}`}</td>
              <td><div style="display:flex;align-items:center;gap:8px;">
                <div class="progress-bar-wrapper" style="width:80px"><div class="progress-bar high" style="width:${(1-c.probability)*100}%"></div></div>
                <span style="color:var(--risk-high);font-weight:600">${fmtPct(c.probability)}</span>
              </div></td>
              <td>${riskBadge(c.risk_level)}</td>
              <td>${c.features?.crashes ?? '—'}</td>
              <td>${c.features?.session_frequency ?? '—'}</td>
            </tr>`).join('')}
          </tbody>
        </table></div>`;
        atRiskEl.querySelectorAll('tr[data-id]').forEach(row => {
          row.addEventListener('click', () => openCustomerDrawer(parseInt(row.dataset.id)));
        });
      } else if (atRiskEl) {
        atRiskEl.innerHTML = `<div class="empty-state">
          <div class="empty-icon">${icon('checkCircle')}</div>
          <div class="empty-title">No High-Risk Customers</div>
          <div class="empty-desc">No customers are currently at high churn risk.</div>
        </div>`;
      }
    } catch (e) { /* ignore */ }

    // Latest Analysis Summary banner if present
    if (stats.latest_batch || stats.latest_analysis) {
      const latestSummaryEl = document.createElement('div');
      latestSummaryEl.className = 'card mt-4';
      latestSummaryEl.innerHTML = `
        <div class="card-title">Latest Analysis Summary</div>
        <div class="card-subtitle">Activity recap from your recent session</div>
        <div class="grid-2" style="margin-top:12px;">
          ${stats.latest_batch ? `
          <div style="background:var(--surface-bg);border-radius:10px;padding:14px;">
            <div style="font-size:0.75rem;color:var(--text-muted);text-transform:uppercase;">Latest Batch Upload</div>
            <div style="font-weight:600;font-size:0.95rem;margin-top:4px;">${stats.latest_batch.filename}</div>
            <div style="font-size:0.8rem;color:var(--text-secondary);margin-top:2px;">
              ${stats.latest_batch.valid_rows} of ${stats.latest_batch.total_rows} rows scored successfully
            </div>
            <div style="font-size:0.72rem;color:var(--text-muted);margin-top:4px;">${stats.latest_batch.created_at?.substring(0,16).replace('T',' ')}</div>
          </div>` : ''}
          ${stats.latest_analysis ? `
          <div style="background:var(--surface-bg);border-radius:10px;padding:14px;">
            <div style="font-size:0.75rem;color:var(--text-muted);text-transform:uppercase;">Latest Saved Snapshot</div>
            <div style="font-weight:600;font-size:0.95rem;margin-top:4px;">${stats.latest_analysis.name}</div>
            <div style="font-size:0.8rem;color:var(--text-secondary);margin-top:2px;">
              Cohort Size: ${stats.latest_analysis.summary?.total_customers ?? '—'} | Avg Prob: ${stats.latest_analysis.summary?.avg_retention_probability != null ? fmtPct(stats.latest_analysis.summary.avg_retention_probability) : '—'}
            </div>
            <div style="font-size:0.72rem;color:var(--text-muted);margin-top:4px;">${stats.latest_analysis.created_at?.substring(0,16).replace('T',' ')}</div>
          </div>` : ''}
        </div>
      `;
      container.appendChild(latestSummaryEl);
    }
  } else {
    // Clean empty state for risk charts and table
    const emptyHTML = `<div class="empty-state">
      <div class="empty-icon">${icon('zap')}</div>
      <div class="empty-title">No Data Yet</div>
      <div class="empty-desc">Go to Predict or Batch Analysis to score customers and see analytics here.</div>
    </div>`;
    const riskCard = document.getElementById('riskChart')?.parentElement;
    if (riskCard) riskCard.innerHTML = `<div class="card-title">Risk Distribution</div><div class="card-subtitle">Customers by retention risk tier</div>${emptyHTML}`;
    const probCard = document.getElementById('probChart')?.parentElement;
    if (probCard) probCard.innerHTML = `<div class="card-title">Retention Probability</div><div class="card-subtitle">Distribution across all scored customers</div>${emptyHTML}`;
    const atRiskEl = document.getElementById('atRiskList');
    if (atRiskEl) atRiskEl.innerHTML = emptyHTML;
  }
}

// ============================================================
// PAGE: Predict
// ============================================================

function renderPredict(container) {
  container.innerHTML = `
    <div class="page-header">
      <div class="breadcrumbs"><span class="crumb">RetentionIQ</span><span>›</span><span class="crumb">Predict</span></div>
      <h1 class="page-title">Single Customer Prediction</h1>
      <p class="page-subtitle">Enter user features to predict retention probability</p>
    </div>
    ${synthAlert()}
    <div class="grid-2" style="align-items:start;">
      <div>
        <div class="card">
          <div class="card-title">User Features</div>
          <div class="card-subtitle">Fill in all fields below</div>
          <form id="predictForm">
            ${FEATURES.map(f => `
              <div class="form-group">
                <label class="form-label" for="f_${f.key}">${f.label} <span class="required">*</span>
                  <span class="text-muted text-sm">(${f.min}–${f.max}${f.unit ? ' ' + f.unit : ''})</span>
                </label>
                <input class="form-input" type="number" id="f_${f.key}"
                       name="${f.key}" min="${f.min}" max="${f.max}" step="${f.step}"
                       value="${f.key === 'age' ? 28 : f.key === 'session_frequency' ? 7 : f.key === 'avg_session_minutes' ? 22.5 : f.key === 'days_since_install' ? 30 : f.key === 'notifications_clicked' ? 8 : f.key === 'crashes' ? 0 : 1}"
                       required aria-describedby="hint_${f.key}"/>
                <div class="form-hint" id="hint_${f.key}">${f.label}: ${f.min} to ${f.max}${f.unit ? ' ' + f.unit : ''}</div>
              </div>`).join('')}
            <div class="flex gap-2 mt-4">
              <button type="submit" class="btn btn-primary w-full" id="predictBtn">
                ${icon('zap')} Run Prediction
              </button>
              <button type="button" class="btn btn-ghost" id="predictResetBtn">Reset</button>
            </div>
          </form>
        </div>
      </div>
      <div>
        <div class="card" id="resultCard">
          <div class="card-title">Prediction Result</div>
          <div class="card-subtitle">Results will appear here after prediction</div>
          <div id="resultContent">
            <div class="empty-state">
              <div class="empty-icon">${icon('zap')}</div>
              <div class="empty-title">Ready to Predict</div>
              <div class="empty-desc">Fill in the form and click Run Prediction.</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  `;

  document.getElementById('predictForm').addEventListener('submit', handlePredictSubmit);
  document.getElementById('predictResetBtn').addEventListener('click', () => {
    document.getElementById('predictForm').reset();
    document.getElementById('resultContent').innerHTML = `<div class="empty-state">
      <div class="empty-icon">${icon('zap')}</div>
      <div class="empty-title">Ready to Predict</div>
      <div class="empty-desc">Fill in the form and click Run Prediction.</div>
    </div>`;
  });
}

async function handlePredictSubmit(e) {
  e.preventDefault();
  const btn = document.getElementById('predictBtn');
  btn.classList.add('loading');
  btn.disabled = true;

  const body = {};
  FEATURES.forEach(f => {
    body[f.key] = parseFloat(document.getElementById(`f_${f.key}`).value);
  });

  try {
    const [pred, explain] = await Promise.all([
      apiPost(API.predict, body),
      apiPost(API.explain.local, body),
    ]);

    state.lastPrediction = { body, pred, explain };

    document.getElementById('resultContent').innerHTML = `
      <div class="gauge-wrapper fade-in-up">
        ${buildGauge(pred.probability, pred.risk_level)}
        <div class="gauge-label">
          <div class="gauge-prob">${fmtPct(pred.probability)}</div>
          <div style="margin-top:6px;">${riskBadge(pred.risk_level)}</div>
          <div style="font-size:0.8rem;color:var(--text-muted);margin-top:6px;">
            ${pred.prediction === 1 ? 'Predicted: Retained' : 'Predicted: Not Retained'}
          </div>
          ${pred.customer_db_id ? `<div style="margin-top:8px;"><span style="display:inline-flex;align-items:center;gap:4px;background:var(--risk-low-bg);color:var(--risk-low);border:1px solid var(--risk-low-border);padding:3px 8px;border-radius:12px;font-size:0.75rem;font-weight:600;">${icon('checkCircle')} Saved to History (ID #${pred.customer_db_id})</span></div>` : ''}
        </div>
      </div>
      <div class="section-divider"></div>
      <div class="card-title" style="margin-bottom:8px;">Why this prediction?</div>
      <p style="font-size:0.85rem;color:var(--text-secondary);margin-bottom:16px;line-height:1.6;">${explain.plain_english}</p>
      <div class="card-title" style="margin-bottom:8px;">Feature Contributions (SHAP)</div>
      ${buildSHAPWaterfall(explain.contribs, explain.bias)}
      ${explain.actions.length ? `
        <div class="section-divider"></div>
        <div class="card-title" style="margin-bottom:8px;">Recommended Actions</div>
        ${explain.actions.map(a => `
          <div class="alert alert-info" style="margin-bottom:8px;">
            ${icon('checkCircle')}
            <div><strong>${FEATURES.find(f=>f.key===a.feature)?.label || a.feature}</strong>: ${a.action}</div>
          </div>`).join('')}` : ''}
      <div class="section-divider"></div>
      <button class="btn btn-secondary btn-sm" id="goWhatIfBtn" style="margin-right:8px;">
        ${icon('cpu')} What-If Simulator
      </button>
      <a href="/api/reports/pdf" target="_blank" class="btn btn-ghost btn-sm">
        ${icon('download')} PDF Report
      </a>
    `;

    document.getElementById('goWhatIfBtn')?.addEventListener('click', () => navigateTo('explain'));

  } catch (err) {
    document.getElementById('resultContent').innerHTML = `
      <div class="alert alert-error">${icon('alertTriangle')} ${err.message}</div>`;
  } finally {
    btn.classList.remove('loading');
    btn.disabled = false;
  }
}

// ============================================================
// PAGE: Batch Analysis
// ============================================================

// ============================================================
// PAGE: Batch Analysis — 3-Stage Dynamic Ingestion
// ============================================================

/**
 * renderBatch — 3-stage dynamic CSV ingestion workflow:
 *   Stage 1: Frictionless dropzone (upload any CSV)
 *   Stage 2: Data Health & Quality Audit (from /api/batch/profile)
 *   Stage 3: Mapping review + scoring + results export
 */
function renderBatch(container) {
  // ── State for this page ──────────────────────────────────────
  let currentUploadId = null;   // returned by /api/batch/profile
  let currentBatchId  = null;   // returned by /api/batch/dynamic-process
  let currentMappings = {};     // { model_feature: user_column } overrides collected from UI
  let currentReport   = null;   // last DatasetHealthReport from profile / remap

  // ── Stage 1 shell ────────────────────────────────────────────
  container.innerHTML = `
    <div class="page-header">
      <div class="breadcrumbs">
        <span class="crumb">RetentionIQ</span><span>›</span>
        <span class="crumb">Batch Analysis</span>
      </div>
      <h1 class="page-title">Batch Analysis &amp; Dynamic Ingestion</h1>
      <p class="page-subtitle">
        Upload <em>any</em> customer CSV — we will match your columns, clean messy values,
        fill gaps with sensible defaults, and show you <strong>exactly</strong> what was changed.
      </p>
    </div>
    ${synthAlert()}

    <!-- Stepper ------------------------------------------------>
    <div class="stepper" id="batchStepper">
      <div class="step-item active" id="step1Indicator">
        <div class="step-bubble">1</div>
        <div class="step-label">Upload File</div>
      </div>
      <div class="step-line"></div>
      <div class="step-item" id="step2Indicator">
        <div class="step-bubble">2</div>
        <div class="step-label">Health Audit</div>
      </div>
      <div class="step-line"></div>
      <div class="step-item" id="step3Indicator">
        <div class="step-bubble">3</div>
        <div class="step-label">Score &amp; Export</div>
      </div>
    </div>

    <!-- Stage 1: Dropzone -------------------------------------->
    <div id="stageUpload">
      <div class="card" style="margin-bottom:20px;">
        <div class="card-title">${icon('upload-cloud')} Drop your CSV — any format accepted</div>
        <div class="card-subtitle" style="margin-bottom:16px;">
          We accept messy, real-world exports: mixed column names, currency symbols, extra columns,
          missing values — no rigid contract required.
        </div>

        <div class="upload-zone" id="uploadZone" role="button" tabindex="0" aria-label="Upload CSV file">
          <div class="upload-icon">${icon('file-text')}</div>
          <div class="upload-text">Drag &amp; drop your CSV here</div>
          <div class="upload-hint">or click to browse &mdash; up to 25 MB, 100 000 rows</div>
          <input type="file" id="csvFileInput" accept=".csv,.tsv,.txt" style="display:none;" aria-label="Select CSV file"/>
        </div>

        <div id="fileInfo" style="margin-top:12px;font-size:0.84rem;color:var(--text-secondary);min-height:20px;"></div>

        <div style="margin-top:14px;display:flex;gap:10px;flex-wrap:wrap;align-items:center;">
          <button class="btn btn-primary" id="profileBtn" disabled>
            ${icon('cpu')} Analyse &amp; Profile Dataset
          </button>
          <a href="${API.batchTemplate}" download class="btn btn-secondary btn-sm">
            ${icon('download')} Blank Template
          </a>
          <a href="${API.batchSample}" download class="btn btn-ghost btn-sm">
            ${icon('download')} Sample CSV (10 rows)
          </a>
        </div>
      </div>

      <!-- Info accordion: what columns are expected -->
      <div class="contract-card">
        <div class="contract-header" id="contractToggle" role="button" tabindex="0" aria-expanded="false">
          <div class="contract-header-title">
            ${icon('info')}
            <span>What columns does the model use?</span>
            <span class="contract-header-badge">7 model features</span>
          </div>
          <div id="contractChevron" style="transition:transform 0.2s ease;transform:rotate(-90deg);">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="6 9 12 15 18 9"/></svg>
          </div>
        </div>
        <div class="contract-body" id="contractBody" style="display:none;">
          <p style="font-size:0.83rem;color:var(--text-secondary);margin-bottom:10px;">
            Your column names do <strong>not</strong> need to match exactly — the engine fuzzy-maps them.
            Columns that cannot be matched are filled with training-set defaults and flagged in the audit.
          </p>
          <div class="table-wrapper">
            <table class="contract-table">
              <thead>
                <tr><th>Model Feature</th><th>Typical Column Names / Aliases</th><th>Type</th><th>Range</th><th>Default if Missing</th></tr>
              </thead>
              <tbody>
                <tr><td><span class="col-code">age</span></td><td>age, user_age, customer_age, dob*</td><td>int</td><td>18–100</td><td>39 (median)</td></tr>
                <tr><td><span class="col-code">session_frequency</span></td><td>sessions, sessions_per_week, weekly_opens</td><td>numeric</td><td>0–100</td><td>7</td></tr>
                <tr><td><span class="col-code">avg_session_minutes</span></td><td>avg_session_minutes, session_duration, time_in_app</td><td>float</td><td>0–180</td><td>22.4</td></tr>
                <tr><td><span class="col-code">days_since_install</span></td><td>days_since_install, tenure, account_age_days</td><td>int</td><td>1–365</td><td>44</td></tr>
                <tr><td><span class="col-code">notifications_clicked</span></td><td>notifications_clicked, notif_clicks, push_clicks</td><td>int</td><td>0–100</td><td>10</td></tr>
                <tr><td><span class="col-code">crashes</span></td>
                  <td>crashes, crash_count, app_crashes</td><td>int</td><td>0–20</td>
                  <td><span style="color:#b45309;font-weight:600">0 ⚠ (biases toward retention)</span></td></tr>
                <tr><td><span class="col-code">purchases</span></td>
                  <td>purchases, transactions, in_app_purchases</td><td>int</td><td>0–50</td>
                  <td><span style="color:#b45309;font-weight:600">0 ⚠ (biases toward churn)</span></td></tr>
              </tbody>
            </table>
          </div>
          <p style="font-size:0.78rem;color:var(--text-secondary);margin-top:8px;">
            *DOB columns are auto-converted to age. Email columns are SHA-256 hashed for privacy.
          </p>
        </div>
      </div>
    </div><!-- /stageUpload -->

    <!-- Stage 2: Health Audit (hidden until profile returns) --->
    <div id="stageAudit" style="display:none;"></div>

    <!-- Stage 3: Scoring Results (hidden until process returns) -->
    <div id="stageResults" style="display:none;"></div>
  `;

  // ── Wire up contract accordion ────────────────────────────────
  const contractToggle  = document.getElementById('contractToggle');
  const contractBody    = document.getElementById('contractBody');
  const contractChevron = document.getElementById('contractChevron');
  let contractOpen = false;
  contractToggle.addEventListener('click', () => {
    contractOpen = !contractOpen;
    contractBody.style.display   = contractOpen ? 'block' : 'none';
    contractChevron.style.transform = contractOpen ? 'rotate(0deg)' : 'rotate(-90deg)';
    contractToggle.setAttribute('aria-expanded', contractOpen);
  });

  // ── Wire up file input ────────────────────────────────────────
  const uploadZone = document.getElementById('uploadZone');
  const fileInput  = document.getElementById('csvFileInput');
  const profileBtn = document.getElementById('profileBtn');
  const fileInfo   = document.getElementById('fileInfo');
  let selectedFile = null;

  uploadZone.addEventListener('click', () => fileInput.click());
  uploadZone.addEventListener('keydown', (e) => { if (e.key === 'Enter' || e.key === ' ') fileInput.click(); });
  uploadZone.addEventListener('dragover', (e) => { e.preventDefault(); uploadZone.classList.add('dragover'); });
  uploadZone.addEventListener('dragleave', () => uploadZone.classList.remove('dragover'));
  uploadZone.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadZone.classList.remove('dragover');
    if (e.dataTransfer.files[0]) pickFile(e.dataTransfer.files[0]);
  });
  fileInput.addEventListener('change', (e) => { if (e.target.files[0]) pickFile(e.target.files[0]); });

  function pickFile(file) {
    selectedFile = file;
    const sizeKB = (file.size / 1024).toFixed(1);
    fileInfo.innerHTML = `<strong>Selected:</strong> <code>${escHtml(file.name)}</code> — ${sizeKB} KB`;
    profileBtn.disabled = false;
    uploadZone.style.borderColor = 'var(--accent-1)';
    // Reset downstream stages if user picks a new file
    document.getElementById('stageAudit').style.display   = 'none';
    document.getElementById('stageAudit').innerHTML       = '';
    document.getElementById('stageResults').style.display = 'none';
    document.getElementById('stageResults').innerHTML     = '';
    setStep(1);
  }

  // ── Stepper helper ────────────────────────────────────────────
  function setStep(n) {
    [1,2,3].forEach(i => {
      const el = document.getElementById(`step${i}Indicator`);
      if (!el) return;
      el.classList.toggle('active',    i === n);
      el.classList.toggle('complete',  i <  n);
    });
  }

  // ── Stage 1 → Profile ─────────────────────────────────────────
  profileBtn.addEventListener('click', async () => {
    if (!selectedFile) return;
    profileBtn.classList.add('loading');
    profileBtn.disabled = true;

    const auditEl = document.getElementById('stageAudit');
    auditEl.style.display = 'block';
    auditEl.innerHTML = skeletonCard('Analysing your dataset…');

    const formData = new FormData();
    formData.append('file', selectedFile);

    try {
      const resp = await fetch(API.batchProfile, { method: 'POST', body: formData });
      const data = await resp.json();
      if (!resp.ok) throw new Error(data.detail || `HTTP ${resp.status}`);
      currentUploadId = data.upload_id;
      currentReport   = data;
      currentMappings = {};
      // Collect initial auto-mappings
      (data.mappings || []).forEach(m => {
        if (m.model_feature && m.user_column) currentMappings[m.model_feature] = m.user_column;
      });
      renderHealthAudit(auditEl, data);
      setStep(2);
    } catch (err) {
      auditEl.innerHTML = alertHtml('error', 'Profile Failed', err.message);
    } finally {
      profileBtn.classList.remove('loading');
      profileBtn.disabled = false;
    }
  });

  // ── Stage 2: render Health Audit card ────────────────────────
  function renderHealthAudit(el, report) {
    const score     = report.quality_score ?? 0;
    const scoreLabel= score >= 80 ? 'high' : score >= 55 ? 'medium' : 'low';
    const nMapped   = (report.mappings || []).filter(m => m.user_column).length;
    const nTotal    = 7;
    const cohort    = report.total_rows ?? 0;
    // API returns `overall_completeness` as a 0-1 fraction; multiply by 100 for display
    const complete  = report.overall_completeness != null
      ? (report.overall_completeness * 100)
      : (report.data_completeness_pct ?? 100);
    const confidence= (report.scoring_confidence || 'high').toLowerCase();

    // Confidence banner colour
    const confColour = confidence === 'high' ? 'success' : confidence === 'medium' ? 'warning' : 'error';
    const confLabel  = confidence === 'high'
      ? 'High — fully observed data, predictions are reliable.'
      : confidence === 'medium'
      ? 'Medium — some features imputed. Treat predictions as indicative.'
      : 'Low — many features imputed. Predictions may be unreliable; review mappings carefully.';

    // Imputation notices
    // API returns `notices` (list of ImputationNotice objects)
    const imputations = (report.notices || report.imputation_notices || []);
    const imputHtml = imputations.length === 0 ? '' : `
      <div style="margin-top:16px;">
        <div class="card-title" style="font-size:0.9rem;margin-bottom:8px;">⚠ Imputation Notices</div>
        ${imputations.map(n => `
          <div class="alert alert-warning" style="margin-bottom:8px;padding:10px 14px;">
            ${icon('info')}
            <div style="font-size:0.83rem;">
              <strong><code>${escHtml(n.feature)}</code></strong> —
              ${escHtml(n.message || `Defaulted to ${n.value_used ?? n.default_value}. ${n.bias_note || ''}`)}
            </div>
          </div>`).join('')}
      </div>`;

    // Mapping review grid
    const MODEL_FEATURES = ['age','session_frequency','avg_session_minutes',
                            'days_since_install','notifications_clicked','crashes','purchases'];
    // All user columns from profile
    const userCols = (report.columns || []).map(c => c.name || c.column_name || '').filter(Boolean);
    const allUserColOptions = ['— Ignore / Impute —', ...userCols].map(c =>
      `<option value="${escHtml(c)}">${escHtml(c)}</option>`).join('');

    const mappingGridHtml = `
      <div style="margin-top:20px;">
        <div style="display:flex;align-items:center;gap:10px;margin-bottom:12px;">
          <div class="card-title" style="font-size:0.9rem;margin:0;">Smart Column Mapping</div>
          <span style="font-size:0.8rem;color:var(--text-secondary);">${nMapped}/${nTotal} features mapped — adjust if needed</span>
        </div>
        <div class="mapping-grid">
          ${MODEL_FEATURES.map(feat => {
            const mapEntry = (report.mappings || []).find(m => m.model_feature === feat);
            const mappedCol = mapEntry ? (mapEntry.user_column || '') : '';
            const conf      = mapEntry ? (mapEntry.confidence || 0) : 0;
            const confClass = conf >= 0.8 ? 'high' : conf >= 0.5 ? 'medium' : 'low';
            const confPct   = (conf * 100).toFixed(0);
            const isImputed = !mappedCol;
            return `
              <div class="mapping-card ${isImputed ? 'imputed' : ''}">
                <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:6px;">
                  <span class="col-code" style="font-size:0.78rem;">${escHtml(feat)}</span>
                  ${isImputed
                    ? `<span class="conf-pill low">imputed</span>`
                    : `<span class="conf-pill ${confClass}">${confPct}% match</span>`}
                </div>
                <select class="mapping-select" data-feature="${escHtml(feat)}" aria-label="Column mapping for ${escHtml(feat)}">
                  ${MODEL_FEATURES.map(f => '').join('')}
                  ${['— Ignore / Impute —', ...userCols].map(c => {
                      const sel = c === mappedCol ? ' selected' : '';
                      return `<option value="${escHtml(c)}"${sel}>${escHtml(c)}</option>`;
                    }).join('')}
                </select>
                ${mappedCol
                  ? `<div style="font-size:0.75rem;color:var(--text-secondary);margin-top:4px;">
                       ← <code>${escHtml(mappedCol)}</code></div>`
                  : `<div style="font-size:0.75rem;color:#b45309;margin-top:4px;">Will use training default</div>`}
              </div>`;
          }).join('')}
        </div>
        <button class="btn btn-ghost btn-sm" id="remapBtn" style="margin-top:12px;">
          ${icon('refresh-cw')} Re-apply Mappings
        </button>
      </div>`;

    // Column health table (first 10 cols)
    const colRows = (report.columns || []).slice(0, 20).map(c => {
      const name     = c.name || c.column_name || '—';
      const dtype    = c.detected_type || c.dtype || '?';
      const nullPct  = c.null_pct != null ? fmtPct(c.null_pct / 100) : '—';
      const outPct   = c.outlier_pct != null ? fmtPct(c.outlier_pct / 100) : '—';
      const mapped   = c.mapped_to || '—';
      return `<tr>
        <td><code>${escHtml(name)}</code></td>
        <td>${escHtml(dtype)}</td>
        <td>${nullPct}</td>
        <td>${outPct}</td>
        <td>${mapped !== '—' ? `<span class="col-code" style="font-size:0.75rem;">${escHtml(mapped)}</span>` : '<span style="color:var(--text-secondary)">—</span>'}</td>
      </tr>`;
    }).join('');

    // Data preview (first 10 rows from report.preview)
    // API returns `data_preview` (10-row sample dict list)
    const preview = report.data_preview || report.preview || [];
    const previewCols = preview.length > 0 ? Object.keys(preview[0]).slice(0, 8) : [];
    const previewHtml = preview.length === 0 ? '' : `
      <div style="margin-top:20px;">
        <div class="card-title" style="font-size:0.9rem;margin-bottom:8px;">Data Preview (first 10 rows)</div>
        <div class="table-wrapper">
          <table style="font-size:0.78rem;">
            <thead><tr>${previewCols.map(c => `<th>${escHtml(c)}</th>`).join('')}</tr></thead>
            <tbody>${preview.slice(0,10).map(row =>
              `<tr>${previewCols.map(c => `<td>${escHtml(String(row[c] ?? ''))}</td>`).join('')}</tr>`
            ).join('')}</tbody>
          </table>
        </div>
      </div>`;

    // Historical retention rate if target detected
    const histHtml = report.historical_retention_rate != null ? `
      <div class="alert alert-info" style="margin-top:14px;">
        ${icon('info')}
        <div style="font-size:0.83rem;">
          <strong>Historical Retention Rate Detected:</strong>
          <code>${fmtPct(report.historical_retention_rate)}</code> — based on the
          <code>${escHtml(report.target_column || 'retained')}</code> column found in your file.
          This column is used for profiling only and is <strong>not</strong> passed to the model.
        </div>
      </div>` : '';

    el.innerHTML = `
      <div class="card fade-in-up" style="margin-bottom:20px;">
        <div class="card-title">
          ${icon('bar-chart-2')} Data Health &amp; Quality Audit
          <span style="font-size:0.8rem;color:var(--text-secondary);font-weight:400;margin-left:8px;">
            ${escHtml(selectedFile?.name || 'upload.csv')}
          </span>
        </div>

        <!-- KPI tiles -->
        <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:14px;margin:16px 0;">
          <div style="text-align:center;padding:16px 8px;background:var(--surface-2);border-radius:10px;">
            <div class="score-badge-circle ${scoreLabel}" style="margin:0 auto 8px;">${score.toFixed(0)}</div>
            <div style="font-size:0.78rem;color:var(--text-secondary);">Quality Score</div>
          </div>
          <div style="text-align:center;padding:16px 8px;background:var(--surface-2);border-radius:10px;">
            <div style="font-size:1.8rem;font-weight:700;color:var(--text-primary);">${cohort.toLocaleString()}</div>
            <div style="font-size:0.78rem;color:var(--text-secondary);">Cohort Size</div>
          </div>
          <div style="text-align:center;padding:16px 8px;background:var(--surface-2);border-radius:10px;">
            <div style="font-size:1.8rem;font-weight:700;color:var(--text-primary);">${nMapped}/${nTotal}</div>
            <div style="font-size:0.78rem;color:var(--text-secondary);">Features Mapped</div>
          </div>
          <div style="text-align:center;padding:16px 8px;background:var(--surface-2);border-radius:10px;">
            <div style="font-size:1.8rem;font-weight:700;color:var(--text-primary);">${fmtPct(complete/100)}</div>
            <div style="font-size:0.78rem;color:var(--text-secondary);">Data Completeness</div>
          </div>
        </div>

        <!-- Confidence banner -->
        <div class="alert alert-${confColour}" style="margin-bottom:16px;">
          ${icon(confidence === 'high' ? 'checkCircle' : 'alertTriangle')}
          <div>
            <strong>Scoring Confidence: ${confidence.charAt(0).toUpperCase() + confidence.slice(1)}</strong>
            — ${confLabel}
          </div>
        </div>

        ${histHtml}
        ${imputHtml}
        ${mappingGridHtml}

        <!-- Column health table -->
        ${colRows ? `
          <div style="margin-top:20px;">
            <div class="card-title" style="font-size:0.9rem;margin-bottom:8px;">Column Health</div>
            <div class="table-wrapper">
              <table style="font-size:0.8rem;">
                <thead>
                  <tr><th>Column</th><th>Type</th><th>Null %</th><th>Outlier %</th><th>Mapped To</th></tr>
                </thead>
                <tbody>${colRows}</tbody>
              </table>
            </div>
            ${(report.columns||[]).length > 20
              ? `<p style="font-size:0.75rem;color:var(--text-secondary);margin-top:4px;">
                   Showing 20 of ${(report.columns||[]).length} columns.</p>` : ''}
          </div>` : ''}

        ${previewHtml}

        <!-- Score Dataset Now button -->
        <div style="margin-top:24px;display:flex;gap:12px;flex-wrap:wrap;align-items:center;">
          <button class="btn btn-primary btn-lg" id="scoreNowBtn">
            ${icon('zap')} Score Dataset Now
          </button>
          <span style="font-size:0.8rem;color:var(--text-secondary);">
            Rows will be scored, saved to the database, and available for export.
          </span>
        </div>
      </div>
    `;

    // ── Wire mapping dropdowns → remap ────────────────────────
    el.querySelectorAll('.mapping-select').forEach(sel => {
      sel.addEventListener('change', () => {
        const feat = sel.getAttribute('data-feature');
        const val  = sel.value;
        if (val && val !== '— Ignore / Impute —') {
          currentMappings[feat] = val;
        } else {
          delete currentMappings[feat];
        }
      });
    });

    // ── Remap button ──────────────────────────────────────────
    const remapBtn = el.querySelector('#remapBtn');
    if (remapBtn) {
      remapBtn.addEventListener('click', async () => {
        remapBtn.classList.add('loading');
        remapBtn.disabled = true;
        try {
          const resp = await fetch(API.batchRemap, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ upload_id: currentUploadId, overrides: currentMappings }),
          });
          const data = await resp.json();
          if (!resp.ok) throw new Error(data.detail || `HTTP ${resp.status}`);
          currentReport = data;
          // Re-render audit with updated mappings
          renderHealthAudit(el, data);
        } catch (err) {
          el.insertAdjacentHTML('afterbegin', alertHtml('error', 'Remap Failed', err.message));
        } finally {
          remapBtn.classList.remove('loading');
          remapBtn.disabled = false;
        }
      });
    }

    // ── Score Now button ──────────────────────────────────────
    const scoreBtn = el.querySelector('#scoreNowBtn');
    if (scoreBtn) {
      scoreBtn.addEventListener('click', async () => {
        scoreBtn.classList.add('loading');
        scoreBtn.disabled = true;
        const resultsEl = document.getElementById('stageResults');
        resultsEl.style.display = 'block';
        resultsEl.innerHTML     = skeletonCard('Scoring your dataset — this may take a moment…');
        resultsEl.scrollIntoView({ behavior: 'smooth', block: 'start' });

        try {
          const resp = await fetch(API.batchProcess, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ upload_id: currentUploadId, overrides: currentMappings }),
          });
          const data = await resp.json();
          if (!resp.ok) throw new Error(data.detail || `HTTP ${resp.status}`);
          currentBatchId = data.batch_id;
          renderScoringResults(resultsEl, data);
          setStep(3);
        } catch (err) {
          resultsEl.innerHTML = alertHtml('error', 'Scoring Failed', err.message);
        } finally {
          scoreBtn.classList.remove('loading');
          scoreBtn.disabled = false;
        }
      });
    }
  }// /renderHealthAudit

  // ── Stage 3: Scoring Results ──────────────────────────────────
  function renderScoringResults(el, data) {
    const results    = data.results || [];
    const batchId    = data.batch_id;
    const confidence = (data.scoring_confidence || 'high').toLowerCase();
    const confColour = confidence === 'high' ? 'success' : confidence === 'medium' ? 'warning' : 'error';

    // Risk distribution counts
    const highC = results.filter(r => (r.risk_tier||'').toLowerCase() === 'high').length;
    const medC  = results.filter(r => (r.risk_tier||'').toLowerCase() === 'medium').length;
    const lowC  = results.filter(r => (r.risk_tier||'').toLowerCase() === 'low').length;

    // Build results rows (first 100)
    const rowsHtml = results.slice(0, 100).map((r, i) => {
      const prob    = r.retention_probability ?? r.probability ?? null;
      const tier    = r.risk_tier || r.risk_level || '—';
      const custId  = r.customer_id || `ROW-${i+1}`;
      const drivers = (r.top_drivers || []).slice(0, 3).map(d =>
        `<span style="font-size:0.72rem;background:var(--surface-2);border-radius:4px;padding:1px 5px;">
           ${escHtml(String(d))}
         </span>`).join(' ');
      const qualFlag = r.data_quality_flag || '';
      const imputed  = (r.imputed_features || []).join(', ');
      return `<tr>
        <td><code style="font-size:0.78rem;">${escHtml(String(custId))}</code></td>
        <td>
          ${prob != null ? `
            <div style="display:flex;align-items:center;gap:8px;">
              <div class="progress-bar-wrapper" style="width:56px;">
                <div class="progress-bar ${tier.toLowerCase()}" style="width:${(prob*100).toFixed(0)}%;"></div>
              </div>
              <span style="font-weight:600;">${fmtPct(prob)}</span>
            </div>` : '<span style="color:var(--text-secondary);">—</span>'}
        </td>
        <td>${riskBadge(tier)}</td>
        <td style="max-width:180px;">${drivers || '<span style="color:var(--text-secondary);font-size:0.78rem;">n/a</span>'}</td>
        <td style="font-size:0.75rem;color:var(--text-secondary);">
          ${imputed ? `<span title="${escHtml(imputed)}">⚠ ${escHtml(imputed.length > 30 ? imputed.slice(0,28)+'…' : imputed)}</span>` : '<span style="color:#16a34a;">✓ Complete</span>'}
        </td>
        <td>
          ${qualFlag === 'poor'   ? `<span class="conf-pill low">${icon('alertTriangle')} poor</span>`   :
            qualFlag === 'fair'   ? `<span class="conf-pill medium">fair</span>` :
            qualFlag === 'good'   ? `<span class="conf-pill high">good</span>`   : '—'}
        </td>
      </tr>`;
    }).join('');

    el.innerHTML = `
      <div class="card fade-in-up" style="margin-bottom:20px;">
        <div class="card-title">${icon('check-circle')} Scoring Complete &mdash; Batch #${batchId}</div>
        <div class="card-subtitle">${results.length.toLocaleString()} customers scored and saved to database</div>

        <!-- Risk distribution pills -->
        <div style="display:flex;gap:12px;margin:16px 0;flex-wrap:wrap;">
          <div style="display:flex;align-items:center;gap:6px;padding:8px 16px;background:#fef2f2;border-radius:8px;border:1px solid #fca5a5;">
            <span style="font-weight:700;font-size:1.2rem;color:#dc2626;">${highC}</span>
            <span style="font-size:0.82rem;color:#dc2626;">High Risk</span>
          </div>
          <div style="display:flex;align-items:center;gap:6px;padding:8px 16px;background:#fffbeb;border-radius:8px;border:1px solid #fcd34d;">
            <span style="font-weight:700;font-size:1.2rem;color:#d97706;">${medC}</span>
            <span style="font-size:0.82rem;color:#d97706;">Medium Risk</span>
          </div>
          <div style="display:flex;align-items:center;gap:6px;padding:8px 16px;background:#f0fdf4;border-radius:8px;border:1px solid #86efac;">
            <span style="font-weight:700;font-size:1.2rem;color:#16a34a;">${lowC}</span>
            <span style="font-size:0.82rem;color:#16a34a;">Low Risk</span>
          </div>
        </div>

        <!-- Confidence banner -->
        ${confidence !== 'high' ? `
          <div class="alert alert-${confColour}" style="margin-bottom:16px;">
            ${icon('alertTriangle')}
            <div style="font-size:0.83rem;">
              <strong>Scoring Confidence: ${confidence.charAt(0).toUpperCase() + confidence.slice(1)}</strong>
              — Some features were imputed. Predictions marked with ⚠ should be treated as estimates.
            </div>
          </div>` : ''}

        <!-- Results table -->
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
          <span style="font-size:0.84rem;color:var(--text-secondary);">
            Showing first ${Math.min(100, results.length)} of ${results.length.toLocaleString()} rows
          </span>
          <a href="${API.batchExport(batchId)}" class="btn btn-secondary btn-sm">
            ${icon('download')} Export Enriched CSV
          </a>
        </div>

        <div class="table-wrapper">
          <table style="font-size:0.8rem;">
            <thead>
              <tr>
                <th>Customer ID</th>
                <th>Retention Prob.</th>
                <th>Risk Tier</th>
                <th>Top Drivers</th>
                <th>Imputed Features</th>
                <th>Data Quality</th>
              </tr>
            </thead>
            <tbody>${rowsHtml}</tbody>
          </table>
        </div>
        ${results.length > 100 ? `
          <p style="font-size:0.75rem;color:var(--text-secondary);margin-top:8px;">
            Showing 100 of ${results.length.toLocaleString()} scored rows. Use <em>Export Enriched CSV</em> for the full dataset.
          </p>` : ''}

        <div class="alert alert-info" style="margin-top:16px;">
          ${icon('info')}
          <div style="font-size:0.82rem;">
            Exported CSV includes original columns plus: <code>predicted_retention</code>,
            <code>retention_probability</code>, <code>risk_tier</code>, <code>top_drivers</code>,
            <code>imputed_features</code>, <code>data_quality_flag</code>.
          </div>
        </div>
      </div>
    `;
  }// /renderScoringResults

  // ── Utility: skeleton placeholder card ───────────────────────
  function skeletonCard(msg) {
    return `<div class="card"><p style="color:var(--text-secondary);font-size:0.9rem;">${escHtml(msg)}</p>
      <div class="skeleton skeleton-chart" style="margin-top:12px;"></div></div>`;
  }

  // ── Utility: generic alert block ─────────────────────────────
  function alertHtml(type, title, msg) {
    const t = type === 'error' ? 'alert-error' : type === 'warning' ? 'alert-warning' : 'alert-info';
    const i = type === 'error' ? icon('alertTriangle') : icon('info');
    return `<div class="alert ${t}" style="margin-bottom:16px;">
      ${i}<div><strong>${escHtml(title)}:</strong> ${escHtml(msg)}</div></div>`;
  }
}

// Render Dry-Run Pre-Flight Validation Report
function renderDryRunValidationReport(report) {
  const container = document.getElementById('batchResults');
  const isValid = report.is_valid;

  container.innerHTML = `
    <div class="card fade-in-up">
      <div class="card-title">Pre-Flight Diagnostic Report (Dry Run)</div>
      <div class="card-subtitle">File: <code>${report.filename}</code> — No records written to database</div>

      <div class="diag-pill-grid">
        <div class="diag-pill success">
          ${icon('checkCircle')} Plain Text CSV Format
        </div>
        <div class="diag-pill ${report.missing_columns.length === 0 ? 'success' : 'danger'}">
          ${report.missing_columns.length === 0 ? icon('checkCircle') + ' All 7 Core Features Found' : icon('alertTriangle') + ' Missing Required Columns'}
        </div>
        <div class="diag-pill ${isValid ? 'success' : 'danger'}">
          ${isValid ? icon('checkCircle') + ` ${report.total_rows} Rows Validated (100% Pass)` : icon('alertTriangle') + ` ${report.error_rows} Invalid / ${report.valid_rows} Valid`}
        </div>
      </div>

      ${isValid ? `
        <div class="alert alert-success" style="margin-bottom:16px;">
          ${icon('checkCircle')} <div><strong>Pre-flight check passed!</strong> All ${report.total_rows} rows satisfy the data contract. You can now click <em>Process & Score CSV</em>.</div>
        </div>
      ` : `
        <div class="alert alert-error" style="margin-bottom:16px;">
          ${icon('alertTriangle')} <div><strong>Validation Alert:</strong> ${report.error_rows} row(s) contain errors and violate the contract. Inspect the error audit table below:</div>
        </div>
        ${buildActionableErrorTable(report.errors)}
      `}
    </div>
  `;
}

// Render Strict Mode Rejection Report (HTTP 422)
function renderStrictRejectionReport(report) {
  const container = document.getElementById('batchResults');
  container.innerHTML = `
    <div class="card fade-in-up" style="border-color:var(--risk-high-border);">
      <div class="card-title" style="color:var(--risk-high);">
        ${icon('alertTriangle')} Strict Mode Ingestion Halted (HTTP 422)
      </div>
      <div class="card-subtitle">
        File: <code>${report.filename || 'upload.csv'}</code> — No rows were written to the database.
      </div>

      <div class="alert alert-error" style="margin-bottom:16px;">
        ${icon('alertTriangle')}
        <div>
          <strong>Batch Rejected:</strong> ${report.error_rows} of ${report.total_rows} rows violated the contract. In Strict Mode, the entire file must be valid. Fix the errors below or switch to Lenient Mode.
        </div>
      </div>

      <div class="diag-pill-grid">
        <div class="diag-pill neutral">Total Rows: ${report.total_rows}</div>
        <div class="diag-pill success">Valid Rows: ${report.valid_rows}</div>
        <div class="diag-pill danger">Failed Rows: ${report.error_rows}</div>
      </div>

      ${buildActionableErrorTable(report.errors || [])}
    </div>
  `;
}

// Render Scored Batch Results (Lenient Mode or 100% Valid Strict Mode)
function renderBatchResults(data) {
  const ok = data.results.filter(r => r.ok);
  const errors = data.results.filter(r => !r.ok);
  const detailedErrors = data.errors || [];

  document.getElementById('batchResults').innerHTML = `
    <div class="card fade-in-up">
      <div class="card-title">Batch Scoring Complete — ${data.filename}</div>
      <div class="card-subtitle">Batch #${data.batch_id} saved to history database</div>

      <div class="diag-pill-grid">
        <div class="diag-pill success">${icon('checkCircle')} Scored: ${data.valid_rows} rows</div>
        ${data.error_rows > 0 ? `<div class="diag-pill danger">${icon('alertTriangle')} Errors: ${data.error_rows} rows</div>` : ''}
        <div class="diag-pill neutral">Total Evaluated: ${data.total_rows} rows</div>
      </div>

      ${errors.length ? `
        <div class="alert alert-error" style="margin-bottom:16px;">
          ${icon('alertTriangle')} <div><strong>Partial Ingestion Notice:</strong> ${errors.length} row(s) contained errors and were skipped. Valid rows were successfully scored and saved.</div>
        </div>
        <div style="margin-bottom:20px;">
          <div class="card-title" style="font-size:0.95rem;color:var(--risk-high);">Actionable Error Audit</div>
          ${buildActionableErrorTable(detailedErrors)}
        </div>
      ` : ''}

      <div class="flex justify-between items-center mb-4" style="margin-top:20px;">
        <span class="text-sm text-muted">${ok.length} customers scored successfully</span>
        <a href="${API.reports.csv}?batch_id=${data.batch_id}" class="btn btn-secondary btn-sm">
          ${icon('download')} Export Scored CSV
        </a>
      </div>

      <div class="table-wrapper">
        <table>
          <thead>
            <tr>
              <th>Row</th>
              <th>Customer ID</th>
              <th>Status</th>
              <th>Probability</th>
              <th>Risk Tier</th>
            </tr>
          </thead>
          <tbody>
            ${data.results.slice(0, 100).map(r => `
              <tr>
                <td>${r.row_index}</td>
                <td><code>${r.customer_id || 'USR-' + r.row_index}</code></td>
                <td>
                  ${r.ok
                    ? `<span style="color:var(--risk-low);font-weight:600;">✓ Scored</span>`
                    : `<span style="color:var(--risk-high);font-weight:600;font-size:0.8rem;" title="${r.error}">✗ Failed</span>`}
                </td>
                <td>
                  ${r.probability != null
                    ? `<div style="display:flex;align-items:center;gap:8px;">
                        <div class="progress-bar-wrapper" style="width:60px;">
                          <div class="progress-bar ${r.risk_level.toLowerCase()}" style="width:${(r.probability*100).toFixed(0)}%;"></div>
                        </div>
                        <span style="font-weight:600;">${fmtPct(r.probability)}</span>
                       </div>`
                    : `<span class="text-muted text-sm">${r.error || '—'}</span>`}
                </td>
                <td>${r.risk_level ? riskBadge(r.risk_level) : '—'}</td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>
      ${data.results.length > 100 ? `<p class="text-muted text-sm mt-2">Showing first 100 rows. Use <em>Export Scored CSV</em> to download the complete cohort.</p>` : ''}
    </div>
  `;
}

// Helper: Build Actionable Error Table
function buildActionableErrorTable(errors) {
  if (!errors || errors.length === 0) {
    return `<p class="text-muted text-sm">No itemized cell errors reported.</p>`;
  }

  return `
    <div class="error-table-wrapper">
      <table class="error-table">
        <thead>
          <tr>
            <th>Row #</th>
            <th>Customer ID</th>
            <th>Column</th>
            <th>Offending Value</th>
            <th>Constraint Violated</th>
            <th>Remediation Tip</th>
          </tr>
        </thead>
        <tbody>
          ${errors.slice(0, 50).map(e => `
            <tr>
              <td style="font-weight:700;">Row ${e.row_index}</td>
              <td><code>${e.customer_id || '—'}</code></td>
              <td><span class="col-code">${e.column}</span></td>
              <td><span class="err-val">${e.invalid_value}</span></td>
              <td style="color:#9F1239;font-weight:500;">${e.constraint}</td>
              <td class="err-remediation">${e.remediation || e.message}</td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    </div>
    ${errors.length > 50 ? `<p class="text-muted text-sm mt-2">Showing first 50 of ${errors.length} errors.</p>` : ''}
  `;
}


// ============================================================
// PAGE: Customers
// ============================================================

async function renderCustomers(container) {
  container.innerHTML = `
    <div class="page-header">
      <div class="breadcrumbs"><span class="crumb">RetentionIQ</span><span>›</span><span class="crumb">Customers</span></div>
      <h1 class="page-title">Customers</h1>
      <p class="page-subtitle">All scored customers — click a row to see SHAP explanation</p>
    </div>
    ${synthAlert()}
    <div class="filter-bar">
      <input type="search" class="form-input" id="custSearch" placeholder="Search customer ID…" style="max-width:250px;" value="${state.customersSearch}"/>
      <select class="filter-select" id="custRisk">
        <option value="">All Risk Levels</option>
        <option value="High" ${state.customersRisk === 'High' ? 'selected' : ''}>High Risk</option>
        <option value="Medium" ${state.customersRisk === 'Medium' ? 'selected' : ''}>Medium Risk</option>
        <option value="Low" ${state.customersRisk === 'Low' ? 'selected' : ''}>Low Risk</option>
      </select>
      <a href="${API.customers.export}" class="btn btn-secondary btn-sm">${icon('download')} Export CSV</a>
    </div>
    <div class="card" id="customersTable">
      <div class="skeleton skeleton-chart"></div>
    </div>
  `;

  document.getElementById('custSearch').addEventListener('input', debounce((e) => {
    state.customersSearch = e.target.value;
    state.customersPage = 0;
    loadCustomersTable();
  }, 300));
  document.getElementById('custRisk').addEventListener('change', (e) => {
    state.customersRisk = e.target.value;
    state.customersPage = 0;
    loadCustomersTable();
  });

  await loadCustomersTable();
}

async function loadCustomersTable() {
  const el = document.getElementById('customersTable');
  if (!el) return;

  const limit = 25;
  const offset = state.customersPage * limit;
  const params = new URLSearchParams({ limit, offset });
  if (state.customersRisk) params.set('risk', state.customersRisk);
  if (state.customersSearch) params.set('search', state.customersSearch);

  try {
    const data = await apiFetch(API.customers.list + '?' + params);
    const totalPages = Math.ceil(data.total / limit);

    if (data.total === 0) {
      el.innerHTML = `<div class="empty-state">
        <div class="empty-icon">${icon('users')}</div>
        <div class="empty-title">No Customers Found</div>
        <div class="empty-desc">Score customers via Predict or Batch Analysis to see them here.</div>
      </div>`;
      return;
    }

    el.innerHTML = `
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
        <span class="text-sm text-muted">${data.total} customers</span>
      </div>
      <div class="table-wrapper">
        <table>
          <thead><tr><th>ID</th><th>Customer</th><th>Date</th><th>Probability</th><th>Risk</th><th>Crashes</th><th>Sessions/wk</th><th>Source</th></tr></thead>
          <tbody>${data.items.map(c => `
            <tr data-id="${c.id}">
              <td>${c.id}</td>
              <td>${c.customer_id || `User #${c.id}`}</td>
              <td style="font-size:0.78rem;color:var(--text-muted)">${c.created_at?.substring(0, 16).replace('T',' ') || '—'}</td>
              <td>
                <div style="display:flex;align-items:center;gap:8px;">
                  <div class="progress-bar-wrapper" style="width:60px">
                    <div class="progress-bar ${c.risk_level.toLowerCase()}" style="width:${c.probability*100}%"></div>
                  </div>
                  <span style="font-weight:600;font-size:0.85rem">${fmtPct(c.probability)}</span>
                </div>
              </td>
              <td>${riskBadge(c.risk_level)}</td>
              <td>${c.features?.crashes ?? '—'}</td>
              <td>${c.features?.session_frequency ?? '—'}</td>
              <td><span style="font-size:0.75rem;color:var(--text-muted);text-transform:capitalize">${c.source}</span></td>
            </tr>`).join('')}
          </tbody>
        </table>
      </div>
      <div class="pagination">
        <span>${offset + 1}–${Math.min(offset + limit, data.total)} of ${data.total}</span>
        <button ${state.customersPage === 0 ? 'disabled' : ''} id="custPrev">${icon('chevronLeft')}</button>
        <button ${state.customersPage >= totalPages - 1 ? 'disabled' : ''} id="custNext">${icon('chevronRight')}</button>
      </div>
    `;

    el.querySelectorAll('tr[data-id]').forEach(row => {
      row.addEventListener('click', () => openCustomerDrawer(parseInt(row.dataset.id)));
    });
    document.getElementById('custPrev')?.addEventListener('click', () => {
      state.customersPage--; loadCustomersTable();
    });
    document.getElementById('custNext')?.addEventListener('click', () => {
      state.customersPage++; loadCustomersTable();
    });
  } catch (err) {
    el.innerHTML = `<div class="alert alert-error">${icon('alertTriangle')} ${err.message}</div>`;
  }
}

async function openCustomerDrawer(id) {
  openDrawer(`Customer #${id}`, `<div class="skeleton skeleton-chart"></div>`);
  try {
    const data = await apiFetch(API.customers.detail(id));
    const exp = data.explanation;
    const risk = data.risk_level;
    document.getElementById('drawerContent').innerHTML = `
      <div style="margin-bottom:20px;">
        <div class="gauge-wrapper">
          ${buildGauge(data.probability, risk)}
          <div class="gauge-label">
            <div class="gauge-prob">${fmtPct(data.probability)}</div>
            <div style="margin-top:6px;">${riskBadge(risk)}</div>
          </div>
        </div>
      </div>
      <div class="section-divider"></div>
      <div style="font-size:0.82rem;color:var(--text-secondary);line-height:1.6;margin-bottom:16px;">${exp.plain_english}</div>
      <div class="card-title" style="margin-bottom:8px;font-size:0.9rem;">SHAP Feature Contributions</div>
      ${buildSHAPWaterfall(exp.contribs, exp.bias)}
      ${exp.actions.length ? `
        <div class="section-divider"></div>
        <div class="card-title" style="margin-bottom:8px;font-size:0.9rem;">Recommended Actions</div>
        ${exp.actions.map(a => `
          <div class="alert alert-info" style="margin-bottom:8px;font-size:0.82rem;">
            ${icon('checkCircle')} <div><strong>${FEATURES.find(f=>f.key===a.feature)?.label || a.feature}</strong>: ${a.action}</div>
          </div>`).join('')}` : ''}
      <div class="section-divider"></div>
      <div class="card-title" style="margin-bottom:8px;font-size:0.9rem;">Feature Values</div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;">
        ${FEATURES.map(f => `
          <div style="background:var(--surface-bg);border-radius:8px;padding:8px 12px;">
            <div style="font-size:0.75rem;color:var(--text-muted)">${f.label}</div>
            <div style="font-weight:600;font-size:0.9rem">${data.features?.[f.key] ?? '—'}${f.unit ? ' ' + f.unit : ''}</div>
          </div>`).join('')}
      </div>
      <div class="section-divider"></div>
      <div style="font-size:0.75rem;color:var(--text-muted);">${data.synthetic_data_notice}</div>
    `;
  } catch (err) {
    document.getElementById('drawerContent').innerHTML =
      `<div class="alert alert-error">${icon('alertTriangle')} ${err.message}</div>`;
  }
}

// ============================================================
// PAGE: Explainability Lab
// ============================================================

async function renderExplain(container) {
  container.innerHTML = `
    <div class="page-header">
      <div class="breadcrumbs"><span class="crumb">RetentionIQ</span><span>›</span><span class="crumb">Explainability Lab</span></div>
      <h1 class="page-title">Explainability Lab</h1>
      <p class="page-subtitle">Global and local model explanations using XGBoost native SHAP contributions</p>
    </div>
    ${synthAlert()}
    <div class="tabs" id="explainTabs">
      <button class="tab-btn active" data-tab="global">Global Importance</button>
      <button class="tab-btn" data-tab="whatif">What-If Simulator</button>
      <button class="tab-btn" data-tab="pdp">Dependence Plots</button>
      <button class="tab-btn" data-tab="modelcard">Model Card</button>
    </div>
    <div id="explainContent">
      <div class="skeleton skeleton-chart"></div>
    </div>
  `;

  document.querySelectorAll('#explainTabs .tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('#explainTabs .tab-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      renderExplainTab(btn.dataset.tab);
    });
  });

  await renderExplainTab('global');
}

async function renderExplainTab(tab) {
  const el = document.getElementById('explainContent');
  el.innerHTML = `<div class="skeleton skeleton-chart"></div>`;

  if (tab === 'global') await renderGlobalTab(el);
  else if (tab === 'whatif') renderWhatIfTab(el);
  else if (tab === 'pdp') await renderPDPTab(el);
  else if (tab === 'modelcard') await renderModelCard(el);
}

function renderBeeswarmPlot(canvasId, g) {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  const dpr = window.devicePixelRatio || 1;
  const width = canvas.parentElement.clientWidth || 700;
  const height = 300;
  canvas.width = width * dpr;
  canvas.height = height * dpr;
  canvas.style.width = width + 'px';
  canvas.style.height = height + 'px';
  ctx.scale(dpr, dpr);

  const margin = { top: 20, right: 30, bottom: 45, left: 150 };
  const plotWidth = width - margin.left - margin.right;
  const plotHeight = height - margin.top - margin.bottom;

  const sortedFeats = Object.entries(g.mean_abs_shap)
    .sort((a, b) => b[1] - a[1])
    .map(e => e[0]);

  let maxAbs = 0.5;
  sortedFeats.forEach(f => {
    (g.all_shap_values[f] || []).forEach(v => {
      if (Math.abs(v) > maxAbs) maxAbs = Math.abs(v);
    });
  });
  maxAbs = maxAbs * 1.08;

  const scaleX = (val) => margin.left + ((val + maxAbs) / (2 * maxAbs)) * plotWidth;
  const zeroX = scaleX(0);

  // Center reference line
  ctx.strokeStyle = '#CBD5E1';
  ctx.lineWidth = 1.5;
  ctx.setLineDash([4, 4]);
  ctx.beginPath();
  ctx.moveTo(zeroX, margin.top);
  ctx.lineTo(zeroX, margin.top + plotHeight);
  ctx.stroke();
  ctx.setLineDash([]);

  const rowHeight = plotHeight / sortedFeats.length;

  sortedFeats.forEach((feat, rowIdx) => {
    const yCenter = margin.top + rowIdx * rowHeight + rowHeight / 2;
    const featInfo = FEATURES.find(f => f.key === feat);
    const label = featInfo ? featInfo.label : feat;

    // Feature label
    ctx.font = '500 12px Inter, system-ui, sans-serif';
    ctx.fillStyle = '#1E1B4B';
    ctx.textAlign = 'right';
    ctx.textBaseline = 'middle';
    ctx.fillText(label, margin.left - 12, yCenter);

    // Baseline
    ctx.strokeStyle = '#F1F5F9';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(margin.left, yCenter);
    ctx.lineTo(margin.left + plotWidth, yCenter);
    ctx.stroke();

    const shapVals = g.all_shap_values[feat] || [];
    const featVals = g.all_feature_values[feat] || [];
    const minVal = Math.min(...featVals);
    const maxVal = Math.max(...featVals);
    const valRange = (maxVal - minVal) || 1;

    shapVals.forEach((sVal, i) => {
      const fVal = featVals[i];
      const norm = Math.max(0, Math.min(1, (fVal - minVal) / valRange));
      const px = scaleX(sVal);
      // Hash-based deterministic jitter
      const jitter = ((Math.sin(i * 12.9898 + rowIdx * 78.233) * 43758.5453) % 1) * (rowHeight * 0.32);
      const py = yCenter + jitter;

      // Gradient: Cool Indigo/Blue (low) to Hot Pink/Red (high)
      const r = Math.round(59 + norm * (236 - 59));
      const gCol = Math.round(130 + norm * (72 - 130));
      const b = Math.round(246 + norm * (153 - 246));

      ctx.fillStyle = `rgba(${r}, ${gCol}, ${b}, 0.60)`;
      ctx.beginPath();
      ctx.arc(px, py, 2.5, 0, Math.PI * 2);
      ctx.fill();
    });
  });

  // Axis labels
  ctx.fillStyle = '#64748B';
  ctx.font = '11px Inter, system-ui, sans-serif';
  ctx.textAlign = 'center';
  ctx.fillText('← Toward Churn (SHAP < 0)', margin.left + plotWidth * 0.25, height - 10);
  ctx.fillText('Toward Retention (SHAP > 0) →', margin.left + plotWidth * 0.75, height - 10);
  ctx.fillText('0', zeroX, height - 24);
}

async function renderGlobalTab(el) {
  try {
    if (!state.globalExplanation) {
      state.globalExplanation = await apiFetch(API.explain.global);
    }
    const g = state.globalExplanation;

    // Sort features by mean |SHAP|
    const sorted = Object.entries(g.mean_abs_shap).sort((a,b) => b[1]-a[1]);
    const labels = sorted.map(([k]) => FEATURES.find(f=>f.key===k)?.label || k);
    const shapVals = sorted.map(([,v]) => v);
    const gainVals = sorted.map(([k]) => g.gain[k] || 0);
    const weightVals = sorted.map(([k]) => g.weight[k] || 0);

    el.innerHTML = `
      <div class="card" style="margin-bottom:20px;">
        <div class="card-title">Feature Importance Comparison</div>
        <div class="card-subtitle">Mean |SHAP| vs Gain vs Weight — same model, different perspectives</div>
        <div class="alert alert-info" style="margin-bottom:16px;">
          ${icon('info')} <span style="font-size:0.82rem;">${g.note}</span>
        </div>
        <canvas id="globalImportanceChart" height="250"></canvas>
      </div>

      <div class="card" style="margin-bottom:20px;">
        <div class="card-title">SHAP Summary Plot (Beeswarm)</div>
        <div class="card-subtitle">Distribution of SHAP impact across 500 sampled customers — points colored by feature value</div>
        <div style="overflow-x:auto;padding-top:12px;">
          <canvas id="shapBeeswarmCanvas" height="300" style="display:block;width:100%;min-width:650px;"></canvas>
        </div>
        <div style="display:flex;justify-content:center;align-items:center;gap:12px;margin-top:12px;font-size:0.75rem;color:var(--text-muted);">
          <span>Low Feature Value</span>
          <div style="width:140px;height:8px;border-radius:4px;background:linear-gradient(90deg, #3B82F6, #EC4899);"></div>
          <span>High Feature Value</span>
        </div>
      </div>

      <div class="grid-2">
        <div class="card">
          <div class="card-title">Mean |SHAP| Ranking</div>
          <div class="card-subtitle">Average absolute impact on individual predictions</div>
          ${sorted.map(([k, v], i) => {
            const max = sorted[0][1];
            const label = FEATURES.find(f=>f.key===k)?.label || k;
            return `<div style="margin-bottom:12px;">
              <div style="display:flex;justify-content:space-between;font-size:0.82rem;margin-bottom:4px;">
                <span style="font-weight:500">${i+1}. ${label}</span>
                <span style="color:var(--accent-1);font-weight:600">${v.toFixed(4)}</span>
              </div>
              <div class="progress-bar-wrapper">
                <div class="progress-bar" style="width:${(v/max*100).toFixed(1)}%;background:var(--accent-grad)"></div>
              </div>
            </div>`;
          }).join('')}
        </div>
        <div class="card">
          <div class="card-title">Gain Importance Ranking</div>
          <div class="card-subtitle">Avg accuracy improvement per split (may differ from SHAP)</div>
          ${Object.entries(g.gain).sort((a,b)=>b[1]-a[1]).map(([k, v], i) => {
            const max = Math.max(...Object.values(g.gain));
            const label = FEATURES.find(f=>f.key===k)?.label || k;
            return `<div style="margin-bottom:12px;">
              <div style="display:flex;justify-content:space-between;font-size:0.82rem;margin-bottom:4px;">
                <span style="font-weight:500">${i+1}. ${label}</span>
                <span style="color:var(--accent-2);font-weight:600">${(v*100).toFixed(1)}%</span>
              </div>
              <div class="progress-bar-wrapper">
                <div class="progress-bar" style="width:${(v/max*100).toFixed(1)}%;background:linear-gradient(90deg,#7C3AED,#A855F7)"></div>
              </div>
            </div>`;
          }).join('')}
        </div>
      </div>
    `;

    destroyChart('globalImportance');
    const ctx = document.getElementById('globalImportanceChart');
    if (ctx) {
      state.charts.globalImportance = new Chart(ctx, {
        type: 'bar',
        data: {
          labels,
          datasets: [
            { label: 'Mean |SHAP|', data: shapVals, backgroundColor: 'rgba(79,70,229,0.75)', borderRadius: 4 },
            { label: 'Gain (norm)', data: gainVals, backgroundColor: 'rgba(124,58,237,0.65)', borderRadius: 4 },
            { label: 'Weight (norm)', data: weightVals, backgroundColor: 'rgba(16,185,129,0.55)', borderRadius: 4 },
          ],
        },
        options: {
          responsive: true,
          plugins: { legend: { position: 'top' } },
          scales: { y: { beginAtZero: true, title: { display: true, text: 'Importance Score' } } },
          animation: { duration: 700 },
        },
      });
    }

    // Render Beeswarm summary plot
    renderBeeswarmPlot('shapBeeswarmCanvas', g);
  } catch (err) {
    el.innerHTML = `<div class="alert alert-error">${icon('alertTriangle')} ${err.message}</div>`;
  }
}

function renderWhatIfTab(el) {
  // Default values matching the predict form
  const defaults = {
    age: 28, session_frequency: 7, avg_session_minutes: 22.5,
    days_since_install: 30, notifications_clicked: 8, crashes: 0, purchases: 1,
  };

  // If there's a last prediction, pre-populate with those values
  const initVals = state.lastPrediction?.body || defaults;

  el.innerHTML = `
    <div class="grid-2" style="align-items:start;">
      <div class="card">
        <div class="card-title">Feature Sliders</div>
        <div class="card-subtitle">Adjust sliders — probability updates live (debounced)</div>
        ${FEATURES.map(f => {
          const val = initVals[f.key] ?? f.min;
          const fillPct = ((val - f.min) / (f.max - f.min) * 100).toFixed(1);
          return `<div class="slider-group">
            <div class="slider-header">
              <span class="slider-label">${f.label}</span>
              <span class="slider-value" id="sv_${f.key}">${val}${f.unit ? ' ' + f.unit : ''}</span>
            </div>
            <input type="range" id="sl_${f.key}" min="${f.min}" max="${f.max}" step="${f.step}"
                   value="${val}" style="--fill:${fillPct}%"
                   aria-label="${f.label}" aria-valuemin="${f.min}" aria-valuemax="${f.max}" aria-valuenow="${val}"/>
          </div>`;
        }).join('')}
        <button class="btn btn-ghost btn-sm" id="whatIfResetBtn" style="margin-top:8px;">Reset to defaults</button>
      </div>
      <div>
        <div class="card" style="margin-bottom:16px;">
          <div class="card-title">Live Prediction</div>
          <div class="gauge-wrapper" id="whatIfGauge">
            <div class="skeleton" style="width:200px;height:120px;border-radius:12px;"></div>
          </div>
          <div id="whatIfRisk" style="text-align:center;margin-top:8px;"></div>
          <div id="whatIfProb" style="text-align:center;font-family:var(--font-heading);font-size:2.2rem;font-weight:700;color:var(--text-primary);"></div>
        </div>
        <div class="card" style="margin-bottom:16px;">
          <div class="card-title">SHAP Waterfall</div>
          <div id="whatIfSHAP"><div class="skeleton skeleton-chart"></div></div>
        </div>
        <div class="card">
          <div class="card-title">What Would It Take to Reach Low Risk?</div>
          <div id="whatIfSuggestion"><div class="skeleton" style="height:60px;border-radius:8px;"></div></div>
        </div>
      </div>
    </div>
  `;

  // Wire slider events
  FEATURES.forEach(f => {
    const slider = document.getElementById(`sl_${f.key}`);
    const valueEl = document.getElementById(`sv_${f.key}`);
    slider.addEventListener('input', () => {
      const v = parseFloat(slider.value);
      const fillPct = ((v - f.min) / (f.max - f.min) * 100).toFixed(1);
      slider.style.setProperty('--fill', `${fillPct}%`);
      valueEl.textContent = `${f.integer ? Math.round(v) : v}${f.unit ? ' ' + f.unit : ''}`;
      debouncedWhatIf();
    });
  });

  document.getElementById('whatIfResetBtn').addEventListener('click', () => {
    FEATURES.forEach(f => {
      const slider = document.getElementById(`sl_${f.key}`);
      const valueEl = document.getElementById(`sv_${f.key}`);
      const val = defaults[f.key] ?? f.min;
      slider.value = val;
      valueEl.textContent = `${val}${f.unit ? ' ' + f.unit : ''}`;
      const fillPct = ((val - f.min) / (f.max - f.min) * 100).toFixed(1);
      slider.style.setProperty('--fill', `${fillPct}%`);
    });
    debouncedWhatIf();
  });

  // Initial load
  runWhatIf();
}

function getSliderValues() {
  const vals = {};
  FEATURES.forEach(f => {
    const el = document.getElementById(`sl_${f.key}`);
    if (el) vals[f.key] = f.integer ? parseInt(el.value) : parseFloat(el.value);
  });
  return vals;
}

function debouncedWhatIf() {
  clearTimeout(state.whatIfDebounceTimer);
  state.whatIfDebounceTimer = setTimeout(runWhatIf, 350);
}

async function runWhatIf() {
  const body = getSliderValues();
  if (!body.age) return;

  try {
    const [pred, exp, sugg] = await Promise.all([
      apiPost(API.predict + '?save=false', body),
      apiPost(API.explain.local, body),
      apiPost(API.explain.whatif, body),
    ]);

    // Update gauge
    const gaugeEl = document.getElementById('whatIfGauge');
    if (gaugeEl) gaugeEl.innerHTML = buildGauge(pred.probability, pred.risk_level);
    const probEl = document.getElementById('whatIfProb');
    if (probEl) probEl.textContent = fmtPct(pred.probability);
    const riskEl = document.getElementById('whatIfRisk');
    if (riskEl) riskEl.innerHTML = riskBadge(pred.risk_level);

    // Update SHAP
    const shapEl = document.getElementById('whatIfSHAP');
    if (shapEl) shapEl.innerHTML = buildSHAPWaterfall(exp.contribs, exp.bias);

    // Update suggestion
    const suggEl = document.getElementById('whatIfSuggestion');
    if (suggEl) {
      if (sugg.already_low_risk) {
        suggEl.innerHTML = `<div class="alert alert-success">${icon('checkCircle')} This user is already at Low Risk! Current probability: ${fmtPct(sugg.current_probability)}.</div>`;
      } else if (sugg.best) {
        const b = sugg.best;
        const featLabel = FEATURES.find(f=>f.key===b.feature)?.label || b.feature;
        suggEl.innerHTML = `<div class="alert alert-info">${icon('cpu')} Smallest change: <strong>${featLabel}</strong> from <strong>${b.original}</strong> → <strong>${b.proposed}</strong> (delta: ${b.delta > 0 ? '+' : ''}${b.delta}) would bring probability to <strong>${fmtPct(b.new_prob)}</strong> (Low Risk).</div>
          ${sugg.suggestions.length > 1 ? `<div style="font-size:0.78rem;color:var(--text-muted);margin-top:6px;">Other options: ${sugg.suggestions.slice(1).map(s => `<strong>${FEATURES.find(f=>f.key===s.feature)?.label || s.feature}</strong> → ${s.proposed}`).join(', ')}</div>` : ''}`;
      } else {
        suggEl.innerHTML = `<div class="alert alert-error">${icon('alertTriangle')} ${sugg.message || 'No single feature change is sufficient to reach Low Risk.'}</div>`;
      }
    }
  } catch(err) {
    const shapEl = document.getElementById('whatIfSHAP');
    if (shapEl) shapEl.innerHTML = `<div class="text-muted text-sm">${err.message}</div>`;
  }
}

async function renderPDPTab(el) {
  el.innerHTML = `
    <div class="card">
      <div class="card-title">Partial Dependence Plots</div>
      <div class="card-subtitle">Effect of varying a single feature on retention probability (all others at median)</div>
      <div style="margin-bottom:16px;">
        <label class="form-label">Select Feature</label>
        <select class="filter-select" id="pdpFeatureSelect">
          ${FEATURES.map(f => `<option value="${f.key}">${f.label}</option>`).join('')}
        </select>
      </div>
      <canvas id="pdpChart" height="250"></canvas>
      <p class="text-muted text-sm mt-2">Note: Each point shows predicted retention probability when this feature takes that value, with all other features held at their median. Does not show interactions.</p>
    </div>
  `;

  async function loadPDP(feature) {
    try {
      const data = await apiFetch(API.explain.pdp(feature));
      destroyChart('pdp');
      const ctx = document.getElementById('pdpChart');
      if (!ctx) return;
      state.charts.pdp = new Chart(ctx, {
        type: 'line',
        data: {
          labels: data.x.map(v => v.toFixed(1)),
          datasets: [{
            label: `Retention Probability vs ${FEATURES.find(f=>f.key===feature)?.label || feature}`,
            data: data.y.map(v => (v * 100).toFixed(1)),
            borderColor: '#4F46E5',
            backgroundColor: 'rgba(79,70,229,0.08)',
            fill: true,
            tension: 0.4,
            pointRadius: 3,
            pointHoverRadius: 6,
          }],
        },
        options: {
          responsive: true,
          plugins: { tooltip: { callbacks: { label: c => `${c.raw}%` } } },
          scales: {
            y: { min: 0, max: 100, title: { display: true, text: 'Retention Probability (%)' } },
            x: { title: { display: true, text: FEATURES.find(f=>f.key===feature)?.label || feature } },
          },
          animation: { duration: 500 },
        },
      });
    } catch (err) {
      const ctx = document.getElementById('pdpChart');
      if (ctx) ctx.parentElement.innerHTML += `<div class="alert alert-error">${err.message}</div>`;
    }
  }

  document.getElementById('pdpFeatureSelect').addEventListener('change', (e) => loadPDP(e.target.value));
  await loadPDP('crashes');
}

async function renderModelCard(el) {
  let meta = {}, metrics = {};
  try {
    const data = await apiFetch(API.meta);
    meta = data.model_info;
    metrics = data.metrics;
  } catch(e) {}

  const cm = metrics.confusion_matrix;
  const clsReport = metrics.classification_report || {};

  el.innerHTML = `
    <div class="card" style="margin-bottom:20px;">
      <div class="card-title">Model Card</div>
      <div class="card-subtitle">Transparent documentation of the RetentionIQ model</div>
      ${synthAlert()}
    </div>

    <div class="grid-2" style="margin-bottom:20px;">
      <div class="card">
        <div class="card-title">Algorithm</div>
        <table style="width:100%;font-size:0.85rem;">
          <tr><td style="color:var(--text-muted);padding:6px 0;">Model Type</td><td style="font-weight:600">XGBClassifier (sklearn API)</td></tr>
          <tr><td style="color:var(--text-muted);padding:6px 0;">Library</td><td>XGBoost ${meta.library_version || '3.4.1'}</td></tr>
          <tr><td style="color:var(--text-muted);padding:6px 0;">Objective</td><td>${meta.objective || 'binary:logistic'}</td></tr>
          <tr><td style="color:var(--text-muted);padding:6px 0;">n_estimators</td><td>${meta.n_estimators || 50}</td></tr>
          <tr><td style="color:var(--text-muted);padding:6px 0;">max_depth</td><td>${meta.max_depth || 3}</td></tr>
          <tr><td style="color:var(--text-muted);padding:6px 0;">learning_rate</td><td>${meta.learning_rate || 0.1}</td></tr>
          <tr><td style="color:var(--text-muted);padding:6px 0;">SHAP Method</td><td>Native pred_contribs=True</td></tr>
          <tr><td style="color:var(--text-muted);padding:6px 0;">Features</td><td>${(meta.features || []).join(', ')}</td></tr>
        </table>
      </div>
      <div class="card">
        <div class="card-title">Dataset</div>
        <table style="width:100%;font-size:0.85rem;">
          <tr><td style="color:var(--text-muted);padding:6px 0;">Type</td><td style="font-weight:600;color:var(--risk-medium)">Synthetic (not real data)</td></tr>
          <tr><td style="color:var(--text-muted);padding:6px 0;">Total Rows</td><td>${metrics.dataset_rows || 3000}</td></tr>
          <tr><td style="color:var(--text-muted);padding:6px 0;">Train / Test Split</td><td>80% / 20% (stratified)</td></tr>
          <tr><td style="color:var(--text-muted);padding:6px 0;">Test Set Size</td><td>600 rows</td></tr>
          <tr><td style="color:var(--text-muted);padding:6px 0;">Random Seed</td><td>42</td></tr>
          <tr><td style="color:var(--text-muted);padding:6px 0;">Target</td><td>retained (0/1)</td></tr>
          <tr><td style="color:var(--text-muted);padding:6px 0;">Class Balance</td><td>~45% not retained, ~55% retained</td></tr>
        </table>
      </div>
    </div>

    <div class="grid-2" style="margin-bottom:20px;">
      <div class="card">
        <div class="card-title">Test-Set Metrics</div>
        ${metrics.xgboost_accuracy != null ? `
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:8px;">
          ${[
            ['Accuracy', metrics.xgboost_accuracy],
            ['Precision', metrics.xgboost_precision],
            ['Recall', metrics.xgboost_recall],
            ['F1 Score', metrics.xgboost_f1_score],
          ].map(([label, val]) => `<div style="background:var(--surface-bg);border-radius:10px;padding:14px;text-align:center;">
            <div style="font-family:var(--font-heading);font-size:1.6rem;font-weight:700;color:var(--accent-1)">${(val*100).toFixed(1)}%</div>
            <div style="font-size:0.75rem;color:var(--text-muted);margin-top:2px">${label}</div>
          </div>`).join('')}
        </div>` : '<p class="text-muted text-sm">Metrics not available.</p>'}
      </div>
      <div class="card">
        <div class="card-title">Confusion Matrix (test set, n=600)</div>
        ${cm ? `
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:12px;text-align:center;">
          <div style="background:var(--risk-low-bg);border-radius:10px;padding:16px;border:1px solid var(--risk-low-border)">
            <div style="font-size:1.6rem;font-weight:700;color:var(--risk-low)">${cm[0][0]}</div>
            <div style="font-size:0.72rem;color:var(--text-muted)">True Negative</div>
          </div>
          <div style="background:var(--risk-high-bg);border-radius:10px;padding:16px;border:1px solid var(--risk-high-border)">
            <div style="font-size:1.6rem;font-weight:700;color:var(--risk-high)">${cm[0][1]}</div>
            <div style="font-size:0.72rem;color:var(--text-muted)">False Positive</div>
          </div>
          <div style="background:var(--risk-high-bg);border-radius:10px;padding:16px;border:1px solid var(--risk-high-border)">
            <div style="font-size:1.6rem;font-weight:700;color:var(--risk-high)">${cm[1][0]}</div>
            <div style="font-size:0.72rem;color:var(--text-muted)">False Negative</div>
          </div>
          <div style="background:var(--risk-low-bg);border-radius:10px;padding:16px;border:1px solid var(--risk-low-border)">
            <div style="font-size:1.6rem;font-weight:700;color:var(--risk-low)">${cm[1][1]}</div>
            <div style="font-size:0.72rem;color:var(--text-muted)">True Positive</div>
          </div>
        </div>` : '<p class="text-muted text-sm">Confusion matrix not available.</p>'}
      </div>
    </div>

    <div class="card" style="margin-bottom:20px;">
      <div class="card-title">Performance & Calibration Curves</div>
      <div class="card-subtitle">Evaluated on stratified hold-out test set (n=600, random seed 42)</div>
      <div class="grid-3" style="margin-top:16px;">
        <div style="background:var(--surface-bg);border-radius:10px;padding:14px;">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
            <span style="font-weight:600;font-size:0.85rem;">ROC Curve</span>
            <span class="badge" id="rocBadge" style="background:var(--accent-1);color:white;font-size:0.75rem;padding:2px 8px;border-radius:10px;">AUC: --</span>
          </div>
          <canvas id="rocCurveChart" height="180"></canvas>
        </div>
        <div style="background:var(--surface-bg);border-radius:10px;padding:14px;">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
            <span style="font-weight:600;font-size:0.85rem;">Precision-Recall</span>
            <span class="badge" id="prBadge" style="background:var(--accent-2);color:white;font-size:0.75rem;padding:2px 8px;border-radius:10px;">PR-AUC: --</span>
          </div>
          <canvas id="prCurveChart" height="180"></canvas>
        </div>
        <div style="background:var(--surface-bg);border-radius:10px;padding:14px;">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
            <span style="font-weight:600;font-size:0.85rem;">Calibration Curve</span>
            <span class="badge" style="background:var(--risk-low);color:white;font-size:0.75rem;padding:2px 8px;border-radius:10px;">10 Bins</span>
          </div>
          <canvas id="calCurveChart" height="180"></canvas>
        </div>
      </div>
    </div>

    <div class="card">
      <div class="card-title">Limitations & Fairness Notes</div>
      <div class="alert alert-synthetic" style="margin-top:8px;">
        ${icon('alertTriangle')} <strong>Synthetic data caveat:</strong> This model was trained on randomly generated data with no connection to real mobile app behaviour.
      </div>
      <ul style="margin-top:12px;list-style:disc;margin-left:20px;font-size:0.875rem;color:var(--text-secondary);line-height:1.8;">
        <li>Accuracy of ~70% means approximately 1 in 3 predictions is wrong.</li>
        <li>The <strong>age</strong> feature is included in the model. In real applications, using age for churn decisions raises ethical and legal fairness concerns. This model has not been audited for demographic bias.</li>
        <li>The model was not evaluated on different demographic subgroups. Subgroup performance may differ substantially.</li>
        <li>This model predicts on a single snapshot of user data; it does not capture temporal trends or engagement trajectories.</li>
        <li>Do not use this model for real business decisions without independent validation on your actual customer data.</li>
        <li>The local SQLite database is not suitable for multi-user or production deployments.</li>
      </ul>
    </div>
  `;

  // Asynchronously load and render ROC, PR, and Calibration curves
  try {
    const curves = await apiFetch(API.curves);
    if (curves) {
      // 1. ROC
      destroyChart('roc');
      const rocCtx = document.getElementById('rocCurveChart');
      if (rocCtx) {
        document.getElementById('rocBadge').textContent = `AUC: ${curves.roc.auc}`;
        state.charts.roc = new Chart(rocCtx, {
          type: 'line',
          data: {
            labels: curves.roc.fpr.map(v => v.toFixed(2)),
            datasets: [
              {
                label: 'ROC',
                data: curves.roc.tpr,
                borderColor: '#4F46E5',
                backgroundColor: 'rgba(79,70,229,0.1)',
                fill: true,
                tension: 0.2,
                pointRadius: 0,
                borderWidth: 2,
              },
              {
                label: 'Chance',
                data: curves.roc.fpr,
                borderColor: '#94A3B8',
                borderDash: [4, 4],
                pointRadius: 0,
                fill: false,
                borderWidth: 1.5,
              },
            ],
          },
          options: {
            responsive: true,
            plugins: { legend: { display: false } },
            scales: {
              x: { min: 0, max: 1, title: { display: true, text: 'FPR' } },
              y: { min: 0, max: 1, title: { display: true, text: 'TPR' } },
            },
            animation: { duration: 600 },
          },
        });
      }

      // 2. PR
      destroyChart('pr');
      const prCtx = document.getElementById('prCurveChart');
      if (prCtx) {
        document.getElementById('prBadge').textContent = `PR-AUC: ${curves.pr.auc}`;
        state.charts.pr = new Chart(prCtx, {
          type: 'line',
          data: {
            labels: curves.pr.recall.map(v => v.toFixed(2)),
            datasets: [
              {
                label: 'Precision',
                data: curves.pr.precision,
                borderColor: '#7C3AED',
                backgroundColor: 'rgba(124,58,237,0.1)',
                fill: true,
                tension: 0.2,
                pointRadius: 0,
                borderWidth: 2,
              },
              {
                label: 'Prevalence',
                data: curves.pr.recall.map(() => curves.pr.baseline),
                borderColor: '#94A3B8',
                borderDash: [4, 4],
                pointRadius: 0,
                fill: false,
                borderWidth: 1.5,
              },
            ],
          },
          options: {
            responsive: true,
            plugins: { legend: { display: false } },
            scales: {
              x: { min: 0, max: 1, title: { display: true, text: 'Recall' } },
              y: { min: 0, max: 1, title: { display: true, text: 'Precision' } },
            },
            animation: { duration: 600 },
          },
        });
      }

      // 3. Calibration
      destroyChart('cal');
      const calCtx = document.getElementById('calCurveChart');
      if (calCtx) {
        state.charts.cal = new Chart(calCtx, {
          type: 'line',
          data: {
            labels: curves.calibration.prob_pred.map(v => v.toFixed(2)),
            datasets: [
              {
                label: 'Model Calibration',
                data: curves.calibration.prob_true,
                borderColor: '#059669',
                backgroundColor: '#059669',
                pointRadius: 4,
                pointHoverRadius: 6,
                fill: false,
                borderWidth: 2,
              },
              {
                label: 'Perfect',
                data: curves.calibration.prob_pred,
                borderColor: '#94A3B8',
                borderDash: [4, 4],
                pointRadius: 0,
                fill: false,
                borderWidth: 1.5,
              },
            ],
          },
          options: {
            responsive: true,
            plugins: { legend: { display: false } },
            scales: {
              x: { min: 0, max: 1, title: { display: true, text: 'Predicted Probability' } },
              y: { min: 0, max: 1, title: { display: true, text: 'Observed Fraction' } },
            },
            animation: { duration: 600 },
          },
        });
      }
    }
  } catch(e) { /* ignore */ }
}

// ============================================================
// PAGE: History & Compare
// ============================================================

async function renderHistory(container) {
  container.innerHTML = `
    <div class="page-header">
      <div class="breadcrumbs"><span class="crumb">RetentionIQ</span><span>›</span><span class="crumb">History</span></div>
      <h1 class="page-title">History & Compare</h1>
      <p class="page-subtitle">Save and compare analysis snapshots over time</p>
    </div>
    ${synthAlert()}
    <div class="flex gap-3 mb-4" style="flex-wrap:wrap;">
      <input type="text" class="form-input" id="analysisName" placeholder="Name this snapshot (e.g. Week 3 cohort)" style="max-width:300px;"/>
      <button class="btn btn-primary" id="saveAnalysisBtn">${icon('save')} Save Current Snapshot</button>
    </div>
    <div id="historyList"><div class="skeleton skeleton-chart"></div></div>
    <div id="compareSection" style="margin-top:24px;"></div>
  `;

  document.getElementById('saveAnalysisBtn').addEventListener('click', async () => {
    const name = document.getElementById('analysisName').value.trim() || `Snapshot ${new Date().toLocaleString()}`;
    try {
      await apiPost(API.history.save, { name });
      await loadHistoryList();
    } catch(err) {
      alert(`Failed to save: ${err.message}`);
    }
  });

  await loadHistoryList();
}

async function loadHistoryList() {
  const el = document.getElementById('historyList');
  try {
    const items = await apiFetch(API.history.list);
    state.historyList = items;

    if (items.length === 0) {
      el.innerHTML = `<div class="empty-state">
        <div class="empty-icon">${icon('clock')}</div>
        <div class="empty-title">No Analysis History Yet</div>
        <div class="empty-desc">Click "Save Current Snapshot" to record the current state for future comparison.</div>
      </div>`;
      return;
    }

    el.innerHTML = `
      <div class="card">
        <div class="card-title">Saved Analyses (${items.length})</div>
        <div class="card-subtitle">Select two to compare side-by-side</div>
        <div class="table-wrapper">
          <table>
            <thead><tr><th>ID</th><th>Name</th><th>Date</th><th>Total</th><th>High Risk</th><th>Avg Prob</th><th>Compare</th></tr></thead>
            <tbody>${items.map(a => `
              <tr>
                <td>${a.id}</td>
                <td style="font-weight:500">${a.name}</td>
                <td style="font-size:0.78rem;color:var(--text-muted)">${a.created_at?.substring(0,16).replace('T',' ') || '—'}</td>
                <td>${a.summary.total_customers ?? '—'}</td>
                <td>${a.summary.high_risk ?? '—'}</td>
                <td>${a.summary.avg_retention_probability != null ? fmtPct(a.summary.avg_retention_probability) : '—'}</td>
                <td>
                  <button class="btn btn-ghost btn-sm" onclick="selectForCompare('A', ${a.id})">A</button>
                  <button class="btn btn-ghost btn-sm" onclick="selectForCompare('B', ${a.id})">B</button>
                </td>
              </tr>`).join('')}
            </tbody>
          </table>
        </div>
      </div>
    `;
  } catch(err) {
    el.innerHTML = `<div class="alert alert-error">${icon('alertTriangle')} ${err.message}</div>`;
  }
}

window.selectForCompare = async (slot, id) => {
  if (slot === 'A') state.compareA = id;
  else state.compareB = id;

  if (state.compareA && state.compareB) {
    try {
      const data = await apiFetch(API.history.compare(state.compareA, state.compareB));
      renderCompare(data);
    } catch(err) {
      document.getElementById('compareSection').innerHTML =
        `<div class="alert alert-error">${icon('alertTriangle')} ${err.message}</div>`;
    }
  }
};

function renderCompare(data) {
  const c = data.comparison;
  const a = data.analysis_a;
  const b = data.analysis_b;

  function delta(val, invert = false) {
    if (val == null) return '—';
    const isPositive = invert ? val < 0 : val > 0;
    const cls = isPositive ? 'positive' : 'negative';
    return `<span class="kpi-delta ${cls}">${val > 0 ? '+' : ''}${val}%</span>`;
  }

  document.getElementById('compareSection').innerHTML = `
    <div class="card">
      <div class="card-title">Side-by-Side Comparison</div>
      <div class="card-subtitle">Snapshot A: "${a.name}" vs Snapshot B: "${b.name}"</div>
      <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:16px;margin-top:16px;text-align:center;">
        <div></div>
        <div style="font-family:var(--font-heading);font-weight:700;color:var(--accent-1)">A — ${a.name}</div>
        <div style="font-family:var(--font-heading);font-weight:700;color:var(--accent-2)">B — ${b.name}</div>
        ${[
          ['Total Customers', c.total_customers_a, c.total_customers_b, null],
          ['High Risk %', c.high_risk_pct_a != null ? c.high_risk_pct_a + '%' : '—',
                          c.high_risk_pct_b != null ? c.high_risk_pct_b + '%' : '—',
                          c.high_risk_pct_delta],
          ['Avg Retention Prob', c.avg_prob_a != null ? fmtPct(c.avg_prob_a) : '—',
                                  c.avg_prob_b != null ? fmtPct(c.avg_prob_b) : '—',
                                  c.avg_prob_delta != null ? (c.avg_prob_delta * 100).toFixed(1) + '%' : null],
        ].map(([label, va, vb, d]) => `
          <div style="color:var(--text-muted);text-align:left;font-size:0.85rem;padding:12px 0;border-bottom:1px solid var(--surface-border)">${label}</div>
          <div style="font-weight:600;padding:12px 0;border-bottom:1px solid var(--surface-border)">${va}</div>
          <div style="font-weight:600;padding:12px 0;border-bottom:1px solid var(--surface-border)">${vb}${d != null ? ` ${delta(parseFloat(d))}` : ''}</div>
        `).join('')}
      </div>
    </div>
  `;
}

// ============================================================
// PAGE: Reports
// ============================================================

function renderReports(container) {
  container.innerHTML = `
    <div class="page-header">
      <div class="breadcrumbs"><span class="crumb">RetentionIQ</span><span>›</span><span class="crumb">Reports</span></div>
      <h1 class="page-title">Reports</h1>
      <p class="page-subtitle">Download PDF and CSV exports of your retention analysis</p>
    </div>
    ${synthAlert()}
    <div class="grid-auto">
      <div class="card" style="text-align:center;">
        <div class="empty-icon" style="margin:0 auto 16px;">${icon('file-text')}</div>
        <div class="card-title">PDF Business Report</div>
        <div class="card-subtitle">KPIs, model metrics, top at-risk customers, limitations disclaimer</div>
        <div style="margin-top:20px;">
          <a href="${API.reports.pdf}" target="_blank" class="btn btn-primary">${icon('download')} Download PDF Report</a>
        </div>
      </div>
      <div class="card" style="text-align:center;">
        <div class="empty-icon" style="margin:0 auto 16px;">${icon('layers')}</div>
        <div class="card-title">Customer CSV Export</div>
        <div class="card-subtitle">All scored customers with risk levels and feature values</div>
        <div style="margin-top:20px;">
          <a href="${API.customers.export}" class="btn btn-primary">${icon('download')} Export Customers CSV</a>
        </div>
      </div>
      <div class="card" style="text-align:center;">
        <div class="empty-icon" style="margin:0 auto 16px;">${icon('cpu')}</div>
        <div class="card-title">Model Metrics JSON</div>
        <div class="card-subtitle">Raw metrics from reports/metrics.json</div>
        <div style="margin-top:20px;">
          <a href="${API.reports.metrics}" target="_blank" class="btn btn-secondary">${icon('externalLink')} View Metrics JSON</a>
        </div>
      </div>
    </div>
  `;
}

// ============================================================
// PAGE: About & Limitations
// ============================================================

function renderAbout(container) {
  container.innerHTML = `
    <div class="page-header">
      <div class="breadcrumbs"><span class="crumb">RetentionIQ</span><span>›</span><span class="crumb">About</span></div>
      <h1 class="page-title">About & Limitations</h1>
      <p class="page-subtitle">What this system is, how it works, and what it cannot do</p>
    </div>
    <div class="grid-2">
      <div class="card">
        <div class="card-title">What RetentionIQ Is</div>
        <p style="font-size:0.875rem;color:var(--text-secondary);line-height:1.8;margin-top:8px;">
          RetentionIQ is an academic machine learning demonstration project. It uses an 
          <strong>XGBoost binary classifier</strong> to predict whether a mobile app user is 
          likely to be retained (continue using the app) based on seven behavioural features.
          The system includes XGBoost native SHAP explanations, a what-if simulator, 
          batch scoring, and a PDF report generator.
        </p>
        <div style="margin-top:16px;">
          <strong style="font-size:0.85rem;">Features used:</strong>
          <ul style="margin-top:6px;list-style:disc;margin-left:18px;font-size:0.84rem;color:var(--text-secondary);line-height:1.8;">
            <li>Age (years)</li>
            <li>Session frequency (per week)</li>
            <li>Average session duration (minutes)</li>
            <li>Days since installation</li>
            <li>Notifications clicked</li>
            <li>App crashes experienced</li>
            <li>In-app purchases made</li>
          </ul>
        </div>
      </div>
      <div class="card">
        <div class="card-title">What Is Real vs. Synthetic</div>
        <div class="alert alert-synthetic" style="margin-bottom:16px;">${icon('alertTriangle')} <strong>The data is entirely synthetic.</strong></div>
        <table style="width:100%;font-size:0.83rem;">
          <tr style="border-bottom:1px solid var(--surface-border)">
            <th style="text-align:left;padding:8px 0;color:var(--text-muted)">Component</th>
            <th style="text-align:left;padding:8px 0;color:var(--text-muted)">Status</th>
          </tr>
          ${[
            ['Training data (3,000 rows)', 'SYNTHETIC — randomly generated'],
            ['Model (XGBoost)', 'REAL — trained on that synthetic data'],
            ['Model metrics (70% accuracy)', 'REAL — computed on synthetic test set'],
            ['SHAP explanations', 'REAL — mathematically exact for this model'],
            ['Predicted probabilities', 'REAL — from the trained model weights'],
            ['Business recommendations', 'ILLUSTRATIVE — based on synthetic patterns'],
          ].map(([c, s]) => `
            <tr style="border-bottom:1px solid var(--surface-border)">
              <td style="padding:8px 0;color:var(--text-secondary)">${c}</td>
              <td style="padding:8px 0;font-weight:600;color:${s.startsWith('REAL') ? 'var(--risk-low)' : s.startsWith('SYNTHETIC') ? 'var(--risk-high)' : 'var(--risk-medium)'}">${s}</td>
            </tr>`).join('')}
        </table>
      </div>
    </div>
    <div class="card" style="margin-top:20px;">
      <div class="card-title">Key Limitations</div>
      <ul style="margin-top:8px;list-style:disc;margin-left:20px;font-size:0.875rem;color:var(--text-secondary);line-height:2;">
        <li>This model is not validated on real customer data and <strong>must not be used for real business decisions</strong> without independent validation.</li>
        <li>The model does not generalise to your specific app, industry, or user demographics.</li>
        <li>Crash-heavy synthetic data may create spurious patterns that don't hold in real data.</li>
        <li>The age feature is included but using age for targeting decisions raises fairness and legal concerns.</li>
        <li>SQLite is used for local persistence only — not suitable for concurrent users or production.</li>
        <li>Uploaded CSV files are processed in-memory; sensitive real customer data should never be uploaded to an unaudited local tool.</li>
      </ul>
    </div>
    <div class="card" style="margin-top:20px;">
      <div class="card-title">Technical Architecture</div>
      <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px;margin-top:12px;">
        ${[
          ['Backend', 'FastAPI + Uvicorn (Python 3.14)'],
          ['ML Model', 'XGBoost 3.4.1 (XGBClassifier)'],
          ['SHAP', 'Native XGBoost pred_contribs=True'],
          ['Database', 'SQLite (stdlib sqlite3, WAL mode)'],
          ['Frontend', 'Vanilla HTML/CSS/JS + Chart.js 4'],
          ['PDF Reports', 'reportlab 5.0.1'],
          ['API Docs', '/docs (Swagger UI)'],
        ].map(([title, val]) => `
          <div style="background:var(--surface-bg);border-radius:10px;padding:14px;">
            <div style="font-size:0.72rem;color:var(--text-muted);text-transform:uppercase;letter-spacing:.05em">${title}</div>
            <div style="font-weight:600;font-size:0.85rem;margin-top:4px">${val}</div>
          </div>`).join('')}
      </div>
    </div>
  `;
}

// ============================================================
// Utilities
// ============================================================

function debounce(fn, delay) {
  let t;
  return function(...args) {
    clearTimeout(t);
    t = setTimeout(() => fn.apply(this, args), delay);
  };
}

// ============================================================
// Init
// ============================================================

document.addEventListener('DOMContentLoaded', () => {
  buildShell();
  
  // Handle deep links from URL hash
  const hash = window.location.hash.slice(1);
  const initialPage = PAGES.find(p => p.id === hash)?.id || 'overview';
  state.currentPage = initialPage;
  updateNavActive();
  renderPage(initialPage);
  
  // Handle browser back/forward
  window.addEventListener('popstate', () => {
    const hash = window.location.hash.slice(1);
    const page = PAGES.find(p => p.id === hash)?.id || 'overview';
    state.currentPage = page;
    updateNavActive();
    renderPage(page);
  });
});
