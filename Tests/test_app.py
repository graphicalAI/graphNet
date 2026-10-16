import dearpygui.dearpygui as dpg

from app import App
from Src.node_editor import NodeEditor


def build(setup: bool = True) -> App:
    return App(
        title="Test",
        logger_config_path="Assets/logger_config.json",
        font_path="Assets/fonts_config.json",
        themes_path="Assets/themes.json",
        setup=setup,
    )


def test_initializes_without_creating_a_window(monkeypatch):
    """App(setup=False) выполняет весь код приложения, но не создаёт окно.

    Собранное приложение проверяется на машине без графического окружения,
    поэтому содержимое окна должно собираться без OpenGL.
    """
    def refuse():
        raise AssertionError("окно создаваться не должно")

    monkeypatch.setattr(dpg, "setup_dearpygui", refuse)

    application = build(setup=False)

    assert application.node_editor is None
    assert application.size_manager is None

    application.build_ui()

    assert isinstance(application.node_editor, NodeEditor)
    assert application.size_manager is not None


def test_setup_flag_only_controls_the_window(monkeypatch):
    """По умолчанию окно создаётся, как и раньше."""
    calls = []
    monkeypatch.setattr(App, "setup_window", lambda self: calls.append(self))

    build()
    assert len(calls) == 1, "окно должно создаваться по умолчанию"

    calls.clear()
    build(setup=False)
    assert calls == [], "окно не должно создаваться при setup=False"