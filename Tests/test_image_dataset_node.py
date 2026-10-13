"""Exercise image datasets through the actual node builder and graph ports."""

import dearpygui.dearpygui as dpg
import numpy as np
from PIL import Image

from Src.Config.node_list import node_list
from Src.Config.Annotations.anot_path import APath
from Src.Utils import get_userdata
from Src.Config.Annotations.anot_image_dataset import preview_pixels


def test_preview_handles_wide_and_fractional_ranges_without_changing_X():
    for values in ([0, 65535], [0, 0.5, 1], [-2, 0, 2]):
        pixels = np.asarray(values, dtype=np.float32).reshape(1, -1, 1)
        original = pixels.copy()
        display, note = preview_pixels(pixels)
        assert display.min() == 0 and display.max() == 255
        assert "X is unchanged" in note
        np.testing.assert_array_equal(pixels, original)
    mnist = np.asarray([0, 73, 255], dtype=np.float32).reshape(1, -1, 1)
    display, note = preview_pixels(mnist)
    np.testing.assert_array_equal(display, mnist)
    assert not note


def build(editor, label="Image dataset"):
    annotation = next(node for groups in node_list.values()
                      for nodes in groups.values() for node in nodes
                      if node.label == label)
    node = get_userdata(editor.builder.build_node(annotation, "node_editor"))
    editor._NodeEditor__start_nodes.append(node)
    return node


def attribute(node, name):
    return next(item for item in dpg.get_item_children(node.node_tag, slot=1)
                if dpg.get_item_label(item) == name)


def set_value(node, name, value):
    assert node.annotations[name].set_value(attribute(node, name), value)


def get_value(node, name):
    return node.annotations[name].get_value(attribute(node, name))


def link(editor, source, output, target, input_name):
    result = editor.link_callback("node_editor", (
        attribute(source, output), attribute(target, input_name)))
    assert result is not None


def dataset(root, classes=("cat", "dog")):
    for index, label in enumerate(classes):
        folder = root / label
        folder.mkdir(parents=True)
        Image.new("RGB", (5, 3), (index * 100, 20, 30)).save(folder / "sample.png")
    return root


def viewer(node):
    group = dpg.get_item_children(attribute(node, "preview"), slot=1)[0]
    return get_userdata(group)


def test_real_image_dataset_ports_feed_fit_and_input(node_editor, tmp_path):
    images = build(node_editor)
    fit = build(node_editor, "Fit model")
    input_node = build(node_editor, "Input")
    set_value(images, "root", dataset(tmp_path / "images"))
    link(node_editor, images, "X", fit, "x")
    link(node_editor, images, "y", fit, "y")
    link(node_editor, images, "shape", input_node, "shape")

    assert images.compile()
    assert get_value(fit, "x") is images.X
    assert get_value(fit, "y") is images.y
    assert get_value(input_node, "shape") == (3, 5, 3)
    assert images.X.dtype == np.float32
    assert images.y.dtype == np.int64
    assert input_node.compile()
    assert tuple(input_node.OUTPUT.layer.shape) == (None, 3, 5, 3)
    assert not any(dpg.get_item_label(item) == "OUTPUT"
                   for item in dpg.get_item_children(images.node_tag, slot=1))
    assert viewer(images).result is images.OUTPUT
    assert viewer(images).texture is None  # GPU allocation is lazy.
    assert dpg.get_item_configuration(viewer(images).button)["enabled"]


def test_class_names_link_preserves_codes_for_incomplete_split(node_editor, tmp_path):
    train = build(node_editor)
    test = build(node_editor)
    set_value(train, "root", dataset(tmp_path / "train"))
    set_value(test, "root", dataset(tmp_path / "test", ("dog",)))
    link(node_editor, train, "class_names", test, "classes")

    visited = node_editor.builder.compile_graph([train])

    assert visited == {train, test}
    assert train.class_names == test.class_names == ["cat", "dog"]
    assert test.y.tolist() == [1]
    assert test.class_names[test.y[0]] == test.OUTPUT.samples[0].label


