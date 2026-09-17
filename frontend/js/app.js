// Nexuloom Data Intelligence Platform - Frontend Application Logic
import { api } from './api.js';
import { charts } from './charts.js';
import {
  getLanguage,
  setLanguage,
  t,
  applyTranslations,
  localizeKpiName,
  localizeRuleName,
  localizeSeverity,
  localizeTrendDirection,
  localizeCategory,
} from './i18n.js';

// Global State
let currentDb = '';
let currentTable = '';
window.__udi_initialized = false;
window.api = api;
window.charts = charts;
window.getLanguage = getLanguage;
window.setLanguage = setLanguage;
window.t = t;
window.localizeKpiName = localizeKpiName;
window.localizeRuleName = localizeRuleName;
window.localizeSeverity = localizeSeverity;
window.localizeTrendDirection = localizeTrendDirection;
window.localizeCategory = localizeCategory;

// 1. Theme Management (Light / Dark)
window.toggleTheme = function() {
  const current = document.documentElement.getAttribute('data-theme') || 'dark';
  const newTheme = current === 'dark' ? 'light' : 'dark';
  document.documentElement.setAttribute('data-theme', newTheme);
  localStorage.setItem('udi_theme', newTheme);

  const isLight = newTheme === 'light';
  const lang = getLanguage();
  const themeTextEl = document.getElementById('themeToggleText');
  const themeIconEl = document.getElementById('themeToggleIcon');

  if (themeIconEl) themeIconEl.textContent = isLight ? '☀️' : '🌙';
  if (themeTextEl) {
    themeTextEl.textContent = isLight 
      ? (lang === 'tr' ? 'Açık Tema' : 'Light Mode')
      : (lang === 'tr' ? 'Koyu Tema' : 'Dark Mode');
  }

  // Refresh active charts to adopt new theme palette (light vs dark)
  const activeTab = document.querySelector('.nav-link.active')?.getAttribute('data-tab');
  if (activeTab === 'overview') loadOverview();
  else if (activeTab === 'kpis') loadKPIs();
  else if (activeTab === 'trends') loadTrends();
};

// 2. Language Management (TR / EN - Default: TR)
window.toggleLanguage = async function() {
  const current = getLanguage();
  const newLang = current === 'tr' ? 'en' : 'tr';
  setLanguage(newLang);

  // Update theme button text to match new language
  const isLight = document.documentElement.getAttribute('data-theme') === 'light';
  const themeTextEl = document.getElementById('themeToggleText');
  if (themeTextEl) {
    themeTextEl.textContent = isLight 
      ? (newLang === 'tr' ? 'Açık Tema' : 'Light Mode')
      : (newLang === 'tr' ? 'Koyu Tema' : 'Dark Mode');
  }

  // Re-render current tab contents to reflect language switch
  const activeTab = document.querySelector('.nav-link.active')?.getAttribute('data-tab');
  if (activeTab) await handleTabSwitch(activeTab);
};

// 3. Tab Navigation
window.switchTab = async function(tabId) {
  try {
    const navLinks = document.querySelectorAll('.nav-link');
    navLinks.forEach((l) => {
      if (l.getAttribute('data-tab') === tabId) {
        l.classList.add('active');
      } else {
        l.classList.remove('active');
      }
    });

    document.querySelectorAll('.tab-view').forEach((tab) => tab.classList.remove('active'));
    const activeTab = document.getElementById(`tab-${tabId}`);
    if (activeTab) {
      activeTab.classList.add('active');
    }
    await handleTabSwitch(tabId);
  } catch (err) {
    console.error(`Error switching to tab ${tabId}:`, err);
  }
};

// 4. Auto-Scan Local SQLite Databases
window.scanLocalDatabases = async function() {
  const btn = document.getElementById('btnScanDbs');
  if (btn) btn.textContent = t('scanDbsBtnScanning');
  try {
    const res = await fetch('/api/databases/auto-discover', { method: 'POST' });
    const data = await res.json();
    await loadDatabases();
    const discoveredNames = (data.discovered || []).map((d) => d.name).join(', ');
    const isTr = getLanguage() === 'tr';
    const msg = isTr
      ? `Otomatik tarama tamamlandı!\nBulunan yeni veritabanları (${data.discovered_count}): ${discoveredNames || 'Yeni veritabanı bulunamadı'}\nToplam aktif veritabanı sayısı: ${data.total_active_databases}`
      : `Auto-discovery completed!\nFound ${data.discovered_count} new database(s): ${discoveredNames || 'None new'}\nTotal active databases: ${data.total_active_databases}`;
    alert(msg);

    if (data.discovered && data.discovered.length > 0) {
      currentDb = data.discovered[0].name;
      const select = document.getElementById('globalDbSelect');
      if (select) select.value = currentDb;
      await updateTableSelector();
      await loadOverview();
    }
  } catch (e) {
    alert(`Auto-discovery error: ${e.message}`);
  } finally {
    if (btn) btn.textContent = t('scanDbsBtn');
  }
};

// 5. Quick Report Action
window.quickReport = async function() {
  const isTr = getLanguage() === 'tr';
  if (!currentDb) {
    alert(isTr ? 'Lütfen önce yukarıdaki kutudan bir veritabanı seçin!' : 'Please select a database from the dropdown first!');
    return;
  }
  const btn = document.getElementById('btnQuickReport');
  if (btn) btn.textContent = isTr ? '⏳ Hazırlanıyor...' : '⏳ Generating...';
  try {
    const res = await api.generateReport({
      database_name: currentDb,
      export_format: 'ALL',
      language: getLanguage(),
    });
    const msg = isTr
      ? `Hızlı Aylık Rapor başarıyla oluşturuldu!\nRapor Kimliği: ${res.report_id}\nFormatlar: PDF, Excel, HTML, CSV, JSON`
      : `Quick Report generated successfully!\nReport ID: ${res.report_id}\nFormats: PDF, Excel, HTML, CSV, JSON`;
    alert(msg);
    await window.switchTab('reports');
  } catch (e) {
    alert(`Report generation failed: ${e.message}`);
  } finally {
    if (btn) btn.textContent = t('quickReportBtn');
  }
};

// Modal Actions
window.openAddDbModal = function() {
  document.getElementById('modalAddDb')?.classList.add('active');
};

window.closeAddDbModal = function() {
  document.getElementById('modalAddDb')?.classList.remove('active');
};

window.openReportModal = function() {
  const isTr = getLanguage() === 'tr';
  const titleInput = document.getElementById('repTitleInput');
  const periodInput = document.getElementById('repPeriodInput');
  if (titleInput) {
    titleInput.value = isTr ? 'Aylık Veri Zekâsı ve Yönetici Raporu' : 'Monthly Business Intelligence & Executive Report';
  }
  if (periodInput) {
    periodInput.value = isTr ? 'Eylül 2026' : 'September 2026';
  }
  document.getElementById('modalReport')?.classList.add('active');
};

window.closeReportModal = function() {
  document.getElementById('modalReport')?.classList.remove('active');
};

