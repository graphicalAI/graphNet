import dearpygui.dearpygui as dpg

from Tests.DPG_test import DPGUnitTest
from Src.Managers import ThemeManager
from Src.Enums import Themes




class test_ThemeManager(DPGUnitTest):
    '''
    Проверка менеджера тем
    '''


    @classmethod
    def setUpClass(cls):
        """
        Загружает темы перед выполнением тестов.
        """
        super().setUpClass()


    def test_load_themes(self):
        """
        Проверяет, что конфигурация тем успешно загружена.
        """
        assert ThemeManager._themes_config != {}


    def test_apply_theme(self):
        """
        Проверяет применение одной темы к элементу.
        """
        with dpg.window():
            button_id = dpg.add_button(label="Test Button")

        ThemeManager.apply_theme(button_id, Themes.ERROR)

        theme_key = (Themes.ERROR,)
        assert theme_key in ThemeManager._created_themes

        theme_id = ThemeManager._created_themes[theme_key]
        assert dpg.get_item_theme(button_id) == theme_id


    def test_add_theme(self):
        """
        Проверяет добавление темы к уже существующим темам элемента.
        """
        with dpg.window():
            button_id = dpg.add_button(label="Test Button")

        ThemeManager.apply_theme(button_id, Themes.DEFAULT)
        ThemeManager.add_theme(button_id, Themes.ERROR)

        assert Themes.DEFAULT in ThemeManager._item_themes[button_id]
        assert Themes.ERROR in ThemeManager._item_themes[button_id]
        assert len(ThemeManager._item_themes[button_id]) == 2


    def test_remove_theme(self):
        """
        Проверяет удаление темы у элемента.
        """
        with dpg.window():
            button_id = dpg.add_button(label="Test Button")

        ThemeManager.apply_theme(button_id, Themes.DEFAULT, Themes.ERROR, Themes.COMPILE)
        ThemeManager.remove_theme(button_id, Themes.ERROR)

        item_themes = ThemeManager._item_themes.get(button_id, [])
        assert Themes.DEFAULT in item_themes
        assert Themes.ERROR not in item_themes
        assert Themes.COMPILE in item_themes
        assert len(item_themes) == 2

        ThemeManager.remove_theme(button_id, Themes.DEFAULT, Themes.COMPILE)
        assert dpg.get_item_theme(button_id) == None


    def test_get_theme(self):
        """
        Проверяет получение (и кэширование) тем.
        """
        theme_id_1 = ThemeManager.get_theme(Themes.COMPILE)
        assert (Themes.COMPILE,) in ThemeManager._created_themes

        theme_id_2 = ThemeManager.get_theme(Themes.COMPILE)
        assert theme_id_1 == theme_id_2


    def test_theme_combination_override(self):
        """
        Проверяет, что стили тем правильно переопределяются при их комбинации.
        """
        with dpg.window():
            with dpg.node_editor():
                node_id = dpg.add_node(label="Test Node")

        ThemeManager.apply_theme(node_id,Themes.DEFAULT, Themes.ERROR)

        theme_key = (Themes.DEFAULT, Themes.ERROR)
        assert theme_key in ThemeManager._created_themes

        combined_theme_id = ThemeManager._created_themes[theme_key]
        assert dpg.get_item_theme(node_id) == combined_theme_id

        assert True