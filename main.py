from sys import argv

import dearpygui.dearpygui as dpg

from app import App
from Src.resources import resource_path


def main():
    my_app = App(
        title="GraphNet",
        logger_config_path=resource_path("logger_config.json"),
        font_path=resource_path("fonts_config.json"),
        themes_path=resource_path("themes.json"),
    )
    if '--smoke-test' in argv:
        dpg.set_frame_callback(3, dpg.stop_dearpygui)
    my_app.run()


if __name__ == "__main__":
    main()
