from dataclasses import dataclass
from abc import ABC
from typing import Callable, Any
import inspect
import traceback

import dearpygui.dearpygui as dpg

from Src.Logging import logging, Logger
from Src.Config.parameter import Parameter, AttrType
from Src.Config.Annotations import ANode
from Src.Enums import Themes
from Src.Managers import ThemeManager
from Src.Exceptions import NetworkException
from Src.Utils import lateinit


class AbstractNode(ABC):
    """
    Нода (узел графа), класс который используется для сохранения связей в графе, а также информации о ноде.

    Attributes:
        node_tag: str | int - индетификатор ноды (dpg.node)
        incoming: list[Node] - связи с нодами, которые подключенны к этой ноде. (Приходящие)
        outgoing: list[Node] - связи с нодами, к которым подключенна эта нода. (Уходящие)
    """

    __error_message: str = None
    __themes: ThemeManager = lateinit(ThemeManager)
    _error_id: int | str = None

    node_tag: str | int
    # Устанавливаем связи не между узлами, а между их аттрибутами
    incoming: dict[str | int, list[str | int]]
    outgoing: dict[str | int, list[str | int]]
    annotations: dict[str, Parameter]
    logic: Callable
    docs: str
    logger: Logger
    theme_name: Themes = Themes.ABSTRACT
    node_data = None

    def __init__(
        self,
        node_tag: int | str,
        annotations: dict[str:type],
        logic: Callable,
        docs: str = None,
    ):
        """
        Нода (узел графа), класс который используется для сохранения связей в графе, а также информации о ноде.

        Args:
            layer: keras.layers.Layer - слой, логику которого нода хранит.
            annotations: dict[str, type] - аннотации на аргументы, которые нужно вводить, для создания слоя.
            docs: str - документация к слою
            node_tag: str | int = None - индетификатор ноды (dpg.node)
        """
        self.node_tag = node_tag
        self.annotations = annotations
        self.logic = logic
        self.incoming = {}
        self.outgoing = {}
        self.OUTPUT = None

        if not docs:
            docs = inspect.getdoc(self.logic)
        self.docs = docs

        self.logger = logging()("nodes")

    def __repr__(self) -> str:
        return f"{self.node_tag}"

    def __str__(self) -> str:
        return f"{self.__class__.__name__} {self.node_tag} {dict(incoming=self.incoming, outgoing=self.outgoing)}"

    def __hash__(self):
        return self.node_tag

    def compile(self, kwargs: dict = None) -> bool:
        """
        Основной метод нодов, содержащий логику их работы. Тут создаются слои нейронной сети, проходит обучение и т.д. В зависимости от ноды, будет разная логика.
        """
        if not kwargs:
            kwargs = {}
        args = []
        arguments = dpg.get_item_children(self.node_tag, slot=1)

        self.logger.info(f"Компиляция ноды - {self.__class__.__name__}")
        self.logger.debug(f"Аргументы ноды - {arguments}")

        for argument in arguments:
            name = dpg.get_item_label(argument)

            if (
                name not in self.annotations
                or self.annotations[name].attr_type != AttrType.INPUT
            ):
                continue

            if name == "INPUT":
                args = self.annotations[name].get_value(argument)
                if not isinstance(args, list):
                    args = [args]
                continue

            self.logger.debug(f"Аннотация - {self.annotations[name]}")

            kwargs[name] = self.annotations[name].get_value(argument)

            self.logger.debug(kwargs)
            self.logger.debug(args)

        try:
            self.OUTPUT = self.logic(*args, **kwargs)
            self.default_theme()

        except AttributeError as ex:
            self.raise_error(ex, "Некорректные данные для узла")
            return False

        except NetworkException as ex:
            self.raise_error(ex, "Сетевая ошибка")
            return False

        except Exception as ex:
            self.raise_error(ex)
            return False

        return True

    def raise_error(
        self, error_message: str, error_message_type: str = "Неизвестная ошибка"
    ):
        self.__themes.add(self.node_tag, Themes.ERROR)

        self._error_id = dpg.generate_uuid()
        with dpg.node_attribute(
            parent=self.node_tag, attribute_type=dpg.mvNode_Attr_Static
        ):
            dpg.add_text("ОШИБКА!", tag=self._error_id)

        with dpg.tooltip(parent=self._error_id):
            dpg.add_text(f"{error_message_type}:")
            dpg.add_text(error_message)

        self.logger.warning(f"Поймана ошибка ({error_message_type}): {error_message}")
        self.logger.info(traceback.format_exc())

        if dpg.does_item_exist("fit_window"):
            dpg.delete_item("fit_window")

    def default_theme(self):
        self.__themes.apply(self.node_tag, self.theme_name, Themes.RESIZABLE)

        if self._error_id and dpg.does_item_exist(self._error_id):
            dpg.delete_item(dpg.get_item_parent(self._error_id))
        self.__error_message = None

    def to_dict(self, serialize_value: Callable[[Any], Any]) -> dict:
        """
        Собирает JSON-совместимый словарь с полным состоянием узла для сериализации:
        __type__, tag, label, position, parameters и inputs (входящие связи).

        tag узла и отправители его связей пишутся с префиксом ``node_``: это отделяет
        пространство имён сохранённых узлов от «сырых» dpg-uuid и исключает коллизии
        при восстановлении графа.

        Args:
            serialize_value: функция-конвертер для отдельных значений параметров.
        """
        param_values = {}
        for argument in dpg.get_item_children(self.node_tag, slot=1) or []:
            name = dpg.get_item_label(argument)
            if name not in self.annotations:
                continue

            parameter = self.annotations[name]

            if parameter.attr_type in (AttrType.INPUT, AttrType.STATIC):
                if isinstance(parameter.hint, ANode) or parameter.hint is ANode:
                    continue
                param_values[name] = serialize_value(parameter.get_value(argument))

        inputs = [
            {
                "sender": f"node_{dpg.get_item_parent(sender_attr)}",
                "sender_pin": dpg.get_item_label(sender_attr),
                "receiver_pin": dpg.get_item_label(receiver_attr),
            }
            for receiver_attr, senders in self.incoming.items()
            for sender_attr in senders
        ]

        label = (
            self.node_data.label
            if self.node_data
            else dpg.get_item_label(self.node_tag)
        )

        return {
            "__type__": "node",
            "tag": f"node_{self.node_tag}",
            "label": label,
            "position": dpg.get_item_pos(self.node_tag),
            "parameters": param_values,
            "inputs": inputs,
        }


@dataclass
class node_link:
    """
    Класс для dpg.add_node_link, указывает какие аттрибуты узлов связываются.
    """

    outgoing: str | int
    incoming: str | int
