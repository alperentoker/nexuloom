from typing import Any, Dict, List, Optional
import numpy as np
from scipy import stats
from app.core.i18n import localize_kpi_name


class TrendAnalyzer:
    """Performs statistical trend detection, regression, moving averages, and sudden change detection."""

    @classmethod
    def analyze_series(
        cls,
        data_points: List[Dict[str, Any]],
        metric_name: str = "Metric",
        unit: str = "",
    ) -> Dict[str, Any]:
        """Analyzes a series of [{"period": "2026-01", "value": 100.0}, ...]."""
        metric_tr = localize_kpi_name(metric_name, "tr")
        if not data_points or len(data_points) < 2:
            return {
                "metric_name": metric_name,
                "metric_name_tr": metric_tr,
                "data_points_count": len(data_points) if data_points else 0,
                "trend_direction": "INSUFFICIENT_DATA",
                "trend_direction_tr": "YETERSİZ VERİ",
                "growth_rate_pct": 0.0,
                "explanation": f"Insufficient historical data points ({len(data_points) if data_points else 0}) to establish a reliable trend for {metric_name}.",
                "explanation_tr": f"{metric_tr} için güvenilir bir trend belirlemek adına yetersiz geçmiş veri noktası ({len(data_points) if data_points else 0}).",
                "moving_average": [],
                "sudden_changes": [],
            }

        periods = [dp.get("period", str(i)) for i, dp in enumerate(data_points)]
        values = np.array([float(dp.get("value", 0.0)) for dp in data_points], dtype=float)
        n = len(values)

        # 1. Total growth rate
        first_val = values[0]
        last_val = values[-1]
        if first_val != 0:
            total_growth_pct = ((last_val - first_val) / abs(first_val)) * 100.0
        else:
            total_growth_pct = 100.0 if last_val > 0 else 0.0

        # 2. Linear Regression Slope
        x_indices = np.arange(n)
        slope, intercept, r_value, p_value, std_err = stats.linregress(x_indices, values)
        r_squared = float(r_value ** 2)

        # Normalized slope relative to mean
        mean_val = float(np.mean(values))
        norm_slope = (slope / abs(mean_val)) if mean_val != 0 else slope

        # Direction threshold (±2% normalized slope per period)
        if norm_slope > 0.02 and p_value < 0.15:
            direction = "UPWARD"
        elif norm_slope < -0.02 and p_value < 0.15:
            direction = "DOWNWARD"
        else:
            direction = "STABLE"

        # 3. Moving Average (window=3)
        window = min(3, n)
        ma_values = []
        for i in range(n):
            if i < window - 1:
                ma_values.append(round(float(np.mean(values[: i + 1])), 2))
            else:
                ma_values.append(round(float(np.mean(values[i - window + 1 : i + 1])), 2))

        ma_series = [{"period": p, "moving_avg": ma} for p, ma in zip(periods, ma_values)]

        # 4. Sudden Change Detection (diffs > 1.6 std or > 25% step change)
        diffs = np.diff(values)
        sudden_changes = []
        if len(diffs) >= 2:
            diff_mean = float(np.mean(diffs))
            diff_std = float(np.std(diffs))
            for i, d in enumerate(diffs):
                z_diff = (abs(d - diff_mean) / diff_std) if diff_std > 0 else 0.0
                rel_change = abs(values[i + 1] - values[i]) / abs(values[i]) if values[i] != 0 else 0.0
                if z_diff >= 1.6 or rel_change >= 0.25:
                    change_pct = ((values[i + 1] - values[i]) / abs(values[i])) * 100 if values[i] != 0 else 0
                    sudden_changes.append({
                        "from_period": periods[i],
                        "to_period": periods[i + 1],
                        "previous_value": round(float(values[i]), 2),
                        "new_value": round(float(values[i + 1]), 2),
                        "change_percentage": round(float(change_pct), 2),
                        "z_score": round(float(z_diff), 2),
                    })

        # 5. Seasonality / Volatility
        volatility_cv = (float(np.std(values)) / abs(mean_val) * 100) if mean_val != 0 else 0.0
        seasonality_present = volatility_cv > 15.0 and len(sudden_changes) > 1

        # 6. Natural Language Explainable Narrative
        sign_str = "increased" if total_growth_pct > 0 else ("decreased" if total_growth_pct < 0 else "remained flat")
        pct_abs = abs(round(total_growth_pct, 1))

        unit_str = f" {unit}" if unit else ""
        narrative = f"{metric_name} {sign_str} {pct_abs}% over the analyzed period (from {round(first_val, 1)}{unit_str} to {round(last_val, 1)}{unit_str}). "

        if direction == "UPWARD":
            narrative += f"The series exhibits a statistically consistent upward trend (R² = {r_squared:.2f}). "
        elif direction == "DOWNWARD":
            narrative += f"The series exhibits a statistically consistent downward trend (R² = {r_squared:.2f}). "
        else:
            narrative += "Overall trajectory remained relatively stable without strong directional momentum. "

        if sudden_changes:
            sc = sudden_changes[0]
            narrative += f"A significant sudden change occurred between {sc['from_period']} and {sc['to_period']} ({sc['change_percentage']:+0.1f}%). "

        # Turkish narrative
        sign_str_tr = "artış gösterdi" if total_growth_pct > 0 else ("azalış gösterdi" if total_growth_pct < 0 else "yatay seyretti")
        narrative_tr = f"{metric_tr}, analiz edilen dönem boyunca %{pct_abs} {sign_str_tr} ({round(first_val, 1)}{unit_str} değerinden {round(last_val, 1)}{unit_str} değerine). "

        if direction == "UPWARD":
            narrative_tr += f"Zaman serisi istatistiksel olarak tutarlı bir yukarı yönlü trend sergilemektedir (R² = {r_squared:.2f}). "
        elif direction == "DOWNWARD":
            narrative_tr += f"Zaman serisi istatistiksel olarak tutarlı bir aşağı yönlü trend sergilemektedir (R² = {r_squared:.2f}). "
        else:
            narrative_tr += "Genel seyir belirgin bir yön momentumu olmaksızın nispeten stabil kalmıştır. "

        if sudden_changes:
            sc = sudden_changes[0]
            narrative_tr += f"{sc['from_period']} ile {sc['to_period']} arasında belirgin bir ani değişim kaydedildi (%{sc['change_percentage']:+0.1f}). "

        dir_map_tr = {
            "UPWARD": "YUKARI YÖNLÜ",
            "DOWNWARD": "AŞAĞI YÖNLÜ",
            "STABLE": "DURAĞAN",
            "INSUFFICIENT_DATA": "YETERSİZ VERİ",
        }

        return {
            "metric_name": metric_name,
            "metric_name_tr": metric_tr,
            "unit": unit,
            "trend_direction": direction,
            "trend_direction_tr": dir_map_tr.get(direction, direction),
            "total_growth_percentage": round(total_growth_pct, 2),
            "linear_slope": round(float(slope), 4),
            "r_squared": round(r_squared, 4),
            "p_value": round(float(p_value), 4),
            "volatility_coefficient_variation": round(volatility_cv, 2),
            "seasonality_detected": seasonality_present,
            "sudden_changes": sudden_changes,
            "moving_average_series": ma_series,
            "explanation": narrative.strip(),
            "explanation_tr": narrative_tr.strip(),
        }
