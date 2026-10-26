from datetime import date, datetime

import pytest
from pydantic import ValidationError

from app import checks, db, ssh
from app.main import CheckRequest


class FakeConn:
    def __init__(self, data: dict[str, list[dict]]):
        self.data = data
        self.inserted: dict[str, list[dict]] = {}
        self.committed = False

    def commit(self):
        self.committed = True


def fake_select(conn, table, where, binds):
    return conn.data.get(table, [])


def fake_insert(conn, table, rows):
    conn.inserted[table] = rows


def test_dated_folders_ignored(monkeypatch):
    out = {"FRAF1": ".\n./CONFIG\n./CONFIG/backup\n./CONFIG/backup/20170101\n./TAP\n", "GBROR": ".\n./CONFIG\n"}
    monkeypatch.setattr(ssh, "run", lambda cmd: out["FRAF1" if "FRAF1" in cmd else "GBROR"])
    assert ssh.missing_dirs("GBROR") == ["./CONFIG/backup", "./TAP"]


def test_ids_from_test_when_missing_in_dev_and_sync(monkeypatch):
    monkeypatch.setattr(db, "select", fake_select)
    monkeypatch.setattr(db, "insert", fake_insert)
    monkeypatch.setattr(db, "virtual_columns", lambda conn, table: [])
    monkeypatch.setattr(db, "unique_number_columns", lambda conn, table: [])
    dev = FakeConn({
        "PRODUCT_CLIENT": [{"CLIENT_TADIG": "GBROR", "ACTIVE_FROM": datetime(2023, 1, 1), "ACTIVE_TO": datetime(2049, 12, 31)}],
        "RAP_PMN_SEQ": [{"PMN": "GBROR"}],
    })
    test = FakeConn({
        "INDUSTRY": [{"PMN": "TURIS", "CURRENCY": "EUR", "IS_ACTIVE": "Y"}],
        "PROCESS_ID_MAP": [{"CLIENT_NAME": "GBROR", "PROCESSID": 88888}],
        "PROCESSMASTER": [{"PROCESSID": 88888}],
    })

    result = checks.table_checks(dev, test, "GBROR", "TURIS", "TI", date(2026, 10, 22))
    by_table = {c.name: c for c in result}
    assert by_table["PRODUCT_CLIENT"].active == 1
    assert by_table["RAP_PMN_SEQ"].active == 1
    assert by_table["PROCESSMASTER"].binds == {"pid": 88888}
    assert by_table["RAP_PMN_SEQ"].binds == {"op": "GBROR", "rp": "TURIS"}
    assert by_table["EXCHANGE_RATE_LIST"].binds["cur"] == "EUR"

    report = checks.sync(dev, test, result)
    assert set(dev.inserted) == {"INDUSTRY", "PROCESS_ID_MAP", "PROCESSMASTER"}
    assert "INDUSTRY (TURIS): 1 row(s) copied" in report
    assert "BILATERAL_AGREEMENT: not found in test, needs manual setup" in report
    assert dev.committed


def test_partner_is_other_tadig_in_filename():
    req = dict(filename="CDTURISGBROR18672", rate_date="2026-10-22")
    assert CheckRequest(**req, direction="TI", operator="GBROR").partner == "TURIS"
    assert CheckRequest(**req, direction="TO", operator="TURIS").partner == "GBROR"
    with pytest.raises(ValidationError):
        CheckRequest(**req, direction="TI", operator="FRAF1")


def test_prepare_drops_virtual_and_renumbers_used_unique(monkeypatch):
    monkeypatch.setattr(db, "virtual_columns", lambda conn, table: ["FILE_PATH"])
    monkeypatch.setattr(db, "unique_number_columns", lambda conn, table: ["SEQNO"])
    monkeypatch.setattr(db, "used_values", lambda conn, table, column, values: ({138}, 1000))
    rows = [{"SEQNO": 138, "FILE_PATH": "x"}, {"SEQNO": 141, "FILE_PATH": "y"}]

    changes = checks.prepare(None, "PROCESS_CONTROL_SYSTEM", rows)

    assert rows == [{"SEQNO": 1001}, {"SEQNO": 141}]
    assert changes == ["SEQNO 138 -> 1001"]
