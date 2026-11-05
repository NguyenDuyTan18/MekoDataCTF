"""Package the exact source repair and a credential-preserving overlay."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parent
PATCH_FILES = (
    'README-GUI-FIX.md', 'provisioning/playbook.yml', 'provisioning/desktop.yml',
    'provisioning/browser-desktop.yml', 'provisioning/gui-repair.yml',
    'provisioning/files/check-vnc.py',
)

def main():
    patch = ROOT.parent / 'MekoDataCTF04-11-gui-patch.zip'
    full = ROOT.parent / 'MekoDataCTF04-11-gui-fixed.zip'
    with ZipFile(patch, 'w', ZIP_DEFLATED) as archive:
        for name in PATCH_FILES: archive.write(ROOT / name, name)
        assert not any('group_vars' in name or 'credentials' in name for name in archive.namelist())
    with ZipFile(full, 'w', ZIP_DEFLATED) as archive:
        for path in sorted(ROOT.rglob('*')):
            if not path.is_file(): continue
            rel = path.relative_to(ROOT)
            if any(part.startswith('.') or part == '__pycache__' for part in rel.parts): continue
            if path.suffix in ('.pyc', '.db', '.sqlite', '.log'): continue
            archive.write(path, rel.as_posix())
        assert 'topology.yml' in archive.namelist()
    print(patch)
    print(full)

if __name__ == '__main__': main()
