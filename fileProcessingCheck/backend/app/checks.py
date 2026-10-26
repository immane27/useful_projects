from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime

import oracledb

from app import db


@dataclass
class TableCheck:
    name: str
    table: str
    where: str
    binds: dict
    rows: list[dict]  # matching rows in dev
    active: int  # rows passing the table's active rule
    shared: bool  # rows are used by other operators too


def in_range(start: str, end: str) -> Callable[[dict], bool]:
    now = datetime.now()
    return lambda r: r[start] <= now <= (r[end] or now)


def table_checks(
    dev: oracledb.Connection, test: oracledb.Connection, operator: str, partner: str, direction: str, rate_date: date
) -> list[TableCheck]:
    """Configuration checks from docs/PLAN.md, in sync order. Ids that depend on a missing dev row are taken from test."""
    checks = []

    def add(
        table: str, where: str, binds: dict, active: Callable[[dict], bool] = lambda r: True, name: str = "", shared: bool = False
    ) -> TableCheck:
        rows = db.select(dev, table, where, binds)
        check = TableCheck(name or table, table, where, binds, rows, sum(map(active, rows)), shared)
        checks.append(check)
        return check

    def value(check: TableCheck, column: str) -> object:
        rows = check.rows or db.select(test, check.table, check.where, check.binds)
        return rows[0][column] if rows else None

    op = {"op": operator}
    pair = {"op": operator, "rp": partner}
    industry_active = lambda r: r["IS_ACTIVE"] == "Y"
    add("PRODUCT_CLIENT", "client_tadig = :op", op, in_range("ACTIVE_FROM", "ACTIVE_TO"))
    add("BILATERAL_AGREEMENT", "client_operator = :op and roaming_operator = :rp", pair, in_range("AG_STARTDATE", "AG_ENDDATE"))
    add("INDUSTRY", "pmn = :op", op, industry_active, f"INDUSTRY ({operator})")
    industry = add("INDUSTRY", "pmn = :op", {"op": partner}, industry_active, f"INDUSTRY ({partner})", shared=True)
    add("RAP_PMN_SEQ", "pmn = :op and homepmn = :rp", pair)
    process_map = add("PROCESS_ID_MAP", "client_name = :op and roaming_partner = :rp and file_direction = :dir", {**pair, "dir": direction})

    add("PROCESS_CONTROL_SYSTEM", "client_operator = :op and file_direction = :dir", {**op, "dir": direction}, lambda r: r["IS_ACTIVE"] == 1)

    process_id = value(process_map, "PROCESSID")
    add("PROCESSMASTER", "processid = :pid", {"pid": process_id}, lambda r: r["IS_ACTIVE"] == 1, shared=True)

    currency = value(industry, "CURRENCY")
    add(
        "EXCHANGE_RATE_LIST",
        "base_currency = :cur and target_currency in ('SDR', 'XDR') and trunc(effective_date) = :rate_date",
        {"cur": currency, "rate_date": rate_date},
        shared=True,
    )
    return checks


def prepare(dev: oracledb.Connection, table: str, rows: list[dict]) -> list[str]:
    """Drop virtual columns and move unique numbers already used in dev to the next free value."""
    for column in db.virtual_columns(dev, table):
        for row in rows:
            row.pop(column, None)
    changes = []
    for column in db.unique_number_columns(dev, table):
        used, top = db.used_values(dev, table, column, [r[column] for r in rows])
        top = max([top] + [r[column] for r in rows])
        for row in rows:
            if row[column] in used:
                top += 1
                changes.append(f"{column} {row[column]} -> {top}")
                row[column] = top
    return changes


def sync(dev: oracledb.Connection, test: oracledb.Connection, checks: list[TableCheck]) -> list[str]:
    """Copy rows of every missing check from test into dev in one transaction. Inactive rows are left for manual review."""
    report = []
    for check in checks:
        if check.rows:
            continue
        rows = db.select(test, check.table, check.where, check.binds)
        if rows:
            changes = prepare(dev, check.table, rows)
            db.insert(dev, check.table, rows)
            report.append(f"{check.name}: {len(rows)} row(s) copied" + "".join(f" ({c})" for c in changes))
        else:
            report.append(f"{check.name}: not found in test, needs manual setup")
    dev.commit()
    return report
