import os
import sys
from pathlib import Path

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import random
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Optional
import numpy as np

from app.core.config import settings
from app.database.registry import connection_registry
from app.metrics.kpi_engine import kpi_engine
from app.rules.rule_engine import business_rule_engine


def generate_synthetic_enterprise_db(
    db_path: Optional[Path] = None,
    order_count: int = 25000,
    production_batches: int = 15000,
) -> Path:
    """Generates a realistic, correlated, deterministic enterprise SQLite database."""
    random.seed(42)
    np.random.seed(42)

    target_path = db_path or (settings.UDI_DATA_DIR / "demo_enterprise.db")
    target_path.parent.mkdir(parents=True, exist_ok=True)

    if target_path.exists():
        try:
            target_path.unlink()
        except Exception:
            pass

    conn = sqlite3.connect(str(target_path))
    cursor = conn.cursor()

    print(f"Creating 11 relational schema tables at: {target_path}")

    # 1. Companies
    cursor.execute("""
        CREATE TABLE companies (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            industry TEXT NOT NULL,
            country TEXT NOT NULL,
            currency TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    # 2. Employees
    cursor.execute("""
        CREATE TABLE employees (
            id INTEGER PRIMARY KEY,
            company_id INTEGER NOT NULL,
            full_name TEXT NOT NULL,
            department TEXT NOT NULL,
            role TEXT NOT NULL,
            salary REAL NOT NULL,
            hire_date TEXT NOT NULL,
            performance_score REAL NOT NULL,
            FOREIGN KEY (company_id) REFERENCES companies(id)
        )
    """)

    # 3. Customers
    cursor.execute("""
        CREATE TABLE customers (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT,
            region TEXT NOT NULL,
            customer_tier TEXT NOT NULL,
            credit_limit REAL NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    # 4. Products
    cursor.execute("""
        CREATE TABLE products (
            id INTEGER PRIMARY KEY,
            sku TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            unit_cost REAL NOT NULL,
            unit_price REAL NOT NULL,
            is_active INTEGER DEFAULT 1,
            created_at TEXT NOT NULL
        )
    """)

    # 5. Orders
    cursor.execute("""
        CREATE TABLE orders (
            id INTEGER PRIMARY KEY,
            customer_id INTEGER NOT NULL,
            order_date TEXT NOT NULL,
            region TEXT NOT NULL,
            order_status TEXT NOT NULL,
            total_amount REAL NOT NULL,
            payment_method TEXT NOT NULL,
            FOREIGN KEY (customer_id) REFERENCES customers(id)
        )
    """)

    # 6. Order Items
    cursor.execute("""
        CREATE TABLE order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            unit_price REAL NOT NULL,
            subtotal REAL NOT NULL,
            FOREIGN KEY (order_id) REFERENCES orders(id),
            FOREIGN KEY (product_id) REFERENCES products(id)
        )
    """)

    # 7. Machines
    cursor.execute("""
        CREATE TABLE machines (
            id TEXT PRIMARY KEY,
            model TEXT NOT NULL,
            facility_line TEXT NOT NULL,
            installation_date TEXT NOT NULL,
            status TEXT NOT NULL
        )
    """)

    # 8. Production
    cursor.execute("""
        CREATE TABLE production (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            batch_code TEXT NOT NULL,
            machine_id TEXT NOT NULL,
            production_date TEXT NOT NULL,
            produced_units INTEGER NOT NULL,
            defect_units INTEGER NOT NULL,
            defect_rate REAL NOT NULL,
            operating_temp_c REAL NOT NULL,
            FOREIGN KEY (machine_id) REFERENCES machines(id)
        )
    """)

    # 9. Maintenance
    cursor.execute("""
        CREATE TABLE maintenance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            machine_id TEXT NOT NULL,
            log_date TEXT NOT NULL,
            maintenance_type TEXT NOT NULL,
            downtime_hours REAL NOT NULL,
            cost REAL NOT NULL,
            notes TEXT,
            FOREIGN KEY (machine_id) REFERENCES machines(id)
        )
    """)

    # 10. Inventory
    cursor.execute("""
        CREATE TABLE inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            warehouse_code TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            minimum_stock INTEGER NOT NULL,
            reorder_point INTEGER NOT NULL,
            last_audited_at TEXT NOT NULL,
            FOREIGN KEY (product_id) REFERENCES products(id)
        )
    """)

    # 11. Expenses
    cursor.execute("""
        CREATE TABLE expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            expense_category TEXT NOT NULL,
            department TEXT NOT NULL,
            amount REAL NOT NULL,
            expense_date TEXT NOT NULL,
            vendor TEXT NOT NULL
        )
    """)

    # Indexes
    cursor.execute("CREATE INDEX idx_orders_customer ON orders(customer_id)")
    cursor.execute("CREATE INDEX idx_orders_date ON orders(order_date)")
    cursor.execute("CREATE INDEX idx_order_items_order ON order_items(order_id)")
    cursor.execute("CREATE INDEX idx_prod_machine ON production(machine_id)")
    cursor.execute("CREATE INDEX idx_inventory_prod ON inventory(product_id)")

    conn.commit()
    print("Populating companies, employees, customers, and products...")

    # Seed Companies
    companies_data = [
        (1, "Apex Industrial Corp", "Manufacturing", "Turkey", "TRY", "2020-01-15"),
        (2, "Vanguard Technologies", "Software & Analytics", "Germany", "EUR", "2021-03-20"),
        (3, "Pacific Logistics Global", "Supply Chain", "United States", "USD", "2019-11-01"),
    ]
    cursor.executemany("INSERT INTO companies VALUES (?, ?, ?, ?, ?, ?)", companies_data)

    # Seed Employees (120 employees)
    departments = ["Engineering", "Operations", "Sales", "Finance", "Quality Assurance", "Logistics"]
    roles = ["Associate", "Specialist", "Senior Specialist", "Team Lead", "Manager", "Director"]
    first_names = ["Ahmet", "Mehmet", "Ayşe", "Fatma", "Can", "Zeynep", "Emre", "Burak", "Selin", "Deniz", "Elena", "Marcus", "Sarah", "David"]
    last_names = ["Yılmaz", "Kaya", "Demir", "Çelik", "Şahin", "Yıldız", "Öztürk", "Aydın", "Özdemir", "Arslan", "Schmidt", "Weber", "Smith", "Johnson"]

    employees_data = []
    base_hire = datetime(2021, 1, 1)
    for emp_id in range(1, 151):
        c_id = random.choice([1, 2, 3])
        dept = random.choice(departments)
        role = random.choice(roles)
        fn = random.choice(first_names)
        ln = random.choice(last_names)
        salary = round(float(np.random.normal(65000, 15000)), 2)
        salary = max(35000.0, salary)
        hire_dt = (base_hire + timedelta(days=random.randint(0, 1800))).strftime("%Y-%m-%d")
        perf = round(float(np.clip(np.random.normal(82, 8), 50, 100)), 1)
        employees_data.append((emp_id, c_id, f"{fn} {ln}", dept, role, salary, hire_dt, perf))
    cursor.executemany("INSERT INTO employees VALUES (?, ?, ?, ?, ?, ?, ?, ?)", employees_data)

    # Seed Customers (1,200 customers with 3.5% intentional NULL emails for data quality check)
    regions = ["Region A", "Region B", "Region C", "Region D", "International"]
    tiers = ["Bronze", "Silver", "Gold", "Enterprise"]
    customers_data = []
    for cid in range(1, 1201):
        name = f"{random.choice(first_names)} {random.choice(last_names)} #{cid}"
        # 3.5% null emails to trigger quality engine warning
        email = None if random.random() < 0.035 else f"customer{cid}@example.com"
        reg = random.choice(regions)
        tier = random.choice(tiers)
        credit = float(random.choice([10000, 25000, 50000, 100000, 250000]))
        reg_dt = (datetime(2023, 1, 1) + timedelta(days=random.randint(0, 1000))).strftime("%Y-%m-%d")
        customers_data.append((cid, name, email, reg, tier, credit, reg_dt))
    cursor.executemany("INSERT INTO customers VALUES (?, ?, ?, ?, ?, ?, ?)", customers_data)

    # Seed Products (150 products with deliberate extreme outlier price on item 142)
    categories = ["Machinery Parts", "Electronics", "Chemicals", "Packaging", "Raw Metals", "Tooling"]
    products_data = []
    for pid in range(1, 151):
        sku = f"SKU-{pid:05d}"
        cat = random.choice(categories)
        pname = f"{cat} Model-{pid}"
        cost = round(float(np.random.uniform(20.0, 450.0)), 2)
        price = round(cost * float(np.random.uniform(1.3, 2.2)), 2)
        # Outlier price on product 142 to trigger Anomaly Engine and Quality Check
        if pid == 142:
            price = 48500.0  # extreme outlier
        products_data.append((pid, sku, pname, cat, cost, price, 1, "2023-01-10"))
    cursor.executemany("INSERT INTO products VALUES (?, ?, ?, ?, ?, ?, ?, ?)", products_data)

    # Seed Machines (25 machines; Machine M-17 will have high temperature anomalies)
    machines_data = []
    for m_idx in range(1, 26):
        mid = f"M-{m_idx:03d}" if m_idx != 17 else "M-102"
        model = f"RoboMill-X{random.randint(100, 900)}"
        line = f"Line-{'Alpha' if m_idx <= 8 else ('Beta' if m_idx <= 16 else 'Gamma')}"
        inst_dt = (datetime(2022, 1, 1) + timedelta(days=m_idx * 40)).strftime("%Y-%m-%d")
        m_status = "OPERATIONAL"
        machines_data.append((mid, model, line, inst_dt, m_status))
    cursor.executemany("INSERT INTO machines VALUES (?, ?, ?, ?, ?)", machines_data)

    conn.commit()
    print("Generating orders and order items across 2025-2026...")

    # Seed Orders & Order Items
    # Seasonality: 2025-01 to 2026-09
    start_date = datetime(2025, 1, 1)
    orders_data = []
    order_items_data = []

    statuses = ["COMPLETED", "COMPLETED", "COMPLETED", "SHIPPED", "PROCESSING", "CANCELLED"]
    pay_methods = ["CREDIT_CARD", "WIRE_TRANSFER", "NET_30", "NET_60"]

    product_prices = {p[0]: p[5] for p in products_data}

    for oid in range(1, order_count + 1):
        # Generate date across 21 months (Jan 2025 - Sep 2026)
        day_offset = random.randint(0, 620)
        odt = start_date + timedelta(days=day_offset, hours=random.randint(8, 18), minutes=random.randint(0, 59))
        date_str = odt.strftime("%Y-%m-%d %H:%M:%S")

        cid = random.randint(1, 1200)
        reg = random.choice(regions)

        # Deliberate anomaly for Insight Engine:
        # In August - September 2026, Region B sales drop significantly!
        is_late_2026 = odt.year == 2026 and odt.month in (8, 9)
        if is_late_2026 and reg == "Region B" and random.random() < 0.65:
            # Skip or switch to reflect major decline
            reg = "Region A"

        status = random.choice(statuses)
        pay_method = random.choice(pay_methods)

        # Generate 1-4 items per order
        num_items = random.randint(1, 4)
        order_total = 0.0
        for _ in range(num_items):
            pid = random.randint(1, 150)
            unit_p = product_prices[pid]
            qty = random.randint(1, 12)
            subtot = round(unit_p * qty, 2)
            order_total += subtot
            order_items_data.append((oid, pid, qty, unit_p, subtot))

        orders_data.append((oid, cid, date_str, reg, status, round(order_total, 2), pay_method))

    cursor.executemany("INSERT INTO orders VALUES (?, ?, ?, ?, ?, ?, ?)", orders_data)
    cursor.executemany("INSERT INTO order_items (order_id, product_id, quantity, unit_price, subtotal) VALUES (?, ?, ?, ?, ?)", order_items_data)
    conn.commit()

    print("Generating production batches and sensor telemetry...")

    # Seed Production Telemetry
    # Machine M-102 (or M-017) has extreme temperature spikes up to 94°C (normal: 65-78°C)
    production_data = []
    for b_idx in range(1, production_batches + 1):
        b_code = f"BATCH-{b_idx:06d}"
        mach = random.choice([m[0] for m in machines_data])
        p_day_offset = random.randint(0, 620)
        p_dt = (start_date + timedelta(days=p_day_offset)).strftime("%Y-%m-%d")

        units = random.randint(250, 1800)

        # Defect rate logic
        is_elevated_defect = mach in ("M-102", "M-008") and p_day_offset > 500
        if is_elevated_defect:
            defects = int(units * random.uniform(0.045, 0.085))
        else:
            defects = int(units * random.uniform(0.005, 0.025))

        defect_rate = round(float(defects / units), 4)

        # Temperature logic
        if mach == "M-102" and random.random() < 0.08:
            # Temperature anomaly! 91°C - 96°C
            temp = round(float(np.random.uniform(91.0, 96.5)), 1)
        else:
            # Normal range 68°C - 78°C
            temp = round(float(np.random.normal(72.5, 2.5)), 1)

        production_data.append((b_code, mach, p_dt, units, defects, defect_rate, temp))

    cursor.executemany(
        "INSERT INTO production (batch_code, machine_id, production_date, produced_units, defect_units, defect_rate, operating_temp_c) VALUES (?, ?, ?, ?, ?, ?, ?)",
        production_data,
    )
    conn.commit()

    # Seed Maintenance
    maintenance_types = ["PREVENTIVE", "CALIBRATION", "EMERGENCY_REPAIR", "INSPECTION"]
    maint_data = []
    for m_log in range(1, 400):
        mach = random.choice([m[0] for m in machines_data])
        m_dt = (start_date + timedelta(days=random.randint(0, 620))).strftime("%Y-%m-%d")
        m_type = "EMERGENCY_REPAIR" if mach == "M-102" and random.random() < 0.4 else random.choice(maintenance_types)
        down_hrs = round(float(np.random.uniform(1.0, 16.0)), 1)
        cost = round(float(down_hrs * np.random.uniform(120.0, 350.0)), 2)
        note = f"Routine service for {mach}" if m_type != "EMERGENCY_REPAIR" else f"Emergency cooling fan replacement on {mach}"
        maint_data.append((mach, m_dt, m_type, down_hrs, cost, note))

    cursor.executemany(
        "INSERT INTO maintenance (machine_id, log_date, maintenance_type, downtime_hours, cost, notes) VALUES (?, ?, ?, ?, ?, ?)",
        maint_data,
    )

    # Seed Inventory (with 7 items below minimum_stock to trigger Business Rule!)
    inv_data = []
    for pid in range(1, 151):
        wh = random.choice(["WH-CENTRAL", "WH-NORTH", "WH-EAST"])
        min_stk = random.choice([50, 100, 150, 200])
        # 7 items specifically below minimum stock
        if pid in (12, 27, 44, 68, 89, 115, 134):
            qty = random.randint(4, min_stk - 15)  # CRITICAL LOW STOCK
        else:
            qty = random.randint(min_stk + 20, min_stk + 400)
        reorder = int(min_stk * 1.5)
        audited = (datetime(2026, 9, 1) - timedelta(days=random.randint(1, 45))).strftime("%Y-%m-%d")
        inv_data.append((pid, wh, qty, min_stk, reorder, audited))

    cursor.executemany(
        "INSERT INTO inventory (product_id, warehouse_code, quantity, minimum_stock, reorder_point, last_audited_at) VALUES (?, ?, ?, ?, ?, ?)",
        inv_data,
    )

    # Seed Expenses
    expense_cats = ["Logistics & Freight", "R&D", "Marketing & Advertising", "Facility Utilities", "Cloud & IT", "Packaging Materials"]
    exp_data = []
    for exp_id in range(1, 1500):
        cat = random.choice(expense_cats)
        dept = random.choice(departments)
        amt = round(float(np.random.exponential(4500.0) + 200.0), 2)
        e_dt = (start_date + timedelta(days=random.randint(0, 620))).strftime("%Y-%m-%d")
        vendor = f"Vendor Partner #{random.randint(10, 99)}"
        exp_data.append((cat, dept, amt, e_dt, vendor))

    cursor.executemany(
        "INSERT INTO expenses (expense_category, department, amount, expense_date, vendor) VALUES (?, ?, ?, ?, ?)",
        exp_data,
    )

    conn.commit()
    conn.close()

    print("Synthetic database generated successfully.")

    # 12. Register Connection in Registry
    print("Registering connection 'demo_enterprise' in system registry...")
    connection_registry.add_connection(
        name="demo_enterprise",
        db_type="sqlite",
        database_name=str(target_path),
    )
    connection_registry.test_and_update_status("demo_enterprise")

    # 13. Register Standard KPIs
    print("Registering demo business KPIs...")
    kpi_engine.add_kpi(
        name="Total Revenue",
        description="Total Gross Invoiced Revenue across all fulfilled and completed orders",
        database_name="demo_enterprise",
        table_name="orders",
        formula="SUM(total_amount)",
        date_column="order_date",
        target_value=12500000.0,
        unit="₺",
        higher_is_better=True,
    )
    kpi_engine.add_kpi(
        name="Total Order Volume",
        description="Total count of customer orders processed",
        database_name="demo_enterprise",
        table_name="orders",
        formula="COUNT(id)",
        date_column="order_date",
        target_value=30000.0,
        unit="",
        higher_is_better=True,
    )
    kpi_engine.add_kpi(
        name="Average Order Value",
        description="Average monetary value per processed order",
        database_name="demo_enterprise",
        table_name="orders",
        formula="SUM(total_amount) / COUNT(id)",
        date_column="order_date",
        target_value=500.0,
        unit="₺",
        higher_is_better=True,
    )
    kpi_engine.add_kpi(
        name="Total Defect Rate",
        description="Average ratio of defective units across manufacturing batches",
        database_name="demo_enterprise",
        table_name="production",
        formula="AVG(defect_rate)",
        date_column="production_date",
        target_value=0.015,
        unit="%",
        higher_is_better=False,
    )

    # 14. Register Business Rules
    print("Registering demo business rules...")
    business_rule_engine.create_rule(
        name="Low Inventory Alert",
        database_name="demo_enterprise",
        table_name="inventory",
        condition_sql="quantity < minimum_stock",
        severity="HIGH",
        alert_message="Warehouse item quantity has dropped below safety minimum stock level!",
    )
    business_rule_engine.create_rule(
        name="Critical Machine Overheating",
        database_name="demo_enterprise",
        table_name="production",
        condition_sql="operating_temp_c >= 88.0",
        severity="CRITICAL",
        alert_message="Machine operating temperature has exceeded maximum thermal threshold (88°C)!",
    )
    business_rule_engine.create_rule(
        name="Abnormal High Batch Scrap",
        database_name="demo_enterprise",
        table_name="production",
        condition_sql="defect_rate >= 0.05",
        severity="HIGH",
        alert_message="Manufacturing defect rate exceeded 5% threshold on production run!",
    )

    print(f"Setup complete! Database is live at {target_path}")
    return target_path


if __name__ == "__main__":
    generate_synthetic_enterprise_db()
