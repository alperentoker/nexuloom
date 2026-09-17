import pytest
from app.profiling.profiler import DataProfiler


def test_profiling_numeric_and_dates():
    profiler = DataProfiler("demo_enterprise")
    res = profiler.profile_table("orders", sample_size=5000)

    assert res["table_name"] == "orders"
    assert res["sampled_rows"] == 5000
    assert "total_amount" in res["columns"]

    # Numeric stats on total_amount
    amt_prof = res["columns"]["total_amount"]
    assert amt_prof["type_category"] == "NUMERIC"
    assert amt_prof["min"] > 0
    assert amt_prof["mean"] > 0
    assert amt_prof["std_dev"] > 0
    assert "p50" in amt_prof["quantiles"]
    assert len(amt_prof["distribution_histogram"]) == 10

    # Date stats on order_date
    date_prof = res["columns"]["order_date"]
    assert date_prof["type_category"] == "DATETIME"
    assert date_prof["min_date"] is not None
    assert date_prof["max_date"] is not None
    assert len(date_prof["monthly_distribution"]) > 0


def test_profiling_strings():
    profiler = DataProfiler("demo_enterprise")
    res = profiler.profile_table("customers", sample_size=1000)

    name_prof = res["columns"]["name"]
    assert name_prof["type_category"] == "STRING"
    assert name_prof["average_length"] > 0
    assert name_prof["unique_count"] > 0
