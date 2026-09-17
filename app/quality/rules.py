from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd


class QualityCheckResult:
    def __init__(
        self,
        rule_id: str,
        rule_name: str,
        table_name: str,
        column_name: Optional[str],
        passed: bool,
        severity: str,  # "LOW", "MEDIUM", "HIGH", "CRITICAL"
        penalty: float,
        message: str,
        violation_count: int = 0,
        violation_percentage: float = 0.0,
        sample_violations: Optional[List[Any]] = None,
        rule_name_tr: Optional[str] = None,
        message_tr: Optional[str] = None,
    ):
        self.rule_id = rule_id
        self.rule_name = rule_name
        self.rule_name_tr = rule_name_tr
        self.table_name = table_name
        self.column_name = column_name
        self.passed = passed
        self.severity = severity
        self.penalty = penalty if not passed else 0.0
        self.message = message
        self.message_tr = message_tr
        self.violation_count = violation_count
        self.violation_percentage = violation_percentage
        self.sample_violations = sample_violations or []

    def to_dict(self) -> Dict[str, Any]:
        sev_tr = {"CRITICAL": "KRİTİK", "HIGH": "YÜKSEK", "MEDIUM": "ORTA", "LOW": "DÜŞÜK"}.get(self.severity, self.severity)
        return {
            "rule_id": self.rule_id,
            "rule_name": self.rule_name,
            "rule_name_tr": self.rule_name_tr or self.rule_name,
            "table_name": self.table_name,
            "column_name": self.column_name,
            "passed": self.passed,
            "severity": self.severity,
            "severity_tr": sev_tr,
            "penalty": round(self.penalty, 2),
            "message": self.message,
            "message_tr": self.message_tr or self.message,
            "violation_count": self.violation_count,
            "violation_percentage": round(self.violation_percentage, 2),
            "sample_violations": self.sample_violations[:5],
        }


class BaseQualityRule(ABC):
    @property
    @abstractmethod
    def rule_id(self) -> str:
        pass

    @property
    @abstractmethod
    def rule_name(self) -> str:
        pass

    @abstractmethod
    def evaluate(self, df: pd.DataFrame, table_name: str, metadata: Dict[str, Any]) -> List[QualityCheckResult]:
        pass


class NullCheckRule(BaseQualityRule):
    rule_id = "QR_NULL_CHECK"
    rule_name = "Null Value Check"

    def evaluate(self, df: pd.DataFrame, table_name: str, metadata: Dict[str, Any]) -> List[QualityCheckResult]:
        results = []
        total_rows = len(df)
        if total_rows == 0:
            return results

        pks = set(metadata.get("primary_keys", []))
        for col in df.columns:
            null_count = int(df[col].isna().sum())
            null_pct = (null_count / total_rows) * 100

            is_pk = col in pks
            threshold = 0.0 if is_pk else 2.0

            if null_count > 0 and null_pct > threshold:
                severity = "CRITICAL" if is_pk else ("HIGH" if null_pct > 20 else "MEDIUM")
                penalty = 15.0 if is_pk else (8.0 if null_pct > 20 else 3.0)
                msg = f"⚠ {null_pct:.1f}% NULL values ({null_count} rows)"
                msg_tr = f"⚠ %{null_pct:.1f} NULL değer ({null_count} satır)"
                if is_pk:
                    msg = f"CRITICAL: Primary key has {null_count} NULL values!"
                    msg_tr = f"KRİTİK: Birincil anahtarda {null_count} adet NULL değer bulundu!"
                results.append(QualityCheckResult(
                    rule_id=self.rule_id,
                    rule_name=self.rule_name,
                    rule_name_tr="Boş Değer Kontrolü",
                    table_name=table_name,
                    column_name=col,
                    passed=False,
                    severity=severity,
                    penalty=penalty,
                    message=msg,
                    message_tr=msg_tr,
                    violation_count=null_count,
                    violation_percentage=null_pct,
                ))
            elif null_count == 0 and is_pk:
                results.append(QualityCheckResult(
                    rule_id=self.rule_id,
                    rule_name=self.rule_name,
                    rule_name_tr="Boş Değer Kontrolü",
                    table_name=table_name,
                    column_name=col,
                    passed=True,
                    severity="LOW",
                    penalty=0.0,
                    message="✓ No NULL values in primary key",
                    message_tr="✓ Birincil anahtarda NULL değer yok",
                ))
        return results


class UniquenessCheckRule(BaseQualityRule):
    rule_id = "QR_UNIQUENESS"
    rule_name = "Uniqueness & Duplicate Check"

    def evaluate(self, df: pd.DataFrame, table_name: str, metadata: Dict[str, Any]) -> List[QualityCheckResult]:
        results = []
        total_rows = len(df)
        if total_rows == 0:
            return results

        pks = metadata.get("primary_keys", [])
        if pks:
            for pk in pks:
                if pk in df.columns:
                    dupes = df[pk].duplicated().sum()
                    if dupes > 0:
                        dupe_pct = (dupes / total_rows) * 100
                        results.append(QualityCheckResult(
                            rule_id=self.rule_id,
                            rule_name=self.rule_name,
                            rule_name_tr="Benzersizlik & Mükerrer Kontrolü",
                            table_name=table_name,
                            column_name=pk,
                            passed=False,
                            severity="CRITICAL",
                            penalty=20.0,
                            message=f"CRITICAL: Primary key has {dupes} duplicate values ({dupe_pct:.1f}%)",
                            message_tr=f"KRİTİK: Birincil anahtarda {dupes} mükerrer değer bulundu (%{dupe_pct:.1f})",
                            violation_count=int(dupes),
                            violation_percentage=dupe_pct,
                        ))
                    else:
                        results.append(QualityCheckResult(
                            rule_id=self.rule_id,
                            rule_name=self.rule_name,
                            rule_name_tr="Benzersizlik & Mükerrer Kontrolü",
                            table_name=table_name,
                            column_name=pk,
                            passed=True,
                            severity="LOW",
                            penalty=0.0,
                            message="✓ No duplicates in primary key",
                            message_tr="✓ Birincil anahtarda mükerrer kayıt yok",
                        ))
        return results


