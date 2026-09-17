// Internationalization (i18n) Module for Universal Data Intelligence Platform
// Supports Turkish (TR - Default) and English (EN)

export const translations = {
  tr: {
    // Brand
    brandTitle: "Nexuloom",
    brandSubtitle: "Evrensel Veri Zekâsı Platformu",
    engineOnline: "Motor Çevrimiçi",

    // Navigation
    navOverview: "Genel Bakış",
    navDatabases: "Veritabanları",
    navSchema: "Şema & İlişkiler",
    navProfiling: "Veri Profili",
    navQuality: "Veri Kalitesi",
    navKpis: "KPI Motoru",
    navTrends: "Trend Analizi",
    navAnomalies: "Anomali Tespiti",
    navRules: "İş Kuralları",
    navInsights: "Kök Neden & İçgörüler",
    navQuery: "Doğal Dil & Güvenli SQL",
    navReports: "Rapor Oluşturucu",
    navAudit: "Denetim & Soykütüğü",

    // Top Filter Bar
    dbLabel: "Veritabanı:",
    tableLabel: "Tablo:",
    scanDbsBtn: "🔍 Yerel DB'leri Tara",
    scanDbsBtnScanning: "⏳ Taranıyor...",
    quickReportBtn: "⚡ Hızlı Aylık Rapor",
    themeToggleLight: "☀️ Açık Tema",
    themeToggleDark: "🌙 Koyu Tema",
    langName: "Türkçe",

    // Overview Tab
    overviewTitle: "Operasyonel Genel Bakış",
    overviewDesc: "Bağlı veritabanı boru hatları genelinde gerçek zamanlı analitik özet.",
    cardTotalRevenue: "Toplam Gelir",
    cardOrderVolume: "Sipariş Hacmi",
    cardDataQualityScore: "Veri Kalite Skoru",
    cardActiveAnomalies: "Aktif Anomaliler",
    cardConnectedDb: "Bağlı Veritabanı",
    cardIndexedTables: "İndekslenen Tablolar",
    cardTotalRecords: "Toplam Kayıt Sayısı",
    chartRevenueTitle: "Gelir Yörüngesi & Hareketli Ortalama",
    chartTableDistTitle: "Tablo Satır Sayısı Dağılımı",
    chartQualityTitle: "Veri Kalitesi Sağlık Dağılımı",
    badgeTrend: "Trend Analizi",
    badgeAudit: "Denetim",
    badgeDeterministic: "Deterministik Sentez",
    obsTitle: "Otonom Yönetici Gözlemleri",
    obsLoading: "Gerçek zamanlı yönetici gözlemleri yükleniyor...",

    // Databases Tab
    dbTitle: "Veritabanı Bağlantıları",
    dbDesc: "PostgreSQL, MySQL, MSSQL ve SQLite soyutlanmış bağlantılarını yönetin.",
    btnAddConnection: "+ Yeni Bağlantı Ekle",
    colDbName: "Bağlantı Adı",
    colDbType: "Tür",
    colDbTarget: "Veritabanı Hedefi",
    colDbHost: "Host / Port",
    colDbStatus: "Durum",
    colDbLastChecked: "Son Kontrol",
    colDbActions: "İşlemler",
    btnTest: "Test Et",
    btnDelete: "Sil",

    // Schema Tab
    schemaTitle: "Şema Kataloğu & İlişki Çizgesi",
    schemaDesc: "Otomatik keşfedilmiş tablolar, yabancı anahtarlar (FK) ve çıkarımsal ER modelleri.",
    catalogTitle: "Tablo & Sütun Kataloğu",
    relationshipsTitle: "İlişki & Çizge Haritası (ER)",
    colTableName: "Tablo Adı",
    colColumns: "Sütunlar",
    colRows: "Satır Sayısı",
    colPK: "Birincil Anahtarlar (PK)",
    colSource: "Kaynak Sütun",
    colTarget: "Hedef Sütun",
    colRelType: "İlişki Türü",
    colRelDesc: "Açıklama",

    // Profiling Tab
    profilingTitle: "Derin Veri Profili & İstatistikler",
    profilingDesc: "Kuantiller, standart sapma, basıklık, histogramlar ve değer sıklığı analizi.",
    colColName: "Sütun Adı",
    colTypeCat: "Tür Kategorisi",
    colNullPct: "Null Oranı (Sayı)",
    colUnique: "Benzersiz Değerler",
    colMinMax: "Min / Max",
    colMeanMedian: "Ortalama / Medyan",
    colStats: "İstatistikler (Std / IQR)",
    colTopValues: "En Sık Değerler",

    // Quality Tab
    qualityTitle: "Veri Kalitesi & Bütünlük Motoru",
    qualityDesc: "Null kontrolleri, benzersizlik, negatif değerler ve aşırı aykırı değer ceza puanlaması (0-100).",
    cardOverallScore: "Genel Kalite Skoru",
    cardQualityGrade: "Kalite Derecesi",
    cardCriticalIssues: "Kritik İhlaller",
    cardTotalWarnings: "Toplam Uyarılar",
    cardTablesAudited: "Denetlenen Tablolar",
    violationsTitle: "Kural İhlali & Denetim Kayıtları",
    colRuleName: "Kural Adı",
    colSeverity: "Önem Derecesi",
    colPenalty: "Ceza",
    colViolationMsg: "İhlal Detayı",

    // KPI Engine Tab
    kpiTitle: "Metrik & KPI Motoru",
    kpiDesc: "Dinamik formüller, dönemsel büyüme (MoM/YoY) ve hedef karşılaştırma analizleri.",
    kpiCardsTitle: "Tanımlı İş Metrikleri",

    // Trend Tab
    trendsTitle: "Trend & Doğrusal Regresyon Analizi",
    trendsDesc: "Doğrusal eğim, R² katsayısı, hareketli ortalamalar ve ani rejim değişiklikleri.",
    colTrendDirection: "Yön",
    colGrowthPct: "Büyüme %",
    colSlope: "Regresyon Eğimi",
    colR2: "R² Uyum",
    colSuddenShifts: "Ani Değişimler",
    colTrendExpl: "İstatistiksel Açıklama",

    // Anomalies Tab
    anomaliesTitle: "İstatistiksel Anomali Tespiti",
    anomaliesDesc: "Z-Score (>2.5σ), IQR Çiti (>1.5x) ve Isolation Forest algoritmalarıyla kritik sapmalar.",
    labelScanCol: "Taranacak Sütun:",
    labelDetectionMethod: "Tespit Metodu:",
    btnScanAnomalies: "Anomalileri Tara",
    methodAll: "Tüm Yöntemler (Toplu)",
    methodZscore: "Z-Score (>2.5σ)",
    methodIqr: "IQR Çiti (>1.5x)",
    methodForest: "Isolation Forest",
    colEntity: "Kayıt / ID",
    colMetric: "Metrik",
    colObserved: "Gözlenen Değer",
    colNormalRange: "Normal Aralık",
    colDeviation: "Sapma %",
    colMethod: "Yöntem",
    colRationale: "Denetim Gerekçesi",

    // Business Rules Tab
    rulesTitle: "İş Kuralları Motoru",
    rulesDesc: "Özel koşullu mantık kuralları tanımlayın (örn. IF stok < min THEN YÜKSEK) ve denetleyin.",
    btnRunAllRules: "⚡ Tüm Kuralları Çalıştır",
    btnCreateRule: "+ Kural Oluştur",
    colRuleCond: "Koşul İfadesi (SQL)",
    colRuleStatus: "Sonuç",
    colViolCount: "İhlal Sayısı",
    colLastRun: "Son Çalıştırma",

    // Insights Tab
    insightsTitle: "Varyans Ayrıştırma & Kök Neden Analizi",
    insightsDesc: "Çok boyutlu yüzde katkı ayrıştırması ve nedensellik hiyerarşi ağacı.",
    rootCauseTitle: "Hiyerarşik Kök Neden Ayrıştırma Ağacı",

    // Query Tab
    queryTitle: "Doğal Dil & Salt-Okunur Güvenli SQL",
    queryDesc: "Doğal dille analitik soru sorun veya salt-okunur (read-only) güvenli SQL çalıştırın.",
    nlLabel: "Doğal Dille Analitik Soru Sorun (örn: 'Bölgeye göre en çok satan ürünler', 'Aylık gelir trendi')",
    nlPlaceholder: "Analitik sorunuzu doğal dille yazın...",
    btnAskNl: "Doğal Dille Sor",
    sqlLabel: "Veya Doğrudan Salt-Okunur SQL Çalıştırın (INSERT/UPDATE/DELETE kesinlikle engellenir):",
    btnRunSql: "▶ SQL Çalıştır",
    sqlSafetyBadge: "Katı Salt-Okunur Mod Aktif",

    // Reports Tab
    reportsTitle: "Yönetici Raporu Oluşturucu",
    reportsDesc: "PDF, çoklu sayfalı Excel (.xlsx), interaktif HTML, CSV ve JSON formatlarında kurumsal raporlar derleyin.",
    btnGenerateReport: "⚡ Rapor Oluştur",
    reportsLibraryTitle: "Oluşturulan Rapor Dosyaları Kütüphanesi",
    colFilename: "Dosya Adı",
    colFormat: "Format",
    colFileSize: "Boyut",
    btnDownload: "⬇ İndir",

    // Audit Tab
    auditTitle: "Denetim Günlükleri & Veri Soykütüğü",
    auditDesc: "Değiştirilemez güvenlik denetim kayıtları ve geriye dönük veri kaynağı zinciri.",
    auditLogsTitle: "Güvenlik & Eylem Denetim Günlükleri",
    lineageTitle: "Geriye Dönük Veri Soykütüğü Kayıtları (Lineage)",
    colTimestamp: "Zaman Damgası",
    colAction: "Eylem",
    colTarget: "Hedef",
    colExecTime: "Süre",
    colDetails: "Sorgu / Detay",
    colItemId: "Öğe ID",
    colItemLabel: "Etiket",
    colSourceTable: "Kaynak DB / Tablo",
    colSourceQuery: "Kaynak Sorgu",

    // Modals
    modalAddDbTitle: "Yeni Veritabanı Bağla",
    modalDbNameLabel: "Bağlantı Adı",
    modalDbTypeLabel: "Veritabanı Türü",
    modalDbTargetLabel: "Veritabanı Dosya Yolu veya Adı",
    modalDbHostLabel: "Host (SQLite için boş bırakılabilir)",
    modalDbPortLabel: "Port (İsteğe bağlı)",
    modalDbUserLabel: "Kullanıcı Adı (İsteğe bağlı)",
    modalDbPassLabel: "Parola (İsteğe bağlı)",
    btnCancel: "İptal",
    btnSaveConnect: "Bağlan & Kaydet",

    modalReportTitle: "Yönetici Raporu Oluştur",
    modalRepTitleLabel: "Rapor Başlığı",
    modalRepPeriodLabel: "Rapor Dönemi",
    modalRepFormatLabel: "Dışa Aktarma Formatı",
    optAllFormats: "Tüm Formatlar (PDF + Excel + HTML + CSV + JSON)",
    optPdf: "PDF (Yayın & Baskı Formatı)",
    optExcel: "Excel (.xlsx Çoklu Sayfa)",
    optHtml: "HTML (İnteraktif Web)",
    btnGenerateNow: "⚡ Hemen Oluştur",
  },
  en: {
    // Brand
    brandTitle: "Nexuloom",
    brandSubtitle: "Data Intelligence Platform",
    engineOnline: "Engine Online",

    // Navigation
    navOverview: "Overview",
    navDatabases: "Databases",
    navSchema: "Schema & Graph",
    navProfiling: "Data Profiling",
    navQuality: "Data Quality",
    navKpis: "KPI Engine",
    navTrends: "Trend Analysis",
    navAnomalies: "Anomalies",
    navRules: "Business Rules",
    navInsights: "Insights & Root Cause",
    navQuery: "Natural Language & SQL",
    navReports: "Report Builder",
    navAudit: "Audit & Lineage",

    // Top Filter Bar
    dbLabel: "Database:",
    tableLabel: "Table:",
    scanDbsBtn: "🔍 Auto-Scan Local DBs",
    scanDbsBtnScanning: "⏳ Scanning...",
    quickReportBtn: "⚡ Quick Monthly Report",
    themeToggleLight: "☀️ Light Mode",
    themeToggleDark: "🌙 Dark Mode",
    langName: "English",

    // Overview Tab
    overviewTitle: "Operational Overview",
    overviewDesc: "Consolidated real-time intelligence summary across connected database pipelines.",
    cardTotalRevenue: "Total Revenue",
    cardOrderVolume: "Order Volume",
    cardDataQualityScore: "Data Quality Score",
    cardActiveAnomalies: "Active Anomalies",
    cardConnectedDb: "Connected Database",
    cardIndexedTables: "Indexed Tables",
    cardTotalRecords: "Total Records",
    chartRevenueTitle: "Revenue Trajectory & Moving Average",
    chartTableDistTitle: "Table Row Count Distribution",
    chartQualityTitle: "Data Quality Health Distribution",
    badgeTrend: "Trend Analysis",
    badgeAudit: "Audit",
    badgeDeterministic: "Deterministic Synthesis",
    obsTitle: "Autonomous Executive Observations",
    obsLoading: "Loading real-time executive observations...",

    // Databases Tab
    dbTitle: "Database Connections",
    dbDesc: "Manage PostgreSQL, MySQL, MSSQL, and SQLite abstracted connections.",
    btnAddConnection: "+ Add New Connection",
    colDbName: "Connection Name",
    colDbType: "Type",
    colDbTarget: "Database Target",
    colDbHost: "Host / Port",
    colDbStatus: "Status",
    colDbLastChecked: "Last Checked",
    colDbActions: "Actions",
    btnTest: "Test",
    btnDelete: "Delete",

    // Schema Tab
    schemaTitle: "Schema Catalog & Relationship Graph",
    schemaDesc: "Auto-discovered tables, foreign keys, and inferred relational ER models.",
    catalogTitle: "Table & Column Catalog",
    relationshipsTitle: "Relationship & Graph Map (ER)",
    colTableName: "Table Name",
    colColumns: "Columns",
    colRows: "Row Count",
    colPK: "Primary Keys (PK)",
    colSource: "Source Column",
    colTarget: "Target Column",
    colRelType: "Relationship Type",
    colRelDesc: "Description",

    // Profiling Tab
    profilingTitle: "Deep Data Profiling & Statistics",
    profilingDesc: "Quantiles, standard deviations, skewness, distribution histograms, and frequency analysis.",
    colColName: "Column Name",
    colTypeCat: "Type Category",
    colNullPct: "Null Rate (Count)",
    colUnique: "Unique Values",
    colMinMax: "Min / Max",
    colMeanMedian: "Mean / Median",
    colStats: "Statistics (Std / IQR)",
    colTopValues: "Top Frequent Values",

    // Quality Tab
    qualityTitle: "Data Quality & Integrity Engine",
    qualityDesc: "Automated checks for nulls, uniqueness, negative values, and extreme outliers (0-100 score).",
    cardOverallScore: "Overall Quality Score",
    cardQualityGrade: "Quality Grade",
    cardCriticalIssues: "Critical Violations",
    cardTotalWarnings: "Total Warnings",
    cardTablesAudited: "Audited Tables",
    violationsTitle: "Rule Violations & Audit Log",
    colRuleName: "Rule Name",
    colSeverity: "Severity",
    colPenalty: "Penalty",
    colViolationMsg: "Violation Details",

    // KPI Engine Tab
    kpiTitle: "Metric & KPI Engine",
    kpiDesc: "Dynamic formulas, period-over-period growth (MoM/YoY), and target comparisons.",
    kpiCardsTitle: "Configured Business Metrics",

    // Trend Tab
    trendsTitle: "Trend & Linear Regression Analysis",
    trendsDesc: "Linear slope, R² goodness-of-fit, rolling averages, and sudden regime changes.",
    colTrendDirection: "Direction",
    colGrowthPct: "Growth %",
    colSlope: "Regression Slope",
    colR2: "R² Fit",
    colSuddenShifts: "Sudden Shifts",
    colTrendExpl: "Statistical Explanation",

    // Anomalies Tab
    anomaliesTitle: "Statistical Anomaly Detection",
    anomaliesDesc: "Z-Score (>2.5σ), IQR Fences (>1.5x), and Isolation Forest machine learning detection.",
    labelScanCol: "Scan Column:",
    labelDetectionMethod: "Detection Method:",
    btnScanAnomalies: "Scan Anomalies",
    methodAll: "All Methods (Ensemble)",
    methodZscore: "Z-Score (>2.5σ)",
    methodIqr: "IQR Fence (>1.5x)",
    methodForest: "Isolation Forest",
    colEntity: "Record / ID",
    colMetric: "Metric",
    colObserved: "Observed Value",
    colNormalRange: "Normal Range",
    colDeviation: "Deviation %",
    colMethod: "Method",
    colRationale: "Audit Rationale",

    // Business Rules Tab
    rulesTitle: "Business Rule Engine",
    rulesDesc: "Define conditional logic rules (e.g. IF stock < min THEN HIGH) and audit evaluations.",
    btnRunAllRules: "⚡ Run All Rules",
    btnCreateRule: "+ Create Rule",
    colRuleCond: "Condition Expression (SQL)",
    colRuleStatus: "Status",
    colViolCount: "Violations Count",
    colLastRun: "Last Executed",

    // Insights Tab
    insightsTitle: "Variance Attribution & Root Cause",
    insightsDesc: "Multi-dimensional percentage contribution attribution and causality drill-down tree.",
    rootCauseTitle: "Hierarchical Root-Cause Tree",

    // Query Tab
    queryTitle: "Natural Language & Strict Read-Only SQL",
    queryDesc: "Ask analytical questions in natural language or execute safe read-only SQL queries.",
    nlLabel: "Ask a Natural Language Question (e.g. 'Top selling products by region', 'Monthly revenue trend')",
    nlPlaceholder: "Type your analytical question in natural language...",
    btnAskNl: "Ask NL Engine",
    sqlLabel: "Or Execute Direct Read-Only SQL (INSERT/UPDATE/DELETE strictly blocked):",
    btnRunSql: "▶ Execute SQL",
    sqlSafetyBadge: "Strict Read-Only Mode Active",

    // Reports Tab
    reportsTitle: "Executive Report Builder",
    reportsDesc: "Compile multi-engine analysis into corporate PDF, multi-sheet Excel (.xlsx), HTML, CSV, or JSON dossiers.",
    btnGenerateReport: "⚡ Generate Report",
    reportsLibraryTitle: "Generated Report Files Library",
    colFilename: "Filename",
    colFormat: "Format",
    colFileSize: "File Size",
    btnDownload: "⬇ Download",

    // Audit Tab
    auditTitle: "Audit Logs & Data Lineage Graph",
    auditDesc: "Immutable security audit records and backwards data provenance chain.",
    auditLogsTitle: "Security & Action Audit Logs",
    lineageTitle: "Data Lineage & Provenance Records",
    colTimestamp: "Timestamp",
    colAction: "Action",
    colTarget: "Target",
    colExecTime: "Execution Time",
    colDetails: "Query / Details",
    colItemId: "Item ID",
    colItemLabel: "Label",
    colSourceTable: "Source DB / Table",
    colSourceQuery: "Source Query",

    // Modals
    modalAddDbTitle: "Connect New Database",
    modalDbNameLabel: "Connection Name",
    modalDbTypeLabel: "Database Type",
    modalDbTargetLabel: "Database File Path or Name",
    modalDbHostLabel: "Host (Optional for SQLite)",
    modalDbPortLabel: "Port (Optional)",
    modalDbUserLabel: "Username (Optional)",
    modalDbPassLabel: "Password (Optional)",
    btnCancel: "Cancel",
    btnSaveConnect: "Connect & Save",

    modalReportTitle: "Generate Executive Report",
    modalRepTitleLabel: "Report Title",
    modalRepPeriodLabel: "Report Period",
    modalRepFormatLabel: "Export Format",
    optAllFormats: "All Formats (PDF + Excel + HTML + CSV + JSON)",
    optPdf: "PDF (Publication Format)",
    optExcel: "Excel (.xlsx Multi-Sheet)",
    optHtml: "HTML (Interactive Web)",
    btnGenerateNow: "⚡ Generate Now",
  }
};

