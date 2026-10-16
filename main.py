import sys
from pathlib import Path

from app import App

from Src.Logging import logging

# Ресурсы лежат рядом с исходниками при разработке и внутри sys._MEIPASS в
# собранном приложении. Часть из них названа относительными путями в
# конфигурации (fonts_config.json называет .ttf), поэтому пути разрешаются
# здесь, один раз, а не через смену рабочего каталога: смена каталога
# увела бы за собой и логи, а писать их внутрь установленного приложения
# нельзя.
BASE_PATH = Path(getattr(sys, '_MEIPASS', '.'))


def asset(name: str) -> str:
    return str(BASE_PATH / name)


if __name__ == "__main__":
    my_app = App(
        title="GraphNet",
        logger_config_path=asset("Assets/logger_config.json"),
        font_path=asset("Assets/fonts_config.json"),
        themes_path=asset("Assets/themes.json"),
        setup="--smoke-test" not in sys.argv,
    )

    if "--smoke-test" in sys.argv:
        # Содержимое окна собирается и без OpenGL: это создаёт все узлы из
        # конфигурации, то есть импортирует Keras целиком. App.run() дальше
        # уходит в цикл событий графики и на сборочной машине не заканчивается,
        # поэтому проверка бандла обрывается здесь.
        my_app.build_ui()

        logging()("main", {}).warning("SMOKE TEST OK")
        sys.exit(0)

    my_app.run()