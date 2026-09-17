// API communication client for Universal Data Intelligence Platform
const API_BASE = '/api';

export const api = {
  // Databases
  async getDatabases() {
    const res = await fetch(`${API_BASE}/databases`);
    return res.json();
  },
  async addDatabase(data) {
    const res = await fetch(`${API_BASE}/databases`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!res.ok) throw new Error((await res.json()).detail || 'Failed to add database');
    return res.json();
  },
  async testDatabase(name) {
    const res = await fetch(`${API_BASE}/databases/${encodeURIComponent(name)}/test`, { method: 'POST' });
    return res.json();
  },
  async deleteDatabase(name) {
    const res = await fetch(`${API_BASE}/databases/${encodeURIComponent(name)}`, { method: 'DELETE' });
    return res.json();
  },

  // Discovery
  async getCatalog(dbName, refresh = false) {
    const res = await fetch(`${API_BASE}/discovery/catalog/${encodeURIComponent(dbName)}?refresh=${refresh}`);
    if (!res.ok) throw new Error((await res.json()).detail || 'Failed to load catalog');
    return res.json();
  },
  async getRelationships(dbName) {
    const res = await fetch(`${API_BASE}/discovery/relationships/${encodeURIComponent(dbName)}`);
    return res.json();
  },

  // Profiling
  async getProfile(dbName, tableName, sampleSize = 50000) {
    const res = await fetch(`${API_BASE}/profiling/${encodeURIComponent(dbName)}/${encodeURIComponent(tableName)}?sample_size=${sampleSize}`);
    if (!res.ok) throw new Error((await res.json()).detail || 'Failed to profile table');
    return res.json();
  },

  // Quality
  async getQuality(dbName, tableName = null) {
    const url = tableName 
      ? `${API_BASE}/quality/${encodeURIComponent(dbName)}/${encodeURIComponent(tableName)}`
      : `${API_BASE}/quality/${encodeURIComponent(dbName)}`;
    const res = await fetch(url);
    return res.json();
  },

  // KPIs
  async getKPIs(dbName = null) {
    const url = dbName ? `${API_BASE}/kpis?database_name=${encodeURIComponent(dbName)}` : `${API_BASE}/kpis`;
    const res = await fetch(url);
    return res.json();
  },
  async evaluateKPI(name) {
    const res = await fetch(`${API_BASE}/kpis/${encodeURIComponent(name)}/evaluate`);
    if (!res.ok) throw new Error((await res.json()).detail || 'Failed to evaluate KPI');
    return res.json();
  },
  async addKPI(data) {
    const res = await fetch(`${API_BASE}/kpis`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    return res.json();
  },
  async deleteKPI(name) {
    const res = await fetch(`${API_BASE}/kpis/${encodeURIComponent(name)}`, { method: 'DELETE' });
    return res.json();
  },

  // Trends
  async getKPITrend(name) {
    const res = await fetch(`${API_BASE}/analytics/kpi-trend/${encodeURIComponent(name)}`);
    return res.json();
  },

  // Anomalies
  async getAnomalies(dbName, tableName, metricCol, method = 'ALL') {
    const url = `${API_BASE}/anomalies/${encodeURIComponent(dbName)}/${encodeURIComponent(tableName)}?metric_column=${encodeURIComponent(metricCol)}&method=${method}`;
    const res = await fetch(url);
    if (!res.ok) throw new Error((await res.json()).detail || 'Failed to scan anomalies');
    return res.json();
  },

  // Rules
  async getRules(dbName = null) {
    const url = dbName ? `${API_BASE}/rules?database_name=${encodeURIComponent(dbName)}` : `${API_BASE}/rules`;
    const res = await fetch(url);
    return res.json();
  },
  async createRule(data) {
    const res = await fetch(`${API_BASE}/rules`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!res.ok) throw new Error((await res.json()).detail || 'Failed to create rule');
    return res.json();
  },
  async executeRule(name) {
    const res = await fetch(`${API_BASE}/rules/${encodeURIComponent(name)}/execute`, { method: 'POST' });
    return res.json();
  },
  async toggleRule(name, isActive) {
    const res = await fetch(`${API_BASE}/rules/${encodeURIComponent(name)}/toggle`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ is_active: isActive }),
    });
    return res.json();
  },
  async executeAllRules(dbName = null) {
    const url = dbName ? `${API_BASE}/rules/execute-all?database_name=${encodeURIComponent(dbName)}` : `${API_BASE}/rules/execute-all`;
    const res = await fetch(url, { method: 'POST' });
    return res.json();
  },

  // Insights
  async getVarianceInsights(data) {
    const res = await fetch(`${API_BASE}/insights/variance`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!res.ok) throw new Error((await res.json()).detail || 'Failed to calculate insights');
    return res.json();
  },
  async getRootCauseTree(data) {
    const res = await fetch(`${API_BASE}/insights/root-cause-tree`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    return res.json();
  },

  // Reports
  async generateReport(data) {
    const res = await fetch(`${API_BASE}/reports/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!res.ok) throw new Error((await res.json()).detail || 'Failed to generate report');
    return res.json();
  },
  async getReportsList() {
    const res = await fetch(`${API_BASE}/reports/list`);
    return res.json();
  },

  // Query & NL
  async executeSQL(dbName, sql) {
    const res = await fetch(`${API_BASE}/query/execute`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ database_name: dbName, sql }),
    });
    if (!res.ok) throw new Error((await res.json()).detail || 'SQL Query execution failed');
    return res.json();
  },

  // Audit & Lineage
  async getAuditLogs(limit = 100) {
    const res = await fetch(`${API_BASE}/audit/logs?limit=${limit}`);
    return res.json();
  },
  async getLineageGraph() {
    const res = await fetch(`${API_BASE}/audit/lineage/graph`);
    return res.json();
  },

  // Scheduler Automation
  async getScheduledJobs() {
    const res = await fetch(`${API_BASE}/scheduler/jobs`);
    return res.json();
  },
  async createScheduledJob(data) {
    const res = await fetch(`${API_BASE}/scheduler/jobs`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!res.ok) throw new Error((await res.json()).detail || 'Failed to create job');
    return res.json();
  },
  async runJobNow(jobId) {
    const res = await fetch(`${API_BASE}/scheduler/jobs/${encodeURIComponent(jobId)}/run`, { method: 'POST' });
    if (!res.ok) throw new Error((await res.json()).detail || 'Failed to trigger job');
    return res.json();
  },
  async toggleJob(jobId) {
    const res = await fetch(`${API_BASE}/scheduler/jobs/${encodeURIComponent(jobId)}/toggle`, { method: 'POST' });
    if (!res.ok) throw new Error((await res.json()).detail || 'Failed to toggle job');
    return res.json();
  },
  async deleteScheduledJob(jobId) {
    const res = await fetch(`${API_BASE}/scheduler/jobs/${encodeURIComponent(jobId)}`, { method: 'DELETE' });
    return res.json();
  },
  async getSchedulerHistory(limit = 50) {
    const res = await fetch(`${API_BASE}/scheduler/history?limit=${limit}`);
    return res.json();
  },

  // Drift Tracking
  async takeDriftSnapshot(dbName, tableName = null) {
    const res = await fetch(`${API_BASE}/drift/snapshot`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ database_name: dbName, table_name: tableName }),
    });
    if (!res.ok) throw new Error((await res.json()).detail || 'Failed to record drift snapshot');
    return res.json();
  },
  async getSchemaDrift(dbName) {
    const res = await fetch(`${API_BASE}/drift/schema/${encodeURIComponent(dbName)}`);
    if (!res.ok) throw new Error((await res.json()).detail || 'Failed to get schema drift');
    return res.json();
  },
  async getDataDrift(dbName, table = null) {
    const url = table ? `${API_BASE}/drift/data/${encodeURIComponent(dbName)}?table=${encodeURIComponent(table)}` : `${API_BASE}/drift/data/${encodeURIComponent(dbName)}`;
    const res = await fetch(url);
    if (!res.ok) throw new Error((await res.json()).detail || 'Failed to get data drift');
    return res.json();
  },

  // Custom BI Dashboards & Widgets
  async getDashboards() {
    const res = await fetch(`${API_BASE}/dashboards`);
    return res.json();
  },
  async getDashboard(id) {
    const res = await fetch(`${API_BASE}/dashboards/${encodeURIComponent(id)}`);
    if (!res.ok) throw new Error((await res.json()).detail || 'Failed to load dashboard');
    return res.json();
  },
  async createDashboard(data) {
    const res = await fetch(`${API_BASE}/dashboards`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    return res.json();
  },
  async addWidget(dashboardId, data) {
    const res = await fetch(`${API_BASE}/dashboards/${encodeURIComponent(dashboardId)}/widgets`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!res.ok) throw new Error((await res.json()).detail || 'Failed to add widget');
    return res.json();
  },
  async updateWidget(dashboardId, widgetId, data) {
    const res = await fetch(`${API_BASE}/dashboards/${encodeURIComponent(dashboardId)}/widgets/${encodeURIComponent(widgetId)}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!res.ok) throw new Error((await res.json()).detail || 'Failed to update widget');
    return res.json();
  },
  async deleteWidget(dashboardId, widgetId) {
    const res = await fetch(`${API_BASE}/dashboards/${encodeURIComponent(dashboardId)}/widgets/${encodeURIComponent(widgetId)}`, {
      method: 'DELETE',
    });
    return res.json();
  },
  async getWidgetData(dashboardId, widgetId) {
    const res = await fetch(`${API_BASE}/dashboards/${encodeURIComponent(dashboardId)}/widgets/${encodeURIComponent(widgetId)}/data`);
    if (!res.ok) throw new Error((await res.json()).detail || 'Failed to fetch widget data');
    return res.json();
  },
  async previewWidget(data) {
    const res = await fetch(`${API_BASE}/dashboards/preview-widget`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!res.ok) throw new Error((await res.json()).detail || 'Failed to preview widget query');
    return res.json();
  },
};
