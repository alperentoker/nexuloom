from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sqlalchemy import text
from sqlalchemy.engine import Engine
from app.core.audit import audit_logger
from app.database.registry import connection_registry


class AnomalyItem:
    def __init__(
        self,
        entity: str,
        metric: str,
        observed_value: float,
        normal_range_min: float,
        normal_range_max: float,
        deviation_pct: float,
        severity: str,
        method: str,
        score: float,
        explanation: str,
        row_id: Optional[Any] = None,
    ):
        self.entity = entity
        self.metric = metric
        self.observed_value = round(observed_value, 2)
        self.normal_range_min = round(normal_range_min, 2)
        self.normal_range_max = round(normal_range_max, 2)
        self.deviation_pct = round(deviation_pct, 2)
        self.severity = severity
        self.method = method
        self.score = round(score, 2)
        self.explanation = explanation
        self.row_id = row_id

    def to_dict(self) -> Dict[str, Any]:
        sign = "+" if self.deviation_pct > 0 else ""
        return {
            "entity": self.entity,
            "metric": self.metric,
            "observed_value": self.observed_value,
            "normal_range": f"{self.normal_range_min} to {self.normal_range_max}",
            "normal_range_min": self.normal_range_min,
            "normal_range_max": self.normal_range_max,
            "deviation_pct": f"{sign}{self.deviation_pct}%",
            "deviation_raw": self.deviation_pct,
            "severity": self.severity,
            "method": self.method,
            "score": self.score,
            "explanation": self.explanation,
            "row_id": self.row_id,
        }


