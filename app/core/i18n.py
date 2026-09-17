"""Backend Internationalization (i18n) Module for Nexuloom.
Provides translations and text formatters for Reports (PDF, HTML, Excel, JSON)
and Analytics Engines in both Turkish (TR) and English (EN).
"""

from typing import Any, Dict, Optional

TRANSLATIONS: Dict[str, Dict[str, str]] = {
    "tr": {
        # General & Brand
        "app_title": "Nexuloom Veri Zekâsı Platformu",
        "default_report_title": "Aylık Veri Zekâsı ve Yönetici Raporu",
        "default_period": "Eylül 2026",
        "production_quality": "Üretim Standartı",
        "generated_at": "Oluşturulma Tarihi",
        "report_period": "Rapor Dönemi",
        "database": "Veritabanı",
        "all_formats": "Tüm Formatlar (PDF + Excel + HTML + CSV + JSON)",

        # Report Sections
        "sec_executive_summary": "Yönetici Özeti",
        "sec_kpi_summary": "KPI & Temel Metrikler Özeti",
        "sec_trend_analysis": "Trend & Regresyon Analizi",
        "sec_anomaly_report": "İstatistiksel Anomali Raporu",
        "sec_data_quality": "Veri Kalitesi Sağlık Değerlendirmesi",
        "sec_rule_violations": "İş Kuralı İhlalleri & Alarmlar",
        "sec_root_cause": "Kök Neden & Varyans Ayrıştırması",
        "sec_detailed_tables": "Detaylı Tablolar",
        "sec_recommendations": "Öneriler & Eylem Planı",
        "sec_appendix": "Ek & Veri Soykütüğü",

        # Observations
        "obs_kpi_increased": "{name} metriği önceki döneme göre %{pct} artış gösterdi.",
        "obs_kpi_decreased": "{name} metriği önceki döneme göre %{pct} azalış gösterdi.",
        "obs_quality_issues": "Veri kalitesi {score}/100 olarak puanlandı ve giderilmesi gereken {crit} kritik bütünlük uyarısı tespit edildi.",
        "obs_quality_good": "Genel veritabanı kalitesi {score}/100 seviyesindedir (Derece: {grade}).",
        "obs_anomalies_found": "Telemetri ve işlem metriklerinde {count} kritik istatistiksel anomali tespit edildi.",
        "obs_rules_triggered": "{count} adet operasyonel iş kuralı alarmı tetiklendi.",
        "obs_all_normal": "Tüm temel metrikler, veri kalitesi skorları ve operasyonel kurallar normal parametreler dahilinde çalışmaktadır.",
        "deterministic_assurance": "Tüm KPI'lar, istatistikler, regresyonlar ve kalite metrikleri matematiksel olarak deterministik hesaplanmıştır.",

        # Quality
        "overall_quality_score": "Genel Kalite Skoru",
        "quality_grade": "Kalite Derecesi",
        "critical_violations": "Kritik Bütünlük İhlalleri",
        "total_warnings": "Toplam Uyarılar",
        "tables_analyzed": "Profili Çıkarılan Tablolar",
        "no_violations": "Tüm veri kalitesi kuralları sağlandı! İhlal tespit edilmedi.",

        # Quality Rule Names & Messages
        "rule_null_check": "Null Değer Kontrolü",
        "rule_duplicate_check": "Mükerrer Satır Kontrolü",
        "rule_negative_check": "Negatif Değer Kontrolü",
        "rule_outlier_check": "Aşırı Aykırı Değer Kontrolü",
        "rule_date_check": "Tarih Mantık Kontrolü",
        "msg_null_pk": "KRİTİK: Birincil anahtarda (PK) {count} NULL değer bulundu!",
        "msg_null_col": "⚠ %{pct:.1f} NULL değer ({count} satır)",
        "msg_duplicate": "⚠ {count} tam mükerrer satır tespit edildi (%{pct:.1f})",
        "msg_negative": "⚠ Pozitif olması gereken sütunda {count} negatif değer bulundu (%{pct:.1f})",
        "msg_outlier": "⚠ {count} aşırı sayısal aykırı değer tespit edildi (%{pct:.1f})",
        "msg_date_future": "⚠ {count} mantıksız gelecek veya geçersiz tarih kaydı bulundu (%{pct:.1f})",

        # Severities
        "sev_critical": "KRİTİK",
        "sev_high": "YÜKSEK",
        "sev_medium": "ORTA",
        "sev_low": "DÜŞÜK",

        # Anomalies
        "anom_title": "Tespit Edilen İstatistiksel Anomaliler",
        "anom_empty": "Kritik istatistiksel anomali tespit edilmedi. Tüm metrikler olağan sınırlardadır.",
        "col_entity": "Kayıt / ID",
        "col_metric": "Metrik",
        "col_severity": "Önem Derecesi",
        "col_normal_range": "Normal Aralık",
        "col_observed": "Gözlenen",
        "col_deviation": "Sapma %",
        "col_method": "Yöntem",
        "col_explanation": "İstatistiksel Açıklama",

        # Business Rules
        "rules_title": "Operasyonel İş Kuralı İhlalleri",
        "rules_empty": "Tüm operasyonel kurallar başarıyla sağlandı. Aktif ihlal bulunmuyor.",
        "col_rule_name": "Kural Adı",
        "col_target_table": "Hedef Tablo",
        "col_condition": "Koşul İfadesi",
        "col_violations": "İhlal Sayısı",
        "col_triggered_msg": "Tetiklenen Mesaj",

        # KPIs & Trends
        "kpi_summary_title": "Temel Performans Göstergeleri (KPI'lar)",
        "col_current_value": "Mevcut Değer",
        "col_mom_trend": "Aylık Değişim (MoM)",
        "col_target": "Hedef",
        "col_formula": "Formül",
        "trend_upward": "YUKARI YÖNLÜ",
        "trend_downward": "AŞAĞI YÖNLÜ",
        "trend_stable": "DURAĞAN",
        "trend_insufficient": "YETERSİZ VERİ",

        # Excel Sheets
        "sheet_summary": "Özet",
        "sheet_kpis": "KPIlar",
        "sheet_trends": "Trendler",
        "sheet_anomalies": "Anomaliler",
        "sheet_quality": "Veri Kalitesi",
        "sheet_rules": "İş Kuralları",
        "sheet_raw": "Ham Sonuçlar",

        # Insights
        "insights_title": "Varyans Ayrıştırma & Tanısal İçgörüler",
        "causality_disclaimer": "Katkı faktörleri korelasyonel varyans ayrıştırmasını belirtir; doğrudan tek nedensellik ifade etmez.",
        "footer_note": "Nexuloom Evrensel Veri Zekâsı ve Raporlama Motoru tarafından oluşturulmuştur.",
    },
    "en": {
        # General & Brand
        "app_title": "Nexuloom Data Intelligence Platform",
        "default_report_title": "Monthly Business Intelligence & Executive Report",
        "default_period": "September 2026",
        "production_quality": "Production Quality",
        "generated_at": "Generated At",
        "report_period": "Report Period",
        "database": "Database",
        "all_formats": "All Formats (PDF + Excel + HTML + CSV + JSON)",

        # Report Sections
        "sec_executive_summary": "Executive Summary",
        "sec_kpi_summary": "KPI Summary",
        "sec_trend_analysis": "Trend Analysis",
        "sec_anomaly_report": "Anomaly Report",
        "sec_data_quality": "Data Quality Assessment",
        "sec_rule_violations": "Business Rule Violations",
        "sec_root_cause": "Root Cause Analysis",
        "sec_detailed_tables": "Detailed Tables",
        "sec_recommendations": "Recommendations & Action Items",
        "sec_appendix": "Appendix & Lineage",

        # Observations
        "obs_kpi_increased": "{name} increased {pct}% compared with the previous period.",
        "obs_kpi_decreased": "{name} decreased {pct}% compared with the previous period.",
        "obs_quality_issues": "Data quality scored at {score}/100 with {crit} critical integrity warnings requiring remediation.",
        "obs_quality_good": "Overall database quality stands at {score}/100 (Grade: {grade}).",
        "obs_anomalies_found": "{count} critical statistical anomalies were identified in telemetry and transactional metrics.",
        "obs_rules_triggered": "{count} business rule alerts triggered active operational warnings.",
        "obs_all_normal": "All baseline metrics, data quality scores, and operational rules are operating within normal parameters.",
        "deterministic_assurance": "All KPIs, statistics, regressions, and quality metrics are deterministically computed.",

        # Quality
        "overall_quality_score": "Overall Quality Score",
        "quality_grade": "Quality Grade",
        "critical_violations": "Critical Integrity Checks",
        "total_warnings": "Total Warnings",
        "tables_analyzed": "Tables Profiled",
        "no_violations": "All data quality rules satisfied! No violations detected.",

        # Quality Rule Names & Messages
        "rule_null_check": "Null Value Check",
        "rule_duplicate_check": "Duplicate Row Check",
        "rule_negative_check": "Negative Value Check",
        "rule_outlier_check": "Extreme Outlier Check",
        "rule_date_check": "Date Logic Check",
        "msg_null_pk": "CRITICAL: Primary key has {count} NULL values!",
        "msg_null_col": "⚠ {pct:.1f}% NULL values ({count} rows)",
        "msg_duplicate": "⚠ {count} exact duplicate rows identified ({pct:.1f}%)",
        "msg_negative": "⚠ {count} negative values found in positive-only column ({pct:.1f}%)",
        "msg_outlier": "⚠ {count} extreme numeric outliers identified ({pct:.1f}%)",
        "msg_date_future": "⚠ {count} unreasonable future or invalid dates found ({pct:.1f}%)",

        # Severities
        "sev_critical": "CRITICAL",
        "sev_high": "HIGH",
        "sev_medium": "MEDIUM",
        "sev_low": "LOW",

        # Anomalies
        "anom_title": "Statistical Anomalies Detected",
        "anom_empty": "No critical statistical anomalies detected. All metrics within normal range.",
        "col_entity": "Entity / ID",
        "col_metric": "Metric",
        "col_severity": "Severity",
        "col_normal_range": "Normal Range",
        "col_observed": "Observed",
        "col_deviation": "Deviation %",
        "col_method": "Method",
        "col_explanation": "Statistical Explanation",

        # Business Rules
        "rules_title": "Operational Business Rule Violations",
        "rules_empty": "All operational rules satisfied. No active violations.",
        "col_rule_name": "Rule Name",
        "col_target_table": "Target Table",
        "col_condition": "Condition",
        "col_violations": "Violations Count",
        "col_triggered_msg": "Triggered Message",

        # KPIs & Trends
        "kpi_summary_title": "Key Performance Indicators (KPIs)",
        "col_current_value": "Current Value",
        "col_mom_trend": "MoM Trend",
        "col_target": "Target",
        "col_formula": "Formula",
        "trend_upward": "UPWARD",
        "trend_downward": "DOWNWARD",
        "trend_stable": "STABLE",
        "trend_insufficient": "INSUFFICIENT DATA",

        # Excel Sheets
        "sheet_summary": "Summary",
        "sheet_kpis": "KPIs",
        "sheet_trends": "Trends",
        "sheet_anomalies": "Anomalies",
        "sheet_quality": "Data Quality",
        "sheet_rules": "Business Rules",
        "sheet_raw": "Raw Results",

        # Insights
        "insights_title": "Attribution & Diagnostic Insights",
        "causality_disclaimer": "Contributing factors denote correlational variance attribution; they do not imply sole direct causality.",
        "footer_note": "Generated by Nexuloom Universal Data Intelligence & Reporting Platform.",
    },
}

