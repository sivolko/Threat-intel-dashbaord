// ═══════════════════ STATE ═══════════════════
let allArticles      = [];
let filteredArticles = [];
let currentPage      = 1;
const PAGE_SIZE      = 50;
let sortKey          = 'pubDate';
let sortDir          = -1;          // -1 = descending
let refreshTimer     = null;
let refreshCountdown = 900;
const REFRESH_INTERVAL = 900;       // seconds
const API_BASE         = 'http://localhost:5100';

// ═══════════════════ SECTOR / SOURCE COLOUR MAPS ═══════════════════
const SECTOR_COLORS = {
  'Ransomware':          { bg: '#fef2f2', text: '#dc2626', border: '#fecaca' },
  'Phishing':            { bg: '#fff7ed', text: '#ea580c', border: '#fed7aa' },
  'Vulnerability':       { bg: '#fefce8', text: '#ca8a04', border: '#fef08a' },
  'Malware':             { bg: '#fdf4ff', text: '#a21caf', border: '#f0abfc' },
  'APT / Nation-State':  { bg: '#f5f3ff', text: '#7c3aed', border: '#ddd6fe' },
  'ICS / Advisory':      { bg: '#eff6ff', text: '#1d4ed8', border: '#bfdbfe' },
  'Supply Chain':        { bg: '#f0fdf4', text: '#15803d', border: '#bbf7d0' },
  'Cloud Security':      { bg: '#f0f9ff', text: '#0369a1', border: '#bae6fd' },
  'Data Breach':         { bg: '#fff1f2', text: '#be123c', border: '#fecdd3' },
  'DDoS':                { bg: '#f8fafc', text: '#475569', border: '#cbd5e1' },
  'AI / ML Threats':     { bg: '#faf5ff', text: '#6d28d9', border: '#ddd6fe' },
  'Identity & Access':   { bg: '#ecfdf5', text: '#065f46', border: '#a7f3d0' },
  'Mobile Security':     { bg: '#fffbeb', text: '#92400e', border: '#fde68a' },
  'Threat Research':     { bg: '#eff6ff', text: '#2563eb', border: '#bfdbfe' },
  'Threat Intelligence': { bg: '#eef2ff', text: '#4338ca', border: '#c7d2fe' },
  'General Security':    { bg: '#f8fafc', text: '#334155', border: '#e2e8f0' },
  'Incident Analysis':   { bg: '#fff7ed', text: '#c2410c', border: '#fed7aa' },
  'Government Advisory': { bg: '#eff6ff', text: '#1e40af', border: '#bfdbfe' },
  'Microsoft Security':  { bg: '#e8f4fd', text: '#0078d4', border: '#bfdbfe' },
  'Malware / Ransomware':{ bg: '#fef2f2', text: '#dc2626', border: '#fecaca' },
  'Malware / APT':       { bg: '#fdf4ff', text: '#a21caf', border: '#f0abfc' },
};

const SOURCE_COLORS = {
  'Bleeping Computer':  '#e53e3e',
  'SANS ISC':           '#dd6b20',
  'Unit 42':            '#2b6cb0',
  'Dark Reading':       '#2c7a7b',
  'CISA':               '#1a365d',
  'Check Point':        '#c05621',
  'CrowdStrike':        '#c53030',
  'Microsoft Security': '#0078d4',
  'WeLiveSecurity':     '#276749',
};

function getSectorBadge(sector) {
  const c = SECTOR_COLORS[sector] || { bg: '#f1f5f9', text: '#64748b', border: '#e2e8f0' };
  return `<span class="sector-badge" style="background:${c.bg};color:${c.text};border-color:${c.border}">${escHtml(sector)}</span>`;
}

function getSourceLabel(source) {
  const color = SOURCE_COLORS[source] || '#4a5568';
  return `<span class="text-xs font-bold whitespace-nowrap" style="color:${color}">${escHtml(source)}</span>`;
}

