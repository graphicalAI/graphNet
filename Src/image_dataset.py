"""Load image files and their annotations as one consistently ordered dataset."""

import csv
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping, Sequence

import numpy as np
from PIL import Image


class DatasetValidationError(ValueError):
    """A dataset cannot be loaded without losing or misaligning samples."""


@dataclass(frozen=True)
class ImageSample:
    relative_path: str
    label: str
    metadata: Mapping[str, str] = field(default_factory=dict)


@dataclass(repr=False)
class ImageDatasetResult:
    X: np.ndarray
    y: np.ndarray
    samples: list[ImageSample]
    class_names: list[str]
    shape: tuple[int, int, int]
    warnings: list[str]

    def __repr__(self):
        return (f"ImageDatasetResult(samples={len(self.samples)}, shape={self.shape}, "
                f"classes={len(self.class_names)}, warnings={len(self.warnings)})")


@dataclass(frozen=True)
class _Record:
    path: Path
    sample: ImageSample
    source: str


_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}
_FORMATS = {"JPEG", "PNG", "BMP", "TIFF", "WEBP"}


def _inside(path: Path, root: Path, source: str) -> Path:
    resolved = path.resolve()
    if not resolved.is_relative_to(root):
        raise DatasetValidationError(f"{source}: path is outside dataset root: {path}")
    return resolved


def _image_paths(root: Path):
    for path in root.rglob("*"):
        parts = path.relative_to(root).parts
        if any(part.startswith(".") or part == "__MACOSX" for part in parts):
            continue
        if path.suffix.lower() in _EXTENSIONS and path.is_file():
            yield path


def _csv_records(root, metadata, path_column, label_column, delimiter):
    records = []
    seen = set()
    with metadata.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream, delimiter=delimiter, strict=True)
        headers = reader.fieldnames
        if not headers or path_column not in headers or label_column not in headers:
            raise DatasetValidationError(
                f"{metadata}: header must include {path_column!r} and {label_column!r}")
        if len(set(headers)) != len(headers) or any(not name.strip() for name in headers):
            raise DatasetValidationError(f"{metadata}: duplicate or empty CSV column names")
        for row in reader:
            source = f"{metadata}: row {reader.line_num}"
            if None in row or any(value is None for value in row.values()):
                raise DatasetValidationError(f"{source}: column count does not match header")
            name, label = row[path_column], row[label_column]
            if not name.strip() or not label.strip():
                raise DatasetValidationError(f"{source}: file path and label must not be empty")
            relative = Path(name)
            if relative.is_absolute():
                raise DatasetValidationError(f"{source}: image path must be relative: {name}")
            path = _inside(metadata.parent / relative, root, source)
            if path in seen:
                raise DatasetValidationError(f"{source}: duplicate image path: {name}")
            if not path.is_file():
                raise DatasetValidationError(f"{source}: image file does not exist: {name}")
            if path.suffix.lower() not in _EXTENSIONS:
                raise DatasetValidationError(f"{source}: unsupported image extension: {name}")
            seen.add(path)
            extras = {key: value for key, value in row.items()
                      if key not in (path_column, label_column)}
            sample = ImageSample(path.relative_to(root).as_posix(), label, extras)
            records.append(_Record(path, sample, source))
    unlisted = sum(path.resolve() not in seen for path in _image_paths(root))
    warnings = [f"{unlisted} image(s) not listed in CSV were skipped."] if unlisted else []
    return records, warnings


def _folder_records(root):
    records = []
    seen = set()
    for path in _image_paths(root):
        relative = path.relative_to(root)
        if len(relative.parts) < 2:
            raise DatasetValidationError(f"{path}: image in root requires CSV annotations or a class folder")
        resolved = _inside(path, root, str(path))
        if resolved in seen:
            raise DatasetValidationError(f"{path}: duplicate image path")
        seen.add(resolved)
        records.append(_Record(resolved, ImageSample(relative.as_posix(), relative.parts[0]), str(path)))
    return records, []


