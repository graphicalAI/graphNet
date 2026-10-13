"""Exercise the real GraphNet graph on 1,000 MNIST PNGs (requires a desktop)."""

import argparse
import csv
import json
import os
from pathlib import Path
import sys

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=PROJECT / ".cache/mnist-images")
    parser.add_argument("--interactive", action="store_true", help="Keep the graph and sample viewer open")
    args = parser.parse_args()
    root = args.dataset.resolve()
    # App assets use paths relative to the checkout.
    os.chdir(PROJECT)

    import dearpygui.dearpygui as dpg
    import numpy as np
    import keras
    from app import App
    from Src.Config.node_list import node_list
    from Src.Enums import ColorMode, Activations, Losses
    from Src.Utils import get_userdata

    with (root / "train/metadata.csv").open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    rows = sorted(rows, key=lambda row: int(row["source_id"]))[:1000]
    assert len(rows) == 1000
    with (root / "graph-smoke.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["file_name", "label", "source_id"])
        writer.writeheader()
        for row in reversed(rows):
            writer.writerow({**row, "file_name": "train/" + row["file_name"]})

    keras.utils.set_random_seed(17)
    app = App("GraphNet — MNIST validation", "Assets/logger_config.json",
              "Assets/fonts_config.json", "Assets/themes.json")
    editor = app.node_editor
    annotations = {annotation.label: annotation for category in node_list.values()
                   for group in category.values() for annotation in group}

    def build(label):
        tag = editor.builder.build_node(annotations[label], "node_editor")
        return get_userdata(tag)

    def port(node, name):
        return next(tag for tag in dpg.get_item_children(node.node_tag, 1)
                    if dpg.get_item_label(tag) == name)

    def set_parameter(node, name, value):
        assert node.annotations[name].set_value(port(node, name), value)

    def connect(source, output, target, input_name):
        assert editor.link_callback("node_editor", (port(source, output), port(target, input_name)))

    dataset = build("Image dataset")
    input_node = editor._NodeEditor__start_nodes[0]
    flatten = build("Flatten")
    dense = build("Dense")
    compile_node = build("Compile model")
    fit = build("Fit model")
    nodes = [dataset, input_node, flatten, dense, compile_node, fit]
    editor._NodeEditor__start_nodes[:] = nodes
    set_parameter(dataset, "root", str(root))
    set_parameter(dataset, "metadata_file", str(root / "graph-smoke.csv"))
    set_parameter(dataset, "color_mode", ColorMode.GRAYSCALE)
    set_parameter(dense, "units", 10)
    set_parameter(dense, "activation", Activations.SOFTMAX)
    set_parameter(compile_node, "loss", Losses.SPARSE_CATEGORICAL_CROSSENTROPY)
    set_parameter(fit, "epochs", 1)
    connect(dataset, "shape", input_node, "shape")
    connect(input_node, "OUTPUT", flatten, "INPUT")
    connect(flatten, "OUTPUT", dense, "INPUT")
    connect(dense, "OUTPUT", compile_node, "INPUT")
    connect(compile_node, "OUTPUT", fit, "INPUT")
    connect(dataset, "X", fit, "x")
    connect(dataset, "y", fit, "y")
    for node, position in zip(nodes, [(10, 10), (490, 10), (490, 170), (800, 10), (1110, 10), (1110, 260)]):
        dpg.set_item_pos(node.node_tag, position)

    dpg.set_viewport_width(1450)
    dpg.set_viewport_height(900)
    dpg.show_viewport()
    for _ in range(3):
        dpg.render_dearpygui_frame()
    visited = editor.builder.compile_graph(editor._NodeEditor__start_nodes)
    assert all(node in visited for node in nodes), "Graph compilation stopped"
    assert dataset.X.shape == (1000, 28, 28, 1)
    assert dataset.y.shape == (1000,)
    assert dataset.class_names == list("0123456789")
    assert fit.history.shape == (1,) and np.isfinite(fit.history).all()

    preview_group = dpg.get_item_children(port(dataset, "preview"), 1)[0]
    viewer = get_userdata(preview_group)
    viewer.open()
    texture = viewer.texture
    viewer.move(1)
    viewer.move(-1)
    viewer.open()
    assert viewer.texture == texture
    for _ in range(3):
        dpg.render_dearpygui_frame()

    report = {"samples": 1000, "X_shape": list(dataset.X.shape), "y_shape": list(dataset.y.shape),
              "classes": dataset.class_names, "epochs": 1, "loss": float(fit.history[0]),
              "visited_nodes": len(visited), "preview_reuses_texture": True}
    if args.interactive:
        dpg.start_dearpygui()
    owned = (viewer.window, viewer.registry, viewer.texture)
    # Exercise lazy dialogs as well, without leaving them open.
    dialogs = []
    for name in ("root", "metadata_file"):
        field = dpg.get_item_children(port(dataset, name), 1)[0]
        dataset.annotations[name].hint._choose(field)
        dialog = get_userdata(field)["dialog"]
        dialogs.append(dialog)
        dpg.configure_item(dialog, show=False)
    editor.delete_node(dataset.node_tag)
    assert all(not dpg.does_item_exist(item) for item in (*owned, *dialogs))
    report["owned_resources_released"] = True
    (root / "graph-validation.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report), flush=True)
    dpg.destroy_context()


if __name__ == "__main__":
    main()
