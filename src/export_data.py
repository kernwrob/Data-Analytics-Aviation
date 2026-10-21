"""Freeze a manifest, copy immutable raw files, rebuild in the package, then ZIP.

Never moves/deletes source data or uploads to a service. The export is restricted
project data; see docs/SHARING.md before transferring it to a university folder.
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def checksum(path):
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination", type=Path, default=ROOT / "exports",
                        help="Local export parent folder. Default: ignored project exports/.")
    args = parser.parse_args()
    manifest_bytes = (ROOT / "data/raw/manifest.jsonl").read_bytes()
    # Freeze at a complete JSONL boundary if a collector is appending concurrently.
    manifest_bytes = manifest_bytes[:manifest_bytes.rfind(b"\n") + 1]
    entries = [json.loads(line) for line in manifest_bytes.decode("utf-8-sig").splitlines() if line.strip()]
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    package = args.destination.resolve() / f"aircraft-data-{stamp}"
    package.mkdir(parents=True, exist_ok=False)
    (package / "data/raw").mkdir(parents=True)
    (package / "data/raw/manifest.jsonl").write_bytes(manifest_bytes)
    for entry in entries:
        if "path" not in entry:
            continue
        # Manifest paths must stay within data/raw; absolute paths/traversal are rejected.
        relative = Path(entry["path"].replace("\\", "/"))
        source = (ROOT / relative).resolve()
        if not source.is_relative_to((ROOT / "data/raw").resolve()):
            raise ValueError("Manifest path is outside data/raw.")
        if checksum(source) != entry["sha256"]:
            raise ValueError(f"Original checksum mismatch: {relative}")
        target = package / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        if checksum(target) != entry["sha256"]:
            raise ValueError(f"Export checksum mismatch: {relative}")
    for folder in ("src", "notebooks", "docs"):
        shutil.copytree(ROOT / folder, package / folder, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".ipynb_checkpoints"))
    for name in ("config.json", "requirements.txt", "requirements-lock.txt", "README.md", "PROJECT_PLAN.md"):
        shutil.copy2(ROOT / name, package / name)
    for name in ("collection_control.jsonl", "main_schedule.json"):
        path = ROOT / "data/raw" / name
        if path.exists():
            shutil.copy2(path, package / "data/raw" / name)
    evidence = package / "provenance"
    evidence.mkdir()
    for name in ("schedule.json", "stop.json", "coverage_summary.json", "task-before-stop.xml", "task_verification.json"):
        path = ROOT / "outputs/pilot" / name
        if path.exists():
            shutil.copy2(path, evidence / name)
    # Rebuilding from the frozen manifest's copied files prevents a stale database /
    # new-manifest mismatch. No API requests are made in this subprocess.
    environment = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    subprocess.run([sys.executable, str(package / "src/prepare.py")], cwd=package, check=True, env=environment)
    (package / "REPRODUCE.md").write_text("""# Restricted dated data package

Use only for this university project under docs/SHARING.md and the linked source conditions.
The raw acquisition manifest was frozen before copying. All referenced raw bytes were
checksum-verified; SQLite was rebuilt from exactly the copied source files and config.
Original project files were preserved. This package does not collect new snapshots.

Extract to your own local folder (outside the collector's folder). On Windows/Python 3.13:

```powershell
python -m venv .venv
.venv\\Scripts\\python.exe -m pip install -r requirements-lock.txt
.venv\\Scripts\\python.exe src/prepare.py
.venv\\Scripts\\python.exe -m jupyterlab
```

Select .venv as the notebook kernel. Do not run a second collector. To use this dataset
with your Git clone, copy the package's data/ folder into that clone, retain its dated
config.json as the data version's configuration, and record the export timestamp.
Review configuration differences before switching datasets. If your analysis clone
already has data/, preserve that whole folder outside the clone before copying the
new data/ folder. Do not merge exports: preparation reads all raw snapshot files,
so leftover files would change the dataset. Never replace the live collector's data.
Verify package_contents.json hashes after extraction. The ZIP's adjacent .sha256 file
checks transfer integrity of the archive. Missing collection periods are missing
observations, not zero aircraft activity. Do not fit final models on pilot-only data.
""", encoding="utf-8")
    contents = [{"path": str(path.relative_to(package)).replace("\\", "/"),
                 "bytes": path.stat().st_size, "sha256": checksum(path)}
                for path in sorted(package.rglob("*")) if path.is_file() and "__pycache__" not in path.parts]
    (package / "package_contents.json").write_text(json.dumps({"exported_at_utc": stamp,
        "python_version": sys.version, "acquisition_entries": len(entries), "files": contents}, indent=2) + "\n", encoding="utf-8")
    archive = Path(shutil.make_archive(str(package), "zip", root_dir=package))
    archive.with_suffix(".zip.sha256").write_text(checksum(archive) + "  " + archive.name + "\n", encoding="ascii")
    print(f"Export folder: {package}\nArchive: {archive}\nOriginal files preserved; nothing uploaded.")


if __name__ == "__main__":
    main()
