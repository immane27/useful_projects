"use client";

import { useRef, useState } from "react";

type Item = {
  kind: "directory" | "table";
  name: string;
  status: "ok" | "missing" | "inactive";
  detail: string;
  rows?: number;
  shared?: boolean;
};

type Entry = {
  file: File;
  name: string; // TAP filename without local extension
  operator: string;
  partner: string;
  items?: Item[];
  error?: string;
  uploaded?: string;
};

// TAP filename: CD + sender(5) + recipient(5) + sequence. TI: client is recipient, TO: client is sender.
function entryFor(file: File, direction: string): Entry {
  const name = file.name.split(".")[0].toUpperCase();
  const sender = name.slice(2, 7);
  const recipient = name.slice(7, 12);
  const operator = direction === "TI" ? recipient : sender;
  return { file, name, operator, partner: operator === sender ? recipient : sender };
}

async function send(path: string, body: object | FormData) {
  const res =
    body instanceof FormData
      ? await fetch(path, { method: "POST", body })
      : await fetch(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  const data = await res.json();
  if (!res.ok) throw new Error(typeof data.detail === "string" ? data.detail : data.detail.map((d: { msg: string }) => d.msg).join("; "));
  return data;
}

const summary = (e: Entry) => {
  if (e.error) return e.error;
  if (!e.items) return "Not checked";
  const bad = e.items.filter((i) => i.status !== "ok").length;
  return bad ? `${bad} of ${e.items.length} checks failing` : "All OK";
};

export default function Home() {
  const today = new Date().toISOString().slice(0, 10);
  const [direction, setDirection] = useState("TI");
  const [rateDate, setRateDate] = useState(today);
  const [dirOnly, setDirOnly] = useState(false);
  const [ext, setExt] = useState("GO");
  const [entries, setEntries] = useState<Entry[]>([]);
  const [selected, setSelected] = useState(0);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const picker = useRef<HTMLInputElement>(null);

  const request = (e: Entry) => ({ filename: e.name, direction, operator: e.operator, rate_date: rateDate, dir_only: dirOnly });
  const ready = (e: Entry) => !!e.items && e.items.every((i) => i.status === "ok") && !e.uploaded;
  const current = entries[selected];

  function choose(files: FileList | null) {
    setEntries(Array.from(files ?? []).map((f) => entryFor(f, direction)));
    setSelected(0);
    setMessage("");
    setError("");
  }

  function clear() {
    if (picker.current) picker.current.value = "";
    choose(null);
    setDirection("TI");
    setRateDate(today);
    setDirOnly(false);
    setExt("GO");
  }

  async function run(action: () => Promise<void>) {
    setBusy(true);
    setError("");
    try {
      await action();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function checkEntry(e: Entry): Promise<Entry> {
    try {
      return { ...e, items: (await send("/api/check", request(e))).items, error: undefined };
    } catch (err) {
      return { ...e, items: undefined, error: (err as Error).message };
    }
  }

  const checkAll = () =>
    run(async () => {
      setMessage("");
      const next = [...entries];
      for (let n = 0; n < next.length; n++) {
        next[n] = await checkEntry(next[n]);
        setEntries([...next]);
      }
    });

  const fix = (path: string, prompt: string, extra = {}) => {
    if (!confirm(prompt)) return;
    run(async () => {
      setMessage((await send(path, { ...request(current), ...extra })).message);
      const updated = await checkEntry(current);
      setEntries(entries.map((e, n) => (n === selected ? updated : e)));
    });
  };

  const remove = (i: Item) =>
    fix(
      "/api/fix/delete",
      `Delete ${i.rows} row(s) of ${i.name} from the DEV database?` + (i.shared ? "\n\nWARNING: these rows are shared with other operators." : ""),
      { name: i.name },
    );

  const upload = (targets: number[]) => {
    if (!confirm(`Upload ${targets.length} file(s) to the dev server?`)) return;
    run(async () => {
      const next = [...entries];
      for (const n of targets) {
        const form = new FormData();
        form.append("file", next[n].file);
        form.append("direction", direction);
        form.append("operator", next[n].operator);
        if (dirOnly) form.append("ext", ext);
        try {
          next[n] = { ...next[n], uploaded: (await send("/api/upload", form)).message };
        } catch (err) {
          next[n] = { ...next[n], error: (err as Error).message };
        }
        setEntries([...next]);
      }
    });
  };

  const readyIndexes = entries.flatMap((e, n) => (ready(e) ? [n] : []));
  const items = current?.items ?? [];
  const dirMissing = items.some((i) => i.kind === "directory" && i.status === "missing");
  const tablesMissing = items.some((i) => i.kind === "table" && i.status === "missing");

  return (
    <main>
      <h1>File Processing Check</h1>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          checkAll();
        }}
      >
        <label>
          Files
          <input ref={picker} type="file" multiple onChange={(e) => choose(e.target.files)} required />
        </label>
        <label>
          Direction
          <select
            value={direction}
            onChange={(e) => {
              setDirection(e.target.value);
              setEntries(entries.map((x) => entryFor(x.file, e.target.value)));
            }}
          >
            <option>TI</option>
            <option>TO</option>
          </select>
        </label>
        <label className="inline">
          <input
            type="checkbox"
            checked={dirOnly}
            onChange={(e) => {
              setDirOnly(e.target.checked);
              setEntries(entries.map((x) => entryFor(x.file, direction)));
            }}
          />
          Directory check only
        </label>
        {dirOnly && (
          <label>
            Extension
            <input value={ext} onChange={(e) => setExt(e.target.value.toUpperCase())} pattern="[A-Za-z0-9]+" size={6} required />
          </label>
        )}
        <label>
          Exchange rate date
          <input type="date" value={rateDate} onChange={(e) => setRateDate(e.target.value)} required />
        </label>
        <button disabled={busy || !entries.length}>{busy ? "Working..." : "Check"}</button>
        <button type="button" className="secondary" disabled={busy} onClick={clear}>
          Clear
        </button>
      </form>

      {error && <p className="error">{error}</p>}
      {message && <p className="note">{message}</p>}

      {entries.length > 0 && (
        <>
          <h2>Files</h2>
          <table>
            <thead>
              <tr>
                <th>Filename</th>
                <th>Client</th>
                <th>Partner</th>
                <th>Result</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {entries.map((e, n) => (
                <tr key={n} className={n === selected ? "selected" : ""} onClick={() => setSelected(n)}>
                  <td>{e.name}</td>
                  <td>{e.operator}</td>
                  <td>{e.partner}</td>
                  <td className={e.uploaded || summary(e) === "All OK" ? "ok" : e.items || e.error ? "missing" : "detail"}>
                    {e.uploaded ?? summary(e)}
                  </td>
                  <td>
                    <button className="secondary small" disabled={busy || !ready(e)} onClick={() => upload([n])}>
                      Upload
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="actions">
            <button disabled={busy || !readyIndexes.length} onClick={() => upload(readyIndexes)}>
              Upload all ready ({readyIndexes.length})
            </button>
          </div>
        </>
      )}

      {items.length > 0 && (
        <>
          <h2>Checks for {current.name}</h2>
          <table>
            <thead>
              <tr>
                <th>Check</th>
                <th>Status</th>
                <th>Count</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {items.map((i) => (
                <tr key={i.name}>
                  <td>{i.name}</td>
                  <td className={i.status === "ok" ? "ok" : "missing"}>{i.status.toUpperCase()}</td>
                  <td className="detail">{i.detail}</td>
                  <td>
                    {!!i.rows && (
                      <button className="secondary small" disabled={busy} onClick={() => remove(i)}>
                        Delete
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="actions">
            {dirMissing && (
              <button disabled={busy} onClick={() => fix("/api/fix/directory", `Create missing directories for ${current.operator} on the dev server?`)}>
                Create directory
              </button>
            )}
            {tablesMissing && (
              <button disabled={busy} onClick={() => fix("/api/fix/sync", `Copy missing configuration for ${current.operator} from TEST into DEV database?`)}>
                Sync from test
              </button>
            )}
          </div>
        </>
      )}
    </main>
  );
}
