from pathlib import Path

import dearpygui.dearpygui as dpg

from Src.Config.Annotations.annotation import Annotation
from Src.Utils import get_userdata, set_userdata, clear_userdata


class APath(Annotation):
    """A single editable path, with a lazily opened file/directory dialog."""

    def __init__(self, directory=False):
        self.directory = directory

    def build(self, *args, **kwargs):
        parent = kwargs.get("parent", 0)
        enabled = kwargs.get("enabled", True)
        with dpg.group(parent=parent, label=kwargs.get("label", "")) as group:
            field = dpg.add_input_text(label=kwargs.get("label", ""),
                                       width=kwargs.get("width", self.BASE_WIDTH), enabled=enabled)
            dpg.add_button(label="Choose folder…" if self.directory else "Choose CSV…",
                           enabled=enabled, callback=lambda: self._choose(group))
        set_userdata(group, value={"field": field, "dialog": None})
        owner = get_userdata(dpg.get_item_parent(parent)) if parent else None
        if hasattr(owner, "register_cleanup"):
            owner.register_cleanup(lambda: self.dispose(group))
        return group

    def _choose(self, group):
        state = get_userdata(group)
        if state["dialog"] is None:
            def selected(sender, app_data):
                self.set(group, app_data["file_path_name"])
                dpg.configure_item(sender, show=False)

            with dpg.file_dialog(directory_selector=self.directory, show=False,
                                 modal=True, width=700, height=450, callback=selected) as dialog:
                if not self.directory:
                    dpg.add_file_extension(".csv")
                    dpg.add_file_extension(".*")
            state["dialog"] = dialog
        dpg.configure_item(state["dialog"], show=True)

    @staticmethod
    def get(input_id):
        return dpg.get_value(get_userdata(input_id)["field"])

    @staticmethod
    def set(input_id, value):
        if not isinstance(value, (str, Path)):
            return False
        dpg.set_value(get_userdata(input_id)["field"], str(value))
        return True

    @staticmethod
    def dispose(input_id):
        state = get_userdata(input_id)
        if state and state["dialog"] is not None and dpg.does_item_exist(state["dialog"]):
            dpg.delete_item(state["dialog"])
        clear_userdata(input_id)