let currentLang = localStorage.getItem('udi_lang') || 'tr';

export function getLanguage() {
  return currentLang;
}

export function setLanguage(lang) {
  if (lang !== 'tr' && lang !== 'en') lang = 'tr';
  currentLang = lang;
  localStorage.setItem('udi_lang', lang);
  document.documentElement.lang = lang;
  applyTranslations();
  window.dispatchEvent(new CustomEvent('udi:languageChanged', { detail: { lang } }));
}

export function t(key, fallback = '') {
  const dict = translations[currentLang] || translations.tr;
  return dict[key] || translations.en[key] || fallback || key;
}

export function applyTranslations() {
  const dict = translations[currentLang] || translations.tr;

  // Update elements with data-i18n
  document.querySelectorAll('[data-i18n]').forEach((el) => {
    const key = el.getAttribute('data-i18n');
    if (dict[key]) {
      el.textContent = dict[key];
    }
  });

  // Update elements with data-i18n-html
  document.querySelectorAll('[data-i18n-html]').forEach((el) => {
    const key = el.getAttribute('data-i18n-html');
    if (dict[key]) {
      el.innerHTML = dict[key];
    }
  });

  // Update elements with data-i18n-placeholder
  document.querySelectorAll('[data-i18n-placeholder]').forEach((el) => {
    const key = el.getAttribute('data-i18n-placeholder');
    if (dict[key]) {
      el.setAttribute('placeholder', dict[key]);
    }
  });

  // Update elements with data-i18n-title
  document.querySelectorAll('[data-i18n-title]').forEach((el) => {
    const key = el.getAttribute('data-i18n-title');
    if (dict[key]) {
      el.setAttribute('title', dict[key]);
    }
  });

  // Update Language Button indicator
  const flagEl = document.getElementById('langFlag');
  const langTextEl = document.getElementById('langToggleText');
  if (flagEl) flagEl.textContent = currentLang === 'tr' ? '🇹🇷' : '🇬🇧';
  if (langTextEl) langTextEl.textContent = currentLang === 'tr' ? 'Türkçe' : 'English';

  // Update Theme Button text based on current theme and language
  const isLight = document.documentElement.getAttribute('data-theme') === 'light';
  const themeTextEl = document.getElementById('themeToggleText');
  if (themeTextEl) {
    themeTextEl.textContent = isLight 
      ? (currentLang === 'tr' ? 'Açık Tema' : 'Light Mode')
      : (currentLang === 'tr' ? 'Koyu Tema' : 'Dark Mode');
  }
}