def _decode(record, color_mode, target_size):
    try:
        with Image.open(record.path) as original:
            if original.format not in _FORMATS:
                raise DatasetValidationError("unsupported image format")
            if getattr(original, "n_frames", 1) != 1:
                raise DatasetValidationError("multi-frame images are not supported")
            original.load()
            if original.mode == "F" and not np.isfinite(np.asarray(original)).all():
                raise DatasetValidationError("image contains NaN or infinite pixel values")
            # As in Keras, grayscale integer/float images retain their pixel range.
            if color_mode == "grayscale" and original.mode in {"I", "I;16", "I;16B", "I;16L", "F"}:
                image = original.copy()
            else:
                image = original.convert({"rgb": "RGB", "rgba": "RGBA", "grayscale": "L"}[color_mode])
            try:
                if target_size is not None:
                    if image.mode.startswith("I"):
                        converted = image.convert("F")
                        image.close()
                        image = converted
                    resized = image.resize((target_size[1], target_size[0]), Image.Resampling.BILINEAR)
                    image.close()
                    image = resized
                array = np.asarray(image, dtype=np.float32)
                if array.ndim == 2:
                    array = array[..., np.newaxis]
                if not np.isfinite(array).all():
                    raise DatasetValidationError("image contains NaN or infinite pixel values")
                return array
            finally:
                image.close()
    except (OSError, ValueError, SyntaxError, Image.DecompressionBombError) as exc:
        raise DatasetValidationError(f"{record.source}: {record.sample.relative_path}: {exc}") from exc


def load_image_dataset(
    root,
    *,
    metadata_file=None,
    path_column="file_name",
    label_column="label",
    delimiter=",",
    color_mode="rgb",
    target_size=None,
    class_names=None,
) -> ImageDatasetResult:
    """Read folder classes or CSV annotations; paths in CSV are relative to that CSV.

    No normalization, splitting or augmentation is performed. Each output row is
    generated from the same sample record. Validation failures never return a
    partially populated result. An explicit class order may include absent classes.
    """
    if color_mode not in {"rgb", "rgba", "grayscale"}:
        raise DatasetValidationError("color_mode must be 'rgb', 'rgba' or 'grayscale'")
    if target_size is not None:
        if (not isinstance(target_size, (tuple, list)) or len(target_size) != 2
                or any(isinstance(v, bool) or not isinstance(v, (int, np.integer)) or v <= 0
                       for v in target_size)):
            raise DatasetValidationError("target_size must contain two positive integers (height, width)")
    if not isinstance(delimiter, str) or len(delimiter) != 1 or delimiter in "\r\n\0":
        raise DatasetValidationError("CSV delimiter must be one non-newline character")
    if (not isinstance(path_column, str) or not path_column.strip()
            or not isinstance(label_column, str) or not label_column.strip()
            or path_column == label_column):
        raise DatasetValidationError("Path and label columns must be distinct nonempty names")
    if class_names is not None:
        if isinstance(class_names, (str, bytes)) or not isinstance(class_names, Sequence):
            raise DatasetValidationError("class_names must be a sequence of class names")
        class_names = list(class_names)
        if not class_names or any(not isinstance(name, str) or not name.strip() for name in class_names):
            raise DatasetValidationError("class_names must contain nonempty strings")
        if len(set(class_names)) != len(class_names):
            raise DatasetValidationError("class_names contains duplicate names")
    if root is None or not str(root).strip():
        raise DatasetValidationError("Select a dataset root folder")
    metadata = None
    try:
        root = Path(root).expanduser().resolve()
        if not root.is_dir():
            raise DatasetValidationError(f"Dataset root is not a directory: {root}")
        if metadata_file is not None:
            metadata = Path(metadata_file).expanduser()
            if not metadata.is_absolute():
                metadata = root / metadata
        elif (root / "metadata.csv").exists():
            metadata = root / "metadata.csv"
        if metadata is not None:
            metadata = _inside(metadata, root, str(metadata))
            records, warnings = _csv_records(root, metadata, path_column, label_column, delimiter)
        else:
            records, warnings = _folder_records(root)
        if not records:
            raise DatasetValidationError(f"{root}: dataset has no annotated images")
        records.sort(key=lambda record: record.sample.relative_path)
        if class_names is None:
            class_names = sorted({record.sample.label for record in records})
        indices = {name: index for index, name in enumerate(class_names)}
        for record in records:
            if record.sample.label not in indices:
                raise DatasetValidationError(
                    f"{record.source}: {record.sample.relative_path}: unknown class {record.sample.label!r}")
        # Allocate once, avoiding a second full-dataset copy when stacking arrays.
        first = _decode(records[0], color_mode, target_size)
        shape = first.shape
        X = np.empty((len(records), *shape), dtype=np.float32)
        X[0] = first
        for index, record in enumerate(records[1:], 1):
            array = _decode(record, color_mode, target_size)
            if array.shape != shape:
                raise DatasetValidationError(
                    f"{record.source}: {record.sample.relative_path}: image shape {array.shape} "
                    f"differs from {shape}; set a common target_size")
            X[index] = array
        y = np.asarray([indices[record.sample.label] for record in records], dtype=np.int64)
        return ImageDatasetResult(X, y, [record.sample for record in records], class_names, shape, warnings)
    except (OSError, UnicodeError, csv.Error) as exc:
        raise DatasetValidationError(f"{metadata or root}: {exc}") from exc
