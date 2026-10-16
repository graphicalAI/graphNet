import json
import sys
from pathlib import Path

import dearpygui.dearpygui as dpg

from Src.Logging import logging
from Src.Managers import ThemeManager
from Src.node_editor import NodeEditor


dpg.create_context()
dpg.create_viewport(title='Custom Title')

base_path = Path(sys._MEIPASS if hasattr(sys, '_MEIPASS') else '.')
font_path = base_path / "Assets/notomono-regular.ttf"
themes_path = base_path / "Assets/themes.json"

ThemeManager.load_themes(themes_path)
node_editor = NodeEditor(minimap=True, minimap_location=dpg.mvNodeMiniMap_Location_TopRight)
main_logger = logging()("main")



with dpg.font_registry():
    with dpg.font(font_path, 18, default_font=True, tag="Default font") as f:
        dpg.add_font_range_hint(dpg.mvFontRangeHint_Cyrillic)
dpg.bind_font("Default font")

with dpg.window(tag="Prime"):
    node_editor.show("Prime")
    main_logger.warning("НАЧАЛИ")


if '--smoke-test' in sys.argv:
    # Exercise every import, the theme manager and the whole node editor, then
    # stop before the GUI event loop. start_dearpygui() blocks until the window
    # is closed, so a build check cannot wait for this process to exit: on a
    # headless runner the event loop never returns.
    main_logger.warning("SMOKE TEST OK")
    dpg.destroy_context()
    sys.exit(0)


dpg.setup_dearpygui()
dpg.show_viewport()
dpg.set_primary_window("Prime", True)
dpg.set_global_font_scale(1)
dpg.start_dearpygui()


dpg.destroy_context()
