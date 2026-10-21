# Three-student workflow

Use one designated collection computer. Each student has a separate local Git clone for code and notebooks. Keep accumulating data outside Git, and use dated, immutable exports in a restricted university OneDrive/Teams folder under `SHARING.md`. Do not sync the live collector folder or `.venv` through OneDrive.

## Repository owner: private setup and invitations

The inspected folder had no `.git`, Git history, remote, configured author identity or GitHub CLI. A local repository on `main` is now prepared with code, empty-output notebooks and documentation. No remote has been added and nothing has been uploaded. Author name/email and the private repository URL remain to be supplied; existing student history was not rewritten.

Create a **private** repository in the chosen GitHub account or university organization. If connecting this prepared folder, leave the online repository empty: do not add a separate README/license/gitignore during creation. A private repository does not confer permission to publish datasets.

After replacing placeholders with the agreed values:

```powershell
git config --local user.name "YOUR NAME"
git config --local user.email "YOUR VERIFIED EMAIL OR GITHUB NOREPLY EMAIL"
git status
git diff --cached --stat
git commit -m "Set up aircraft research pilot and optional metadata"
git remote add origin https://github.com/OWNER/REPOSITORY.git
git push -u origin main
```

Authenticate through Git Credential Manager/GitHub's own login flow. Do not paste passwords, tokens or OAuth secrets into this chat, files or remote URLs. Verify the online repository is private before pushing. If a remote repository already has commits, fetch/review it and integrate history; never force-push over your classmates' work.

In repository **Settings → Collaborators** (or organization access settings), invite the other two students by GitHub username. They accept the invitation through their GitHub notifications/email using the intended account. Sharing a private URL alone does not give access. The owner should retain administrative access; each collaborator needs permission to push branches and open pull requests.

Official guides: [create a repository](https://docs.github.com/en/repositories/creating-and-managing-repositories/creating-a-new-repository), [invite collaborators](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/repository-access-and-collaboration/inviting-collaborators-to-a-personal-repository), [clone](https://docs.github.com/en/repositories/creating-and-managing-repositories/cloning-a-repository).

## Each student: clone and install

After accepting the invitation:

```powershell
git clone https://github.com/OWNER/REPOSITORY.git aircraft-project
cd aircraft-project
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
```

The lock was tested with Python 3.13.15 on Windows. Use Python 3.13 for closest reproduction. In VS Code choose **Python: Select Interpreter → .venv\Scripts\python.exe**, then use that environment in each notebook's kernel picker. Alternatively run `.venv\Scripts\python.exe -m jupyterlab` and select the environment's kernel. No environment activation is needed when using the full executable path.

Do not run `collect.py snapshot` or register collection tasks on classmates' computers. Existing preparation, EDA and models can use a shared export without API credentials.

## Obtain a dated data version

The collector owner produces an export:

```powershell
.venv\Scripts\python.exe src/export_data.py
```

This creates `exports/aircraft-data-UTC_TIMESTAMP/`, its ZIP and adjacent ZIP checksum. It freezes the collection manifest, copies every referenced raw file, verifies SHA-256, includes config/code/environment/source conditions, and rebuilds SQLite **inside the package**. This prevents a new raw manifest being paired with a stale live database. Originals are preserved and the command uploads nothing.

After confirming university/project sharing conditions, put the ZIP and `.zip.sha256` into a member-restricted OneDrive/Teams folder, e.g. `AircraftProject/DataExports/`. Do not replace an older ZIP with a differently generated dataset. Record the export timestamp in your notebook notes and agree one data version for cross-review. Public sharing links are unsuitable.

Each student downloads and verifies the ZIP:

```powershell
Get-FileHash -Algorithm SHA256 "C:\PATH\aircraft-data-TIMESTAMP.zip"
```

Compare to the adjacent `.sha256` value. Extract into a separate dated folder. Follow `REPRODUCE.md`, or copy its `data/` folder into your own Git clone and retain the export's `config.json` as the dataset's configuration. Review any difference with the clone's config before using it; do not silently analyze data with different thresholds/bounds. If the clone already contains `data/`, preserve that whole folder outside the clone before copying the new one. Do not merge two exports: preparation reads every raw snapshot in the folder, so leftover files would silently change the agreed dataset. Never replace the live collector's data folder. Expected paths are:

- `data/raw/opensky/*.json`, `data/raw/airports/*.csv`, `data/raw/manifest.jsonl`;
- optional `data/raw/aircraft_metadata/*.csv`;
- `data/processed/aircraft.sqlite` and generated audit/descriptive CSVs.

Run `.venv\Scripts\python.exe src/prepare.py` to rebuild, then notebooks 01–03 in order. Optional metadata cells are appended to 01 and 02. The two-hour pilot cannot satisfy the multi-day model guard; do not remove that guard just to obtain numbers.

## Daily branch and review routine

Start with a clean working tree. Commit or otherwise preserve your own unfinished work before pulling.

```powershell
git switch main
git pull --ff-only
git switch -c student-b/eda-coverage
# Edit the assigned files and verify outputs locally.
git status
git add notebooks/01_data_and_eda.ipynb docs/DECISIONS.md
git diff --cached --stat
git commit -m "Explain coverage and altitude overlap"
git push -u origin student-b/eda-coverage
```

Open a pull request in GitHub, summarize the concrete change, name the tested data version and checks, and request another student's review. Merge after review, then everyone pulls `main`. Use meaningful branch names and small changes. Do not force-push shared branches or resolve a notebook conflict by blindly choosing one whole file.

## Notebook ownership and secrets

Student A owns collection/database code; B owns notebook 01; C owns notebooks 02–03. These are provisional roles: agree names before main collection. One person edits each notebook at a time; other students review explanations and results. Use different notebooks/files rather than simultaneous cell edits, and tell the group when ownership changes.

Keep shared notebooks free of private data outputs: clear outputs before committing and keep generated figures/tables in ignored `outputs/`. Share rendered results privately with the matching dated data package. Before every commit inspect `git status`, notebook outputs and the staged diff. `.gitignore` excludes raw/processed data, exports, SQLite, environments, caches and secret files, but it cannot remove a secret already committed. No real credentials were found in the prepared files; test credential strings are dummy offline fixtures.

Public code publication for the grading bonus is a later decision. First sanitize results/identifiers, settle source conditions, and obtain group authorization; the current workflow remains private.
