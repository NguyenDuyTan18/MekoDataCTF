"""Build clean handoff archives without runtime data or private credentials."""
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parent
EXCLUDE_PARTS = {".git", ".venv", "__pycache__", ".pytest_cache", ".runtime", "runtime", "dist", "build"}
EXCLUDE_SUFFIXES = {".pyc", ".sqlite", ".sqlite3", ".db", ".log"}
EXCLUDE_NAMES = {"state.json", "credentials.json", "checker.env", "checker-key", "coverage.json"}

def safe(path):
    rel=path.relative_to(ROOT)
    return not any(part in EXCLUDE_PARTS or part.lower().startswith(".local") or "secret" in part.lower() for part in rel.parts) and path.name not in EXCLUDE_NAMES and path.suffix.lower() not in EXCLUDE_SUFFIXES and not path.name.startswith(".")

def create_archive(path, files, prefix, base=ROOT):
    with ZipFile(path,"w",ZIP_DEFLATED) as archive:
        for item in sorted(set(files)):
            if safe(item): archive.write(item, (Path(prefix)/item.relative_to(base)).as_posix() if prefix else item.relative_to(base).as_posix())
        names=archive.namelist()
        assert names and not any("state.json" in n or "credentials" in n.lower() or "checker.env" in n or "__pycache__" in n for n in names)
    return path

def main():
    source=[p for folder in (ROOT/"sandbox",ROOT/"tests",ROOT/"docs") for p in folder.rglob("*") if p.is_file()]
    source += [ROOT/n for n in ("README.md","requirements.txt","requirements-dev.txt","package_lab.py")]
    source_zip=create_archive(ROOT/"meko-boutique-v2-source.zip",source,"fashion_shop_v2")
    sandbox=[p for folder in (ROOT/"sandbox/provisioning",ROOT/"sandbox/app",ROOT/"sandbox/checker") for p in folder.rglob("*") if p.is_file()]
    sandbox += [ROOT/"sandbox/topology.yml"]
    sandbox_zip=create_archive(ROOT/"meko-boutique-v2-sandbox.zip",sandbox,"",ROOT/"sandbox")
    with ZipFile(sandbox_zip) as archive:
        names=set(archive.namelist())
        assert {"topology.yml","provisioning/playbook.yml","app/app.py","app/data/seed.json","checker/check.py"} <= names
    print(source_zip)
    print(sandbox_zip)

if __name__=="__main__": main()