class AnomalyDetector:
    """Multi-method anomaly detection: Z-score, IQR, Rolling Statistics, and Isolation Forest."""

    @classmethod
    def calculate_severity(cls, z_or_factor: float) -> str:
        """Determines severity from deviation factor.
        Low: 2.0 - 2.5
        Medium: 2.5 - 3.2
        High: 3.2 - 4.0
        Critical: >= 4.0
        """
        val = abs(z_or_factor)
        if val >= 4.0:
            return "CRITICAL"
        elif val >= 3.2:
            return "HIGH"
        elif val >= 2.5:
            return "MEDIUM"
        else:
            return "LOW"

    @classmethod
    def detect_zscore(
        cls,
        series: pd.Series,
        metric_name: str,
        entity_series: Optional[pd.Series] = None,
        threshold: float = 2.5,
    ) -> List[AnomalyItem]:
        clean = series.dropna()
        if len(clean) < 10:
            return []

        mean = float(clean.mean())
        std = float(clean.std())
        if std <= 0:
            return []

        anomalies = []
        normal_min = mean - 2.0 * std
        normal_max = mean + 2.0 * std

        for idx, val in clean.items():
            z = (val - mean) / std
            if abs(z) >= threshold:
                dev_pct = ((val - mean) / abs(mean)) * 100 if mean != 0 else 100.0
                sev = cls.calculate_severity(z)
                ent = str(entity_series[idx]) if entity_series is not None and idx in entity_series else f"Row {idx}"
                sign = "+" if dev_pct > 0 else ""
                exp = (
                    f"Observed value {val:.1f} deviates {sign}{dev_pct:.1f}% from mean {mean:.1f} "
                    f"(Z-Score: {z:.2f}, Severity: {sev}). Normal range: [{normal_min:.1f}, {normal_max:.1f}]."
                )
                anomalies.append(
                    AnomalyItem(
                        entity=ent,
                        metric=metric_name,
                        observed_value=float(val),
                        normal_range_min=normal_min,
                        normal_range_max=normal_max,
                        deviation_pct=dev_pct,
                        severity=sev,
                        method="Z-SCORE",
                        score=float(abs(z)),
                        explanation=exp,
                        row_id=idx,
                    )
                )

        return sorted(anomalies, key=lambda x: x.score, reverse=True)

    @classmethod
    def detect_iqr(
        cls,
        series: pd.Series,
        metric_name: str,
        entity_series: Optional[pd.Series] = None,
        iqr_multiplier: float = 1.5,
    ) -> List[AnomalyItem]:
        clean = series.dropna()
        if len(clean) < 10:
            return []

        q25 = float(clean.quantile(0.25))
        q75 = float(clean.quantile(0.75))
        iqr = q75 - q25
        if iqr <= 0:
            return []

        lower_bound = q25 - iqr_multiplier * iqr
        upper_bound = q75 + iqr_multiplier * iqr
        median = float(clean.median())

        anomalies = []
        for idx, val in clean.items():
            if val < lower_bound or val > upper_bound:
                diff = (val - upper_bound) if val > upper_bound else (lower_bound - val)
                iqr_factor = diff / iqr
                severity_metric = 2.0 + iqr_factor  # maps to severity thresholds
                sev = cls.calculate_severity(severity_metric)

                dev_pct = ((val - median) / abs(median)) * 100 if median != 0 else 100.0
                ent = str(entity_series[idx]) if entity_series is not None and idx in entity_series else f"Row {idx}"
                sign = "+" if dev_pct > 0 else ""
                exp = (
                    f"Observed value {val:.1f} lies {sign}{dev_pct:.1f}% outside IQR fence [{lower_bound:.1f}, {upper_bound:.1f}] "
                    f"(Factor: {iqr_factor:.1f}x IQR, Severity: {sev})."
                )
                anomalies.append(
                    AnomalyItem(
                        entity=ent,
                        metric=metric_name,
                        observed_value=float(val),
                        normal_range_min=lower_bound,
                        normal_range_max=upper_bound,
                        deviation_pct=dev_pct,
                        severity=sev,
                        method="IQR",
                        score=float(severity_metric),
                        explanation=exp,
                        row_id=idx,
                    )
                )

        return sorted(anomalies, key=lambda x: x.score, reverse=True)

    @classmethod
    def detect_rolling(
        cls,
        df: pd.DataFrame,
        metric_col: str,
        time_col: str,
        entity_col: Optional[str] = None,
        window: int = 5,
        threshold: float = 2.5,
    ) -> List[AnomalyItem]:
        if len(df) < window + 2 or metric_col not in df.columns:
            return []

        sorted_df = df.dropna(subset=[metric_col]).copy()
        if time_col in sorted_df.columns:
            sorted_df["_dt"] = pd.to_datetime(sorted_df[time_col], errors="coerce")
            sorted_df = sorted_df.sort_values("_dt")

        s = sorted_df[metric_col]
        rolling_mean = s.rolling(window=window, min_periods=window).mean().shift(1)
        rolling_std = s.rolling(window=window, min_periods=window).std().shift(1)

        anomalies = []
        for idx in s.index:
            r_mean = rolling_mean.loc[idx]
            r_std = rolling_std.loc[idx]
            val = s.loc[idx]

            if pd.notna(r_mean) and pd.notna(r_std) and r_std > 0:
                z = (val - r_mean) / r_std
                if abs(z) >= threshold:
                    dev_pct = ((val - r_mean) / abs(r_mean)) * 100 if r_mean != 0 else 100.0
                    sev = cls.calculate_severity(z)
                    ent = str(sorted_df.loc[idx, entity_col]) if entity_col and entity_col in sorted_df.columns else f"Row {idx}"
                    norm_min = r_mean - 2.0 * r_std
                    norm_max = r_mean + 2.0 * r_std
                    exp = (
                        f"Observed value {val:.1f} spiked {dev_pct:+0.1f}% above local moving baseline {r_mean:.1f} "
                        f"(Rolling Z-Score: {z:.2f}, Window: {window}, Severity: {sev})."
                    )
                    anomalies.append(
                        AnomalyItem(
                            entity=ent,
                            metric=metric_col,
                            observed_value=float(val),
                            normal_range_min=norm_min,
                            normal_range_max=norm_max,
                            deviation_pct=dev_pct,
                            severity=sev,
                            method="ROLLING_WINDOW",
                            score=float(abs(z)),
                            explanation=exp,
                            row_id=idx,
                        )
                    )

        return sorted(anomalies, key=lambda x: x.score, reverse=True)

    @classmethod
    def detect_isolation_forest(
        cls,
        df: pd.DataFrame,
        numeric_cols: List[str],
        entity_col: Optional[str] = None,
        contamination: float = 0.03,
    ) -> List[AnomalyItem]:
        valid_cols = [c for c in numeric_cols if c in df.columns and pd.api.types.is_numeric_dtype(df[c])]
        if not valid_cols or len(df) < 20:
            return []

        sub_df = df[valid_cols].dropna()
        if len(sub_df) < 20:
            return []

        model = IsolationForest(contamination=contamination, random_state=42)
        preds = model.fit_predict(sub_df)
        scores = -model.decision_function(sub_df)  # higher means more anomalous

        anomalies = []
        for (idx, pred), score in zip(zip(sub_df.index, preds), scores):
            if pred == -1:  # outlier detected
                primary_col = valid_cols[0]
                val = float(sub_df.loc[idx, primary_col])
                mean_col = float(sub_df[primary_col].mean())
                std_col = float(sub_df[primary_col].std()) if len(sub_df) > 1 else 1.0

                z = (val - mean_col) / std_col if std_col > 0 else 2.5
                sev = "HIGH" if score > 0.15 else "MEDIUM"
                dev_pct = ((val - mean_col) / abs(mean_col)) * 100 if mean_col != 0 else 100.0

                ent = str(df.loc[idx, entity_col]) if entity_col and entity_col in df.columns else f"Row {idx}"
                exp = (
                    f"Multivariate outlier identified by Isolation Forest (Anomaly Score: {score:.3f}, Severity: {sev}). "
                    f"Observed value: {val:.1f} for {primary_col}."
                )
                anomalies.append(
                    AnomalyItem(
                        entity=ent,
                        metric=", ".join(valid_cols),
                        observed_value=val,
                        normal_range_min=mean_col - 2 * std_col,
                        normal_range_max=mean_col + 2 * std_col,
                        deviation_pct=dev_pct,
                        severity=sev,
                        method="ISOLATION_FOREST",
                        score=float(score * 10),
                        explanation=exp,
                        row_id=idx,
                    )
                )

        return sorted(anomalies, key=lambda x: x.score, reverse=True)


