"""Check retained original files and original notebook computational cells."""
from pathlib import Path
from hashlib import sha256
import json

ROOT = Path(__file__).resolve().parents[1]


def digest(payload):
    return sha256(payload).hexdigest()


def main():
    manifest = json.loads((ROOT / "docs/original_manifest.json").read_text())
    checked = 0
    for item in manifest:
        if item["status"] == "removed_cache":
            continue
        path = ROOT / item["retained_path"]
        if not path.is_file():
            raise SystemExit(f"Missing original: {path}")
        if item["status"] == "notebook_navigation_added":
            nb = json.loads(path.read_text())
            cells = [c for c in nb["cells"] if c["cell_type"] == "code"]
            actual = digest(json.dumps(cells, sort_keys=True, ensure_ascii=False).encode())
            expected = item["original_code_cells_sha256"]
        else:
            actual, expected = digest(path.read_bytes()), item["sha256"]
        if actual != expected:
            raise SystemExit(f"Original contents changed: {path}")
        checked += 1
    print(f"Verified {checked} retained original files, including all original Python sources and notebook code/output cells.")


if __name__ == "__main__":
    main()
