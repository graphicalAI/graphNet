import enum

import dearpygui.dearpygui as dpg

from Src.Config.Annotations.annotation import Annotation
from Src.Enums import DPGType


class AEnum(Annotation):
    """
    Аннотация для создания выпадающего списка (dpg.add_combo).
    Используется для полей с предопределенным набором строковых значений.
    """


    def __class_getitem__(cls, enum_source: type):
        """
        Позволяет создавать объект AEnum с помощью синтаксиса AEnum[YourEnumClass].
        Не вызывает ошибок, просто передает источник в конструктор.
        """
        return cls(source=enum_source)


    def __init__(self, source: enum.Enum):
        """
        Args:
            source (type): Источник данных. Может быть списком строк
                                        или классом, унаследованным от enum.Enum.
        """
        self.source = source
        self.items = [member.value for member in source]


    def build(self, *args, **kwargs):
        """
        Создает dpg.add_combo с предопределенными элементами.
        """
        kwargs = Annotation.check_kwargs(dpg.add_combo, kwargs)

        kwargs['items'] = self.items
        kwargs['default_value'] = self.items[0]

        return dpg.add_combo(*args, **kwargs)


    def get(self, input_id: int | str):
        """
        Получает текущее выбранное значение из dpg.add_combo.
        """
        if DPGType(input_id) != DPGType.COMBO:
            raise Exception(f"Incompatable item for AEnum.get - {dpg.get_item_type(input_id)}") 
        
        return dpg.get_value(input_id)


    def set(self, input_id: str | int, value: enum.Enum) -> bool:
        """
        Устанавливает значение для dpg.add_combo.
        """
        if not isinstance(value, enum.Enum) or \
            value.value not in self.items or \
            DPGType(input_id) != DPGType.COMBO:
            return False

        dpg.set_value(input_id, value.value)
        return True
    