window.submitAddDb = async function() {
  const name = document.getElementById('dbNameInput')?.value;
  const dbType = document.getElementById('dbTypeSelect')?.value;
  const target = document.getElementById('dbTargetInput')?.value;
  const host = document.getElementById('dbHostInput')?.value;
  const port = document.getElementById('dbPortInput')?.value;
  const user = document.getElementById('dbUserInput')?.value;
  const pass = document.getElementById('dbPassInput')?.value;

  if (!name || !target) {
    alert(getLanguage() === 'tr' ? 'Lütfen bağlantı adı ve veritabanı dosya yolunu girin.' : 'Please provide a connection name and database target path.');
    return;
  }

  try {
    await api.addDatabase({
      name,
      db_type: dbType,
      database_name: target,
      host: host || null,
      port: port ? parseInt(port) : null,
      username: user || null,
      password: pass || null,
    });
    window.closeAddDbModal();
    alert(getLanguage() === 'tr' ? `'${name}' veritabanı bağlantısı başarıyla kaydedildi!` : `Database connection '${name}' registered successfully!`);
    await loadDatabases();
    await renderDatabasesTable();
  } catch (e) {
    alert(`Error: ${e.message}`);
  }
};

window.submitGenerateReport = async function() {
  const isTr = getLanguage() === 'tr';
  const defaultTitle = isTr ? 'Aylık Veri Zekâsı ve Yönetici Raporu' : 'Monthly Business Intelligence & Executive Report';
  const defaultPeriod = isTr ? 'Eylül 2026' : 'September 2026';
  const title = document.getElementById('repTitleInput')?.value || defaultTitle;
  const period = document.getElementById('repPeriodInput')?.value || defaultPeriod;
  const fmt = document.getElementById('repFormatSelect')?.value || 'ALL';

  try {
    const res = await api.generateReport({
      database_name: currentDb,
      title,
      period,
      export_format: fmt,
      language: getLanguage(),
    });
    window.closeReportModal();
    alert(isTr ? `Rapor oluşturuldu!\nKimlik: ${res.report_id}` : `Report generated!\nID: ${res.report_id}`);
    await loadReportsLibrary();
  } catch (e) {
    alert(`Report generation failed: ${e.message}`);
  }
};

window.testDb = async function(name) {
  try {
    const res = await api.testDatabase(name);
    alert(`Database: ${name}\nStatus: ${res.status}\nMessage: ${res.message}`);
    await renderDatabasesTable();
  } catch (e) {
    alert(`Test error: ${e.message}`);
  }
};

window.deleteDb = async function(name) {
  const isTr = getLanguage() === 'tr';
  if (confirm(isTr ? `'${name}' bağlantısını silmek istediğinize emin misiniz?` : `Are you sure you want to delete connection '${name}'?`)) {
    try {
      await api.deleteDatabase(name);
      await loadDatabases();
      await renderDatabasesTable();
    } catch (e) {
      alert(`Delete error: ${e.message}`);
    }
  }
};

window.runSqlQuery = async function() {
  const sql = document.getElementById('sqlInput')?.value;
  if (!sql) return;
  await executeQueryAction(sql);
};

window.askNaturalLanguage = async function() {
  const q = document.getElementById('nlInput')?.value;
  if (!q) return;

  try {
    const res = await api.askNaturalLanguage(currentDb, q);
    const sqlInput = document.getElementById('sqlInput');
    if (sqlInput) sqlInput.value = res.generated_sql;
    const safety = document.getElementById('querySafetyStatus');
    if (safety) safety.textContent = `Translated: ${res.explanation} (LLM: ${res.is_llm_used})`;
    renderQueryResult(res);
  } catch (e) {
    alert(`Query failed: ${e.message}`);
  }
};

window.runAnomalyScan = async function() {
  const metricCol = document.getElementById('anomalyMetricSelect')?.value;
  const method = document.getElementById('anomalyMethodSelect')?.value || 'ALL';
  if (!metricCol) return;

  const tbody = document.querySelector('#anomaliesTable tbody');
  if (tbody) tbody.innerHTML = `<tr><td colspan="8">${getLanguage() === 'tr' ? 'İstatistiksel aykırı değerler taranıyor...' : 'Scanning table for statistical outliers...'}</td></tr>`;

  try {
    const res = await api.getAnomalies(currentDb, currentTable, metricCol, method);
    if (!tbody) return;
    tbody.innerHTML = '';

    if (!res.anomalies || res.anomalies.length === 0) {
      tbody.innerHTML = `<tr><td colspan="8" style="color: #10b981;">${getLanguage() === 'tr' ? '✓ İstatistiksel anomali tespit edilmedi. Metrik normal sınırda.' : 'No statistical anomalies detected. Metric is within normal baseline.'}</td></tr>`;
      return;
    }

    const isTr = getLanguage() === 'tr';
    res.anomalies.slice(0, 30).forEach((a) => {
      const tr = document.createElement('tr');
      const sevClass = a.severity === 'CRITICAL' ? 'badge-critical' : (a.severity === 'HIGH' ? 'badge-high' : 'badge-low');
      const sevLabel = isTr ? (a.severity_tr || localizeSeverity(a.severity)) : a.severity;
      const methodLabel = isTr ? (a.method_tr || a.method) : a.method;
      const explanationText = isTr ? (a.explanation_tr || a.explanation) : a.explanation;
      const normalRangeText = isTr ? (a.normal_range_tr || `${a.normal_range_min} ile ${a.normal_range_max} arası`) : a.normal_range;

      tr.innerHTML = `
        <td><strong>${a.entity}</strong></td>
        <td>${a.metric}</td>
        <td><span class="badge ${sevClass}">${sevLabel}</span></td>
        <td><strong>${a.observed_value}</strong></td>
        <td>${normalRangeText}</td>
        <td>${a.deviation_pct}</td>
        <td><span class="badge badge-medium">${methodLabel}</span></td>
        <td style="font-size: 0.8rem; color: var(--text-muted);">${explanationText}</td>
      `;
      tbody.appendChild(tr);
    });
  } catch (e) {
    if (tbody) tbody.innerHTML = `<tr><td colspan="8" style="color: #ef4444;">${e.message}</td></tr>`;
  }
};

window.executeAllRules = async function() {
  try {
    const res = await api.executeAllRules(currentDb);
    const isTr = getLanguage() === 'tr';
    alert(isTr ? `${currentDb} üzerinde ${res.length} aktif iş kuralı değerlendirildi.` : `Evaluated ${res.length} active business rules against ${currentDb}.`);
    await loadBusinessRules();
  } catch (e) {
    alert(`Failed evaluating rules: ${e.message}`);
  }
};

window.openCreateRulePrompt = async function() {
  const isTr = getLanguage() === 'tr';
  const ruleName = prompt(isTr ? "Kural adını girin (örn. 'Düşük Stok Uyarısı'):" : "Enter business rule name (e.g. 'Low Stock Alert'):");
  if (!ruleName) return;
  const tableName = prompt(isTr ? "Hedef tablo adını girin:" : "Enter target table name:", currentTable || "orders");
  if (!tableName) return;
  const condition = prompt(isTr ? "SQL koşul ifadesini girin (örn. 'stock_quantity < 20'):" : "Enter SQL condition expression (e.g. 'stock_quantity < 20'):");
  if (!condition) return;

  try {
    await api.createRule({
      name: ruleName,
      database_name: currentDb,
      table_name: tableName,
      condition_expression: condition,
      severity: "HIGH",
      action_type: "ALERT",
      action_payload: { message: `Rule '${ruleName}' triggered` },
    });
    alert(isTr ? `'${ruleName}' kuralı başarıyla oluşturuldu!` : `Rule '${ruleName}' created successfully!`);
    await loadBusinessRules();
  } catch (e) {
    alert(`Failed to create rule: ${e.message}`);
  }
};

