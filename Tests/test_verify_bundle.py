"""Test verify_bundle.py against synthetic bundles.

The verifier is the gate that catches a missing runtime library before a user
does, so it is tested on the two things it inspects: the directory layout of a
bundle, and the import directory of every binary in it.

The binaries here are hand-built PE files rather than the 450 MB release
artifact: the verifier only reads the import directory, so a real artifact
would add a download to the suite without testing anything more. The parser
itself was validated against the real 0.2.0 bundle during the fix; see the
commit message of the commit that added this file.
"""
from __future__ import annotations

from pathlib import Path
import contextlib
import io
import struct
import sys

import pytest


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import verify_bundle


HEADER_SIZE = 0x400     # SizeOfHeaders
SECTION_RVA = 0x1000    # VirtualAddress of the only section
SECTION_SIZE = 0x1000
# The import descriptor table starts the section; the name follows the single
# descriptor and the null descriptor that terminates the table.
IMPORT_RVA = SECTION_RVA
NAME_RVA = SECTION_RVA + 40


def minimal_pe(dll_name: str) -> bytes:
    """Return a PE32+ file whose import directory names ``dll_name``."""
    header = bytearray(HEADER_SIZE)
    header[0:2] = b"MZ"
    struct.pack_into("<I", header, 0x3C, 0x80)        # e_lfanew
    struct.pack_into("<I", header, 0x80, 0x00004550)  # PE signature
    coff = 0x84
    struct.pack_into("<H", header, coff + 2, 1)             # NumberOfSections
    struct.pack_into("<H", header, coff + 16, 0xE0)         # SizeOfOptionalHeader
    optional = coff + 20
    struct.pack_into("<H", header, optional, 0x20B)         # PE32+ magic
    struct.pack_into("<I", header, optional + 112 + 8, IMPORT_RVA)  # import dir RVA
    section = optional + 0xE0
    struct.pack_into("<I", header, section + 8, SECTION_SIZE)   # VirtualSize
    struct.pack_into("<I", header, section + 12, SECTION_RVA)   # VirtualAddress
    struct.pack_into("<I", header, section + 16, SECTION_SIZE)  # SizeOfRawData
    struct.pack_into("<I", header, section + 20, HEADER_SIZE)   # PointerToRawData

    # IMAGE_IMPORT_DESCRIPTOR: OriginalFirstThunk, TimeDateStamp,
    # ForwarderChain, Name, FirstThunk.
    body = struct.pack("<IIIII", NAME_RVA, 0, 0, NAME_RVA, 0)
    body += b"\x00" * 20
    body += dll_name.encode("latin-1") + b"\x00"
    body += b"\x00" * (SECTION_SIZE - len(body))
    return bytes(header) + body


def make_bundle(root: Path, libs: dict[str, dict[str, str]]) -> Path:
    """Create a bundle whose runtime library directories are given by ``libs``.

    ``libs`` maps a ``<distribution>.libs`` directory name to the DLLs inside it
    and the DLL each of those links against.
    """
    bundle = root / "GraphNet"
    internal = bundle / "_internal"
    internal.mkdir(parents=True)
    (bundle / "GraphNet.exe").write_bytes(minimal_pe("KERNEL32.dll"))
    for asset in verify_bundle.REQUIRED_ASSETS:
        path = internal / asset
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{}")

    for directory, libraries in libs.items():
        staged = internal / directory
        staged.mkdir()
        for library, imports in libraries.items():
            (staged / library).write_bytes(minimal_pe(imports))
    return bundle


def run(bundle: Path, libs: list[Path]) -> tuple[int, str]:
    """Run the verifier against ``bundle`` with a controlled environment.

    ``dll_library_dirs`` is what couples the verifier to the interpreter it runs
    in. In a build that is the environment being frozen, so the test replaces it
    with the directories it staged instead of the host's own.
    """
    verify_bundle.dll_library_dirs = lambda: list(libs)
    argv = sys.argv
    sys.argv = [str(SCRIPTS / "verify_bundle.py"), str(bundle)]
    stdout = io.StringIO()
    try:
        with contextlib.redirect_stdout(stdout):
            code = verify_bundle.main()
    finally:
        sys.argv = argv
    return code, stdout.getvalue()


ENVIRONMENT = [Path("numpy.libs"), Path("scipy.libs")]


def test_pe_imports_reads_the_import_directory() -> None:
    assert verify_bundle.pe_imports(minimal_pe("optree.dll")) == ["optree.dll"]


def test_pe_imports_ignores_files_that_are_not_pe() -> None:
    assert verify_bundle.pe_imports(b"\x7fELF not a PE file at all") == []
    assert verify_bundle.pe_imports(b"") == []


def test_fails_when_a_runtime_library_directory_is_missing() -> None:
    import tempfile
    with tempfile.TemporaryDirectory() as temporary:
        bundle = make_bundle(Path(temporary), {
            "numpy.libs": {"libnumpy.dll": "KERNEL32.dll"},
            # scipy.libs present in the environment but not in the bundle: the
            # case PyInstaller produces when another distribution ships the same
            # binary name and wins the deduplication.
        })
        code, output = run(bundle, ENVIRONMENT)
    assert code == 1
    assert "_internal/scipy.libs is missing" in output
    assert "scipy cannot resolve the libraries" in output


