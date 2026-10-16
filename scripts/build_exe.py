"""Build the desktop application with PyInstaller and the active environment.

A PyInstaller build is easy to make and easy to get subtly wrong: the command
succeeds, the executable appears, and the failure only shows up on the target
machine when a compiled extension cannot load one of its own runtime libraries.
This script therefore does two things beyond invoking PyInstaller: it collects
the packages that ship compiled code by name, and after the build it stages the
``*.libs`` directories those packages rely on.
"""
from __future__ import annotations

import shutil
import site
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUNDLE = ROOT / "dist" / "GraphNet"
INTERNAL = BUNDLE / "_internal"

# Packages that ship compiled extensions or data PyInstaller cannot discover
# from the import graph alone.
COLLECT_ALL = ["keras", "tensorflow", "optree", "dearpygui", "librosa", "matplotlib"]

# Directories read through ``sys._MEIPASS`` at run time. Keep this in sync with
# the paths passed to App() in main.py.
ASSETS = ["Assets"]


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
    makes that impossible, and it is also what covers distributions whose
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
    command = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm", "--clean",
        "--onedir", "--windowed", "--name", "GraphNet",
    ]
    for package in COLLECT_ALL:
        command += ["--collect-all", package]
    command += ["--copy-metadata", "keras", "--copy-metadata", "tensorflow"]
    command += ["--add-data", f"{ASSETS[0]}:{ASSETS[0]}", "main.py"]

    subprocess.run(command, cwd=ROOT, check=True)
    stage_dll_libraries()


if __name__ == "__main__":
    main()