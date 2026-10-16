"""Build the desktop application with the active Python environment."""
from __future__ import annotations

import shutil
import site
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUNDLE = ROOT / "dist" / "GraphNet"
INTERNAL = BUNDLE / "_internal"


def dll_library_dirs() -> list[Path]:
    """Return every ``*.libs`` directory in the active environment.

    Distributions built with delvewheel ship their compiled extensions next to
    a ``<distribution>.libs`` directory holding the runtime DLLs those
    extensions link against.
    """
    found: list[Path] = []
    for entry in site.getsitepackages():
        root = Path(entry)
        if root.is_dir():
            found.extend(sorted(path for path in root.glob("*.libs") if path.is_dir()))
    return found


def stage_dll_libraries() -> None:
    """Copy every ``*.libs`` directory into the frozen bundle.

    Each package adds its own ``<distribution>.libs`` directory with
    ``os.add_dll_directory()`` before importing its extension module, so the
    directory has to exist inside ``_internal`` under its original name.

    PyInstaller keeps a single copy of a binary when two distributions embed the
    same file name, so the copy a package needs can be dropped in favour of the
    one belonging to another package. Staging the directories after the build
    makes that impossible, and it is also what catches distributions whose
    runtime libraries PyInstaller has no static import edge to follow.
    """
    for libs in dll_library_dirs():
        destination = INTERNAL / libs.name
        if destination.is_dir() and any(destination.glob("*.dll")):
            continue
        print(f"staging {libs} -> {destination}")
        shutil.copytree(libs, destination, dirs_exist_ok=True)


def main() -> None:
    """Bundle dependencies and runtime assets beside the GraphNet executable."""
    subprocess.run([
        sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean",
        "--onedir", "--windowed", "--name", "GraphNet",
        "--collect-all", "keras", "--collect-all", "tensorflow",
        "--collect-all", "optree", "--collect-all", "dearpygui",
        "--copy-metadata", "keras", "--copy-metadata", "tensorflow",
        "--add-data", "Assets:Assets", "main.py",
    ], cwd=ROOT, check=True)
    stage_dll_libraries()


if __name__ == "__main__":
    main()