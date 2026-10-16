import os
import sys
from pathlib import Path

from app import App

from Src.Logging import logging

# Assets live next to the sources in development and inside sys._MEIPASS in a
# frozen build. Some of them are referenced from the configuration by relative
# path (fonts_config.json names the .ttf), so the process has to look there
# while App is constructed rather than where it happens to be started from.
BASE_PATH = Path(getattr(sys, '_MEIPASS', '.'))

if __name__ == "__main__":
    os.chdir(BASE_PATH)

    my_app = App(
        title="GraphNet",
        logger_config_path="Assets/logger_config.json",
        font_path="Assets/fonts_config.json",
        themes_path="Assets/themes.json",
    )

    if "--smoke-test" in sys.argv:
        # Constructing App already imports every dependency, loads the themes
        # and builds the whole node editor, so reaching this point means the
        # frozen bundle resolved. App.run() then blocks in the GUI event loop
        # until the window is closed, which never happens on a build runner, so
        # the build check has to stop here instead.
        logging()("main", {}).warning("SMOKE TEST OK")
        sys.exit(0)

    my_app.run()