import dearpygui.dearpygui as dpg

from Src.node_editor import NodeEditor
from Src.Config import NodeAnnotation, Parameter
from Src.Config.Annotations import ANode
from Src.Nodes import AbstractNode
from Src.Enums.attr_type import AttrType
from Src.Utils import get_userdata, set_userdata


def test_initialize(node_editor):
    assert isinstance(node_editor, NodeEditor)


def test_drop_callback(node_editor):
    node = NodeAnnotation(
                label="Example",
                node_type=AbstractNode,
                logic = lambda x:x,
                annotations={}
                )

    with dpg.window():
        btn = dpg.add_button(label=node.label)
        set_userdata(btn, value=node)

    nodes_count = len(dpg.get_item_children("node_editor", slot=1))

    node_id = node_editor.drop_callback("node_editor", btn)
    assert dpg.get_item_pos(node_editor._NodeEditor__start_nodes[-1].node_tag) == [8,8]
    assert len(dpg.get_item_children("node_editor", slot=1)) == nodes_count + 1
    assert dpg.get_item_children("node_editor", slot=1)[0] == node_id
    assert dpg.get_item_label(node_id) == "Example"


def test_hovered_nodes_input_order(node_editor, monkeypatch):
    node = NodeAnnotation(
                label="Example",
                node_type=AbstractNode,
                logic = lambda x:x,
                annotations={}
                )

    node_id1 = node_editor.builder.build_node(node, "node_editor")
    node_id2 = node_editor.builder.build_node(node, "node_editor")
    hovered_node = node_id1
    monkeypatch.setattr(dpg, "is_item_hovered", lambda item: item == hovered_node)

    click_handler = next(
        item for item in dpg.get_all_items()
        if dpg.get_item_type(item) == "mvAppItemType::mvMouseClickHandler"
    )
    dpg.get_item_callback(click_handler)(0, None)

    node_order = dpg.get_item_children("node_editor", slot=1)
    assert node_order[0] == node_id1

    hovered_node = node_id2
    release_handler = next(
        item for item in dpg.get_all_items()
        if dpg.get_item_type(item) == "mvAppItemType::mvMouseReleaseHandler"
    )
    dpg.get_item_callback(release_handler)(0, None)

    node_order = dpg.get_item_children("node_editor", slot=1)
    assert node_order[:2] == [node_id2, node_id1]


def test_input_order_preserves_links(node_editor, monkeypatch):
    with dpg.node(parent="node_editor") as lower:
        lower_pin = dpg.add_node_attribute(attribute_type=dpg.mvNode_Attr_Output)
    with dpg.node(parent="node_editor") as upper:
        upper_pin = dpg.add_node_attribute(attribute_type=dpg.mvNode_Attr_Input)
    link = dpg.add_node_link(lower_pin, upper_pin, parent="node_editor")
    nodes = dpg.get_item_children("node_editor", slot=1)
    monkeypatch.setattr(dpg, "is_item_hovered", lambda item: item == upper)
    move_handler = next(item for item in dpg.get_all_items()
                        if dpg.get_item_type(item) == "mvAppItemType::mvMouseMoveHandler")

    dpg.get_item_callback(move_handler)(0, None)

    assert dpg.get_item_children("node_editor", slot=1) == [upper] + [n for n in nodes if n != upper]
    assert dpg.get_item_children("node_editor", slot=0) == [link]


def test_pointer_outside_nodes_preserves_input_order(node_editor, monkeypatch):
    nodes = dpg.get_item_children("node_editor", slot=1)
    monkeypatch.setattr(dpg, "is_item_hovered", lambda item: False)
    node_editor._NodeEditor__sync_node_input_order(0, None)
    assert dpg.get_item_children("node_editor", slot=1) == nodes


def test_link_callback(node_editor):
    anode1 = NodeAnnotation(
                label="Example",
                node_type=AbstractNode,
                logic = lambda x:x,
                annotations={
                    "x": Parameter(AttrType.OUTPUT, ANode[object])
                    }
                )
    anode2 = NodeAnnotation(
                label="Example In 1",
                node_type=AbstractNode,
                logic = lambda x: x,
                annotations={
                    "x": Parameter(AttrType.INPUT, ANode[object])
                }
    )
    anode3 = NodeAnnotation(
                label="Example In 2",
                node_type=AbstractNode,
                logic = lambda x: x,
                annotations={
                    "x": Parameter(AttrType.INPUT, ANode[object])
                }
    )

    node_id1 = node_editor.builder.build_node(anode1, "node_editor")
    node_id2 = node_editor.builder.build_node(anode2, "node_editor")
    node_id3 = node_editor.builder.build_node(anode3, "node_editor")

    node1: AbstractNode = get_userdata(node_id1)
    node2: AbstractNode = get_userdata(node_id2)
    node3: AbstractNode = get_userdata(node_id3)
    node_editor._NodeEditor__start_nodes += [node1, node2, node3]

    node_attr1 = None
    node_attr2 = None
    node_attr3 = None

    for attribute in dpg.get_item_children(node_id1, slot=1):
        for field in dpg.get_item_children(attribute, slot=1):
            if dpg.get_item_label(field) == "x":
                node_attr1 = attribute
                break

    for attribute in dpg.get_item_children(node_id2, slot=1):
        for field in dpg.get_item_children(attribute, slot=1):
            if dpg.get_item_label(field) == "x":
                node_attr2 = attribute
                break

    for attribute in dpg.get_item_children(node_id3, slot=1):
        for field in dpg.get_item_children(attribute, slot=1):
            if dpg.get_item_label(field) == "x":
                node_attr3 = attribute
                break

    node_editor.link_callback("node_editor", (node_attr1, node_attr2))
    node_editor.link_callback("node_editor", (node_attr1, node_attr3))

    assert node2 not in node_editor._NodeEditor__start_nodes
    assert node3 not in node_editor._NodeEditor__start_nodes

    assert isinstance(node1.outgoing[node_attr1], list)

    assert len(node1.outgoing[node_attr1]) == 2

    assert node_attr2 in node1.outgoing[node_attr1]
    assert node_attr3 in node1.outgoing[node_attr1]

    assert node_attr1 in node2.incoming[node_attr2]
    assert node_attr1 in node3.incoming[node_attr3]