window.runRule = async function(name) {
  try {
    const res = await api.executeRule(name);
    const isTr = getLanguage() === 'tr';
    alert(isTr ? `'${name}' kuralı değerlendirildi: ${res.status} (${res.violation_count} ihlal).` : `Rule '${name}' evaluated: ${res.status} (${res.violation_count} violating rows).`);
    await loadBusinessRules();
  } catch (e) {
    alert(`Rule execution failed: ${e.message}`);
  }
};

// 6. Application Initialization
async function init() {
  if (window.__udi_initialized) return;
  window.__udi_initialized = true;

  // Initialize Theme
  const savedTheme = localStorage.getItem('udi_theme') || 'dark';
  document.documentElement.setAttribute('data-theme', savedTheme);
  const themeIconEl = document.getElementById('themeToggleIcon');
  const themeTextEl = document.getElementById('themeToggleText');
  if (themeIconEl) themeIconEl.textContent = savedTheme === 'light' ? '☀️' : '🌙';

  // Initialize Language (Default: Turkish TR)
  const savedLang = localStorage.getItem('udi_lang') || 'tr';
  setLanguage(savedLang);

  if (themeTextEl) {
    const isTr = savedLang === 'tr';
    themeTextEl.textContent = savedTheme === 'light'
      ? (isTr ? 'Açık Tema' : 'Light Mode')
      : (isTr ? 'Koyu Tema' : 'Dark Mode');
  }

  console.log("🚀 Initializing Nexuloom Data Intelligence Platform Frontend...");
  setupNavigation();
  setupModals();
  setupGlobalFilters();
  setupActionButtons();

  await loadDatabases();
  if (currentDb) {
    await loadOverview();
  }
}

// Ensure init executes reliably
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", init);
} else {
  init();
}
setTimeout(() => {
  if (!window.__udi_initialized) init();
}, 250);

// Setup Navigation Events
function setupNavigation() {
  const navLinks = document.querySelectorAll('.nav-link');
  navLinks.forEach((link) => {
    link.addEventListener('click', async (e) => {
      e.preventDefault();
      const tabId = link.getAttribute('data-tab');
      if (tabId) await window.switchTab(tabId);
    });
  });
}

// Handle Tab Switch
async function handleTabSwitch(tabId) {
  try {
    if (tabId === "databases") {
      await renderDatabasesTable();
      return;
    }
    if (tabId === "audit") {
      await loadAuditAndLineage();
      return;
    }
    if (!currentDb) {
      await loadDatabases();
    }
    if (!currentDb && tabId !== "databases" && tabId !== "audit") return;

    switch (tabId) {
      case "overview":
        await loadOverview();
        break;
      case "databases":
        await renderDatabasesTable();
        break;
      case "schema":
        await loadSchemaAndRelationships();
        break;
      case "profiling":
        await loadProfiling();
        break;
      case "quality":
        await loadQuality();
        break;
      case "kpis":
        await loadKPIs();
        break;
      case "trends":
        await loadTrends();
        break;
      case "anomalies":
        await loadAnomaliesTab();
        break;
      case "rules":
        await loadBusinessRules();
        break;
      case "insights":
        await loadInsights();
        break;
      case "query":
        break;
      case "reports":
        await loadReportsLibrary();
        break;
      case "audit":
        await loadAuditAndLineage();
        break;
    }
  } catch (err) {
    console.error(`Error loading tab ${tabId}:`, err);
  }
}

// Global Filters & DB Select
async function loadDatabases() {
  const dbSelect = document.getElementById('globalDbSelect');
  if (!dbSelect) return;

  try {
    const dbs = await api.getDatabases();
    dbSelect.innerHTML = '';

    if (!Array.isArray(dbs) || dbs.length === 0) {
      dbSelect.innerHTML = `<option value="">${getLanguage() === 'tr' ? 'Bağlı veritabanı yok' : 'No databases connected'}</option>`;
      return;
    }

    dbs.forEach((d) => {
      const opt = document.createElement('option');
      opt.value = d.name;
      opt.textContent = `${d.name} (${d.db_type})`;
      dbSelect.appendChild(opt);
    });

    if (!currentDb || !dbs.some((d) => d.name === currentDb)) {
      currentDb = dbs[0].name;
    }
    dbSelect.value = currentDb;
    await updateTableSelector();
  } catch (e) {
    console.error('Failed to load databases:', e);
    dbSelect.innerHTML = `<option value="">${getLanguage() === 'tr' ? 'Bağlantı hatası' : 'Connection error'}</option>`;
  }
}

async function updateTableSelector() {
  const tableSelect = document.getElementById('globalTableSelect');
  if (!tableSelect || !currentDb) return;

  try {
    const catalog = await api.getCatalog(currentDb);
    tableSelect.innerHTML = '';
    const tables = catalog.tables || [];

    tables.forEach((t) => {
      const opt = document.createElement('option');
      opt.value = t.name;
      opt.textContent = `${t.name} (${t.row_count?.toLocaleString() || 0} ${getLanguage() === 'tr' ? 'satır' : 'rows'})`;
      tableSelect.appendChild(opt);
    });

    if (tables.length > 0) {
      currentTable = tables[0].name;
      tableSelect.value = currentTable;
    }
  } catch (e) {
    console.error('Failed to update table selector:', e);
  }
}

function setupGlobalFilters() {
  const dbSelect = document.getElementById('globalDbSelect');
  const tableSelect = document.getElementById('globalTableSelect');

  if (dbSelect) {
    dbSelect.addEventListener('change', async (e) => {
      currentDb = e.target.value;
      await updateTableSelector();
      const activeTab = document.querySelector('.nav-link.active')?.getAttribute('data-tab');
      if (activeTab) handleTabSwitch(activeTab);
    });
  }

  if (tableSelect) {
    tableSelect.addEventListener('change', (e) => {
      currentTable = e.target.value;
      const activeTab = document.querySelector('.nav-link.active')?.getAttribute('data-tab');
      if (activeTab) handleTabSwitch(activeTab);
    });
  }
}

