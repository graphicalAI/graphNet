import dearpygui.dearpygui as dpg

from Src.Config.Annotations.annotation import Annotation
from Src.Enums import DPGType




class AInteger(Annotation):


    @staticmethod
    def build(*args, **kwargs):
        return dpg.add_input_int(**Annotation.check_kwargs(dpg.add_input_int, kwargs))
    

    @staticmethod
    def get(input_id: int | str):
        if DPGType(input_id) != DPGType.INPUT_INT:
            raise Exception(f"Incompatable item for AInteger.get - {dpg.get_item_type(input_id)}") 
        
        return dpg.get_value(input_id)
    

    @staticmethod
    def set(input_id: str| int, value: int) -> bool:
        if not isinstance(value, int) or DPGType(input_id) != DPGType.INPUT_INT:
            return False
        
        dpg.set_value(input_id, value)
        return True 
    