class AnomalyEngine:
    def __init__(self, db_name: str, engine: Optional[Engine] = None):
        self.db_name = db_name
        self.engine = engine or connection_registry.get_engine_for(db_name)

    def scan_table(
        self,
        table_name: str,
        metric_col: str,
        entity_col: Optional[str] = None,
        method: str = "ALL",  # "ZSCORE", "IQR", "ROLLING", "ISOLATION_FOREST", "ALL"
        limit: int = 50000,
    ) -> Dict[str, Any]:
        query = f'SELECT * FROM "{table_name}" LIMIT {limit}'
        try:
            with self.engine.connect() as conn:
                df = pd.read_sql(text(query), conn)
        except Exception:
            with self.engine.connect() as conn:
                df = pd.read_sql(text(f"SELECT * FROM {table_name} LIMIT {limit}"), conn)

        if metric_col not in df.columns:
            raise ValueError(f"Column '{metric_col}' not found in table '{table_name}'.")

        ent_series = df[entity_col] if entity_col and entity_col in df.columns else None
        results: List[AnomalyItem] = []

        m_upper = method.upper()
        if m_upper in ("ZSCORE", "ALL"):
            results.extend(AnomalyDetector.detect_zscore(df[metric_col], metric_name=metric_col, entity_series=ent_series))

        if m_upper in ("IQR", "ALL"):
            results.extend(AnomalyDetector.detect_iqr(df[metric_col], metric_name=metric_col, entity_series=ent_series))

        if m_upper in ("ISOLATION_FOREST", "ALL"):
            results.extend(AnomalyDetector.detect_isolation_forest(df, numeric_cols=[metric_col], entity_col=entity_col))

        # Deduplicate results by row_id / entity
        unique_anomalies = []
        seen = set()
        for a in sorted(results, key=lambda x: x.score, reverse=True):
            k = (a.row_id, a.method)
            if k not in seen:
                seen.add(k)
                unique_anomalies.append(a.to_dict())

        sev_counts = {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0}
        for u in unique_anomalies:
            s = u["severity"]
            sev_counts[s] = sev_counts.get(s, 0) + 1

        audit_logger.log(
            action="ANOMALY_DETECTION",
            database_name=self.db_name,
            target=f"{table_name}.{metric_col}",
            details={"anomalies_found": len(unique_anomalies), "critical": sev_counts["CRITICAL"]},
        )

        return {
            "database_name": self.db_name,
            "table_name": table_name,
            "metric": metric_col,
            "total_anomalies": len(unique_anomalies),
            "severity_summary": sev_counts,
            "anomalies": unique_anomalies[:100],  # Top 100 anomalies
        }