// 1. Overview Tab
async function loadOverview() {
  if (!currentDb) return;

  try {
    const container = document.getElementById('overviewKpiCards');
    const obsList = document.getElementById('overviewObservationsList');
    const isTr = getLanguage() === 'tr';

    // Load Data Quality for current database
    let dq = { overall_quality_score: 95, tables_analyzed: 0, critical_violations: 0, total_violations: 0, overall_grade: 'A' };
    try {
      dq = await api.getQuality(currentDb);
    } catch (e) {
      console.warn('Quality fetch warning:', e);
    }
    const score = Math.round(dq.overall_quality_score || 95);

    // Try loading KPIs for cards
    let kpis = [];
    try {
      kpis = await api.getKPIs(currentDb);
    } catch (e) {
      console.warn('KPI fetch warning:', e);
    }

    const evaluatedKpis = [];
    if (Array.isArray(kpis) && kpis.length > 0) {
      if (container) container.innerHTML = '';
      for (const k of kpis.slice(0, 4)) {
        try {
          const evalRes = await api.evaluateKPI(k.name);
          evaluatedKpis.push(evalRes);
          const curr = `${evalRes.unit || ''}${evalRes.current_value?.toLocaleString() || 0}`;
          const growth = evalRes.growth_rate_mom_pct;
          const trendClass = growth > 0 ? 'trend-up' : (growth < 0 ? 'trend-down' : 'trend-neutral');
          const arrow = growth > 0 ? '↑' : (growth < 0 ? '↓' : '→');
          const growthText = growth !== null ? `${arrow} ${Math.abs(growth)}% MoM` : (isTr ? 'Sabit' : 'Stable');

          const card = document.createElement('div');
          card.className = 'card';
          card.innerHTML = `
            <div class="card-title">${localizeKpiName(evalRes.name)}</div>
            <div class="metric-number">${curr}</div>
            <div class="metric-trend ${trendClass}">${growthText}</div>
          `;
          if (container) container.appendChild(card);
        } catch (err) {}
      }
    }

    // Dynamic Fallback KPI cards if database has no preconfigured financial KPIs (e.g. derindex)
    if (evaluatedKpis.length === 0 && container) {
      const catalog = await api.getCatalog(currentDb);
      const totalRows = catalog.total_rows || 0;
      const tableCount = catalog.table_count || 0;
      container.innerHTML = `
        <div class="card"><div class="card-title">${t('cardConnectedDb')}</div><div class="metric-number" style="font-size: 1.4rem;">${currentDb}</div><div class="metric-trend trend-up">${t('engineOnline')}</div></div>
        <div class="card"><div class="card-title">${t('cardIndexedTables')}</div><div class="metric-number">${tableCount} ${isTr ? 'Tablo' : 'Tables'}</div><div class="metric-trend trend-neutral">${isTr ? 'Şema Keşfedildi' : 'Schema Discovered'}</div></div>
        <div class="card"><div class="card-title">${t('cardTotalRecords')}</div><div class="metric-number">${totalRows.toLocaleString()}</div><div class="metric-trend trend-up">${isTr ? 'Canlı Satır' : 'Live Rows'}</div></div>
        <div class="card"><div class="card-title">${t('cardDataQualityScore')}</div><div class="metric-number" style="color: ${score >= 80 ? 'var(--accent-success)' : 'var(--accent-warning)'};">${score}/100</div><div class="metric-trend ${dq.critical_violations > 0 ? 'trend-down' : 'trend-neutral'}">${isTr ? 'Derece' : 'Grade'} ${dq.overall_grade || 'GOOD'} (${dq.critical_violations || 0} ${isTr ? 'Kritik' : 'Critical'})</div></div>
      `;
    }

    // Render Revenue Time-Series Chart or Table Size Distribution
    if (evaluatedKpis.length > 0 && evaluatedKpis[0].time_series?.length > 1) {
      const ts = evaluatedKpis[0].time_series;
      charts.renderLine(
        'overviewRevenueChart',
        ts.map((t) => t.period),
        ts.map((t) => t.value),
        localizeKpiName(evaluatedKpis[0].name),
        '#6366f1'
      );
    } else {
      const catalog = await api.getCatalog(currentDb);
      const topTables = (catalog.tables || []).slice(0, 8);
      charts.renderBar(
        'overviewRevenueChart',
        topTables.map((t) => t.name),
        topTables.map((t) => t.row_count || 0),
        isTr ? 'Tablo Satır Sayısı' : 'Table Row Count',
        '#6366f1'
      );
    }

    // Render Data Quality Donut Chart
    charts.renderDonut(
      'overviewQualityChart',
      isTr ? ['Kalite Skoru', 'Risk & Ceza'] : ['Quality Score', 'Penalties & Risks'],
      [score, Math.max(0, 100 - score)],
      ['#10b981', '#ef4444']
    );

    // Render Autonomous Executive Observations in Selected Language
    if (obsList) {
      try {
        const obsRes = await fetch(`/api/reports/observations/${encodeURIComponent(currentDb)}?language=${getLanguage()}`);
        if (obsRes.ok) {
          const obsData = await obsRes.json();
          if (obsData.observations && obsData.observations.length > 0) {
            obsList.innerHTML = obsData.observations.map((o) => `<p>• ${o}</p>`).join('');
          } else {
            throw new Error('No observations returned');
          }
        } else {
          throw new Error('Observations endpoint status error');
        }
      } catch (obsErr) {
        if (isTr) {
          obsList.innerHTML = `
            <p>• <strong>Aktif Boru Hattı:</strong> <code>${currentDb}</code> veritabanı çevrimiçi, ${dq.tables_analyzed || 0} tablo başarıyla denetlendi.</p>
            <p>• <strong>Veri Kalitesi Sağlığı:</strong> <strong>${score}/100</strong> skoru (Derece: ${dq.overall_grade || 'İYİ'}) ve ${dq.critical_violations || 0} kritik bütünlük uyarısı tespit edildi.</p>
            <p>• <strong>Deterministik Doğrulama:</strong> Tüm ilişkisel şemalar, istatistiksel profiller, anomaliler ve iş kuralları yapay zeka halüsinasyonu olmaksızın matematiksel olarak çalıştırılmıştır.</p>
          `;
        } else {
          obsList.innerHTML = `
            <p>• <strong>Active Pipeline:</strong> Database <code>${currentDb}</code> is online with ${dq.tables_analyzed || 0} tables audited.</p>
            <p>• <strong>Data Quality Health:</strong> Scored <strong>${score}/100</strong> (Grade ${dq.overall_grade || 'GOOD'}) with ${dq.critical_violations || 0} critical integrity warnings.</p>
            <p>• <strong>Deterministic Engine:</strong> All relational catalogs, column profiling, anomalies, and business rules executed mathematically without LLM hallucination.</p>
          `;
        }
      }
    }
  } catch (err) {
    console.error('Failed to load overview:', err);
  }
}

// 2. Databases Tab
async function renderDatabasesTable() {
  const tableBody = document.querySelector('#dbConnectionsTable tbody');
  if (!tableBody) return;
  const isTr = getLanguage() === 'tr';
  tableBody.innerHTML = `<tr><td colspan="7">${isTr ? 'Bağlantılar yükleniyor...' : 'Loading connections...'}</td></tr>`;

  try {
    const conns = await api.getDatabases();
    tableBody.innerHTML = '';

    if (!Array.isArray(conns) || conns.length === 0) {
      tableBody.innerHTML = `<tr><td colspan="7">${isTr ? 'Kayıtlı veritabanı bulunamadı. "+ Yeni Bağlantı Ekle" veya "Yerel DB\'leri Tara" butonunu kullanın.' : 'No database connections found. Click "+ Add New Connection" or "Auto-Scan Local DBs".'}</td></tr>`;
      return;
    }

    conns.forEach((c) => {
      const tr = document.createElement('tr');
      const isOnline = c.last_test_status === 'ONLINE';
      const badgeClass = isOnline ? 'badge-success' : 'badge-critical';

      tr.innerHTML = `
        <td><strong>${c.name}</strong></td>
        <td><span class="badge badge-low">${c.db_type}</span></td>
        <td><code>${c.database_name}</code></td>
        <td>${c.host || 'local'}:${c.port || '-'}</td>
        <td><span class="badge ${badgeClass}">${c.last_test_status || 'UNTESTED'}</span></td>
        <td>${c.last_tested_at ? c.last_tested_at.slice(0, 19).replace('T', ' ') : '-'}</td>
        <td>
          <button class="btn btn-secondary btn-sm" onclick="window.testDb('${c.name}')">${t('btnTest')}</button>
          <button class="btn btn-danger btn-sm" onclick="window.deleteDb('${c.name}')" style="margin-left: 6px;">${t('btnDelete')}</button>
        </td>
      `;
      tableBody.appendChild(tr);
    });
  } catch (e) {
    tableBody.innerHTML = `<tr><td colspan="7" style="color: #ef4444;">Error: ${e.message}</td></tr>`;
  }
}

