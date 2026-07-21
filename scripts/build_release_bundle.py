import argparse
import json
import shutil
import zipfile
from pathlib import Path


MANIFEST_NAME = "release_manifest.json"


def load_manifest(root: Path) -> dict:
    return json.loads((root / MANIFEST_NAME).read_text(encoding="utf-8"))


def _is_forbidden(rel: Path, forbidden: set[str]) -> bool:
    parts = set(rel.parts)
    rel_text = rel.as_posix()
    return rel_text in forbidden or bool(parts & forbidden)


def manifest_files(root: Path, manifest: dict) -> list[Path]:
    forbidden = set(manifest.get("forbidden", []))
    files = []
    for item in manifest.get("include", []):
        rel = Path(item)
        if _is_forbidden(rel, forbidden):
            raise ValueError(f"Forbidden path in manifest: {item}")
        src = root / rel
        if not src.exists() or not src.is_file():
            raise FileNotFoundError(str(src))
        files.append(rel)
    return files


def build_bundle(root: Path | str, destination: Path | str) -> list[Path]:
    root = Path(root).resolve()
    destination = Path(destination).resolve()
    manifest = load_manifest(root)
    files = manifest_files(root, manifest)
    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir(parents=True, exist_ok=True)
    copied = []
    for rel in files:
        src = root / rel
        target = destination / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, target)
        copied.append(rel)
    return copied


def write_zip(bundle_dir: Path, zip_path: Path) -> None:
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for file in sorted(bundle_dir.rglob("*")):
            if file.is_file():
                archive.write(file, file.relative_to(bundle_dir).as_posix())


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a clean 云芝画布 commercial release bundle.")
    parser.add_argument("--output", default="output/release/canvas-saas-commercial")
    parser.add_argument("--zip", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    bundle_dir = (root / args.output).resolve()
    copied = build_bundle(root, bundle_dir)
    print(f"Copied {len(copied)} files to {bundle_dir}")
    if args.zip:
        zip_path = bundle_dir.with_suffix(".zip")
        write_zip(bundle_dir, zip_path)
        print(f"Wrote {zip_path}")


if __name__ == "__main__":
    main()