# Known Standard Mappings
KPI_NAME_TRANSLATIONS = {
    "Total Revenue": {"tr": "Toplam Gelir", "en": "Total Revenue"},
    "Total Order Volume": {"tr": "Toplam Sipariş Hacmi", "en": "Total Order Volume"},
    "Average Order Value": {"tr": "Ortalama Sipariş Tutarı", "en": "Average Order Value"},
    "Total Defect Rate": {"tr": "Toplam Hata Oranı", "en": "Total Defect Rate"},
    "Total Incurred Expenses": {"tr": "Toplam İşletme Giderleri", "en": "Total Incurred Expenses"},
}

BUSINESS_RULE_TRANSLATIONS = {
    "Low Inventory Alert": {
        "name_tr": "Düşük Stok Seviyesi Uyarısı",
        "alert_tr": "Depo ürün miktarı kritik güvenlik stok seviyesinin altına düştü!",
    },
    "Critical Machine Overheating": {
        "name_tr": "Kritik Makine Aşırı Isınması",
        "alert_tr": "Makine çalışma sıcaklığı azami termal eşiği (88°C) aştı!",
    },
    "Abnormal High Batch Scrap": {
        "name_tr": "Yüksek Parti Fire Oranı Alarmı",
        "alert_tr": "Üretim partisi hata oranı %5 kritik sınırını aştı!",
    },
}