// ═══════════════════ FETCH & INIT ═══════════════════
async function loadFeeds() {
  show('loading-state');
  hide('dashboard');
  hide('error-state');

  try {
    const resp = await fetch(`${API_BASE}/api/feeds`);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const data = await resp.json();

    allArticles = (data.articles || []).map((a, i) => ({ ...a, _origIndex: i }));

    populateFilters(data.sources || [], data.sectors || []);
    renderSourcePills(data.sources_status || {});
    renderKPIs(data.sources_status || {});
    applyFilters();

    const badge = document.getElementById('last-updated-badge');
    document.getElementById('last-updated-text').textContent = formatTimeAgo(data.last_updated);
    badge.classList.remove('hidden');
    badge.classList.add('flex');

    hide('loading-state');
    show('dashboard');
    startRefreshTimer();
  } catch (e) {
    hide('loading-state');
    const err = document.getElementById('error-state');
    err.classList.remove('hidden');
    err.classList.add('flex');
  }
}

async function refreshFeeds() {
  const btn  = document.getElementById('btn-refresh');
  const icon = document.getElementById('refresh-icon');
  btn.disabled = true;
  icon.textContent = '⏳';

  try {
    const resp = await fetch(`${API_BASE}/api/refresh`);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await loadFeeds();
  } catch (e) {
    // Show error state if backend is down
    hide('loading-state');
    const err = document.getElementById('error-state');
    err.classList.remove('hidden');
    err.classList.add('flex');
  } finally {
    btn.disabled = false;
    icon.textContent = '🔄';
  }
}

// ═══════════════════ RENDER KPI & PILLS ═══════════════════
function renderKPIs(sourcesStatus) {
  setText('kpi-total', allArticles.length);

  const active = Object.values(sourcesStatus).filter(s => s.ok).length;
  setText('kpi-sources', `${active}/9`);

  const sectorSet = new Set(allArticles.map(a => a.sector));
  setText('kpi-sectors', sectorSet.size);

  const today = new Date().toISOString().slice(0, 10);
  const todayCount = allArticles.filter(a => (a.pubDate || '').startsWith(today)).length;
  setText('kpi-today', todayCount);
}

function renderSourcePills(sourcesStatus) {
  document.getElementById('source-pills').innerHTML =
    Object.entries(sourcesStatus).map(([name, info]) => {
      const ok  = info.ok;
      const cls = ok
        ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
        : 'bg-red-50 text-red-500 border-red-200';
      const dot = ok ? 'bg-emerald-400' : 'bg-red-400';
      return `<span class="inline-flex items-center gap-1.5 ${cls} border text-xs font-semibold px-2.5 py-1 rounded-full">
        <span class="w-1.5 h-1.5 rounded-full ${dot} inline-block"></span>
        ${escHtml(name)}${ok ? ` <span class="opacity-60">(${info.count})</span>` : ' <span class="opacity-60">offline</span>'}
      </span>`;
    }).join('');
}

function populateFilters(sources, sectors) {
  const srcSel = document.getElementById('filter-source');
  const secSel = document.getElementById('filter-sector');
  const curSrc = srcSel.value;
  const curSec = secSel.value;

  srcSel.innerHTML = '<option value="">All Sources</option>' +
    sources.map(s => `<option value="${escHtml(s)}">${escHtml(s)}</option>`).join('');
  secSel.innerHTML = '<option value="">All Sectors</option>' +
    sectors.map(s => `<option value="${escHtml(s)}">${escHtml(s)}</option>`).join('');

  srcSel.value = curSrc;
  secSel.value = curSec;
}