class NonNegativeMetricRule(BaseQualityRule):
    rule_id = "QR_NON_NEGATIVE"
    rule_name = "Positive Metric Range Check"

    # Column names that logically should never be negative
    POSITIVE_KEYWORDS = ("price", "amount", "cost", "quantity", "inventory", "stock", "revenue", "salary")

    def evaluate(self, df: pd.DataFrame, table_name: str, metadata: Dict[str, Any]) -> List[QualityCheckResult]:
        results = []
        total_rows = len(df)
        if total_rows == 0:
            return results

        for col in df.columns:
            col_lower = col.lower()
            if any(k in col_lower for k in self.POSITIVE_KEYWORDS) and pd.api.types.is_numeric_dtype(df[col]):
                series = df[col].dropna()
                negatives = series[series < 0]
                neg_count = len(negatives)
                if neg_count > 0:
                    neg_pct = (neg_count / total_rows) * 100
                    results.append(QualityCheckResult(
                        rule_id=self.rule_id,
                        rule_name=self.rule_name,
                        rule_name_tr="Pozitif Metrik Aralık Kontrolü",
                        table_name=table_name,
                        column_name=col,
                        passed=False,
                        severity="HIGH" if neg_pct > 1.0 else "MEDIUM",
                        penalty=10.0 if neg_pct > 1.0 else 5.0,
                        message=f"⚠ {neg_pct:.1f}% negative values found in positive metric ({neg_count} rows)",
                        message_tr=f"⚠ Pozitif olması gereken sütunda {neg_count} negatif değer bulundu (%{neg_pct:.1f}, {neg_count} satır)",
                        violation_count=neg_count,
                        violation_percentage=neg_pct,
                        sample_violations=list(negatives.head(5)),
                    ))
        return results


class OutlierQualityRule(BaseQualityRule):
    rule_id = "QR_EXTREME_OUTLIERS"
    rule_name = "Extreme Outlier Check"

    def evaluate(self, df: pd.DataFrame, table_name: str, metadata: Dict[str, Any]) -> List[QualityCheckResult]:
        results = []
        total_rows = len(df)
        if total_rows < 10:
            return results

        for col in df.columns:
            if pd.api.types.is_numeric_dtype(df[col]) and not pd.api.types.is_bool_dtype(df[col]):
                s = df[col].dropna()
                if len(s) < 10:
                    continue
                q25 = s.quantile(0.25)
                q75 = s.quantile(0.75)
                iqr = q75 - q25
                if iqr <= 0:
                    continue
                # Extreme outliers: 3 * IQR
                extreme = s[(s < q25 - 3 * iqr) | (s > q75 + 3 * iqr)]
                extreme_count = len(extreme)
                if extreme_count > 0:
                    pct = (extreme_count / total_rows) * 100
                    results.append(QualityCheckResult(
                        rule_id=self.rule_id,
                        rule_name=self.rule_name,
                        rule_name_tr="Aşırı Aykırı Değer Kontrolü",
                        table_name=table_name,
                        column_name=col,
                        passed=False,
                        severity="MEDIUM" if pct < 2.0 else "HIGH",
                        penalty=4.0 if pct < 2.0 else 8.0,
                        message=f"⚠ {extreme_count} extreme outliers detected (>3x IQR)",
                        message_tr=f"⚠ {extreme_count} aşırı aykırı değer tespit edildi (>3x IQR)",
                        violation_count=extreme_count,
                        violation_percentage=pct,
                        sample_violations=[round(float(v), 2) for v in extreme.head(5)],
                    ))
        return results


class DateValidityRule(BaseQualityRule):
    rule_id = "QR_DATE_VALIDITY"
    rule_name = "Date Format and Range Validity"

    def evaluate(self, df: pd.DataFrame, table_name: str, metadata: Dict[str, Any]) -> List[QualityCheckResult]:
        results = []
        total_rows = len(df)
        if total_rows == 0:
            return results

        date_keywords = ("date", "created_at", "updated_at", "timestamp", "birth_date")
        for col in df.columns:
            if any(k in col.lower() for k in date_keywords):
                non_null = df[col].dropna()
                if len(non_null) == 0:
                    continue
                # Test date parsing
                parsed = pd.to_datetime(non_null, errors="coerce")
                invalid_dates = int(parsed.isna().sum())
                if invalid_dates > 0:
                    inv_pct = (invalid_dates / total_rows) * 100
                    results.append(QualityCheckResult(
                        rule_id=self.rule_id,
                        rule_name=self.rule_name,
                        rule_name_tr="Tarih Format ve Geçerlilik Kontrolü",
                        table_name=table_name,
                        column_name=col,
                        passed=False,
                        severity="HIGH",
                        penalty=10.0,
                        message=f"⚠ {invalid_dates} invalid or unparseable dates ({inv_pct:.1f}%)",
                        message_tr=f"⚠ {invalid_dates} geçersiz veya ayrıştırılamayan tarih kaydı ({inv_pct:.1f}%)",
                        violation_count=invalid_dates,
                        violation_percentage=inv_pct,
                    ))
        return results
