# File Processing Check

Sanity check for TAP file processing on the dev server: operator directory tree (vs FRAF1) and
database configuration (docs/PLAN.md). Missing directories can be created, missing rows synced from
test, and any dev configuration deleted so it can be synced again.

Usage: select one or more TAP files and the direction, then Check. Fix what is missing per file.
When all checks of a file are OK, Upload copies it to `DATA/<client>/TAP/ForClient` (TI) or
`FromClient` (TO) as `<filename>.<FILE_EXT>` (from PROCESS_CONTROL_SYSTEM). Existing files are never overwritten.
Tick "Directory check only" to skip the database checks: only the directory structure is checked and the
extension is taken from the Extension field (default GO).

## Run on the dev server (10.0.39.201)

All commands as `ngcplus` on 10.0.39.201 unless stated.

1. Copy the project (from your laptop, WSL):

   ```sh
   rsync -av --exclude .env --exclude node_modules --exclude .next --exclude out --exclude .venv \
     --exclude __pycache__ --exclude backend/static \
     ~/APP/fileProcessingCheck/ ngcplus@10.0.39.201:/u01/ngcplus/DCH/API_APP/FILE_PROCESSING_CHECK/
   ```

2. Create an SSH key the app uses to log in to this server (one time):

   ```sh
   ssh-keygen -t ed25519 -N "" -C file-processing-check -f ~/.ssh/fpc_app
   cat ~/.ssh/fpc_app.pub >> ~/.ssh/authorized_keys
   ssh -i ~/.ssh/fpc_app ngcplus@10.0.39.201 true && echo OK
   ```

3. Configure:

   ```sh
   cd /u01/ngcplus/DCH/API_APP/FILE_PROCESSING_CHECK
   cp .env.example .env
   chmod 600 .env
   vi .env    # DEV_DB_PASSWORD, TEST_DB_PASSWORD, SSH_KEY_FILE=/u01/ngcplus/.ssh/fpc_app
   ```

4. Start (builds the image, restarts automatically after a reboot):

   ```sh
   sh scripts/start.sh
   ```

5. Open http://10.0.39.201:8010 from your browser. If port 8010 is not reachable from your network,
   use an SSH tunnel from your laptop and open http://localhost:8020:

   ```sh
   ssh -N -L 8020:127.0.0.1:8010 ngcplus@10.0.39.201
   ```

Stop: `sh scripts/stop.sh`. Update: copy again (step 1), then `sh scripts/start.sh`.
After any change to `.env`, run `sh scripts/start.sh` again; settings are read only at start.

## If login fails

The error on the page names the connection that failed, for example
`TEST database login failed (ngcplus@10.0.39.231:1521/TSTTNRPT_NGCPLUS_PDB1): ORA-01017 ...`.

| Error | Cause | Fix |
|---|---|---|
| `DEV/TEST database login failed ... ORA-01017` | Wrong user or password in `.env` | Correct `DEV_DB_*` / `TEST_DB_*` (no quotes, no spaces), then `sh scripts/start.sh`. Test the same password in SQL Developer first. Do not retry repeatedly: the account can get locked. |
| `... ORA-28000` | Account locked | Ask the DBA to unlock `ngcplus`, then fix the password as above. |
| `... ORA-28001` | Password expired | Change it in SQL Developer, update `.env`, restart. |
| `... DPY-6005` / timeout | Database not reachable | Check `DEV_DB_DSN` / `TEST_DB_DSN` and the network from the server. |
| `SSH login failed ... Authentication failed` | Key not in `~/.ssh/authorized_keys` | Repeat step 2; check `SSH_KEY_FILE` in `.env`. |
| `SSH login failed ... No such file or directory` | `SSH_KEY_FILE` path wrong | Point it to the private key (not `.pub`), restart. |
| `SSH login failed ... timed out` | Container cannot reach 10.0.39.201 | Check the server firewall allows Docker to reach port 22. |

Useful commands:

```sh
docker logs --tail 50 file-processing-check
docker exec file-processing-check uv run --no-dev python -c "from app import db; db.connect('dev'); db.connect('test'); print('DB OK')"
docker exec file-processing-check uv run --no-dev python -c "from app import ssh; ssh.run('true'); print('SSH OK')"
```

## Develop locally

- Same `.env` with `SSH_KEY_FILE=~/.ssh/dev_ngcplus.priv`, then `sh scripts/start.sh` and open http://localhost:8010.
- Backend tests: `cd backend && uv run pytest`
- Frontend build: `cd frontend && npm run build` (static export served by the backend)
