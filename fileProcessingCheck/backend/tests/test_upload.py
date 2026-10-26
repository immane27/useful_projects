from contextlib import nullcontext

from fastapi.testclient import TestClient

from app import db, main, ssh

client = TestClient(main.app)


def test_upload_uses_configured_extension_and_folder(monkeypatch):
    sent = {}
    monkeypatch.setattr(db, "connect", lambda env: nullcontext())
    monkeypatch.setattr(db, "select", lambda conn, table, where, binds: [{"FILE_EXT": "GO"}])
    monkeypatch.setattr(ssh, "upload", lambda data, folder, name: sent.update(folder=folder, name=name, data=data.read()))

    res = client.post("/api/upload", files={"file": ("CDTURISGBROR18672.tmp", b"tap")}, data={"direction": "TI", "operator": "GBROR"})

    assert res.status_code == 200
    assert sent == {"folder": "/u01/ngcplus/DCH/DATA/GBROR/TAP/ForClient", "name": "CDTURISGBROR18672.GO", "data": b"tap"}


def test_upload_with_given_extension_skips_database(monkeypatch):
    sent = {}
    monkeypatch.setattr(db, "connect", lambda env: (_ for _ in ()).throw(AssertionError("database used")))
    monkeypatch.setattr(ssh, "upload", lambda data, folder, name: sent.update(folder=folder, name=name))

    res = client.post("/api/upload", files={"file": ("CDTURISGBROR18672", b"")}, data={"direction": "TO", "operator": "TURIS", "ext": "GO"})

    assert res.status_code == 200
    assert sent == {"folder": "/u01/ngcplus/DCH/DATA/TURIS/TAP/FromClient", "name": "CDTURISGBROR18672.GO"}


def test_check_directory_only_skips_database(monkeypatch):
    monkeypatch.setattr(ssh, "missing_dirs", lambda operator: [])
    monkeypatch.setattr(db, "connect", lambda env: (_ for _ in ()).throw(AssertionError("database used")))

    body = {"filename": "CDTURISGBROR18672", "direction": "TI", "operator": "GBROR", "rate_date": "2026-10-22", "dir_only": True}
    res = client.post("/api/check", json=body)

    assert [i["status"] for i in res.json()["items"]] == ["ok"]


def test_upload_rejects_unsafe_name(monkeypatch):
    monkeypatch.setattr(ssh, "upload", lambda *a: None)
    res = client.post("/api/upload", files={"file": ("CDTURISGBROR/x", b"")}, data={"direction": "TI", "operator": "GBROR"})
    assert res.status_code == 422
    assert "pattern" in res.json()["detail"]