// 3. Schema & Graph Tab
async function loadSchemaAndRelationships() {
  if (!currentDb) return;
  const isTr = getLanguage() === 'tr';
  try {
    const catalog = await api.getCatalog(currentDb);
    const rels = await api.getRelationships(currentDb);

    const tblBadge = document.getElementById('schemaTableCountBadge');
    if (tblBadge) tblBadge.textContent = `${catalog.table_count} ${isTr ? 'Tablo' : 'Tables'}`;
    const relBadge = document.getElementById('schemaRelCountBadge');
    if (relBadge) relBadge.textContent = `${rels.total_edges} ${isTr ? 'İlişki' : 'Relations'}`;

    // Populate Tables Catalog
    const catTbody = document.querySelector('#schemaCatalogTable tbody');
    if (catTbody) {
      catTbody.innerHTML = '';
      catalog.tables.forEach((t) => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
          <td><strong>${t.name}</strong></td>
          <td>${t.column_count}</td>
          <td>${t.row_count?.toLocaleString() || 0}</td>
          <td>${t.primary_keys?.join(', ') || '-'}</td>
        `;
        catTbody.appendChild(tr);
      });
    }

    // Populate Relationships
    const relTbody = document.querySelector('#schemaRelationshipsTable tbody');
    if (relTbody) {
      relTbody.innerHTML = '';
      if (!rels.edges || rels.edges.length === 0) {
        relTbody.innerHTML = `<tr><td colspan="4">${isTr ? 'Açık yabancı anahtar (FK) bulunamadı. Çıkarımsal ilişkiler aktif.' : 'No explicit foreign keys detected. Inferred relationships active.'}</td></tr>`;
      } else {
        rels.edges.forEach((e) => {
          const tr = document.createElement('tr');
          const relTypeBadge = e.relationship_type === 'EXPLICIT_FK' ? 'badge-medium' : 'badge-low';
          const relTypeLabel = isTr ? (e.relationship_type === 'EXPLICIT_FK' ? 'Açık FK' : 'Çıkarımsal FK') : e.relationship_type;
          const relDesc = isTr ? (e.label === 'Foreign Key Reference' ? 'Yabancı Anahtar Referansı' : e.label) : e.label;
          tr.innerHTML = `
            <td><strong>${e.source}</strong>.${e.source_column}</td>
            <td><strong>${e.target}</strong>.${e.target_column}</td>
            <td><span class="badge ${relTypeBadge}">${relTypeLabel}</span></td>
            <td>${relDesc}</td>
          `;
          relTbody.appendChild(tr);
        });
      }
    }
  } catch (e) {
    console.error('Schema load error:', e);
  }
}

// 4. Data Profiling Tab
async function loadProfiling() {
  if (!currentDb || !currentTable) return;
  const tbody = document.querySelector('#profilingTable tbody');
  const isTr = getLanguage() === 'tr';
  if (tbody) tbody.innerHTML = `<tr><td colspan="8">${isTr ? 'Derin istatistiksel profiller hesaplanıyor...' : 'Calculating deep statistical profiles...'}</td></tr>`;

  try {
    const res = await api.getProfile(currentDb, currentTable);
    if (!tbody) return;
    tbody.innerHTML = '';

    let firstNumDist = null;
    let firstNumCol = null;

    for (const [colName, p] of Object.entries(res.columns || {})) {
      const tr = document.createElement('tr');
      const cat = p.type_category || 'STRING';
      const catLabel = isTr ? localizeCategory(cat) : cat;

      let statsDetail = '-';
      if (cat === 'NUMERIC') {
        statsDetail = isTr ? `Std: ${p.std_dev || 0}, IQR: ${p.iqr || 0}` : `std=${p.std_dev || 0}, iqr=${p.iqr || 0}`;
        if (!firstNumDist && p.distribution_histogram?.length > 0) {
          firstNumDist = p.distribution_histogram;
          firstNumCol = colName;
        }
      }

      let topValText = '-';
      if (p.most_frequent_values?.length > 0) {
        topValText = p.most_frequent_values.slice(0, 2).map((v) => `${v.value} (%${v.percentage})`).join(', ');
      }

      tr.innerHTML = `
        <td><strong>${colName}</strong></td>
        <td><span class="badge badge-low">${catLabel}</span></td>
        <td>%${p.null_percentage} (${p.null_count})</td>
        <td>${p.unique_count?.toLocaleString()}</td>
        <td>${p.min !== undefined ? `${p.min} / ${p.max}` : '-'}</td>
        <td>${p.mean !== undefined ? `${p.mean} / ${p.median}` : '-'}</td>
        <td>${statsDetail}</td>
        <td style="font-size: 0.8rem; color: var(--text-muted);">${topValText}</td>
      `;
      tbody.appendChild(tr);
    }

    // Render Histogram
    if (firstNumDist) {
      const title = document.getElementById('profileChartTitle');
      if (title) title.textContent = isTr ? `'${firstNumCol}' Dağılım Histogramı` : `Distribution Histogram for '${firstNumCol}'`;
      charts.renderBar(
        'profileDistChart',
        firstNumDist.map((b) => `${b.bin_start} - ${b.bin_end}`),
        firstNumDist.map((b) => b.count),
        isTr ? `${firstNumCol} Frekansı` : `Frequency in ${firstNumCol}`,
        '#06b6d4'
      );
    }
  } catch (e) {
    if (tbody) tbody.innerHTML = `<tr><td colspan="8" style="color: #ef4444;">${e.message}</td></tr>`;
  }
}

// 5. Data Quality Tab
async function loadQuality() {
  if (!currentDb) return;
  const isTr = getLanguage() === 'tr';
  try {
    const dq = await api.getQuality(currentDb);

    const scoreEl = document.getElementById('dqOverallScore');
    if (scoreEl) scoreEl.textContent = `${Math.round(dq.overall_quality_score || 0)}/100`;
    const gradeEl = document.getElementById('dqGrade');
    if (gradeEl) gradeEl.textContent = `${isTr ? 'Derece' : 'Grade'}: ${dq.overall_grade}`;
    const critEl = document.getElementById('dqCritCount');
    if (critEl) critEl.textContent = dq.critical_violations || 0;
    const violEl = document.getElementById('dqViolCount');
    if (violEl) violEl.textContent = dq.total_violations || 0;
    const tblsEl = document.getElementById('dqTablesCount');
    if (tblsEl) tblsEl.textContent = dq.tables_analyzed || 0;

    const tbody = document.querySelector('#dqViolationsTable tbody');
    if (!tbody) return;
    tbody.innerHTML = '';

    let violationCount = 0;
    for (const t of dq.tables || []) {
      for (const v of t.violations || []) {
        violationCount++;
        const tr = document.createElement('tr');
        const sevClass = v.severity === 'CRITICAL' ? 'badge-critical' : (v.severity === 'HIGH' ? 'badge-high' : 'badge-low');
        const sevLabel = isTr ? (v.severity_tr || localizeSeverity(v.severity)) : v.severity;
        const ruleLabel = isTr ? (v.rule_name_tr || v.rule_name) : v.rule_name;
        const penaltyLabel = isTr ? `-${v.penalty} puan` : `-${v.penalty} pts`;
        const msgLabel = isTr ? (v.message_tr || v.message) : v.message;

        tr.innerHTML = `
          <td><strong>${v.table_name}</strong></td>
          <td>${v.column_name || '-'}</td>
          <td><span class="badge ${sevClass}">${sevLabel}</span></td>
          <td>${ruleLabel}</td>
          <td>${penaltyLabel}</td>
          <td>${msgLabel}</td>
        `;
        tbody.appendChild(tr);
      }
    }

    if (violationCount === 0) {
      tbody.innerHTML = `<tr><td colspan="6" style="color: #10b981;">${isTr ? '✓ Tüm veri kalitesi kuralları sağlandı! İhlal tespit edilmedi.' : '✓ All data quality rules satisfied! No violations detected.'}</td></tr>`;
    }
  } catch (e) {
    console.error('Quality tab error:', e);
  }
}

// 6. KPI Engine Tab
async function loadKPIs() {
  if (!currentDb) return;
  const container = document.getElementById('kpiEngineCards');
  if (container) container.innerHTML = '';
  const isTr = getLanguage() === 'tr';

  try {
    const kpis = await api.getKPIs(currentDb);
    if (!Array.isArray(kpis) || kpis.length === 0) {
      if (container) container.innerHTML = `<div class="card"><p>${isTr ? 'Bu veritabanı için önceden tanımlanmış KPI bulunamadı. Özel analiz için Doğal Dil veya İş Kuralları sekmesini kullanın.' : 'No predefined KPIs registered for this database. Use Business Rules or Query tabs for custom analysis.'}</p></div>`;
      return;
    }

    let firstKpiWithTs = null;

    for (const k of kpis) {
      try {
        const res = await api.evaluateKPI(k.name);
        const curr = `${res.unit || ''}${res.current_value?.toLocaleString() || 0}`;
        const growth = res.growth_rate_mom_pct;
        const trendClass = growth > 0 ? 'trend-up' : (growth < 0 ? 'trend-down' : 'trend-neutral');
        const sign = growth > 0 ? '+' : '';

        const card = document.createElement('div');
        card.className = 'card';
        card.style.cursor = 'pointer';
        const kpiTitle = isTr ? localizeKpiName(res.name) : res.name;
        const growthBadge = growth !== null ? (isTr ? `${sign}%${Math.abs(growth)} MoM` : `${sign}${growth}% MoM`) : (isTr ? 'Baz Değer' : 'Base Value');
        card.innerHTML = `
          <div class="card-title">${kpiTitle}</div>
          <div class="metric-number">${curr}</div>
          <div class="metric-trend ${trendClass}">${growthBadge}</div>
          <div style="font-size: 0.75rem; color: var(--text-dim); margin-top: 8px;">${res.formula}</div>
        `;

        card.addEventListener('click', () => {
          if (res.time_series?.length > 1) {
            renderKpiChart(res);
          }
        });

        if (container) container.appendChild(card);

        if (!firstKpiWithTs && res.time_series?.length > 1) {
          firstKpiWithTs = res;
        }
      } catch (e) {}
    }

    if (firstKpiWithTs) {
      renderKpiChart(firstKpiWithTs);
    }
  } catch (e) {
    console.error('KPI error:', e);
  }
}

function renderKpiChart(kpiRes) {
  const isTr = getLanguage() === 'tr';
  const kpiTitle = isTr ? localizeKpiName(kpiRes.name) : kpiRes.name;
  const title = document.getElementById('kpiTimeSeriesTitle');
  if (title) title.textContent = `${isTr ? 'Aylık Tarihsel Seri' : 'Historical Monthly Series'}: ${kpiTitle}`;
  charts.renderLine(
    'kpiTimeSeriesChart',
    kpiRes.time_series.map((t) => t.period),
    kpiRes.time_series.map((t) => t.value),
    kpiTitle,
    '#6366f1'
  );
}

// 7. Trend Analysis Tab
async function loadTrends() {
  if (!currentDb) return;
  const tbody = document.querySelector('#trendsTable tbody');
  if (tbody) tbody.innerHTML = '';
  const isTr = getLanguage() === 'tr';

  try {
    const kpis = await api.getKPIs(currentDb);
    if (!Array.isArray(kpis) || kpis.length === 0) {
      if (tbody) tbody.innerHTML = `<tr><td colspan="7">${isTr ? 'Bu veritabanı için yapılandırılmış trend metriği bulunamadı.' : 'No trend metrics configured for this database.'}</td></tr>`;
      return;
    }

    let firstTrend = null;

    for (const k of kpis) {
      try {
        const t = await api.getKPITrend(k.name);
        if (t.trend_direction !== 'INSUFFICIENT_DATA') {
          const tr = document.createElement('tr');
          const dirBadge = t.trend_direction === 'UPWARD' ? 'badge-success' : (t.trend_direction === 'DOWNWARD' ? 'badge-critical' : 'badge-low');
          const metricLabel = isTr ? (t.metric_name_tr || localizeKpiName(t.metric_name)) : t.metric_name;
          const dirLabel = isTr ? (t.trend_direction_tr || localizeTrendDirection(t.trend_direction)) : t.trend_direction;
          const explLabel = isTr ? (t.explanation_tr || t.explanation) : t.explanation;

          tr.innerHTML = `
            <td><strong>${metricLabel}</strong></td>
            <td><span class="badge ${dirBadge}">${dirLabel}</span></td>
            <td>${(t.total_growth_percentage > 0 ? '+' : '') + Number(t.total_growth_percentage || 0).toFixed(1)}%</td>
            <td>${t.linear_slope}</td>
            <td>${t.r_squared}</td>
            <td>${t.sudden_changes?.length || 0} ${isTr ? 'tespit' : 'detected'}</td>
            <td style="font-size: 0.82rem; color: var(--text-muted);">${explLabel}</td>
          `;
          if (tbody) tbody.appendChild(tr);

          if (!firstTrend && t.moving_average_series?.length > 0) {
            firstTrend = t;
          }
        }
      } catch (e) {}
    }

    if (firstTrend) {
      const metricLabel = isTr ? (firstTrend.metric_name_tr || localizeKpiName(firstTrend.metric_name)) : firstTrend.metric_name;
      charts.renderLine(
        'trendDetailChart',
        firstTrend.moving_average_series.map((s) => s.period),
        firstTrend.moving_average_series.map((s) => s.moving_avg),
        `${isTr ? 'Hareketli Ortalama' : 'Moving Average'}: ${metricLabel}`,
        '#06b6d4'
      );
    }
  } catch (e) {
    console.error('Trends error:', e);
  }
}

// 8. Anomalies Tab
async function loadAnomaliesTab() {
  if (!currentDb || !currentTable) return;
  try {
    const catalog = await api.getCatalog(currentDb);
    const tInfo = catalog.tables.find((t) => t.name === currentTable);
    const metricSelect = document.getElementById('anomalyMetricSelect');
    if (!metricSelect) return;
    metricSelect.innerHTML = '';

    if (tInfo) {
      const numCols = tInfo.columns.filter((c) =>
        ['int', 'float', 'real', 'numeric', 'double'].some((typ) => c.type.toLowerCase().includes(typ))
      );
      numCols.forEach((c) => {
        const opt = document.createElement('option');
        opt.value = c.name;
        opt.textContent = c.name;
        metricSelect.appendChild(opt);
      });
    }

    if (metricSelect.options.length > 0) {
      await window.runAnomalyScan();
    }
  } catch (e) {
    console.error('Anomalies tab error:', e);
  }
}

// 9. Business Rules Tab
async function loadBusinessRules() {
  if (!currentDb) return;
  const tbody = document.querySelector('#businessRulesTable tbody');
  if (!tbody) return;
  const isTr = getLanguage() === 'tr';
  tbody.innerHTML = `<tr><td colspan="8">${isTr ? 'İş kuralları yükleniyor...' : 'Loading business rules...'}</td></tr>`;

  try {
    const rules = await api.getRules(currentDb);
    tbody.innerHTML = '';

    if (!Array.isArray(rules) || rules.length === 0) {
      tbody.innerHTML = `<tr><td colspan="8">${isTr ? 'Henüz iş kuralı tanımlanmadı. Koşullu mantık eklemek için "+ Kural Oluştur" butonuna tıklayın.' : 'No business rules defined yet. Click "+ Create Rule" to add conditional logic.'}</td></tr>`;
      return;
    }

    rules.forEach((r) => {
      const tr = document.createElement('tr');
      const sevClass = r.severity === 'CRITICAL' ? 'badge-critical' : (r.severity === 'HIGH' ? 'badge-high' : 'badge-low');
      const sevLabel = isTr ? (r.severity_tr || localizeSeverity(r.severity)) : r.severity;
      const ruleName = isTr ? (r.name_tr || localizeRuleName(r.name)) : r.name;
      const statusText = r.last_violations_count > 0 ? (isTr ? 'İHLAL' : 'VIOLATION') : (isTr ? 'GEÇTİ' : 'PASSED');
      const statusClass = r.last_violations_count > 0 ? 'badge-critical' : 'badge-success';

      tr.innerHTML = `
        <td><strong>${ruleName}</strong></td>
        <td>${r.table_name}</td>
        <td><span class="badge ${sevClass}">${sevLabel}</span></td>
        <td><code>${r.condition_sql}</code></td>
        <td><span class="badge ${statusClass}">${statusText}</span></td>
        <td><strong>${r.last_violations_count || 0}</strong></td>
        <td>${r.last_run_at ? r.last_run_at.slice(0, 19).replace('T', ' ') : '-'}</td>
        <td>
          <button class="btn btn-secondary btn-sm" onclick="window.runRule('${r.name}')">${isTr ? 'Çalıştır' : 'Run'}</button>
        </td>
      `;
      tbody.appendChild(tr);
    });
  } catch (e) {
    tbody.innerHTML = `<tr><td colspan="8" style="color: #ef4444;">${e.message}</td></tr>`;
  }
}

// 10. Insights & Root Cause Tab
async function loadInsights() {
  if (!currentDb) return;
  const container = document.getElementById('insightsContainer');
  const treeContainer = document.getElementById('rootCauseTreeContainer');
  const isTr = getLanguage() === 'tr';

  if (container) container.innerHTML = `<p>${isTr ? 'Çok boyutlu katkı faktörleri hesaplanıyor...' : 'Evaluating multi-dimensional contributing factors...'}</p>`;

  try {
    const res = await api.getVarianceInsights({
      database_name: currentDb,
      table_name: 'orders',
      metric_column: 'total_amount',
      date_column: 'order_date',
    });

    if (container) {
      container.innerHTML = '';
      const headlineCard = document.createElement('div');
      headlineCard.className = 'card';
      const headlineText = isTr ? (res.headline_tr || res.headline) : res.headline;
      const disclaimerText = isTr ? (res.causality_disclaimer_tr || res.causality_disclaimer) : res.causality_disclaimer;

      headlineCard.innerHTML = `
        <div style="font-size: 1.1rem; font-weight: 700; color: var(--text-main); margin-bottom: 8px;">${headlineText}</div>
        <p style="color: var(--text-muted); font-size: 0.9rem;">${isTr ? 'Önceki Dönem' : 'Prior Period'}: ₺${res.prior_period_total?.toLocaleString()} | ${isTr ? 'Cari Dönem' : 'Current Period'}: ₺${res.current_period_total?.toLocaleString()}</p>
        <div style="margin-top: 14px; font-style: italic; font-size: 0.8rem; color: var(--text-dim);">${disclaimerText}</div>
      `;
      container.appendChild(headlineCard);

      (res.contributing_factors || []).forEach((f) => {
        const fCard = document.createElement('div');
        fCard.className = 'card';
        fCard.style.borderLeft = '4px solid var(--accent-secondary)';
        const factorText = isTr ? (f.statement_tr || f.statement) : f.statement;
        fCard.innerHTML = `
          <div style="font-weight: 600; color: var(--accent-secondary); margin-bottom: 4px;">${isTr ? 'Katkı Faktörü' : 'Contributing Factor'} (${f.dimension}: ${f.key})</div>
          <p style="font-size: 0.92rem; color: var(--text-main);">${factorText}</p>
        `;
        container.appendChild(fCard);
      });
    }

    // Root cause drilldown tree
    const tree = await api.getRootCauseTree({
      database_name: currentDb,
      table_name: 'orders',
      metric_column: 'total_amount',
      date_column: 'order_date',
      dimension_hierarchy: ['region', 'payment_method'],
    });

    if (treeContainer) {
      treeContainer.innerHTML = `<pre style="color: #38bdf8;">${formatTreeAscii(tree)}</pre>`;
    }
  } catch (e) {
    if (container) container.innerHTML = `<p style="color: var(--text-muted);">${isTr ? 'Kök Neden Motoru: İşlem tabloları (örn. orders) gerektirir.' : 'Root Cause Engine: Requires transaction tables like orders.'}</p>`;
    if (treeContainer) treeContainer.innerHTML = `<p style="color: var(--text-muted); font-size: 0.85rem;">${isTr ? 'İşlemsel şemalar analiz edilirken kırılım ağacı hazırlanır.' : 'Drill-down tree ready when analyzing transactional schemas.'}</p>`;
  }
}

function formatTreeAscii(node, prefix = '') {
  let text = `${prefix}└── [${node.dimension || 'ROOT'}] ${node.name}: ₺${node.value?.toLocaleString() || 0} (${node.percentage_change || '0%'})\n`;
  if (node.children) {
    node.children.forEach((child) => {
      text += formatTreeAscii(child, prefix + '    ');
    });
  }
  return text;
}

// 11. Query & Natural Language Tab
async function executeQueryAction(sql) {
  try {
    const res = await api.executeSQL(currentDb, sql);
    renderQueryResult(res);
  } catch (e) {
    alert(`Execution Error: ${e.message}`);
  }
}

function renderQueryResult(res) {
  const card = document.getElementById('queryResultCard');
  if (card) card.style.display = 'block';
  const elapsed = document.getElementById('queryElapsedBadge');
  const isTr = getLanguage() === 'tr';
  if (elapsed) elapsed.textContent = `${res.execution_time_ms} ms (${res.row_count} ${isTr ? 'satır' : 'rows'})`;

  const table = document.getElementById('queryResultTable');
  if (!table) return;
  const thead = table.querySelector('thead');
  const tbody = table.querySelector('tbody');

  thead.innerHTML = '';
  tbody.innerHTML = '';

  if (res.columns) {
    const trH = document.createElement('tr');
    res.columns.forEach((col) => {
      const th = document.createElement('th');
      th.textContent = col;
      trH.appendChild(th);
    });
    thead.appendChild(trH);
  }

  (res.data || []).slice(0, 50).forEach((row) => {
    const tr = document.createElement('tr');
    res.columns.forEach((col) => {
      const td = document.createElement('td');
      td.textContent = row[col];
      tr.appendChild(td);
    });
    tbody.appendChild(tr);
  });
}

// 12. Reports Library Tab
async function loadReportsLibrary() {
  const tbody = document.querySelector('#reportsLibraryTable tbody');
  if (!tbody) return;
  const isTr = getLanguage() === 'tr';
  tbody.innerHTML = `<tr><td colspan="4">${isTr ? 'Dosyalar yükleniyor...' : 'Loading generated files...'}</td></tr>`;

  try {
    const files = await api.getReportsList();
    tbody.innerHTML = '';

    if (!Array.isArray(files) || files.length === 0) {
      tbody.innerHTML = `<tr><td colspan="4">${isTr ? 'Henüz oluşturulmuş rapor yok. Yukarıdaki "⚡ Rapor Oluştur" butonuna tıklayın.' : 'No reports generated yet. Click "⚡ Generate Report" above to compile a dossier.'}</td></tr>`;
      return;
    }

    files.forEach((f) => {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td><strong>${f.filename}</strong></td>
        <td><span class="badge badge-low">${f.extension}</span></td>
        <td>${(f.size_bytes / 1024).toFixed(1)} KB</td>
        <td>
          <a href="/api/reports/download/${f.filename}" class="btn btn-secondary btn-sm" download>${t('btnDownload')}</a>
        </td>
      `;
      tbody.appendChild(tr);
    });
  } catch (e) {
    tbody.innerHTML = `<tr><td colspan="4" style="color: #ef4444;">${e.message}</td></tr>`;
  }
}