export const KPI_TRANSLATIONS = {
  "Total Revenue": { tr: "Toplam Gelir", en: "Total Revenue" },
  "Total Order Volume": { tr: "Toplam Sipariş Hacmi", en: "Total Order Volume" },
  "Average Order Value": { tr: "Ortalama Sipariş Tutarı", en: "Average Order Value" },
  "Total Defect Rate": { tr: "Toplam Hata Oranı", en: "Total Defect Rate" },
  "Total Incurred Expenses": { tr: "Toplam İşletme Giderleri", en: "Total Incurred Expenses" },
};

export const RULE_TRANSLATIONS = {
  "Low Inventory Alert": { tr: "Düşük Stok Seviyesi Uyarısı", en: "Low Inventory Alert" },
  "Critical Machine Overheating": { tr: "Kritik Makine Aşırı Isınması", en: "Critical Machine Overheating" },
  "Abnormal High Batch Scrap": { tr: "Yüksek Parti Fire Oranı Alarmı", en: "Abnormal High Batch Scrap" },
};

export function localizeKpiName(name) {
  if (KPI_TRANSLATIONS[name]) {
    return KPI_TRANSLATIONS[name][currentLang] || name;
  }
  return name;
}

export function localizeRuleName(name) {
  if (RULE_TRANSLATIONS[name]) {
    return RULE_TRANSLATIONS[name][currentLang] || name;
  }
  return name;
}

export function localizeSeverity(sev) {
  if (currentLang === 'tr') {
    const map = {
      'CRITICAL': 'KRİTİK',
      'HIGH': 'YÜKSEK',
      'MEDIUM': 'ORTA',
      'LOW': 'DÜŞÜK'
    };
    return map[(sev || '').toUpperCase()] || sev;
  }
  return (sev || '').toUpperCase();
}

export function localizeTrendDirection(dir) {
  if (currentLang === 'tr') {
    const map = {
      'UPWARD': 'YUKARI YÖNLÜ',
      'DOWNWARD': 'AŞAĞI YÖNLÜ',
      'STABLE': 'DURAĞAN',
      'INSUFFICIENT_DATA': 'YETERSİZ VERİ'
    };
    return map[dir] || dir;
  }
  return dir;
}

export function localizeCategory(cat) {
  if (currentLang === 'tr') {
    const map = {
      'NUMERIC': 'SAYISAL',
      'STRING': 'METİN',
      'DATETIME': 'TARİH / ZAMAN',
      'BOOLEAN': 'MANTIKSAL',
      'OTHER': 'DİĞER'
    };
    return map[cat] || cat;
  }
  return cat;
}
