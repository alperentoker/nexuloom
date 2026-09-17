#!/usr/bin/env python3
import json
import sys
from pathlib import Path
from typing import Optional

# Ensure project directory is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

import click
import uvicorn
from app.core.config import settings
from app.database.registry import connection_registry
from app.discovery.schema import SchemaDiscoverer
from app.profiling.profiler import DataProfiler
from app.quality.engine import DataQualityEngine
from app.metrics.kpi_engine import kpi_engine
from app.analytics.trends import TrendAnalyzer
from app.anomaly.detector import AnomalyEngine
from app.rules.rule_engine import business_rule_engine
from app.insights.insight_engine import InsightEngine
from app.reports.builder import ReportBuilder
from app.reports.html_exporter import HTMLExporter
from app.reports.pdf_exporter import PDFExporter
from app.reports.excel_exporter import ExcelExporter
from app.database.connection import db_manager
from scripts.seed_demo_db import generate_synthetic_enterprise_db


@click.group()
def cli():
    """Nexuloom Data Intelligence Platform CLI."""
    pass


@cli.command()
def health():
    """Checks the platform health, directory state, and components."""
    click.secho(f"=== {settings.APP_NAME} ===", fg="cyan", bold=True)
    click.echo(f"Version:      {settings.APP_VERSION}")
    click.echo(f"Data Dir:     {settings.UDI_DATA_DIR.resolve()}")
    click.echo(f"Reports Dir:  {settings.UDI_REPORTS_DIR.resolve()}")
    click.echo(f"LLM Enabled:  {settings.UDI_LLM_ENABLED}")

    # Check connection count
    conns = connection_registry.list_connections()
    click.echo(f"Databases:    {len(conns)} registered")
    click.secho("Status:       OPERATIONAL", fg="green", bold=True)


@cli.command()
def seed():
    """Generates deterministic synthetic enterprise demo database (11 tables)."""
    click.secho("Generating enterprise demo database...", fg="yellow")
    p = generate_synthetic_enterprise_db()
    click.secho(f"Success! Database created and registered at: {p}", fg="green", bold=True)


@cli.command()
def databases():
    """Lists all registered databases and their online statuses."""
    conns = connection_registry.list_connections()
    if not conns:
        click.echo("No databases registered yet. Run 'udi seed' to create the demo database.")
        return

    click.secho(f"{'NAME':<20} {'TYPE':<12} {'DATABASE':<30} {'STATUS':<10}", bold=True)
    click.echo("-" * 75)
    for c in conns:
        status = c.get("last_test_status") or "UNTESTED"
        color = "green" if status == "ONLINE" else ("yellow" if status == "UNTESTED" else "red")
        db_disp = str(c.get("database_name", ""))
        if len(db_disp) > 28:
            db_disp = "..." + db_disp[-25:]
        click.echo(f"{c['name']:<20} {c['db_type']:<12} {db_disp:<30} ", nl=False)
        click.secho(f"{status:<10}", fg=color)


@cli.command()
@click.option("--name", prompt=True, help="Connection identifier name")
@click.option("--type", "db_type", type=click.Choice(["sqlite", "postgresql", "mysql", "mssql"]), prompt=True)
@click.option("--database", prompt=True, help="Database name or file path")
@click.option("--host", default=None, help="Database host")
@click.option("--port", default=None, type=int, help="Port")
@click.option("--username", default=None, help="Database username")
@click.password_option(required=False, help="Database password")
def connect(name, db_type, database, host, port, username, password):
    """Registers and tests a new database connection."""
    click.echo(f"Registering database connection '{name}'...")
    res = connection_registry.add_connection(
        name=name,
        db_type=db_type,
        database_name=database,
        host=host,
        port=port,
        username=username,
        password=password,
    )
    test_res = connection_registry.test_and_update_status(name)
    if test_res.get("success"):
        click.secho(f"✓ Connection '{name}' registered and verified successfully!", fg="green", bold=True)
    else:
        click.secho(f"⚠ Connection saved, but test failed: {test_res.get('message')}", fg="yellow")


@cli.command()
@click.option("--database", required=True, help="Database name")
@click.option("--table", default=None, help="Specific table to inspect")
def inspect(database, table):
    """Discovers schema catalog or table columns and constraints."""
    discoverer = SchemaDiscoverer(database)
    if table:
        t_info = discoverer.inspect_table(table)
        click.secho(f"=== Table: {table} (Rows: {t_info.get('row_count'):,}) ===", fg="cyan", bold=True)
        click.secho(f"{'COLUMN':<25} {'TYPE':<18} {'NULLABLE':<10} {'PK':<6} {'KEY'}", bold=True)
        click.echo("-" * 75)
        for c in t_info.get("columns", []):
            fk_str = f"FK -> {c['foreign_key']['referred_table']}.{c['foreign_key']['referred_column']}" if c.get("foreign_key") else ""
            click.echo(f"{c['name']:<25} {c['type']:<18} {str(c['nullable']):<10} {str(c['primary_key']):<6} {fk_str}")
    else:
        catalog = discoverer.discover_catalog()
        click.secho(f"=== Database Schema: {database} ===", fg="cyan", bold=True)
        click.echo(f"Total Tables: {catalog.get('table_count')} | Total Records: {catalog.get('total_rows'):,}\n")
        click.secho(f"{'TABLE NAME':<30} {'COLUMNS':<10} {'ROW COUNT':<15}", bold=True)
        click.echo("-" * 60)
        for t in catalog.get("tables", []):
            click.echo(f"{t['name']:<30} {t.get('column_count', 0):<10} {t.get('row_count', 0):<15,}")


