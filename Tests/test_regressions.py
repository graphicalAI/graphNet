import re
import tempfile
from pathlib import Path
from unittest import mock

import numpy as np
import keras
import dearpygui.dearpygui as dpg
from PIL import Image

from Src.node_builder import NodeBuilder
from Src.Config.node_list import node_list
from Src.Config.Annotations import AString, AEnum
from Src.Enums import Losses, Optimizers, Metrics, Datasets, ColorMode
from Src.Nodes import AbstractNode, LayerNode, LayerResult
from Tests.DPG_test import DPGUnitTest


def find_node(label: str):
    for group in node_list.values():
        for nodes in group.values():
            for node in nodes:
                if node.label == label: return node
    raise KeyError(label)


class test_regressions(DPGUnitTest):
    builder: NodeBuilder
    editor: int | str


    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.builder = NodeBuilder(node_list, lambda node_id: None)
        cls.editor = dpg.add_node_editor(parent=cls.parent)


    @staticmethod
    def get_attr(node_id: int | str, name: str) -> int | str:
        for attribute in dpg.get_item_children(node_id, slot=1):
            if dpg.get_item_label(attribute) == name: return attribute
        raise KeyError(name)


    def build(self, label: str) -> AbstractNode:
        node_id = self.builder.build_node(find_node(label), parent=self.editor)
        node = dpg.get_item_user_data(node_id)
        node.errors = []
        node.raise_error = lambda error, *args: node.errors.append(error)
        return node


    def link(self, node_out, node_in):
        attr_out = self.get_attr(node_out.node_tag, "OUTPUT")
        attr_in = self.get_attr(node_in.node_tag, "INPUT")
        dpg.set_item_user_data(attr_in, (dpg.get_item_user_data(attr_in) or []) + [attr_out])


    def make_input(self, shape: tuple[int]) -> AbstractNode:
        node = self.build("Dense")
        tensor = keras.Input(shape=shape)
        node.OUTPUT = LayerResult(tensor, {tensor})
        return node


    def test_every_layer_builds(self):
        layer_nodes = [node for group in node_list.values() for nodes in group.values()
                       for node in nodes if issubclass(node.node_type, LayerNode)]
        assert layer_nodes

        for annotation in layer_nodes:
            with self.subTest(layer=annotation.label):
                dims = re.search(r"(\d)D$", annotation.label)
                shape = (8,) * int(dims.group(1)) + (3,) if dims else (8, 3)

                node = self.build(annotation.label)
                inputs = 2 if annotation.label in ("Add", "Concatenate") else 1
                for _ in range(inputs):
                    self.link(self.make_input(shape), node)

                assert node.compile(), node.errors
                assert isinstance(node.OUTPUT.layer, keras.KerasTensor)

                if "Pooling" in annotation.label:
                    assert node.OUTPUT.layer.shape[1] == 4, node.OUTPUT.layer.shape


    def test_losses_optimizers_metrics(self):
        for enum, getter in ((Losses, keras.losses.get),
                             (Optimizers, keras.optimizers.get),
                             (Metrics, keras.metrics.get)):
            for member in enum:
                with self.subTest(enum=enum.__name__, value=member.value):
                    assert getter(member.value) is not None


    def test_images_data(self):
        with tempfile.TemporaryDirectory() as folder:
            for i in range(3):
                Image.new("RGB", (10, 12), (i * 40, 0, 0)).save(Path(folder) / f"{i}.png")

            node = self.build("Images data")
            field = dpg.get_item_children(self.get_attr(node.node_tag, "files"), slot=1)[0]
            assert AString.set(field, folder)
            mode = dpg.get_item_children(self.get_attr(node.node_tag, "color_mode"), slot=1)[0]
            assert AEnum[ColorMode].set(mode, ColorMode.RGB)

            assert node.compile(), node.errors

        assert node.OUTPUT.shape == (3, 12, 10, 3)
        assert node.shape == (12, 10, 3)
        assert node.annotations["shape"].get_value(self.get_attr(node.node_tag, "shape")) == [12, 10, 3]


    def test_dataset(self):
        data = ((np.zeros((6, 28, 28)), np.zeros((6,))), (np.zeros((2, 28, 28)), np.zeros((2,))))

        node = self.build("Load Dataset")
        field = dpg.get_item_children(self.get_attr(node.node_tag, "dataset"), slot=1)[0]
        assert AEnum[Datasets].set(field, Datasets.MNIST)

        with mock.patch("keras.datasets.mnist.load_data", return_value=data), \
             mock.patch("Src.Nodes.dataset_node.socket.create_connection"):
            assert node.compile(), node.errors

        assert node.shape == (28, 28)
        assert node.X_train.shape == (6, 28, 28)
        assert node.y_test.shape == (2,)
        assert node.annotations["shape"].get_value(self.get_attr(node.node_tag, "shape"))[-2:] == [28, 28]