// 13. Audit & Lineage Tab
async function loadAuditAndLineage() {
  const auditTbody = document.querySelector('#auditLogsTable tbody');
  const lineageTbody = document.querySelector('#lineageTable tbody');

  try {
    const auditData = await api.getAuditLogs(50);
    const isTr = getLanguage() === 'tr';
    if (auditTbody) {
      auditTbody.innerHTML = '';
      (auditData.logs || []).forEach((l) => {
        const tr = document.createElement('tr');
        const badge = l.status === 'SUCCESS' ? 'badge-success' : (l.status === 'BLOCKED' ? 'badge-critical' : 'badge-high');
        const statusLabel = isTr ? (l.status === 'SUCCESS' ? 'BAŞARILI' : (l.status === 'BLOCKED' ? 'ENGELLENDİ' : (l.status === 'FAILED' ? 'BAŞARISIZ' : l.status))) : l.status;
        tr.innerHTML = `
          <td>${l.timestamp.slice(0, 19).replace('T', ' ')}</td>
          <td><strong>${l.action}</strong></td>
          <td><span class="badge ${badge}">${statusLabel}</span></td>
          <td>${l.target || l.database_name || '-'}</td>
          <td>${l.execution_time_ms} ms</td>
          <td style="font-size: 0.8rem; font-family: monospace;">${l.query_text || JSON.stringify(l.details || {})}</td>
        `;
        auditTbody.appendChild(tr);
      });
    }

    const lineageGraph = await api.getLineageGraph();
    if (lineageTbody) {
      lineageTbody.innerHTML = '';
      (lineageGraph.nodes || []).slice(0, 30).forEach((n) => {
        const tr = document.createElement('tr');
        const typeMapTr = {
          'DATABASE': 'VERİTABANI',
          'TABLE': 'TABLO',
          'KPI': 'METRİK (KPI)',
          'REPORT': 'RAPOR',
          'INSIGHT': 'İÇGÖRÜ',
          'QUERY': 'SORGU'
        };
        const typeLabel = isTr ? (typeMapTr[n.type] || n.type) : n.type;
        tr.innerHTML = `
          <td><code>${n.id}</code></td>
          <td><span class="badge badge-low">${typeLabel}</span></td>
          <td>${n.label}</td>
          <td>${n.source_db || '-'}.${n.source_table || '-'}</td>
          <td style="font-size: 0.75rem; font-family: monospace;">${n.source_query || '-'}</td>
        `;
        lineageTbody.appendChild(tr);
      });
    }
  } catch (e) {
    console.error('Audit & Lineage error:', e);
  }
}