def t(key: str, lang: str = "tr", **kwargs) -> str:
    """Returns the localized string for a given key, with optional format arguments."""
    lang_dict = TRANSLATIONS.get(lang, TRANSLATIONS["tr"])
    template = lang_dict.get(key, TRANSLATIONS["en"].get(key, key))
    if kwargs:
        try:
            return template.format(**kwargs)
        except Exception:
            return template
    return template


def localize_kpi_name(name: str, lang: str = "tr") -> str:
    if name in KPI_NAME_TRANSLATIONS:
        return KPI_NAME_TRANSLATIONS[name].get(lang, name)
    return name


def localize_severity(sev: str, lang: str = "tr") -> str:
    if lang == "tr":
        return {
            "CRITICAL": "KRİTİK",
            "HIGH": "YÜKSEK",
            "MEDIUM": "ORTA",
            "LOW": "DÜŞÜK",
        }.get(sev.upper(), sev)
    return sev.upper()


def localize_trend_direction(dir_str: str, lang: str = "tr") -> str:
    if lang == "tr":
        return {
            "UPWARD": "YUKARI YÖNLÜ",
            "DOWNWARD": "AŞAĞI YÖNLÜ",
            "STABLE": "DURAĞAN",
            "INSUFFICIENT_DATA": "YETERSİZ VERİ",
        }.get(dir_str, dir_str)
    return dir_str


def localize_rule(rule_name: str, alert_message: str, lang: str = "tr") -> Dict[str, str]:
    if lang == "tr" and rule_name in BUSINESS_RULE_TRANSLATIONS:
        return {
            "name": BUSINESS_RULE_TRANSLATIONS[rule_name]["name_tr"],
            "alert_message": BUSINESS_RULE_TRANSLATIONS[rule_name]["alert_tr"],
        }
    return {"name": rule_name, "alert_message": alert_message}
