from pathlib import Path
import json
from collections import defaultdict

import dearpygui.dearpygui as dpg

from Src.Managers.font_manager.font import FontUnit
from Src.Utils import singleton, lateinit, get_children
from Src.Logging import logging
from Src.Utils import set_userdata, get_userdata



@singleton
class FontManager:
    __logger = lateinit(logging(), 'managers')
    __registry: str | int
    fonts: dict[str, dict[int, FontUnit]]
    default: FontUnit


    def __init__(self, path_config: Path, base_path: Path = None):
        if not path_config.exists():
            self.__logger.error(f"Не существует конфигационного файла {path_config}")
            return

        config = json.load(path_config.open())
        self.fonts = defaultdict(defaultdict)
        self.default = None
        for font_name, font_config in config.items():

            if base_path is not None:
                font_config['path'] = str(base_path / font_config['path'])
            font_config['sizes'].sort()
            font_ids = [dpg.generate_uuid() for _ in font_config['sizes']]

            font = FontUnit(font_config['path'], font_config['hints'],
                            font_name, font_config['sizes'][0], font_ids[0])
            self.fonts[font_name][font_config['sizes'][0]] = font

            for size, curr_id, next_id in zip(font_config['sizes'][1:], font_ids[:-1], font_ids[1:]):

                font: FontUnit = get_userdata(curr_id)
                next_font = FontUnit(Path(font_config['path']).resolve(), font_config['hints'],
                                     font_name, size, next_id, prev = font)
                font.next = next_font
                self.fonts[font_name][size] = next_font

            if not font_config.get('default'): continue
            if self.default:
                self.__logger.error(f"Конфигурация шрифтов имеет несколько стандартных шрифтов! Установите один.")

            self.default = self.fonts[font_name][font_config.get('default_size', 14)]
            dpg.bind_font(self.default.id)

        self.__logger.info("Шрифты инициализированы!")


    def __set(self, id: str | int, font: FontUnit, children: bool = True):
        items = {id}
        if children: items|= get_children(id)
        min_font = next(iter(self.fonts[font.name].values()))

        for item in items:
            dpg.bind_item_font(item, font.id)
            if get_userdata(item, 'min_font_size'): continue
            set_userdata(item, 'min_font_size', min_font)


    def get(self, item: str | int) -> FontUnit:
        font = get_userdata(dpg.get_item_font(item) or self.default.id)
        if not get_userdata(item, 'min_font_size'):
            min_font = next(iter(self.fonts[font.name].values()))
            set_userdata(item, 'min_font_size', min_font)
        return font


    def increase(self, item: str | int, children: bool = True) -> FontUnit:
        font: FontUnit = self.get(item)
        self.__set(item, font.next, children)
        return font.next


    def reduce(self, item: str | int, children: bool = True) -> FontUnit:
        font: FontUnit = self.get(item)
        self.__set(item, font.prev, children)
        return font.prev


    def set(self, item: str | int, font_name: str = None, size: int = None, children: bool = True) -> FontUnit:
        font_name = font_name or self.default.name
        font_size = size or self.default.size
        font: FontUnit = self.fonts[font_name][font_size]
        self.__set(item, font, children)
        return font
