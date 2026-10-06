from time import time
from pathlib import Path

import dearpygui.dearpygui as dpg

from Src.Enums import Themes
from Src.Enums.dpg_types import DPGType
from Src.Logging import logging
from Src.resources import resource_path
from Src.node_editor import NodeEditor
from Src.Managers import EventManager, ThemeManager, FontManager, SizeManager
from Src.Enums import EventType




class App:
    """
    Основной класс приложения, который отвечает за
    создание UI и запуск главного цикла DearPyGui.
    """
    font_manager: FontManager
    theme_manager: ThemeManager
    event_manager: EventManager
    size_manager: SizeManager
    __last_zoom_time: float


    def __init__(
            self,
            title: str,
            logger_config_path: str,
            font_path: str,
            themes_path: str,
    ):
        """
        Инициализирует приложение
        """
        self.title = title
        self.logger_config_path = logger_config_path

        self.logger = None
        self.size_manager = None
        self.node_editor = None

        self._setup_logging()
        dpg.create_context()

        self.font_manager = FontManager(Path(font_path), resource_path("").parent)
        self.theme_manager = ThemeManager(Path(themes_path))
        self.event_manager = EventManager()
        self.__last_zoom_time = 0.0


    def _setup_logging(self):
        """Настраивает систему логирования."""
        logging(logging.open_config(resource_path("logger_config.json"), False))

        debug_config = logging.open_config(resource_path("logger_debug.json"))
        group_config = logging.open_config(resource_path("logger_group.json"))
        stream_config = logging.open_config(resource_path("logger_stream.json"))

        self.logger = logging()('main', group_config)
        logging()('nodes', group_config | debug_config)
        logging()('functions', group_config | debug_config)
        logging()('events', group_config | debug_config)
        logging()('managers', group_config | debug_config)

        self.logger.info("Система логирования инициализирована.")


    def _create_ui(self):
        """Создает основной интерфейс приложения."""
        self.node_editor = NodeEditor(
            minimap=True,
            minimap_location=dpg.mvNodeMiniMap_Location_TopRight
        )

        with dpg.window(tag="Prime") as wnd:
            self.node_editor.show("Prime")

        dpg.set_primary_window("Prime", True)

        self.event_manager.add(
            EventType.MOUSE_WHEEL,
            self.__size_increase
            )
        self.logger.info("UI создан.")


    def __size_increase(self, sender, app_data: int):
        now = time()
        if now - self.__last_zoom_time < 1 / 60: return
        self.__last_zoom_time = now

        sizing_method = self.size_manager.increase if app_data > 0 else self.size_manager.reduce
        height, width = self.size_manager.get_bbox("node_editor")
        # if dpg.is_key_down(dpg.mvKey_LControl) or dpg.is_key_down(dpg.mvKey_RControl):
        #     sizing_method("Prime")

        if dpg.is_item_hovered("node_editor"):
            # Приближение увеличивает узлы, у которых размер рассчитывается абсолютно
            # для избежания накопления ошибки плавающей точки
            # С изменением позиции для имитации зума так не получиться, поэтому
            # там рассчитывается относительный ratio

            prev_size = self.font_manager.get("node_editor").size
            sizing_method("node_editor")
            actual_size = self.font_manager.get("node_editor").size
            self.node_editor.zoom(actual_size / prev_size)

        self.size_manager.set_bbox("node_editor", height, width)



    def run(self):
        """Запускает главный цикл приложения."""
        try:
            dpg.create_viewport(title=self.title)
            dpg.setup_dearpygui()
            dpg.show_viewport()
            self._create_ui()
            self.size_manager = SizeManager()
            self.node_editor.on_viewport_resize_callback()
            self.logger.info("Приложение запущено.")
            dpg.start_dearpygui()
        finally:
            dpg.destroy_context()