@cli.command()
@click.option("--database", required=True, help="Database name")
@click.option("--table", required=True, help="Table name")
@click.option("--samples", default=50000, help="Max sample rows")
def profile(database, table, samples):
    """Runs deep statistical profiling on a table and its columns."""
    click.echo(f"Profiling {database}.{table} (samples: {samples:,})...")
    profiler = DataProfiler(database)
    res = profiler.profile_table(table, sample_size=samples)

    click.secho(f"\n=== Profile Summary: {table} (Sampled: {res.get('sampled_rows'):,}/{res.get('total_rows'):,}) ===", fg="cyan", bold=True)
    click.secho(f"{'COLUMN':<22} {'TYPE':<10} {'NULL %':<8} {'UNIQUE':<8} {'STATS / FREQUENT VALUES'}", bold=True)
    click.echo("-" * 85)

    for col_name, c_prof in res.get("columns", {}).items():
        cat = c_prof.get("type_category", "STRING")
        null_p = f"{c_prof.get('null_percentage', 0):.1f}%"
        uniq = str(c_prof.get("unique_count", 0))

        detail = ""
        if cat == "NUMERIC":
            detail = f"min={c_prof.get('min')}, max={c_prof.get('max')}, mean={c_prof.get('mean')}, std={c_prof.get('std_dev')}"
        elif cat == "DATETIME":
            detail = f"range=[{c_prof.get('min_date', '')[:10]} to {c_prof.get('max_date', '')[:10]}]"
        else:
            top_vals = [f"{v['value']} ({v['count']})" for v in c_prof.get("most_frequent_values", [])[:2]]
            detail = f"top: {', '.join(top_vals)}" if top_vals else f"avg_len={c_prof.get('average_length', 0)}"

        click.echo(f"{col_name:<22} {cat:<10} {null_p:<8} {uniq:<8} {detail}")


@cli.command()
@click.option("--database", required=True, help="Database name")
@click.option("--table", default=None, help="Optional table name")
def quality(database, table):
    """Evaluates data quality rules and scores."""
    dq = DataQualityEngine(database)
    if table:
        res = dq.evaluate_table(table)
        click.secho(f"=== Quality Report: {table} ===", fg="cyan", bold=True)
        click.echo(f"Score: {res['quality_score']}/100 ({res['quality_grade']}) - {res['scoring_explanation']}")
        click.echo(f"Checks: {res['total_checks']} | Violations: {res['violations_count']}")
        for v in res.get("violations", []):
            color = "red" if v["severity"] == "CRITICAL" else ("yellow" if v["severity"] == "HIGH" else "cyan")
            click.secho(f"  [{v['severity']}] {v['rule_name']} on '{v['column_name']}': {v['message']}", fg=color)
    else:
        res = dq.evaluate_database()
        click.secho(f"=== Database Quality Health: {database} ===", fg="cyan", bold=True)
        click.echo(f"Overall Score: {res['overall_quality_score']}/100 ({res['overall_grade']})")
        click.echo(f"Tables Profiled: {res['tables_analyzed']} | Total Violations: {res['total_violations']} (Critical: {res['critical_violations']})")


@cli.command()
@click.argument("action", type=click.Choice(["list", "evaluate"]))
@click.option("--name", default=None, help="KPI Name")
@click.option("--database", default=None, help="Database name")
def kpi(action, name, database):
    """Manages and evaluates business KPIs."""
    if action == "list":
        kpis = kpi_engine.list_kpis(database)
        click.secho(f"{'KPI NAME':<25} {'DATABASE':<18} {'TABLE':<16} {'FORMULA'}", bold=True)
        click.echo("-" * 80)
        for k in kpis:
            click.echo(f"{k['name']:<25} {k['database_name']:<18} {k['table_name']:<16} {k['formula']}")
    elif action == "evaluate":
        if not name:
            click.echo("Please provide --name <kpi_name> to evaluate.")
            return
        res = kpi_engine.evaluate_kpi(name)
        click.secho(f"=== KPI: {name} ===", fg="cyan", bold=True)
        curr = f"{res.get('unit', '')}{res.get('current_value', 0):,}"
        click.echo(f"Current Value:       {curr}")
        if res.get("growth_rate_mom_pct") is not None:
            sign = "+" if res['growth_rate_mom_pct'] > 0 else ""
            click.echo(f"MoM Growth:          {sign}{res['growth_rate_mom_pct']}%")
        if res.get("target_value") is not None:
            click.echo(f"Target:              {res.get('unit', '')}{res.get('target_value'):,} ({res.get('target_achievement_pct')}%)")


