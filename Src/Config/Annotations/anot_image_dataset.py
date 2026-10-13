import dearpygui.dearpygui as dpg
import numpy as np
from PIL import Image

from Src.Config.Annotations.annotation import Annotation
from Src.Utils import get_userdata, set_userdata, clear_userdata


def preview_pixels(pixels):
    """Map only the display copy to bytes; retain the dataset's numeric range."""
    low, high = float(pixels.min()), float(pixels.max())
    scaled = low < 0 or high > 255 or 0 < high <= 1
    if scaled:
        if high > low:
            pixels = (pixels.astype(np.float64) - low) * (255.0 / (high - low))
        else:
            pixels = np.full(pixels.shape, 255 if high > 0 else 0)
    return np.clip(pixels, 0, 255).astype(np.uint8), (
        f"\nPreview scaled from range {low:g}..{high:g}; X is unchanged" if scaled else "")


class DatasetPreview:
    """One viewer and one fixed-size texture owned by a dataset node."""

    SIZE = 256

    def __init__(self, group, enabled):
        self.result = None
        self.index = 0
        self.window = self.registry = self.texture = None
        self.summary = dpg.add_text("Dataset not loaded", parent=group, wrap=256)
        self.button = dpg.add_button(label="View samples", parent=group,
                                     enabled=False, callback=self.open)
        self.enabled = enabled

    def set(self, result):
        self.result = result
        self.index = 0
        text = "Dataset not loaded"
        if result is not None:
            text = f"Images: {len(result.samples)} | Classes: {len(result.class_names)}"
            if result.warnings:
                text += "\n" + "\n".join(result.warnings)
        dpg.set_value(self.summary, text)
        dpg.configure_item(self.button, enabled=self.enabled and result is not None)
        if self.window is not None:
            if result is None:
                dpg.configure_item(self.window, show=False)
                dpg.set_value(self.texture, np.zeros(self.SIZE * self.SIZE * 4, dtype=np.float32))
                dpg.set_value(self.details, "Dataset not loaded")
                dpg.set_value(self.classes, "")
            else:
                self.refresh()

    def open(self, *args):
        if self.result is None:
            return
        if self.window is None:
            with dpg.texture_registry(show=False) as self.registry:
                self.texture = dpg.add_dynamic_texture(
                    self.SIZE, self.SIZE,
                    np.zeros(self.SIZE * self.SIZE * 4, dtype=np.float32))
            with dpg.window(label="Image dataset - samples", width=660, height=620,
                            on_close=lambda: dpg.configure_item(self.window, show=False)) as self.window:
                dpg.add_image(self.texture)
                with dpg.group(horizontal=True):
                    dpg.add_button(label="Previous", callback=lambda: self.move(-1))
                    dpg.add_button(label="Next", callback=lambda: self.move(1))
                self.details = dpg.add_text("", wrap=620)
                with dpg.collapsing_header(label="Classes"):
                    self.classes = dpg.add_text("", wrap=620)
        self.refresh()
        dpg.configure_item(self.window, show=True)

    def move(self, delta):
        if self.result is not None:
            self.index = (self.index + delta) % len(self.result.samples)
            self.refresh()

    def refresh(self):
        result = self.result
        sample = result.samples[self.index]
        pixels, range_note = preview_pixels(result.X[self.index])
        if pixels.shape[-1] == 1:
            pixels = pixels[..., 0]
        thumb = Image.fromarray(pixels).convert("RGBA")
        scale = min(self.SIZE / thumb.width, self.SIZE / thumb.height)
        thumb = thumb.resize((max(1, round(thumb.width * scale)),
                              max(1, round(thumb.height * scale))), Image.Resampling.NEAREST)
        canvas = Image.new("RGBA", (self.SIZE, self.SIZE), (32, 32, 32, 255))
        canvas.paste(thumb, ((self.SIZE - thumb.width) // 2, (self.SIZE - thumb.height) // 2))
        dpg.set_value(self.texture, (np.asarray(canvas, dtype=np.float32) / 255).ravel())
        metadata = "\n".join(f"{key}: {value}" for key, value in sample.metadata.items())
        dpg.set_value(self.details, f"{self.index + 1} / {len(result.samples)}\n"
                      f"{sample.relative_path}\nLabel: {sample.label} | Code: {result.y[self.index]}"
                      + ("\n" + metadata if metadata else "") + range_note)
        dpg.set_value(self.classes, "\n".join(f"{i}: {name}" for i, name in enumerate(result.class_names)))

    def dispose(self):
        for item in (self.window, self.registry):
            if item is not None and dpg.does_item_exist(item):
                dpg.delete_item(item)
        self.window = self.registry = self.texture = None
        self.result = None


class AImageDatasetPreview(Annotation):
    @staticmethod
    def build(*args, **kwargs):
        parent = kwargs.get("parent", 0)
        owner = get_userdata(dpg.get_item_parent(parent)) if parent else None
        # Static output controls remain interactive on nodes; palette cards do not.
        active = hasattr(owner, "register_cleanup")
        with dpg.group(parent=parent) as group:
            viewer = DatasetPreview(group, active)
        set_userdata(group, value=viewer)
        if active:
            def dispose():
                viewer.dispose()
                clear_userdata(group)
            owner.register_cleanup(dispose)
        return group

    @staticmethod
    def get(input_id):
        return get_userdata(input_id).result

    @staticmethod
    def set(input_id, value):
        get_userdata(input_id).set(value)
        return True
