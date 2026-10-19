import unittest

import dearpygui.dearpygui as dpg

from Src.Managers import ThemeManager


class DPGUnitTest(unittest.TestCase):
    '''
    Класс реализующий создание контекста и его разрушение, для тестирование элементов DPG
    '''

    @classmethod
    def setUpClass(cls):
        cls.context = dpg.create_context()
        ThemeManager._created_themes.clear()
        ThemeManager._item_themes.clear()
        cls.parent = "Tests"
        cls.window = dpg.add_window(tag=cls.parent)
        ThemeManager.load_themes("Assets/themes.json")
        return super().setUpClass()
    

    @classmethod
    def tearDownClass(cls):
        dpg.destroy_context()
        return super().tearDownClass()