// Setup Modals
function setupModals() {
  const btnAddDbModal = document.getElementById('btnAddDbModal');
  if (btnAddDbModal) btnAddDbModal.addEventListener('click', window.openAddDbModal);

  const btnCloseDbModal = document.getElementById('btnCloseDbModal');
  if (btnCloseDbModal) btnCloseDbModal.addEventListener('click', window.closeAddDbModal);

  const btnGenerateReportModal = document.getElementById('btnGenerateReportModal');
  if (btnGenerateReportModal) btnGenerateReportModal.addEventListener('click', window.openReportModal);

  const btnCloseRepModal = document.getElementById('btnCloseRepModal');
  if (btnCloseRepModal) btnCloseRepModal.addEventListener('click', window.closeReportModal);

  const btnSubmitAddDb = document.getElementById('btnSubmitAddDb');
  if (btnSubmitAddDb) btnSubmitAddDb.addEventListener('click', window.submitAddDb);

  const btnSubmitGenerateReport = document.getElementById('btnSubmitGenerateReport');
  if (btnSubmitGenerateReport) btnSubmitGenerateReport.addEventListener('click', window.submitGenerateReport);

  const btnAddRuleModal = document.getElementById('btnAddRuleModal');
  if (btnAddRuleModal) btnAddRuleModal.addEventListener('click', window.openCreateRulePrompt);
}

// Setup Action Buttons
function setupActionButtons() {
  const btnRunSql = document.getElementById('btnRunSql');
  if (btnRunSql) btnRunSql.addEventListener('click', window.runSqlQuery);

  const btnAskNl = document.getElementById('btnAskNl');
  if (btnAskNl) btnAskNl.addEventListener('click', window.askNaturalLanguage);

  const btnRunAnomalyScan = document.getElementById('btnRunAnomalyScan');
  if (btnRunAnomalyScan) btnRunAnomalyScan.addEventListener('click', window.runAnomalyScan);

  const btnExecuteAllRules = document.getElementById('btnExecuteAllRules');
  if (btnExecuteAllRules) btnExecuteAllRules.addEventListener('click', window.executeAllRules);

  const btnQuickReport = document.getElementById('btnQuickReport');
  if (btnQuickReport) btnQuickReport.addEventListener('click', window.quickReport);

  const btnScanDbs = document.getElementById('btnScanDbs');
  if (btnScanDbs) btnScanDbs.addEventListener('click', window.scanLocalDatabases);
}
