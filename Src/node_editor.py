import dearpygui.dearpygui as dpg

from Src.Nodes import AbstractNode, node_link
from Src.node_builder import NodeBuilder
from Src.Logging import logging, Logger
from Src.Config.node_list import node_list, NodeAnnotation
from Src.Config.Annotations import ANode
from Src.Utils.serialization.project_manager import ProjectManager
from Src.Utils import lateinit, get_userdata, set_userdata, clear_userdata
from Src.Managers import EventManager, ThemeManager
from Src.Enums import EventType, Themes


class NodeEditor:
    '''
    Класс реализующий логику управления нодами.

    Attributes:
        logger: Logger - логировщик
        builder: NodeBuilder - построитель узлов
        project_manager: ProjectManager - менеджер сохранения/загрузки проекта
    '''
    __logger: Logger = lateinit(logging(), 'main')
    builder: NodeBuilder
    project_manager: ProjectManager
    events: EventManager = lateinit(EventManager)
    themes: ThemeManager = lateinit(ThemeManager)
    __stage_tag: str | int
    __group_tag: str | int
    __start_nodes: list[AbstractNode]


    @classmethod
    def get_mouse_pos(self):
        # Реализовать создание нода, через обычные координаты мыши не получится
        # потому что координаты в node_editor отличаются от координат мыши
        # поэтому координаты размещения нового нода рассчитываются относительно уже стоящего
        pos = dpg.get_mouse_pos(local=False)
        ref_node = dpg.get_item_children("node_editor", slot=1)[0]
        ref_screen_pos = dpg.get_item_rect_min(ref_node)
        ref_grid_pos = dpg.get_item_pos(ref_node)

        NODE_PADDING = (8, 8)

        pos[0] = pos[0] - (ref_screen_pos[0] - NODE_PADDING[0]) + ref_grid_pos[0]
        pos[1] = pos[1] - (ref_screen_pos[1] - NODE_PADDING[1]) + ref_grid_pos[1]
        return pos


    def __init__(self, *args, **kwargs):
        '''
        Вызвать окно, для создания графа.

        Args:
            *args, **kwargs - передаются в dpg.node_editor
        '''
        self.builder = NodeBuilder(node_list, self.delete_node)
        self.__stage_tag = dpg.generate_uuid()
        self.__group_tag = dpg.generate_uuid()
        self.__start_nodes = []

        self.project_manager = ProjectManager("node_editor", self.builder, self.__start_nodes, self.link_callback)

        self.events.add(EventType.VIEWPORT_RESIZE, self.on_viewport_resize_callback)

        with dpg.file_dialog(directory_selector=False, show=False, callback=self._on_save_file_selected, tag="save_project_dialog", width=600, height=400):
            dpg.add_file_extension(".json", color=(255, 255, 0, 255))
            dpg.add_file_extension(".*")

        with dpg.file_dialog(directory_selector=False, show=False, callback=self._on_load_file_selected, tag="load_project_dialog", width=600, height=400):
            dpg.add_file_extension(".json", color=(0, 255, 0, 255))
            dpg.add_file_extension(".*")

        with dpg.stage(tag=self.__stage_tag):
            # Делим окно на 2, чтоб слева были блоки, а справа конструктор графа
            with dpg.group(horizontal=True, tag=self.__group_tag) as group:

                self.builder.build_list(parent=group)

                # Именно в группу задаём drop_callback, который создаёт ноду по перетягиванию её с окна справа
                with dpg.group(tag="editor_group", drop_callback=self.drop_callback):

                    # Используем редактор нодов из DearPyGUI
                    with dpg.node_editor(*args, tag="node_editor", callback=self.link_callback, \
                                        delink_callback=self.delink_callback, **kwargs):

                        input_id = self.builder.build_input("node_editor")
                        self.__start_nodes.append(get_userdata(input_id))

                    with dpg.group(horizontal=True):
                        dpg.add_button(label="Запустить",
                                       callback = lambda: self.builder.compile_graph(self.__start_nodes))
                        dpg.add_button(label="Сохранить проект",
                                      callback = lambda: dpg.show_item("save_project_dialog"))
                        dpg.add_button(label="Загрузить проект",
                                      callback = lambda: dpg.show_item("load_project_dialog"))
                        dpg.add_button(label="Очистить доску",
                                      callback = lambda: self.project_manager.clear_board(recreate_input=True))

        self.themes.apply("node_editor", Themes.DEFAULT)
        self.on_viewport_resize_callback()


    def on_viewport_resize_callback(self, *args, **kwargs):
        '''
        Callback для изменения размера node_editor'a
        '''
        if dpg.does_item_exist('node_editor'):
            dpg.configure_item('node_editor', height=dpg.get_viewport_height()*0.9)


    def drop_callback(self, sender: str | int, app_data: str | int) -> str | int:
        '''
        Функция, которая выполняется, при перетягивания блока в окно редакторования графа. Создаём новую ноду в окне.

        Args:
            sender: str | int - зачастую является окном редакторивания графа (dpg.node_editor)
            app_data: str | int - элемент, который перетащили.
        '''
        self.__logger.debug(f"На вход пришло {sender}, {app_data}, {get_userdata(app_data)}")

        pos = self.get_mouse_pos()

        self.__logger.info(f"Узел поставлен на позиции - {pos}")

        node_data: NodeAnnotation = get_userdata(app_data)
        node_id = self.builder.build_node(node_data, parent="node_editor")
        dpg.set_item_pos(node_id, pos)

        # Мы только создали узел и у него ещё нет связей
        self.__start_nodes.append(get_userdata(node_id))

        self.__logger.debug(f"Start nodes: {self.__start_nodes}")

        return node_id


    def link_callback(self, sender: str | int, app_data: tuple[str | int, str | int]) -> str | int:
        '''
        Функция, которая вызывается, когда создаётся новая связь между нодами.

        Args:
            sender: int | str - зачастую является окном редакторивания графа (dpg.node_editor)
            app_data: tuple(str | int, str | int) - исходящие и приходящие атрибуты нодов.
        '''
        self.__logger.debug(f"На вход пришло {app_data}")

        node_out: AbstractNode = get_userdata(dpg.get_item_parent(app_data[0]))
        node_in: AbstractNode = get_userdata(dpg.get_item_parent(app_data[1]))

        # Проверка при связывании, что правильные узлы связываются
        accaptable: ANode = node_in.annotations[dpg.get_item_label(app_data[1])].hint
        if not isinstance(node_out, accaptable.node_type):
            self.__logger.warning(f"Некорректная попытка связывания узлов: {node_out} -> {node_in}({dpg.get_item_label(app_data[1])}) должно быть {accaptable.node_type}")
            return
        # Проверка, что не больше одной связи, если нужно
        if accaptable.single and get_userdata(app_data[1]):
            self.__logger.warning(f"Некорректная попытка связывания узлов: {node_out} -> {node_in}({dpg.get_item_label(app_data[1])}) связей не может быть больше 1!")
            return

        self.__logger.debug(f"Node_out - {dpg.get_item_label(dpg.get_item_parent(app_data[0]))}")

        link_id = dpg.add_node_link(app_data[0], app_data[1], parent=sender)
        set_userdata(link_id, value=node_link(app_data[0], app_data[1]))

        self.__logger.debug(f"Связи до: {node_out} {node_in}")

        data_in: list | None = get_userdata(app_data[1])
        if not data_in: data_in = []
        data_in.append(app_data[0])

        set_userdata(app_data[1], value=data_in)

        data_out: list | None = get_userdata(app_data[0])
        if not data_out: data_out = []
        data_out.append(app_data[1])
        set_userdata(app_data[0], value=data_out)

        node_out.outgoing[app_data[0]] = data_out
        node_in.incoming[app_data[1]] = data_in

        if node_in in self.__start_nodes: self.__start_nodes.remove(node_in)

        self.__logger.debug(f"Связи после: {node_out} {node_in}")
        self.__logger.debug(f"Start nodes: {self.__start_nodes}")

        return link_id


    def delink_callback(self, sender: int | str, app_data: int | str):
        '''
        Функция, которая вызывается, когда убирается связь между нодами.

        Args:
            sender: int | str - зачастую является окном редакторивания графа (dpg.node_editor)
            app_data: str | int - связь между нодами (dpg.add_node_link)
        '''
        link: node_link = get_userdata(app_data)

        self.delink(link.outgoing, link.incoming)

        clear_userdata(app_data)
        dpg.delete_item(app_data)


    def delink(self, attr_outgoing: str | int, attr_incoming: str | int):
        self.__logger.debug(f"Связи до: {attr_outgoing} {attr_incoming}")

        node_out: AbstractNode = get_userdata(dpg.get_item_parent(attr_outgoing))
        node_in: AbstractNode = get_userdata(dpg.get_item_parent(attr_incoming))

        node_out.outgoing[attr_outgoing].remove(attr_incoming)
        node_in.incoming[attr_incoming].remove(attr_outgoing)

        set_userdata(attr_outgoing, value=node_out.outgoing[attr_outgoing])
        set_userdata(attr_incoming, value=node_in.incoming[attr_incoming])

        if not node_out.outgoing[attr_outgoing]: del node_out.outgoing[attr_outgoing]
        if not node_in.incoming[attr_incoming]: del node_in.incoming[attr_incoming]

        if not node_in.incoming: self.__start_nodes.append(node_in)

        self.__logger.debug(f"Связи после: {attr_outgoing} {attr_incoming}")
        self.__logger.debug(f"Start nodes: {self.__start_nodes}")


    def delete_node(self, node_id: str | int):
        '''
        Функция для удаления нода, вместе с его связями.

        Args:
            node_id: str | int - индетификатор нода, которого нужно удалить (dpg.node)
        '''
        node: AbstractNode = get_userdata(node_id)
        if len(dpg.get_item_children("node_editor", slot=1)) == 1 and \
            dpg.get_item_children("node_editor", slot=1)[0] == node_id:
            node.raise_error("Нельзя удалять узел, когда он один на поле!",
                             "Некорректное действие пользователя")
            return

        # Удаляем связи с этим узлом

        incoming = node.incoming.copy()
        outgoing = node.outgoing.copy()

        for attr_in in incoming.keys():
            for attr_out in incoming[attr_in]:
                self.delink(attr_out, attr_in)

        for attr_out in outgoing.keys():
            for attr_in in outgoing[attr_out]:
                self.delink(attr_out, attr_in)

        if node in self.__start_nodes: self.__start_nodes.remove(node)

        clear_userdata(node_id)

        del node
        dpg.delete_item(node_id)

        self.__logger.debug(f"Start nodes: {self.__start_nodes}")


    def show(self, parent: str | int):
        '''
        Отобразить элемент.

        Args:
            parent: str | int - родительское окно в котором отобразить.
        '''
        dpg.move_item(self.__group_tag, parent=parent)


    def hide(self):
        '''
        Спрятать элемент
        '''
        dpg.move_item(self.__group_tag, parent=self.__stage_tag)


    def zoom(self, ratio: float):
        zoom_ratio = ratio - 1
        nodes = dpg.get_item_children("node_editor", slot=1)
        pos = self.get_mouse_pos()

        for node_id in nodes:
            if not isinstance(get_userdata(node_id), AbstractNode): continue

            node_pos = dpg.get_item_pos(node_id)
            node_pos[0] += (node_pos[0] - pos[0]) * zoom_ratio
            node_pos[1] += (node_pos[1] - pos[1]) * zoom_ratio
            dpg.set_item_pos(node_id, node_pos)


    def _on_save_file_selected(self, sender: str | int, app_data: dict):
        '''
        Callback для файлового менеджера при сохранении проекта.
        '''
        filepath = app_data['file_path_name']
        self.__logger.info(f"Сохранение в файл: {filepath}")
        self.project_manager.save_project(filepath)


    def _on_load_file_selected(self, sender: str | int, app_data: dict):
        '''
        Callback для файлового менеджера при выгрузке (загрузке) проекта.
        '''
        filepath = app_data['file_path_name']
        self.__logger.info(f"Загрузка из файла: {filepath}")
        self.project_manager.load_project(filepath)
