import dearpygui.dearpygui as dpg

from Src.Config.Annotations.annotation import Annotation
from Src.Enums import DPGType




class ABoolean(Annotation):


    @staticmethod
    def build(*args, **kwargs):
        return dpg.add_checkbox(**Annotation.check_kwargs(dpg.add_checkbox, kwargs))
    

    @staticmethod
    def get(input_id: int | str):
        if DPGType(input_id) != DPGType.CHECKBOX:
            raise Exception(f"Incompatable item for ABoolean.get - {dpg.get_item_type(input_id)}")
        
        return dpg.get_value(input_id)
    

    @staticmethod
    def set(input_id: str| int, value: bool) -> bool:
        if not isinstance(value, bool) or DPGType(input_id) != DPGType.CHECKBOX:
            return False
        
        dpg.set_value(input_id, value)
        return True
  
