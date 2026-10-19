import json
from pathlib import Path

import dearpygui.dearpygui as dpg

from Src.node_editor import NodeEditor
from Src.Config.node_list import node_list
from Src.Config.Annotations import *
from Src.Enums import *
from Src.Logging.logger_factory import Logger_factory
from Tests.DPG_test import DPGUnitTest


class test_compilation(DPGUnitTest):
    '''
    Проверка компиляции графа
    '''
    node_editor: NodeEditor

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        dpg.create_viewport(title='Custom Title')
        with open("Tests/logger_config.json") as f:
            config = json.load(f)

        log_factory = Logger_factory(config)
        cls.node_editor = NodeEditor()


    def test_simple_compilation(self):
        self.node_editor.builder.compile_graph(self.node_editor._NodeEditor__start_nodes)
        assert True


    def test_compilation(self):
        nodes_in_mock = {
            "Table data": node_list["Data & Preprocessing"]["Import data"][0],
            "To categorical": node_list["Data & Preprocessing"]["Processing Utils"][0],
            "Dense": node_list["Neural Network Layers"]["Full"][0],
            "Compile": node_list["Training"]["General"][0],
            "Fit": node_list["Training"]["General"][1],
            "Predict": node_list["Training"]["General"][2],
            "Save": node_list["Training"]["Utils"][3]
        }
        get_attr = lambda attr_name, node_id: [attribute for attribute in dpg.get_item_children(node_id, slot=1) \
                                               for field in dpg.get_item_children(attribute, slot=1)\
                                                if dpg.get_item_label(field) == attr_name][0]
        with dpg.window():
            for node in nodes_in_mock.keys():
                nodes_in_mock[node] = dpg.add_button(label=node, user_data=nodes_in_mock[node])

        # Создаём нужные узлы для пайплайна через кэллбэк,
        # чтоб добиться полной имитации
        input = dpg.get_item_children("node_editor", slot=1)[0]
        dataX = self.node_editor.drop_callback("node_editor", nodes_in_mock["Table data"])
        dense = self.node_editor.drop_callback("node_editor", nodes_in_mock["Dense"])
        dataY = self.node_editor.drop_callback("node_editor", nodes_in_mock["Table data"])
        categorical = self.node_editor.drop_callback("node_editor", nodes_in_mock["To categorical"])
        compile = self.node_editor.drop_callback("node_editor", nodes_in_mock["Compile"])
        fit = self.node_editor.drop_callback("node_editor", nodes_in_mock["Fit"])
        predict = self.node_editor.drop_callback("node_editor", nodes_in_mock["Predict"])
        save = self.node_editor.drop_callback("node_editor", nodes_in_mock["Save"])
        nodes = [input, dataX, dataY, dense, categorical, compile, fit, predict, save]

        # Соединяем их в пайплайн
        self.node_editor.link_callback("node_editor", (get_attr("shape", dataX), get_attr("shape", input)))
        self.node_editor.link_callback("node_editor", (get_attr("OUTPUT", input), get_attr("INPUT", dense)))
        self.node_editor.link_callback("node_editor", (get_attr("OUTPUT", dataY), get_attr("INPUT", categorical)))
        self.node_editor.link_callback("node_editor", (get_attr("OUTPUT", dense), get_attr("INPUT", compile)))

        self.node_editor.link_callback("node_editor", (get_attr("OUTPUT", dataX), get_attr("x", fit)))
        self.node_editor.link_callback("node_editor", (get_attr("OUTPUT", compile), get_attr("INPUT", fit)))
        self.node_editor.link_callback("node_editor", (get_attr("OUTPUT", categorical), get_attr("y", fit)))

        self.node_editor.link_callback("node_editor", (get_attr("OUTPUT", fit), get_attr("INPUT", predict)))
        self.node_editor.link_callback("node_editor", (get_attr("OUTPUT", dataX), get_attr("x", predict)))
        self.node_editor.link_callback("node_editor", (get_attr("OUTPUT", predict), get_attr("X", save)))

        # Задаём данные в ноды
        assert AString.set(dpg.get_item_children(get_attr("files", dataX), slot=1)[0], "./Tests/X.txt")
        assert AString.set(dpg.get_item_children(get_attr("files", dataY), slot=1)[0], "./Tests/y.txt")
        assert AInteger.set(dpg.get_item_children(get_attr("num_classes", categorical), slot=1)[0], 2)
        assert AInteger.set(dpg.get_item_children(get_attr("units", dense), slot=1)[0], 2)
        assert AEnum[Activations].set(dpg.get_item_children(get_attr("activation", dense), slot=1)[0], Activations.SOFTMAX)
        assert AEnum[Losses].set(dpg.get_item_children(get_attr("loss", compile), slot=1)[0], Losses.BINARY_CROSSENTROPY)
        assert AInteger.set(dpg.get_item_children(get_attr("epochs", fit), slot=1)[0], 10)

        # Компилируем
        visited = self.node_editor.builder.compile_graph(self.node_editor._NodeEditor__start_nodes)

        assert all([dpg.get_item_user_data(node) in visited for node in nodes])

        filepath: Path = Path(AString.get(dpg.get_item_children(get_attr("fname", save), slot=1)[0]))
        assert filepath.exists()
        filepath.unlink(missing_ok=True)