def test_passes_when_every_import_is_satisfied() -> None:
    import tempfile
    with tempfile.TemporaryDirectory() as temporary:
        bundle = make_bundle(Path(temporary), {
            "numpy.libs": {"libnumpy.dll": "KERNEL32.dll"},
            "scipy.libs": {"libscipy_openblas.dll": "libnumpy.dll"},
        })
        code, output = run(bundle, ENVIRONMENT)
    assert code == 0, output
    assert "bundle verification passed" in output


def test_reports_an_unsatisfied_import() -> None:
    import tempfile
    with tempfile.TemporaryDirectory() as temporary:
        bundle = make_bundle(Path(temporary), {
            "numpy.libs": {"libnumpy.dll": "KERNEL32.dll"},
            "scipy.libs": {"libscipy_openblas.dll": "libnumpy.dll"},
        })
        (bundle / "_internal" / "broken.pyd").write_bytes(minimal_pe("totally_absent.dll"))
        code, output = run(bundle, ENVIRONMENT)
    assert code == 1
    assert "broken.pyd imports totally_absent.dll, which is not in the bundle" in output


def test_whitelists_windows_and_vcredist_libraries() -> None:
    import tempfile
    with tempfile.TemporaryDirectory() as temporary:
        bundle = make_bundle(Path(temporary), {
            "numpy.libs": {"libnumpy.dll": "KERNEL32.dll"},
            "scipy.libs": {"libscipy_openblas.dll": "libnumpy.dll"},
        })
        (bundle / "_internal" / "system.pyd").write_bytes(minimal_pe("d3d11.dll"))
        (bundle / "_internal" / "vcredist.pyd").write_bytes(minimal_pe("VCRUNTIME140_1.dll"))
        (bundle / "_internal" / "ucrt.pyd").write_bytes(
            minimal_pe("api-ms-win-crt-runtime-l1-1-0.dll"))
        code, output = run(bundle, ENVIRONMENT)
    assert code == 0, output


def test_common_controls_count_as_a_system_library() -> None:
    """matplotlib's Tk backend pulls in comctl32.dll, which lives in System32."""
    import tempfile
    with tempfile.TemporaryDirectory() as temporary:
        bundle = make_bundle(Path(temporary), {
            "numpy.libs": {"libnumpy.dll": "KERNEL32.dll"},
            "scipy.libs": {"libscipy_openblas.dll": "libnumpy.dll"},
        })
        internal = bundle / "_internal"
        (internal / "matplotlib" / "backends").mkdir(parents=True)
        (internal / "matplotlib" / "backends" / "_tkagg.cp312-win_amd64.pyd").write_bytes(
            minimal_pe("COMCTL32.dll"))
        (internal / "tk86t.dll").write_bytes(minimal_pe("COMCTL32.dll"))
        code, output = run(bundle, ENVIRONMENT)
    assert code == 0, output


def test_optional_libraries_are_reported_but_do_not_fail() -> None:
    """numba's tbbpool imports tbb12.dll that nothing in the lock ships.

    numba only loads it for the ``tbb`` threading layer and falls back when it
    is missing, so it must not fail the build, but it must stay visible.
    """
    import tempfile
    with tempfile.TemporaryDirectory() as temporary:
        bundle = make_bundle(Path(temporary), {
            "numpy.libs": {"libnumpy.dll": "KERNEL32.dll"},
            "scipy.libs": {"libscipy_openblas.dll": "libnumpy.dll"},
        })
        pool = bundle / "_internal" / "numba" / "np" / "ufunc"
        pool.mkdir(parents=True)
        (pool / "tbbpool.cp312-win_amd64.pyd").write_bytes(minimal_pe("tbb12.dll"))
        code, output = run(bundle, ENVIRONMENT)
    assert code == 0, output
    assert "note:" in output
    assert "tbbpool.cp312-win_amd64.pyd imports tbb12.dll" in output


def test_reports_a_bundled_asset_that_is_missing() -> None:
    import tempfile
    with tempfile.TemporaryDirectory() as temporary:
        bundle = make_bundle(Path(temporary), {
            "numpy.libs": {"libnumpy.dll": "KERNEL32.dll"},
            "scipy.libs": {"libscipy_openblas.dll": "libnumpy.dll"},
        })
        (bundle / "_internal" / "Assets" / "themes.json").unlink()
        code, output = run(bundle, ENVIRONMENT)
    assert code == 1
    assert "Assets/themes.json was not bundled" in output


def test_reports_a_missing_executable() -> None:
    import tempfile
    with tempfile.TemporaryDirectory() as temporary:
        bundle = make_bundle(Path(temporary), {
            "numpy.libs": {"libnumpy.dll": "KERNEL32.dll"},
            "scipy.libs": {"libscipy_openblas.dll": "libnumpy.dll"},
        })
        (bundle / "GraphNet.exe").unlink()
        code, output = run(bundle, ENVIRONMENT)
    assert code == 1
    assert "GraphNet.exe is missing" in output


@pytest.fixture(autouse=True)
def restore_dll_library_dirs():
    """Undo the monkeypatching so test order cannot matter."""
    original = verify_bundle.dll_library_dirs
    yield
    verify_bundle.dll_library_dirs = original