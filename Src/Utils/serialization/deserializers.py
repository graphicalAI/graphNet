import json
from pathlib import Path
from typing import Any

import dearpygui.dearpygui as dpg

from Src.Config.Annotations import AFile, AEnum, ASequence
from Src.Enums.dpg_types import DPGType
from Src.Utils import get_userdata
from Src.Logging.logger_factory import Logger_factory


logger = Logger_factory()(__name__)


class ProjectDecoder(json.JSONDecoder):
    """
    Восстанавливает граф из JSON: узлы строятся в object_hook по мере разбора,
    связи — отдельным проходом после decode(), т.к. в файле порядок BFS, а не
    порядок, безопасный для резолва связей (отправитель может встретиться позже получателя).

    Колбэки: build_node(annotation) -> tag, resolve_annotation(label) -> NodeAnnotation | None,
    link(sender_attr, receiver_attr).
    """

    DESERIALIZERS: dict = {
        AFile: lambda hint, val: [Path(p) for p in val],
        AEnum: lambda hint, val: next((m for m in hint.source if m.value == val), None),
        ASequence: lambda hint, val: tuple(val),
    }

    def __init__(self, build_node, resolve_annotation, link):
        self.build_node = build_node
        self.resolve_annotation = resolve_annotation
        self.link = link

        self.old_to_new: dict = {}  # сохранённый tag -> tag воссозданного узла
        self.pending_links: list = []  # (receiver_tag, [link, ...]) для второго прохода

        super().__init__(object_hook=self._object_hook)

    @classmethod
    def deserialize_value(cls, hint: Any, value: Any) -> Any:
        """
        Преобразует JSON-совместимое значение обратно в исходный тип Python
        на основе словаря-диспетчера DESERIALIZERS.
        """
        if value is None:
            return None

        hint_cls = hint if isinstance(hint, type) else type(hint)

        if handler := cls.DESERIALIZERS.get(hint_cls):
            return handler(hint, value)

        return value

    def load(self, filepath: Path | str) -> list:
        """
        Читает файл и разбирает его встроенным ``json.JSONDecoder.decode()``: узлы
        строятся прямо в ``object_hook`` по мере разбора. Связи резолвятся отдельным
        проходом сразу после ``decode()``, когда все узлы уже существуют.

        Returns:
            Список стартовых узлов (без входящих связей) — их подхватывает ProjectManager.
        """
        with open(filepath, "r", encoding="utf-8") as f:
            nodes = [node for node in self.decode(f.read()) if node is not None]

        for receiver_tag, inputs in self.pending_links:
            for link in inputs:
                self._restore_link(receiver_tag, link)

        return [node for node in nodes if not node.incoming]

    def _object_hook(self, obj: dict):
        """
        Хук ``json.JSONDecoder``: вызывается для каждого разобранного JSON-объекта.
        Узлом считаем только словарь с ``__type__ == "node"`` — словари параметров и
        описания связей пропускаем как есть, их уже обработал вложенный разбор.
        """
        if obj.get("__type__") != "node":
            return obj

        return self._rebuild_node(obj)

    def _rebuild_node(self, obj: dict):
        """Строит один узел по сериализованному словарю (без связей — их ставит load вторым проходом)."""
        annotation = self.resolve_annotation(obj["label"])
        if annotation is None:
            logger.error(f"Неизвестный тип узла: {obj['label']}")
            return None

        node_tag = self.build_node(annotation)
        node = get_userdata(node_tag)

        dpg.set_item_pos(node_tag, obj["position"])
        self._apply_parameters(node, obj.get("parameters", {}))

        self.old_to_new[obj["tag"]] = node_tag
        if obj.get("inputs"):
            self.pending_links.append((node.node_tag, obj["inputs"]))

        return node

    def _apply_parameters(self, node, parameters: dict):
        """Заполняет параметры воссозданного узла сохранёнными значениями."""
        for argument in dpg.get_item_children(node.node_tag, slot=1) or []:
            name = dpg.get_item_label(argument)
            if name not in node.annotations or name not in parameters:
                continue

            parameter = node.annotations[name]
            parameter.set_value(
                argument, self.deserialize_value(parameter.hint, parameters[name])
            )

    @staticmethod
    def _find_attribute_by_label(node_tag: int | str, pin_label: str):
        """Ищет tag атрибута (пина) внутри узла по его имени."""
        if not (children := dpg.get_item_children(node_tag, slot=1)):
            return None

        for attr in children:
            if (
                DPGType(attr) == DPGType.NODE_ATTRIBUTE
                and dpg.get_item_label(attr) == pin_label
            ):
                return attr
        return None

    def _restore_link(self, receiver_tag: str | int, link: dict):
        """Восстанавливает одну входящую связь узла по описанию из его поля inputs."""
        sender_tag = self.old_to_new.get(link["sender"])
        if sender_tag is None:
            logger.warning(
                "Невозможно восстановить связь: отправитель отсутствует в проекте"
            )
            return

        sender_attr = self._find_attribute_by_label(sender_tag, link["sender_pin"])
        receiver_attr = self._find_attribute_by_label(
            receiver_tag, link["receiver_pin"]
        )
        if not (sender_attr and receiver_attr):
            logger.warning("Невозможно восстановить связь: не найден пин узла")
            return

        # link сам создаёт dpg.node_link и обновляет incoming/outgoing узлов.
        self.link(sender_attr, receiver_attr)
