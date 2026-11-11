# PostgreSQL mirror (bonus)

Added 11 November 2026 (roadmap CC-3, issue #22).

## Why

Bonus criterion: PostgreSQL (not SQLite) with joins and aggregations from Python. **SQLite stays the primary database** and the mandatory part of the project: `src/prepare.py` builds `data/processed/aircraft.sqlite`, all other notebooks read it. PostgreSQL only holds a **mirror** built from that file by `src/postgres_mirror.py`. It is never edited by hand and can be rebuilt at any time.

Compared with SQLite, the mirror adds:

- explicit column types (`TIMESTAMPTZ`, `DATE`, `BIGINT`, `DOUBLE PRECISION`, …);
- enforced primary keys and foreign keys, so a broken join key stops the mirror;
- PostgreSQL functions SQLite does not have, e.g. exact medians (`percentile_cont`) and `FILTER` on aggregates.

`notebooks/04_postgresql.ipynb` runs the SQL from Python: a join of observations, airports and wind, an aggregation by zone and altitude band, window functions (`ROW_NUMBER`, `RANK`), and a check that row counts and one identical aggregation agree with SQLite.

## Mirrored tables and keys

| Table | Primary key | Foreign key |
|---|---|---|
| `airports` | `ident` | – |
| `observations` | `(icao24, time_position)` | `airport_ident → airports.ident` |
| `aircraft_metadata` | `icao24` | – |
| `weather_levels` | `(time_utc, grid_lat, grid_lon, level_hpa)` | – |
| `observation_wind` | `(icao24, time_position)` | `(icao24, time_position) → observations` |
| `integration_audit`, `metadata_integration_audit`, `weather_integration_audit` | – | – |

The column types are written out in `TABLES` in `src/postgres_mirror.py`. If `prepare.py` gains or loses a column, the mirror stops with a message naming the column; add it to `TABLES` then. There is no foreign key from `observations` to `aircraft_metadata`, because unmatched aircraft are kept on purpose.

The mirror runs in **one transaction**: drop the mirrored tables, create them, load them with `COPY`, compare row counts with SQLite. If a key is violated or a count differs, nothing in PostgreSQL changes. `DROP … CASCADE` also removes your own views that depend on mirrored tables, so keep custom SQL in the notebook instead.

## Connection: `DATABASE_URL`

The script and the notebook read the connection from:

1. the environment variable `DATABASE_URL`, if it is set; otherwise
2. a line `DATABASE_URL=...` in the file `.env` in the project folder.

`.env` is in `.gitignore`. `.env.example` (committed) is the template. Passwords belong **only** in `.env` or the environment, never in code, notebooks, screenshots, GitHub or the AI log. Output always shows the URL with `***` instead of the password.

Format: `postgresql+psycopg://USER:PASSWORD@HOST:PORT/DATABASE`. Plain `postgresql://` also works. Special characters in the password must be URL-encoded: `@` → `%40`, `:` → `%3A`, `/` → `%2F`, `#` → `%23`.

### VS Code notebooks and `.env`

Notebook 04 does not depend on VS Code to load `.env`, because `load_database_url()` reads the file itself, relative to the project folder, whatever the notebook's working directory.

The VS Code Python/Jupyter extensions additionally load the workspace `.env` into terminals and kernels they start (setting `python.envFile`, default `${workspaceFolder}/.env`). The workspace folder must then be the project folder, not a parent folder. A value that ends up in the environment this way wins over the file, as does one exported in the shell.

After editing `.env`, **restart the kernel** (*Restart* in the notebook toolbar), because a running kernel keeps its old environment. A stale `DATABASE_URL` exported in `~/.zshrc` or in the Windows user variables also wins over `.env`. Remove it if the notebook connects to the wrong place.

## macOS (Homebrew)

```bash
brew install postgresql@16
brew services start postgresql@16          # starts now and at every login
/opt/homebrew/opt/postgresql@16/bin/createdb aviation
cp .env.example .env                       # contains DATABASE_URL=postgresql+psycopg://localhost/aviation
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python src/postgres_mirror.py    # after every src/prepare.py
```

Then open `notebooks/04_postgresql.ipynb`, select the `.venv` kernel and run all cells.

Notes:

- Homebrew's `postgresql@16` is keg-only: `psql`, `createdb` and the other programs are not on the `PATH`. Either use the full path as above, or add `export PATH="/opt/homebrew/opt/postgresql@16/bin:$PATH"` to `~/.zshrc`.
- Homebrew's cluster lets your macOS user log in locally without a password, so the URL needs no password.
- To stop the server for good, run `brew services stop postgresql@16`. To start it only when needed, use `brew services run postgresql@16`, which does not register it for login.
- To look around: `/opt/homebrew/opt/postgresql@16/bin/psql aviation`, then `\dt` lists the tables, `\d observations` shows types and keys, `\q` quits.

## Windows (Kevin, Robin)

Prerequisite: a working project copy with `.venv` and a built SQLite database (`docs/COLLABORATION.md`: import the dated export, then `.venv\Scripts\python.exe src/prepare.py`).

**1. Install PostgreSQL 16**

Use the installer from <https://www.postgresql.org/download/windows/> (EDB), or run `winget install PostgreSQL.PostgreSQL.16` in PowerShell. In the installer:

- Keep the default components. *Stack Builder* is not needed.
- Choose a password for the user `postgres` and note it.
- Keep port `5432`.

The Windows service `postgresql-x64-16` starts automatically, now and after every reboot.

**2. Create the database**

In PowerShell; it asks for the `postgres` password:

```powershell
& "C:\Program Files\PostgreSQL\16\bin\createdb.exe" -U postgres -h localhost aviation
```

**3. Install the Python packages** (adds `psycopg` and `SQLAlchemy`)

```powershell
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

**4. Create `.env`**

```powershell
Copy-Item .env.example .env
notepad .env
```

In `.env`, delete or comment out the macOS line and keep only:

```
DATABASE_URL=postgresql+psycopg://postgres:YOUR_PASSWORD@localhost:5432/aviation
```

Replace `YOUR_PASSWORD` with your password, URL-encoded as described above. Never commit `.env`. `git status` must not list it.

**5. Build the mirror** (again after every `src/prepare.py`)

```powershell
.venv\Scripts\python.exe src\postgres_mirror.py
```

The output lists each table with its rows in SQLite and in PostgreSQL and ends with `Row counts match.`

**6. Run notebook 04**

Open `notebooks/04_postgresql.ipynb` in VS Code, select the `.venv` kernel (top right) and choose *Run All*. Section 1 must show `match = True` for every table.

**Service control.** Open *Services* (`services.msc`) and find `postgresql-x64-16`, or use PowerShell as administrator:

```powershell
Get-Service postgresql*
Stop-Service postgresql-x64-16
Start-Service postgresql-x64-16
```

## Troubleshooting

| Message | Cause and fix |
|---|---|
| `DATABASE_URL is not set` | No environment variable and no `DATABASE_URL=` line in `.env`. Create `.env` from `.env.example`. |
| `connection refused` / `Cannot reach PostgreSQL` | Server not running. macOS: `brew services start postgresql@16`. Windows: `Start-Service postgresql-x64-16`. |
| `password authentication failed` | Wrong password in `.env`, or special characters not URL-encoded. |
| `database "aviation" does not exist` | Run the `createdb` step. |
| `Tables [...] are missing in PostgreSQL` | The mirror was never built: run `src/postgres_mirror.py`. |
| `Mirror is out of date` (notebook 04) | SQLite was rebuilt after the last mirror: run `src/postgres_mirror.py` again. |
| `violates foreign key constraint` | The SQLite data break a key (e.g. an airport missing). PostgreSQL stays unchanged; fix the data in `prepare.py`, not in PostgreSQL. |
| `SQLite columns differ from the PostgreSQL schema` | `prepare.py` changed its tables: update `TABLES` in `src/postgres_mirror.py` and the tests. |
