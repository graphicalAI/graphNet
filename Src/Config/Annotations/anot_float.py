import dearpygui.dearpygui as dpg

from Src.Config.Annotations.annotation import Annotation
from Src.Enums import DPGType




class AFloat(Annotation):


    @staticmethod
    def build(*args, **kwargs):
        return dpg.add_input_float(**Annotation.check_kwargs(dpg.add_input_float, kwargs))
    

    @staticmethod
    def get(input_id: int | str):
        if DPGType(input_id) != DPGType.INPUT_FLOAT:
            raise Exception(f"Incompatable item for AFloat.get - {dpg.get_item_type(input_id)}")
        
        return dpg.get_value(input_id)
    

    @staticmethod
    def set(input_id: str| int, value: float) -> bool: 
        if not isinstance(value, float) or DPGType(input_id) != DPGType.INPUT_FLOAT:
            return False
        
        dpg.set_value(input_id, value)
        return True
  
