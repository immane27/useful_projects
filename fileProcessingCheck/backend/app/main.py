from datetime import date
from typing import Annotated, Literal

from fastapi import FastAPI, Form, Request, UploadFile
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, ValidationError, model_validator

from app import checks, db, ssh
from app.config import get_settings

app = FastAPI(title="File Processing Check")


class CheckRequest(BaseModel):
    filename: str = Field(pattern=r"^CD[A-Z0-9]{10}[A-Z0-9]*$")
    direction: Literal["TI", "TO"]
    operator: str = Field(pattern=r"^[A-Z0-9]{5}$")
    rate_date: date
    dir_only: bool = False  # skip database checks

    @model_validator(mode="after")
    def operator_in_filename(self) -> "CheckRequest":
        if self.operator not in (self.filename[2:7], self.filename[7:12]):
            raise ValueError(f"{self.operator} is not one of the TADIGs in {self.filename}")
        return self

    @property
    def partner(self) -> str:
        """The other TADIG in the filename (CD + sender + recipient + sequence)."""
        sender, recipient = self.filename[2:7], self.filename[7:12]
        return recipient if self.operator == sender else sender


class DeleteRequest(CheckRequest):
    name: str


@app.exception_handler(ValidationError)
def invalid_input(request: Request, exc: ValidationError) -> JSONResponse:
    return JSONResponse({"detail": "; ".join(e["msg"] for e in exc.errors())}, status_code=422)


@app.exception_handler(Exception)
def show_error(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse({"detail": str(exc)}, status_code=500)


def table_checks(req: CheckRequest, dev, test) -> list[checks.TableCheck]:
    return checks.table_checks(dev, test, req.operator, req.partner, req.direction, req.rate_date)


@app.post("/api/check")
def check(req: CheckRequest) -> dict:
    missing = ssh.missing_dirs(req.operator)
    items = [
        {
            "kind": "directory",
            "name": f"Directory {req.operator}",
            "status": "missing" if missing else "ok",
            "detail": f"{len(missing)} folder(s) missing vs {get_settings().ref_operator}" if missing else "Matches " + get_settings().ref_operator,
        }
    ]
    if req.dir_only:
        return {"items": items}
    with db.connect("dev") as dev, db.connect("test") as test:
        for c in table_checks(req, dev, test):
            status = "ok" if c.active else "inactive" if c.rows else "missing"
            detail = f"{len(c.rows)} row(s), {c.active} active" if c.rows else "0 rows"
            items.append({"kind": "table", "name": c.name, "status": status, "detail": detail, "rows": len(c.rows), "shared": c.shared})
    return {"items": items}


@app.post("/api/fix/directory")
def fix_directory(req: CheckRequest) -> dict:
    missing = ssh.missing_dirs(req.operator)
    if missing:
        ssh.create_dirs(req.operator, missing)
    return {"message": f"Created {len(missing)} folder(s) for {req.operator}"}


@app.post("/api/fix/sync")
def fix_sync(req: CheckRequest) -> dict:
    with db.connect("dev") as dev, db.connect("test") as test:
        report = checks.sync(dev, test, table_checks(req, dev, test))
    return {"message": "; ".join(report) or "Nothing to sync"}


@app.post("/api/fix/delete")
def fix_delete(req: DeleteRequest) -> dict:
    """Delete one configuration from dev so it can be synced again from test."""
    with db.connect("dev") as dev, db.connect("test") as test:
        c = next(c for c in table_checks(req, dev, test) if c.name == req.name)
        deleted = db.delete(dev, c.table, c.where, c.binds)
        dev.commit()
    return {"message": f"{c.name}: {deleted} row(s) deleted from dev"}


@app.post("/api/upload")
def upload(
    file: UploadFile,
    direction: Annotated[Literal["TI", "TO"], Form()],
    operator: Annotated[str, Form()],
    ext: Annotated[str | None, Form(pattern=r"^[A-Za-z0-9]+$")] = None,
) -> dict:
    """Upload a checked file to the operator's TAP folder with the extension configured in PROCESS_CONTROL_SYSTEM,
    or with ext when database checks are bypassed."""
    req = CheckRequest(filename=file.filename.split(".")[0].upper(), direction=direction, operator=operator, rate_date=date.today())
    if not ext:
        with db.connect("dev") as dev:
            rows = db.select(dev, "PROCESS_CONTROL_SYSTEM", "client_operator = :op and file_direction = :dir", {"op": req.operator, "dir": req.direction})
        if not rows:
            raise RuntimeError(f"No PROCESS_CONTROL_SYSTEM row for {req.operator} {req.direction} in dev")
        ext = rows[0]["FILE_EXT"]
    name = f"{req.filename}.{ext}"
    folder = f"{get_settings().data_root}/{req.operator}/TAP/{'ForClient' if req.direction == 'TI' else 'FromClient'}"
    ssh.upload(file.file, folder, name)
    return {"message": f"Uploaded {name} to {folder}"}


app.mount("/", StaticFiles(directory="static", html=True, check_dir=False), name="static")
