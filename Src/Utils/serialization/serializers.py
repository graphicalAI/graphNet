import enum
from pathlib import Path
import json

from Src.Nodes.abstract_node import AbstractNode


class ProjectEncoder(json.JSONEncoder):
    """
    Кастомный JSON-энкодер, инкапсулирующий в себе всю логику
    сериализации сложных и неизвестных типов данных.
    """

    _SERIALIZERS: dict = {
        Path:         lambda self, obj: str(obj),
        enum.Enum:    lambda self, obj: obj.value,
        tuple:        lambda self, obj: [self.serialize(item) for item in obj],
        AbstractNode: lambda self, obj: obj.to_dict(self.serialize),
    }

    def serialize(self, obj: any) -> any:
        """
        Преобразует значение в JSON-совместимый тип.
        Для стандартных типов (str, int, float, bool, list, dict) возвращает как есть.
        Для специальных типов использует словарь-диспетчер _SERIALIZERS.
        """
        handler = self._SERIALIZERS.get(type(obj))
        if handler:
            return handler(self, obj)
        # Проверяем базовые классы (например, подклассы Enum или AbstractNode)
        for base_type, base_handler in self._SERIALIZERS.items():
            if isinstance(obj, base_type):
                return base_handler(self, obj)
        return obj

    def default(self, obj: any) -> any:
        """
        Переопределенный стандартный метод JSON-энкодера.
        Вызывается только для типов, которые стандартный энкодер не умеет обработать.
        Использует LBYL: явная проверка типа перед вызовом serialize.
        Для нераспознанных типов вызывает super().default(), чтобы получить
        правильное исключение вместо бесконечной рекурсии.
        """
        if isinstance(obj, AbstractNode):
            return self.serialize(obj)
        return super().default(obj)