def test_delink_callback(node_editor):
    anode1 = NodeAnnotation(
                label="Example",
                node_type=AbstractNode,
                logic = lambda x:x,
                annotations={
                    "x": Parameter(AttrType.OUTPUT, ANode[object])
                    }
                )
    anode2 = NodeAnnotation(
                label="Example",
                node_type=AbstractNode,
                logic = lambda x:x,
                annotations={
                    "x": Parameter(AttrType.INPUT, ANode[object])
                    }
                )

    node_id1 = node_editor.builder.build_node(anode1, "node_editor")
    node_id2 = node_editor.builder.build_node(anode2, "node_editor")
    node1: AbstractNode = get_userdata(node_id1)
    node2: AbstractNode = get_userdata(node_id2)
    node_editor._NodeEditor__start_nodes += [node1, node2]
    node_attr1 = None
    node_attr2 = None

    for attribute in dpg.get_item_children(node_id1, slot=1):
        for field in dpg.get_item_children(attribute, slot=1):
            if dpg.get_item_label(field) == "x":
                node_attr1 = attribute
                break

    for attribute in dpg.get_item_children(node_id2, slot=1):
        for field in dpg.get_item_children(attribute, slot=1):
            if dpg.get_item_label(field) == "x":
                node_attr2 = attribute
                break

    node_editor.link_callback("node_editor", (node_attr1, node_attr2))

    assert get_userdata(node_attr1) == [node_attr2]
    assert get_userdata(node_attr2) == [node_attr1]

    link_id = dpg.get_item_children("node_editor", slot=0)[-1]

    node_editor.delink_callback("node_editor", link_id)

    assert node_attr1 not in node1.outgoing
    assert node_attr2 not in node2.incoming

    assert get_userdata(node_attr1) == []
    assert get_userdata(node_attr2) == []


def test_delete_node(node_editor):
    anode1 = NodeAnnotation(
                label="Example",
                node_type=AbstractNode,
                logic = lambda x:x,
                annotations={
                    "x": Parameter(AttrType.OUTPUT, ANode[object])
                    }
                )
    anode2 = NodeAnnotation(
                label="Example",
                node_type=AbstractNode,
                logic = lambda x:x,
                annotations={
                    "x": Parameter(AttrType.INPUT, ANode[object])
                    }
                )

    node_id1 = node_editor.builder.build_node(anode1, "node_editor")
    node_id2 = node_editor.builder.build_node(anode2, "node_editor")
    node1: AbstractNode = get_userdata(node_id1)
    node2: AbstractNode = get_userdata(node_id2)
    node_editor._NodeEditor__start_nodes += [node1, node2]
    node_attr1 = None
    node_attr2 = None

    for attribute in dpg.get_item_children(node_id1, slot=1):
        for field in dpg.get_item_children(attribute, slot=1):
            if dpg.get_item_label(field) == "x":
                node_attr1 = attribute
                break

    for attribute in dpg.get_item_children(node_id2, slot=1):
        for field in dpg.get_item_children(attribute, slot=1):
            if dpg.get_item_label(field) == "x":
                node_attr2 = attribute
                break

    node_editor.link_callback("node_editor", (node_attr1, node_attr2))

    links_count = len(dpg.get_item_children("node_editor", slot=0))
    nodes_count = len(dpg.get_item_children("node_editor", slot=1))

    node_editor.delete_node(node_id1)

    assert len(dpg.get_item_children("node_editor", slot=0)) == links_count - 1
    assert len(dpg.get_item_children("node_editor", slot=1)) == nodes_count - 1
    assert node_attr2 not in node2.incoming
    assert node2 in node_editor._NodeEditor__start_nodes


def test_node_editor_tag_in_dpg(node_editor):
    assert dpg.does_item_exist("node_editor")


def test_drop_callback_returns_node_id(node_editor):
    node = NodeAnnotation(
        label="Example",
        node_type=AbstractNode,
        logic=lambda x: x,
        annotations={}
    )

    with dpg.window():
        btn = dpg.add_button(label=node.label)
        set_userdata(btn, value=node)

    node_id = node_editor.drop_callback("node_editor", btn)

    assert node_id in dpg.get_all_items()
