import pytest
from pathlib import Path
from itertools import chain
import enum
import json
import dearpygui.dearpygui as dpg

from Src.Utils.serialization.serializers import ProjectEncoder
from Src.Utils.serialization.deserializers import ProjectDecoder
from Src.Utils.serialization.project_manager import ProjectManager
from Src.Nodes.abstract_node import AbstractNode
from Src.Config import NodeAnnotation
from Src.Config.parameter import Parameter, AttrType
from Src.Config.Annotations import AFile, AEnum, ASequence, ANode
from Src.node_builder import NodeBuilder
from Src.Utils import get_userdata


class DummyEnum(enum.Enum):
    A = "A"
    B = "B"


def _pin(node_id, label):
    """tag пина узла по его label."""
    return next(x for x in dpg.get_item_children(node_id, slot=1) if dpg.get_item_label(x) == label)


def _incoming(node):
    """Плоский список входящих связей узла."""
    return list(chain.from_iterable(node.incoming.values()))

def test_project_encoder_basic():
    encoder = ProjectEncoder()
    assert encoder.serialize(123) == 123
    assert encoder.serialize("str") == "str"
    assert encoder.serialize([1, 2]) == [1, 2]

def test_project_encoder_serialize_path():
    encoder = ProjectEncoder()
    path = Path("/dummy/path")
    assert encoder.serialize(path) == str(path)

def test_project_encoder_serialize_enum():
    encoder = ProjectEncoder()
    assert encoder.serialize(DummyEnum.A) == "A"

def test_project_encoder_serialize_tuple():
    encoder = ProjectEncoder()
    assert encoder.serialize((1, "2", DummyEnum.B)) == [1, "2", "B"]


def test_deserialize_value_afile():
    val = ["/path1", "/path2"]
    res = ProjectDecoder.deserialize_value(AFile, val)
    assert isinstance(res, list)
    assert res[0] == Path("/path1")
    assert res[1] == Path("/path2")

def test_deserialize_value_aenum():
    val = "A"
    res = ProjectDecoder.deserialize_value(AEnum[DummyEnum], val)
    assert res == DummyEnum.A

def test_deserialize_value_asequence():
    val = [1, 2, 3]
    res = ProjectDecoder.deserialize_value(ASequence, val)
    assert res == (1, 2, 3)

def test_deserialize_parameter_value():
    assert ProjectDecoder.deserialize_value(ASequence, [1, 2, 3]) == (1, 2, 3)
    assert ProjectDecoder.deserialize_value(None, None) is None
    assert ProjectDecoder.deserialize_value(int, 42) == 42 # Fallback


def test_project_manager_save_and_load_roundtrip(node_editor, tmp_path):
    """
    Проверяет полный цикл: сборка графа -> save_project -> load_project
    восстанавливает узлы, их позиции и связь между ними.
    """
    anode_out = NodeAnnotation(
        label="Producer",
        node_type=AbstractNode,
        logic=lambda: 42,
        annotations={"x": Parameter(AttrType.OUTPUT, ANode[object])},
    )
    anode_in = NodeAnnotation(
        label="Consumer",
        node_type=AbstractNode,
        logic=lambda x: x,
        annotations={"x": Parameter(AttrType.INPUT, ANode[object])},
    )
    node_editor.builder.node_list = {"Test": {"Test": [anode_out, anode_in]}}

    # Убираем стартовый узел "Input", чтобы не зависеть от него в этом тесте
    node_editor.project_manager.clear_board(recreate_input=False)

    node_id_out = node_editor.builder.build_node(anode_out, "node_editor")
    node_id_in = node_editor.builder.build_node(anode_in, "node_editor")
    node_editor._NodeEditor__start_nodes += [get_userdata(node_id_out), get_userdata(node_id_in)]

    attr_out = next(a for a in dpg.get_item_children(node_id_out, slot=1) if dpg.get_item_label(a) == "x")
    attr_in = next(a for a in dpg.get_item_children(node_id_in, slot=1) if dpg.get_item_label(a) == "x")
    node_editor.link_callback("node_editor", (attr_out, attr_in))

    dpg.set_item_pos(node_id_out, [123, 45])

    filepath = tmp_path / "project.json"
    node_editor.project_manager.save_project(str(filepath))

    with open(filepath) as f:
        saved = json.load(f)
    assert len(saved) == 2
    assert sum(len(node["inputs"]) for node in saved) == 1

    node_editor.project_manager.load_project(str(filepath))

    nodes_after = dpg.get_item_children("node_editor", slot=1)
    assert len(nodes_after) == 2

    labels_after = {dpg.get_item_label(n): n for n in nodes_after}
    assert set(labels_after) == {"Producer", "Consumer"}
    assert dpg.get_item_pos(labels_after["Producer"]) == [123, 45]

    producer = get_userdata(labels_after["Producer"])
    consumer = get_userdata(labels_after["Consumer"])
    assert list(producer.outgoing.values())
    assert list(consumer.incoming.values())


def test_project_manager_roundtrip_shortcut_edge(node_editor, tmp_path):
    """
    Граф со «срезающей» связью: A->C и A->B->C. Обход в ширину может поставить C
    в файл раньше B, поэтому загрузка обязана восстанавливать связи независимо от
    порядка узлов в файле. После round-trip должны выжить все три связи.
    """
    a = NodeAnnotation(
        label="A", node_type=AbstractNode, logic=lambda: 1,
        annotations={"out": Parameter(AttrType.OUTPUT, ANode[object])},
    )
    b = NodeAnnotation(
        label="B", node_type=AbstractNode, logic=lambda inp: inp,
        annotations={
            "inp": Parameter(AttrType.INPUT, ANode[object]),
            "out": Parameter(AttrType.OUTPUT, ANode[object]),
        },
    )
    c = NodeAnnotation(
        label="C", node_type=AbstractNode, logic=lambda inp: inp,
        annotations={"inp": Parameter(AttrType.INPUT, ANode[object])},
    )
    node_editor.builder.node_list = {"T": {"T": [a, b, c]}}

    node_editor.project_manager.clear_board(recreate_input=False)

    id_a = node_editor.builder.build_node(a, "node_editor")
    id_b = node_editor.builder.build_node(b, "node_editor")
    id_c = node_editor.builder.build_node(c, "node_editor")
    node_editor._NodeEditor__start_nodes.append(get_userdata(id_a))

    # порядок создания: сначала «срезающая» A->C, затем A->B и B->C
    node_editor.link_callback("node_editor", (_pin(id_a, "out"), _pin(id_c, "inp")))
    node_editor.link_callback("node_editor", (_pin(id_a, "out"), _pin(id_b, "inp")))
    node_editor.link_callback("node_editor", (_pin(id_b, "out"), _pin(id_c, "inp")))

    filepath = tmp_path / "shortcut.json"
    node_editor.project_manager.save_project(str(filepath))
    node_editor.project_manager.load_project(str(filepath))

    by_label = {
        dpg.get_item_label(n): get_userdata(n)
        for n in dpg.get_item_children("node_editor", slot=1)
    }
    assert set(by_label) == {"A", "B", "C"}

    assert len(_incoming(by_label["A"])) == 0
    assert len(_incoming(by_label["B"])) == 1   # A -> B
    assert len(_incoming(by_label["C"])) == 2   # A -> C и B -> C