@cli.command()
@click.option("--database", required=True, help="Database name")
@click.option("--table", required=True, help="Table name")
@click.option("--metric", required=True, help="Metric column to scan")
def anomalies(database, table, metric):
    """Scans a metric column for statistical anomalies."""
    eng = AnomalyEngine(database)
    click.echo(f"Scanning {database}.{table}.{metric} for anomalies...")
    res = eng.scan_table(table, metric_col=metric)

    click.secho(f"\n=== Anomalies Detected: {res['total_anomalies']} ===", fg="cyan", bold=True)
    click.echo(f"Severity Breakdown: {res['severity_summary']}\n")

    click.secho(f"{'ENTITY':<15} {'SEVERITY':<10} {'OBSERVED':<10} {'NORMAL RANGE':<18} {'DEV %':<10} {'METHOD'}", bold=True)
    click.echo("-" * 80)
    for a in res.get("anomalies", [])[:15]:
        sev = a["severity"]
        color = "red" if sev == "CRITICAL" else ("yellow" if sev == "HIGH" else "cyan")
        click.echo(f"{str(a['entity']):<15} ", nl=False)
        click.secho(f"{sev:<10}", fg=color, nl=False)
        click.echo(f"{str(a['observed_value']):<10} {a['normal_range']:<18} {a['deviation_pct']:<10} {a['method']}")


@cli.command()
@click.argument("action", type=click.Choice(["list", "run"]))
@click.option("--database", default=None, help="Database name")
@click.option("--name", default=None, help="Rule name for run action")
def rules(action, database, name):
    """Manages and executes business rules."""
    if action == "list":
        all_rules = business_rule_engine.list_rules(database)
        click.secho(f"{'RULE NAME':<25} {'TABLE':<16} {'SEVERITY':<10} {'CONDITION'}", bold=True)
        click.echo("-" * 75)
        for r in all_rules:
            click.echo(f"{r['name']:<25} {r['table_name']:<16} {r['severity']:<10} {r['condition_sql']}")
    elif action == "run":
        if name:
            res = business_rule_engine.execute_rule(name)
            click.secho(f"=== Rule Execution: {name} ===", fg="cyan", bold=True)
            click.echo(f"Status: {res['status']} | Violations: {res['violation_count']} rows")
            click.echo(f"Alert: {res['alert_message']}")
        else:
            runs = business_rule_engine.execute_all_rules(database)
            for r in runs:
                status_color = "red" if r.get("status") == "VIOLATION" else "green"
                click.secho(f"[{r.get('status')}] {r.get('rule_name')}: {r.get('violation_count', 0)} violations", fg=status_color)


@cli.command()
@click.argument("report_type", default="monthly")
@click.option("--database", required=True, help="Database name")
@click.option("--format", "export_fmt", default="ALL", type=click.Choice(["ALL", "PDF", "HTML", "EXCEL", "CSV", "JSON"], case_sensitive=False))
def report(report_type, database, export_fmt):
    """Generates an executive intelligence report (PDF, HTML, Excel)."""
    click.echo(f"Compiling {report_type} intelligence report for '{database}'...")
    title = f"{report_type.capitalize()} Business Intelligence & Reporting Analysis"

    builder = ReportBuilder(database)
    data = builder.build_report_data(title=title, period="September 2026")

    fmt = export_fmt.upper()
    generated = []

    if fmt in ("HTML", "ALL"):
        p = HTMLExporter.export(data)
        generated.append(str(p))
    if fmt in ("PDF", "ALL"):
        p = PDFExporter.export(data)
        generated.append(str(p))
    if fmt in ("EXCEL", "ALL"):
        p = ExcelExporter.export(data)
        generated.append(str(p))

    click.secho("\n✓ Report Generation Completed Successfully!", fg="green", bold=True)
    for g in generated:
        click.echo(f"  → File: {g}")


@cli.command()
@click.option("--database", required=True, help="Database name")
@click.option("--sql", required=True, help="Direct safe read-only SQL query")
def query(database, sql):
    """Executes safe read-only SQL query."""

    engine = connection_registry.get_engine_for(database)
    df = db_manager.execute_read_only_df(engine, sql_query=sql, max_rows=50)
    click.echo(f"\nReturned {len(df)} rows:")
    click.echo(df.to_string(index=False))


@cli.command()
@click.option("--host", default="0.0.0.0", help="Host address")
@click.option("--port", default=8001, type=int, help="Port to run server on")
def dashboard(host, port):
    """Launches the web dashboard and FastAPI server."""
    import socket
    actual_port = port
    for p in range(port, port + 50):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind((host, p))
                actual_port = p
                break
            except OSError:
                continue

    if actual_port != port:
        click.secho(f"⚠️ Port {port} is busy. Switched to available port {actual_port}.", fg="yellow")

    click.secho(f"Launching Nexuloom Data Intelligence Dashboard on http://localhost:{actual_port}...", fg="green", bold=True)
    uvicorn.run("app.main:app", host=host, port=actual_port, reload=False)


if __name__ == "__main__":
    cli()
