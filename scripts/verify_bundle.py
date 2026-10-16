"""Verify a frozen GraphNet bundle without launching it.

A PyInstaller build can complete cleanly and still be broken for the user: a
missing runtime library only shows up when a compiled extension is loaded, so
the failure surfaces at launch instead of at build time. This script inspects
the bundle so that class of defect fails the build.

The check has two parts. First the layout: the executable, the bundled assets
and one ``*.libs`` directory per delvewheel-built distribution in the
environment. Second the link closure: every binary in the bundle is parsed for
its PE import table, so an unsatisfied import is reported here instead of by a
user on Windows.
"""
from __future__ import annotations

from pathlib import Path
import struct
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

from build_exe import dll_library_dirs


# Libraries that ship with Windows itself and therefore need no copy in the
# bundle. The Direct3D/DXGI pair is part of the graphics stack present on every
# Windows install DearPyGui can run on.
SYSTEM_DLLS = {
    "advapi32.dll", "bcrypt.dll", "comdlg32.dll", "crypt32.dll",
    "d3d11.dll", "d3d9.dll", "d3dcompiler_47.dll", "dbghelp.dll", "dnsapi.dll",
    "dwmapi.dll", "dxgi.dll", "dxva2.dll",
    "gdi32.dll", "gdi32full.dll", "imm32.dll", "iphlpapi.dll", "kernel32.dll",
    "kernelbase.dll", "msacm32.dll", "mscoree.dll", "msvcrt.dll",
    "netapi32.dll", "normaliz.dll", "ntdll.dll", "ole32.dll", "oleaut32.dll",
    "opengl32.dll", "powrprof.dll", "propsys.dll", "psapi.dll", "rpcrt4.dll",
    "secur32.dll", "setupapi.dll", "shell32.dll", "shlwapi.dll", "user32.dll",
    "userenv.dll", "version.dll", "winmm.dll", "winspool.drv", "wldap32.dll",
    "ws2_32.dll",
}

# Provided by the Visual C++ redistributable on the target machine.
RUNTIME_DLLS = {
    "concrt140.dll", "msvcp140.dll", "ucrtbase.dll", "vcomp140.dll",
    "vcruntime140.dll", "vcruntime140_1.dll",
}

# Assets the application reads through sys._MEIPASS. Keep in sync with the
# paths passed to App() in main.py.
REQUIRED_ASSETS = [
    "Assets/logger_config.json",
    "Assets/logger_debug.json",
    "Assets/logger_group.json",
    "Assets/logger_stream.json",
    "Assets/fonts_config.json",
    "Assets/themes.json",
    "Assets/notomono-regular.ttf",
]


def pe_imports(data: bytes) -> list[str]:
    """Return the DLL names listed in a PE file's import directory."""
    if data[:2] != b"MZ":
        return []
    e_lfanew = struct.unpack_from("<I", data, 0x3C)[0]
    if data[e_lfanew:e_lfanew + 4] != b"PE\x00\x00":
        return []
    coff = e_lfanew + 4
    (section_count,) = struct.unpack_from("<H", data, coff + 2)
    (optional_size,) = struct.unpack_from("<H", data, coff + 16)
    optional = coff + 20
    (magic,) = struct.unpack_from("<H", data, optional)
    directories = optional + (112 if magic == 0x20B else 96)
    (import_rva,) = struct.unpack_from("<I", data, directories + 8)
    if not import_rva:
        return []

    sections = []
    section_table = optional + optional_size
    for index in range(section_count):
        base = section_table + 40 * index
        vsize, vaddr, rsize, raddr = struct.unpack_from("<IIII", data, base + 8)
        sections.append((vaddr, vsize, raddr, rsize))

    def rva_to_offset(rva: int) -> int | None:
        for vaddr, vsize, raddr, rsize in sections:
            if vaddr <= rva < vaddr + max(vsize, rsize):
                return raddr + (rva - vaddr)
        return None

    offset = rva_to_offset(import_rva)
    names: list[str] = []
    while offset is not None:
        fields = struct.unpack_from("<IIIII", data, offset)
        if fields == (0, 0, 0, 0, 0):
            break
        name_offset = rva_to_offset(fields[3])
        if name_offset is None:
            break
        end = data.index(b"\x00", name_offset)
        names.append(data[name_offset:end].decode("latin-1"))
        offset += 20
    return names


def main() -> int:
    bundle = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("dist/GraphNet")
    internal = bundle / "_internal"
    problems: list[str] = []

    if not (bundle / "GraphNet.exe").is_file():
        problems.append(f"{bundle / 'GraphNet.exe'} is missing")
    if not internal.is_dir():
        problems.append(f"{internal} is missing")
        for problem in problems:
            print(f"FAIL: {problem}")
        return 1

    for asset in REQUIRED_ASSETS:
        if not (internal / asset).is_file():
            problems.append(f"{asset} was not bundled")

    for libs in dll_library_dirs():
        staged = internal / libs.name
        if not staged.is_dir() or not any(staged.glob("*.dll")):
            problems.append(
                f"_internal/{libs.name} is missing: {libs.name.removesuffix('.libs')} "
                "cannot resolve the libraries its extension module links against"
            )

    binaries = sorted(
        path for path in internal.rglob("*")
        if path.suffix.lower() in {".dll", ".pyd"}
    )
    available = {path.name.lower() for path in binaries}
    for binary in binaries:
        for library in pe_imports(binary.read_bytes()):
            name = library.lower()
            if name in available or name in SYSTEM_DLLS or name in RUNTIME_DLLS:
                continue
            if name.startswith("api-ms-win-"):
                continue
            problems.append(f"{binary.relative_to(internal)} imports {library}, "
                            "which is not in the bundle")

    print(f"checked {len(binaries)} binaries, {len(REQUIRED_ASSETS)} assets and "
          f"{len(dll_library_dirs())} runtime library directories")
    if problems:
        for problem in problems:
            print(f"FAIL: {problem}")
        return 1
    print("bundle verification passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())