// ═══════════════════ FILTER & SORT ═══════════════════
function applyFilters() {
  const search = document.getElementById('search-input').value.trim().toLowerCase();
  const source = document.getElementById('filter-source').value;
  const sector = document.getElementById('filter-sector').value;
  const date   = document.getElementById('filter-date').value;

  const now     = new Date();
  const todayStr = now.toISOString().slice(0, 10);
  const d7       = new Date(now - 7  * 86400000).toISOString().slice(0, 10);
  const d30      = new Date(now - 30 * 86400000).toISOString().slice(0, 10);

  filteredArticles = allArticles.filter(a => {
    if (source && a.source !== source)                                                   return false;
    if (sector && a.sector !== sector)                                                   return false;
    if (date === 'today' && !(a.pubDate || '').startsWith(todayStr))                    return false;
    if (date === '7d'    && (a.pubDate || '') < d7)                                     return false;
    if (date === '30d'   && (a.pubDate || '') < d30)                                    return false;
    if (search && !a.title.toLowerCase().includes(search) &&
        !(a.description || '').toLowerCase().includes(search))                          return false;
    return true;
  });

  // Sort
  filteredArticles.sort((a, b) => {
    if (sortKey === 'index') {
      return ((a._origIndex ?? 0) - (b._origIndex ?? 0)) * sortDir;
    }
    if (sortKey === 'pubDate') {
      const ta = parseDateMs(a.pubDate);
      const tb = parseDateMs(b.pubDate);
      if (!ta && !tb) return 0;
      if (!ta) return 1;   // no date always goes to bottom
      if (!tb) return -1;
      return (ta - tb) * sortDir;
    }
    const va = String(a[sortKey] || '');
    const vb = String(b[sortKey] || '');
    return va.localeCompare(vb) * sortDir;
  });

  setText('result-count', filteredArticles.length);
  currentPage = 1;
  renderTable();
}

function sortBy(key) {
  sortDir = (sortKey === key) ? sortDir * -1 : (key === 'pubDate' ? -1 : 1);
  sortKey = key;
  document.querySelectorAll('.sort-icon').forEach(el => {
    if (el.dataset.col === key) {
      el.textContent = sortDir === 1 ? '↑' : '↓';
      el.classList.remove('opacity-40');
      el.classList.add('text-blue-500');
    } else {
      el.textContent = '↕';
      el.classList.add('opacity-40');
      el.classList.remove('text-blue-500');
    }
  });
  applyFilters();
}

function clearFilters() {
  document.getElementById('search-input').value   = '';
  document.getElementById('filter-source').value  = '';
  document.getElementById('filter-sector').value  = '';
  document.getElementById('filter-date').value    = 'all';
  applyFilters();
}

// ═══════════════════ TABLE RENDER ═══════════════════
function renderTable() {
  const tbody      = document.getElementById('table-body');
  const start      = (currentPage - 1) * PAGE_SIZE;
  const pageItems  = filteredArticles.slice(start, start + PAGE_SIZE);
  const totalPages = Math.max(1, Math.ceil(filteredArticles.length / PAGE_SIZE));

  if (pageItems.length === 0) {
    tbody.innerHTML = `<tr>
      <td colspan="7" class="text-center py-16 text-slate-400">
        <div class="text-3xl mb-3">🔍</div>
        <div class="font-semibold text-slate-500">No articles match the current filters</div>
        <div class="text-xs mt-1 text-slate-400">Try broadening your search or clearing filters</div>
      </td>
    </tr>`;
  } else {
    tbody.innerHTML = pageItems.map((a, i) => {
      const rowNum  = start + i + 1;
      const title   = escHtml(a.title   || '');
      const desc    = escHtml(a.description || '');
      const link    = escHtml(a.link    || '#');
      const dateStr = formatDisplayDate(a.pubDate);
      const rowBg   = rowNum % 2 === 0 ? 'bg-slate-50/40' : 'bg-white';
      return `<tr class="${rowBg} hover:bg-blue-50/30 transition-colors group">
        <td class="px-4 py-3.5 text-slate-400 text-xs tabular-nums w-10">${rowNum}</td>
        <td class="px-4 py-3.5 max-w-sm">
          <a href="${link}" target="_blank" rel="noopener noreferrer"
             class="font-semibold text-slate-800 hover:text-blue-600 transition-colors leading-snug block line-clamp-2"
             title="${title}">${title}</a>
        </td>
        <td class="px-4 py-3.5 max-w-xs">
          <span class="text-slate-500 text-xs leading-relaxed line-clamp-2">
            ${desc || '<span class="text-slate-300 italic">No description available</span>'}
          </span>
        </td>
        <td class="px-4 py-3.5">${getSectorBadge(a.sector)}</td>
        <td class="px-4 py-3.5">${getSourceLabel(a.source)}</td>
        <td class="px-4 py-3.5 whitespace-nowrap">
          <span class="text-xs text-slate-500">${dateStr}</span>
        </td>
        <td class="px-4 py-3.5 text-center">
          ${a.link
            ? `<a href="${link}" target="_blank" rel="noopener noreferrer"
                 class="inline-flex items-center gap-1 bg-blue-50 hover:bg-blue-100 active:bg-blue-200 text-blue-700 font-semibold text-xs px-3 py-1.5 rounded-lg transition-colors border border-blue-200 whitespace-nowrap">
                 Read ↗
               </a>`
            : '<span class="text-slate-300">—</span>'
          }
        </td>
      </tr>`;
    }).join('');
  }

  setText('page-info', `Page ${currentPage} of ${totalPages}`);
  document.getElementById('btn-prev').disabled = currentPage <= 1;
  document.getElementById('btn-next').disabled = currentPage >= totalPages;
}

