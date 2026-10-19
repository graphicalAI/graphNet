import importlib
import json
import tomllib
from pathlib import Path

import pytest

from Src.resources import resource_path


@pytest.mark.parametrize("filename", [
    "themes.json",
    "logger_config.json",
    "logger_debug.json",
    "logger_group.json",
    "logger_stream.json",
    "notomono-regular.ttf",
])
def test_resources_do_not_depend_on_working_directory(tmp_path, monkeypatch, filename):
    '''Ресурсы находятся, откуда бы ни запускалось приложение.'''
    monkeypatch.chdir(tmp_path)
    path = resource_path(filename)
    assert path.is_file()
    if path.suffix == ".json":
        assert isinstance(json.loads(path.read_text(encoding="utf-8")), dict)
    else:
        assert path.stat().st_size > 0


def test_importing_entry_point_does_not_create_gui(monkeypatch):
    '''Импорт точки входа не должен открывать окно.'''
    import dearpygui.dearpygui as dpg

    def unexpected_context(*args, **kwargs):
        pytest.fail("Импорт точки входа не должен создавать GUI-контекст")

    monkeypatch.setattr(dpg, "create_context", unexpected_context)
    module = importlib.import_module("main")
    importlib.reload(module)
    assert callable(module.main)


def test_project_declares_console_script_and_build_backend():
    root = Path(__file__).resolve().parents[1]
    with (root / "pyproject.toml").open("rb") as f:
        pyproject = tomllib.load(f)

    assert pyproject["build-system"]["build-backend"] == "hatchling.build"
    assert pyproject["project"]["scripts"]["graphnet"] == "main:main"

    wheel = pyproject["tool"]["hatch"]["build"]["targets"]["wheel"]
    assert "Src" in wheel["packages"]
    assert "main.py" in wheel["force-include"]
    assert "Assets" in wheel["force-include"]


def test_dearpygui_is_pinned_to_a_working_version():
    root = Path(__file__).resolve().parents[1]
    with (root / "pyproject.toml").open("rb") as f:
        pyproject = tomllib.load(f)

    # 2.1.1 — последняя версия, в которой не падает удаление узла со связями
    # (в 2.3.x это воспроизводится); обновлять только после ручной проверки.
    assert "dearpygui==2.1.1" in pyproject["project"]["dependencies"]


def test_tensorflow_is_bounded_below_2_20():
    root = Path(__file__).resolve().parents[1]
    with (root / "pyproject.toml").open("rb") as f:
        pyproject = tomllib.load(f)

    # Начиная с 2.20 libtensorflow_framework.so экспортирует символы LLVM
    # (llvm::PassRegistry и др.). Если OpenGL рисует через программный
    # растеризатор Mesa (swrast_dri.so + системный libLLVM), драйвер
    # связывается с несовместимой копией LLVM из TensorFlow, реестр проходов
    # ломается и приложение падает с segfault на первых кадрах. Проверено:
    # 2.19.0 работает, 2.20.0 и 2.21.0 падают.
    assert "tensorflow>=2.19.0,<2.20.0" in pyproject["project"]["dependencies"]
