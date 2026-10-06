import os
from pathlib import Path
import subprocess
import sys

import pytest


@pytest.mark.parametrize("mode", ["unshown", "run", "loop_error"])
def test_native_application_shutdown(mode, tmp_path):
    root = Path(__file__).resolve().parents[1]
    script = f"""
from pathlib import Path
Path.home = lambda: Path({str(tmp_path)!r})
import dearpygui.dearpygui as dpg
from app import App
from Src.resources import resource_path

app = App("GraphNet", resource_path("logger_config.json"),
          resource_path("fonts_config.json"), resource_path("themes.json"))
assert not dpg.is_viewport_ok()
native_destroy = dpg.destroy_context
calls = []
def destroy():
    native_destroy()
    calls.append(True)
dpg.destroy_context = destroy
if {mode!r} == "unshown":
    dpg.destroy_context()
else:
    def stop():
        assert dpg.does_item_exist("Prime")
        dpg.stop_dearpygui()
    dpg.set_frame_callback(3, stop)
    if {mode!r} == "loop_error":
        def fail():
            assert dpg.does_item_exist("Prime")
            dpg.render_dearpygui_frame()
            raise RuntimeError("render loop failure")
        dpg.start_dearpygui = fail
        try:
            app.run()
        except RuntimeError as error:
            assert str(error) == "render loop failure"
        else:
            raise AssertionError("Expected render error")
    else:
        app.run()
assert calls == [True]
"""
    result = subprocess.run(
        [sys.executable, "-c", script], cwd=tmp_path,
        env=os.environ | {"PYTHONPATH": str(root)}, capture_output=True, text=True, timeout=60,
    )
    assert result.returncode == 0, result.stdout + result.stderr