function prevPage() {
  if (currentPage > 1) { currentPage--; renderTable(); scrollToTable(); }
}
function nextPage() {
  const total = Math.ceil(filteredArticles.length / PAGE_SIZE);
  if (currentPage < total) { currentPage++; renderTable(); scrollToTable(); }
}
function scrollToTable() {
  document.querySelector('.bg-white.rounded-2xl.shadow-sm')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

// ═══════════════════ AUTO-REFRESH TIMER ═══════════════════
function startRefreshTimer() {
  if (refreshTimer) clearInterval(refreshTimer);
  refreshCountdown = REFRESH_INTERVAL;
  document.getElementById('refresh-bar').classList.remove('hidden');
  document.getElementById('refresh-bar').classList.add('flex');

  refreshTimer = setInterval(() => {
    refreshCountdown--;
    const m = String(Math.floor(refreshCountdown / 60)).padStart(2, '0');
    const s = String(refreshCountdown % 60).padStart(2, '0');
    setText('refresh-countdown', `${m}:${s}`);
    if (refreshCountdown <= 0) {
      clearInterval(refreshTimer);
      refreshTimer = null;
      loadFeeds();
    }
  }, 1000);
}

// ═══════════════════ UTILITIES ═══════════════════
function parseDateMs(str) {
  if (!str) return 0;
  try {
    const d = new Date(str.replace(' ', 'T'));
    const ms = d.getTime();
    return isNaN(ms) ? 0 : ms;
  } catch (e) { return 0; }
}

function escHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function formatDisplayDate(dateStr) {
  if (!dateStr) return '—';
  try {
    const d = new Date(dateStr.replace(' ', 'T') + (dateStr.length === 16 ? ':00' : ''));
    if (isNaN(d)) return dateStr;
    const diffMs   = Date.now() - d.getTime();
    const diffDays = Math.floor(diffMs / 86400000);
    if (diffDays === 0) return `Today ${d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
    if (diffDays === 1) return 'Yesterday';
    if (diffDays <  7) return `${diffDays}d ago`;
    return d.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' });
  } catch (e) { return dateStr; }
}

function formatTimeAgo(dateStr) {
  if (!dateStr) return 'just now';
  try {
    const d       = new Date(dateStr.replace(' ', 'T'));
    const diffSec = Math.floor((Date.now() - d.getTime()) / 1000);
    if (diffSec < 60)   return 'just now';
    if (diffSec < 3600) return `${Math.floor(diffSec / 60)}m ago`;
    return `${Math.floor(diffSec / 3600)}h ago`;
  } catch (e) { return 'just now'; }
}

function setText(id, val) {
  const el = document.getElementById(id);
  if (el) el.textContent = val;
}

function show(id) { document.getElementById(id)?.classList.remove('hidden'); }
function hide(id) { document.getElementById(id)?.classList.add('hidden'); }

// ═══════════════════ BOOT ═══════════════════
document.addEventListener('DOMContentLoaded', loadFeeds);
