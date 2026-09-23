from typing import Callable
from itertools import chain
import traceback

import dearpygui.dearpygui as dpg

from Src.Logging import logging, Logger
from Src.Nodes import AbstractNode, InputLayerNode
from Src.Config.node_list import NodeAnnotation, Annotation
from Src.Utils import lateinit, set_userdata, get_userdata, clear_userdata
from Src.Managers import SizeManager, FontManager, ThemeManager
from Src.Enums import Themes




class NodeBuilder:
    '''
    Класс реализующий логику связывания Keras и Нодов.

    Attributes:
        factory: InputsFactory - фабрика конвертации аннотаций в инпуты
        layers_list: dict[str: AbstractNode] - список слоёв с параметрами, которые использовать в конструкторе
    '''
    card_width: int = Annotation.BASE_WIDTH + 115
    node_list: dict[str, dict[str, list[NodeAnnotation]]]
    delete_callback: Callable
    logger: Logger = lateinit(logging(), "nodes")
    theme_manager: ThemeManager = lateinit(ThemeManager)
    font_manager: FontManager = lateinit(FontManager)
    size_manager: SizeManager = lateinit(SizeManager)


    def __init__(self,
                 node_list: dict[str: AbstractNode],
                 delete_callback: Callable,):
        '''
        Args:
            layers_list: dict[str: AbstractNode] - список слоёв с параметрами, которые использовать в конструкторе
        '''
        self.delete_callback = delete_callback
        self.node_list = node_list

    def build_list(self, parent: str | int) -> str | int:
        '''
        Построить список (tree_node) из списка слоёв. Используется для панели слева в конструкторе.

        Args:
            parent: str | int - родительский элемент в котором создать список.

        Returns:
            str | int - индетификатор списка
        '''
        with dpg.group(parent=parent) as list:
            for anchor in self.node_list.keys():
                with dpg.tree_node(label=anchor) as tree_anchor:

                    for subanchor in self.node_list[anchor].keys():
                        with dpg.tree_node(label=subanchor) as tree_subanchor:

                            for node in self.node_list[anchor][subanchor]:
                              self.__build_list_node(node_data=node, parent=tree_subanchor)

        return list

    def __build_list_node(self, node_data: NodeAnnotation, parent: int | str) -> int | str:
        '''
        Построение элемента списка нод, визуально имитирующего ноду в редакторе.

        Args:
            node_data: NodeAnnotation - аннотация ноды из node_list
            parent:    int | str      - родительский элемент (tree_node подкатегории)

        Returns:
            int | str - идентификатор созданной группы
        '''
        card_id = dpg.generate_uuid()

        params = [(label, param) for label, param in node_data.annotations.items() if label != 'INPUT']

        items_count = len(params)
        if node_data.input: items_count += 1
        if node_data.output: items_count += 1

        with dpg.child_window(
            tag=card_id,
            parent=parent,
            auto_resize_y=True,
            auto_resize_x=True,
            no_scrollbar=True,
            border=True # Костыль, нужно заменить с использованием set_userdata
        ) as card:

            with dpg.group() as drag_group:
                with dpg.drag_payload(parent=drag_group, drag_data=card_id):
                    dpg.add_text(node_data.label)

                header_button = dpg.add_button(label=node_data.label, width=-1)

                dpg.add_spacer(height=2)

                with dpg.group(indent=8) as body_group:
                    if node_data.input:
                        dpg.add_text("INPUT")

                    dpg.add_spacer(height=1)

                    with dpg.tree_node(label="Docs"):
                        dpg.add_text(node_data.docs, wrap=self.card_width - 30)

                    for label, param in params:
                        parameter = param.hint.build(label=label, parent=body_group, width=Annotation.BASE_WIDTH, enabled=False)

                    delete_button = dpg.add_button(label="Delete")

                    if node_data.output: dpg.add_text("OUTPUT")

        set_userdata(card_id, value=node_data)

        self.theme_manager.apply(card, Themes.CARD)
        self.theme_manager.apply(body_group, Themes.CARD)
        self.theme_manager.apply(delete_button, Themes.DEFAULT)
        self.theme_manager.apply(header_button, node_data.node_type.theme_name, Themes.CARD)
        dpg.add_spacer(height=10)
        return card_id


    def build_node(self, node_data: NodeAnnotation, parent: str | int) -> str | int:
        '''
        Построение dpg.node из класса AbstractNode. Используется, для создания новых нодов в редакторе. Ноды берутся из user_data в списке слева.

        Args:
            node: AbstractNode - нода из которой создать dpg.node
            parent: str | int - родитель, внутри которого создать ноду. Чаще всего это dpg.node_editor.

        Returns:
            str | int - индетификатор новой dpg.node.
        '''
        node_id = dpg.generate_uuid()
        node: AbstractNode = node_data.node_type(node_id, **node_data.kwargs)

        node.node_data = node_data

        with dpg.node(label=node_data.label, parent=parent, tag=node_id):
            set_userdata(node_id, value=node)
            if node_data.input:
                node_data.input.build(label="INPUT", parent=node_id)

            with dpg.node_attribute(attribute_type=dpg.mvNode_Attr_Static):
                with dpg.tree_node(label="Docs"):
                    dpg.add_text(node.docs)

            for label, attribute in node.annotations.items():
                if label == 'INPUT': continue
                self.logger.debug(f"Attribute label: {label}")
                attr = attribute.build(label=label, parent=node_id)

            with dpg.node_attribute(label="Delete", attribute_type=dpg.mvNode_Attr_Static):
                delete = dpg.add_button(label="Delete", callback=lambda: self.delete_callback(node_id))

            if node_data.output:
                node_data.output.build(label="OUTPUT", parent=node_id)

        self.theme_manager.apply(delete, Themes.DEFAULT)
        node.default_theme()

        font = self.font_manager.get("node_editor")
        min_font = get_userdata("node_editor", 'min_font_size')
        self.font_manager.set(node_id, font.name, font.size)
        self.size_manager.transform(node_id, font.size / min_font.size, True)

        return node_id


    def build_input(self, parent: str | int) -> str | int:
        '''
        Особенный метод, реализующий построение слоя входа.

        Args:
            parent: str | int - родительский элемент в котором построить нод. Чаще всего node_editor.
            shape: tuple[int] - форма данных, передаётся в входной слой.

        Returns:
            str | int - индетификатор новой ноды
        '''
        layer = None
        for group in self.node_list.values():
            for group2 in group.values():
                for node in group2:
                    if node.node_type is not InputLayerNode: continue
                    layer = node
                    break

        node_id = self.build_node(layer, parent=parent)

        return node_id


    def compile_graph(self, start_nodes: list[AbstractNode]) -> set[AbstractNode]:
        '''
        Компиляция графа, от его концов. Работает через обход в ширину. Вызывает метод compile у нода, если все ноды, пришедшие к нему уже скомпилированы. Начинает с нодов, у которых нет входов.
        '''

        visited = set()
        queue = start_nodes[:]
        self.logger.info("Началась сборка графа.")
        status = True

        while queue:
            self.logger.debug(f"Текущая очередь - {queue}")
            current_node = queue.pop(0)
            self.logger.debug(f"Текущая нода - {current_node}")

            if all([get_userdata(dpg.get_item_parent(value)) in visited \
                for value in chain(*current_node.incoming.values())]):
                self.logger.debug("Нода подошла.")

                try:
                    status = current_node.compile()

                except Exception as ex:
                    self.raise_error(ex)
                    status = False

                if not status: break

                self.logger.debug(f"resulted OUTPUT - {current_node.OUTPUT}")

                for attr_id in chain(*current_node.outgoing.values()):
                    neightbor: AbstractNode = get_userdata(dpg.get_item_parent(attr_id))
                    if neightbor not in queue:
                        queue.append(neightbor)

                visited.add(current_node)

        return visited


    def raise_error(self, error_message: str, error_message_type: str = "Неизвестная ошибка"):
        with dpg.window(label="Непревиденная ошибка", modal=True, no_title_bar=True, \
                        no_resize=True, no_move=True) as error_window:
            dpg.add_text("Произошла непредвиденная ошибка, сообщите пожалуйста разработчикам.")
            dpg.add_text(f"{error_message_type}:")
            dpg.add_text(error_message)
            dpg.add_text(traceback.format_exc())
            dpg.add_button(label="Close", callback=lambda: dpg.configure_item(error_window, show=False))

        # TODO: Прикрепить модальное окно на середину при изменении размера
        dpg.set_item_pos(error_window, [
            (dpg.get_viewport_width() - dpg.get_item_width(error_window)) // 4,
            (dpg.get_viewport_height() - dpg.get_item_height(error_window)) // 3
        ])

        self.logger.warning(f"Поймана ошибка ({error_message_type}): {error_message}")
