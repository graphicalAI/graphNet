import json
from collections import deque
from itertools import chain
from pathlib import Path
import dearpygui.dearpygui as dpg

from Src.Utils.serialization.serializers import ProjectEncoder
from Src.Utils.serialization.deserializers import ProjectDecoder
from Src.Utils import get_userdata, clear_userdata
from Src.node_builder import NodeBuilder
from Src.Logging.logger_factory import Logger_factory


logger = Logger_factory()(__name__)


class ProjectManager:
    def __init__(
        self,
        node_editor_tag: str,
        builder: NodeBuilder,
        start_nodes: list,
        link_callback=None,
    ):
        self.node_editor_tag = node_editor_tag
        self.builder = builder
        self.start_nodes = start_nodes
        self.link_callback = link_callback

    def save_project(self, filepath: str | Path):
        """
        Сохраняет узлы холста в JSON. Порядок — обход в ширину от стартовых узлов
        (файл читаемее: корни сверху); загрузка от порядка не зависит. Связи лежат
        внутри самих узлов, в поле inputs.
        """
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self._ordered_nodes(), f, cls=ProjectEncoder, indent=4)

        logger.info(f"Проект успешно сохранён в {filepath}")

    def load_project(self, filepath: Path | str):
        """Очищает холст и восстанавливает граф через ProjectDecoder."""
        self.clear_board(recreate_input=False)

        decoder = ProjectDecoder(self._build_node, self._resolve_annotation, self._link)
        self.start_nodes.extend(decoder.load(filepath))

        logger.info(f"Проект успешно загружен из {filepath}")

    def _build_node(self, annotation) -> str | int:
        """Колбэк для ProjectDecoder: строит узел по аннотации на текущем холсте."""
        return self.builder.build_node(annotation, parent=self.node_editor_tag)

    def _resolve_annotation(self, label: str):
        """Колбэк для ProjectDecoder: NodeAnnotation по label в актуальном node_list."""
        for subgroups in self.builder.node_list.values():
            for annotations in subgroups.values():
                for annotation in annotations:
                    if annotation.label == label:
                        return annotation
        return None

    def _link(self, sender_attr: str | int, receiver_attr: str | int):
        """
        Колбэк для ProjectDecoder: создаёт связь между пинами — через link_callback
        редактора (он же обновляет incoming/outgoing узлов) либо напрямую.
        """
        if self.link_callback:
            self.link_callback(self.node_editor_tag, (sender_attr, receiver_attr))
        else:
            dpg.add_node_link(sender_attr, receiver_attr, parent=self.node_editor_tag)

    def _ordered_nodes(self) -> list:
        """Узлы холста в порядке обхода в ширину от стартовых (start_nodes покрывают и несвязанные узлы)."""
        ordered = {}
        queue = deque(self.start_nodes)

        while queue:
            node = queue.popleft()
            if node is None or node.node_tag in ordered:
                continue
            ordered[node.node_tag] = node

            queue.extend(
                get_userdata(dpg.get_item_parent(attr_id))
                for attr_id in chain.from_iterable(node.outgoing.values())
            )

        return list(ordered.values())

    def clear_board(self, recreate_input: bool = False):
        """
        Очищает холст редактора узлов перед загрузкой нового проекта.
        """
        if not (children := dpg.get_item_children(self.node_editor_tag, slot=1)):
            return

        for item in children:
            if dpg.does_item_exist(item):
                clear_userdata(item)
                dpg.delete_item(item)

        # Очищаем внутренний список узлов
        self.start_nodes.clear()
        logger.debug("Рабочая область очищена.")

        if recreate_input and self.builder:
            input_id = self.builder.build_input(self.node_editor_tag)
            self.start_nodes.append(get_userdata(input_id))