def test_failed_reload_clears_outputs_and_stops_downstream(node_editor, tmp_path, monkeypatch):
    images = build(node_editor)
    input_node = build(node_editor, "Input")
    root = dataset(tmp_path / "images")
    set_value(images, "root", root)
    link(node_editor, images, "shape", input_node, "shape")
    assert node_editor.builder.compile_graph([images]) == {images, input_node}
    successful = images.OUTPUT

    calls = []
    original_compile = input_node.compile
    monkeypatch.setattr(input_node, "compile", lambda: calls.append(True) or original_compile())
    (root / "dog" / "sample.png").write_bytes(b"not an image")

    assert node_editor.builder.compile_graph([images]) == set()
    assert calls == []
    assert images.OUTPUT is images.X is images.y is images.preview is None
    assert images.class_names == []
    assert tuple(images.shape) == (0, 0, 0)
    assert tuple(get_value(images, "shape")) == (0, 0, 0)
    assert viewer(images).result is None
    assert not dpg.get_item_configuration(viewer(images).button)["enabled"]
    assert dpg.does_item_exist(images._error_id)

    Image.new("RGB", (5, 3), (255, 0, 0)).save(root / "dog" / "sample.png")
    assert node_editor.builder.compile_graph([images]) == {images, input_node}
    assert calls == [True]
    assert images.OUTPUT is not successful
    assert viewer(images).result is images.OUTPUT
    assert not dpg.does_item_exist(images._error_id)


def test_independent_picker_dialogs_and_disposal(node_editor, tmp_path):
    first, second = build(node_editor), build(node_editor)
    set_value(first, "root", dataset(tmp_path / "first"))
    set_value(second, "root", dataset(tmp_path / "second"))
    assert first.compile() and second.compile()
    first_view, second_view = viewer(first), viewer(second)
    groups = [dpg.get_item_children(attribute(node, "root"), slot=1)[0]
              for node in (first, second)]
    for node, group in zip((first, second), groups):
        node.annotations["root"].hint._choose(group)
    dialogs = [get_userdata(group)["dialog"] for group in groups]
    assert dialogs[0] != dialogs[1]
    assert all(dpg.does_item_exist(dialog) for dialog in dialogs)
    # Single-path annotation must retain a string and reject legacy file lists.
    assert isinstance(APath.get(groups[0]), str)
    assert not APath.set(groups[0], [str(tmp_path)])

    node_editor.delete_node(first.node_tag)

    assert not dpg.does_item_exist(dialogs[0])
    assert dpg.does_item_exist(dialogs[1])
    assert first_view.result is None
    assert second_view.result is second.OUTPUT
    assert get_userdata(groups[0]) is None
    assert first.X is first.y is first.OUTPUT is None
    assert second.X.shape == (2, 3, 5, 3)
    node_editor.delete_node(second.node_tag)
    assert not dpg.does_item_exist(dialogs[1])
    assert second_view.result is None


def test_node_ui_invalid_size_and_explicit_csv_override(node_editor, tmp_path):
    images = build(node_editor)
    root = dataset(tmp_path / "images")
    (root / "metadata.csv").write_text("wrong,header\n", encoding="utf-8")
    (root / "labels.csv").write_text(
        "path;target;source\ndog/sample.png;second;custom\ncat/sample.png;first;custom\n",
        encoding="utf-8")
    set_value(images, "root", root)
    set_value(images, "metadata_file", root / "labels.csv")
    set_value(images, "path_column", "path")
    set_value(images, "label_column", "target")
    set_value(images, "delimiter", ";")
    assert images.compile()
    assert images.class_names == ["first", "second"]
    assert images.OUTPUT.samples[0].metadata == {"source": "custom"}
    set_value(images, "target_size", (0, 4))
    assert not images.compile()
    assert images.X is None
    set_value(images, "target_size", (4, 7))
    assert images.compile()
    assert images.X.shape == (2, 4, 7, 3)
