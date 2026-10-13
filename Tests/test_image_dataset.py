"""Contract tests using actual images, independent of node/UI behavior."""

import csv

import numpy as np
import pytest
from PIL import Image

from Src.image_dataset import DatasetValidationError, load_image_dataset


def picture(path, value=42, size=(3, 2)):
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(np.full((size[1], size[0]), value, dtype=np.uint8)).save(path)
    return path


def table(path, rows, headers=("file_name", "label"), delimiter=","):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.writer(stream, delimiter=delimiter)
        writer.writerow(headers)
        writer.writerows(rows)
    return path


def test_csv_joint_order_and_metadata(tmp_path):
    for name, value in [("1.png", 1), ("10.png", 10), ("2.png", 2)]:
        picture(tmp_path / name, value)
    table(tmp_path / "metadata.csv", [("2.png", "two", "id2"), ("1.png", "one", "id1"),
                                     ("10.png", "ten", "id10")], ("file_name", "label", "id"))
    result = load_image_dataset(tmp_path, color_mode="grayscale")
    assert result.X.dtype == np.float32
    assert result.y.dtype == np.int64
    assert result.X.shape == (3, 2, 3, 1)
    assert result.shape == (2, 3, 1)
    assert result.X[:, 0, 0, 0].tolist() == [1, 10, 2]
    assert [result.class_names[i] for i in result.y] == ["one", "ten", "two"]
    assert [sample.metadata["id"] for sample in result.samples] == ["id1", "id10", "id2"]
    assert "array" not in repr(result) and "id10" not in repr(result)
    table(tmp_path / "metadata.csv", [("10.png", "ten", "id10"), ("2.png", "two", "id2"),
                                     ("1.png", "one", "id1")], ("file_name", "label", "id"))
    reordered = load_image_dataset(tmp_path, color_mode="grayscale")
    np.testing.assert_array_equal(reordered.X, result.X)
    np.testing.assert_array_equal(reordered.y, result.y)
    assert reordered.samples == result.samples


def test_nested_csv_relative_paths_explicit_priority_and_custom_columns(tmp_path):
    picture(tmp_path / "снимки" / "мой файл.png", 99)
    picture(tmp_path / "ignored.png")
    (tmp_path / "metadata.csv").write_text("not valid", encoding="utf-8")
    table(tmp_path / "annotations" / "custom.csv", [("../снимки/мой файл.png", "класс", "extra")],
          ("path", "target", "note"), ";")
    result = load_image_dataset(tmp_path, metadata_file="annotations/custom.csv",
                                path_column="path", label_column="target", delimiter=";")
    assert result.samples[0].relative_path == "снимки/мой файл.png"
    assert result.samples[0].metadata == {"note": "extra"}
    assert result.X.shape == (1, 2, 3, 3)
    assert len(result.warnings) == 1 and "1 image" in result.warnings[0]


def test_class_folders_nested_names_service_files_and_explicit_classes(tmp_path):
    picture(tmp_path / "b" / "same.png", 20)
    picture(tmp_path / "a" / "nested" / "same.png", 10)
    picture(tmp_path / ".hidden" / "hidden.png")
    picture(tmp_path / "__MACOSX" / "resource.png")
    (tmp_path / ".DS_Store").write_bytes(b"metadata")
    (tmp_path / "readme.txt").write_text("not an image")
    result = load_image_dataset(tmp_path, class_names=["b", "absent", "a"])
    assert result.class_names == ["b", "absent", "a"]
    assert result.y.tolist() == [2, 0]
    assert [s.relative_path for s in result.samples] == ["a/nested/same.png", "b/same.png"]
    default = load_image_dataset(tmp_path)
    assert default.class_names == ["a", "b"]
    assert default.y.tolist() == [0, 1]


@pytest.mark.parametrize("rows,message", [
    ([("missing.png", "0")], "does not exist"),
    ([("a.png", "0"), ("./a.png", "1")], "duplicate image"),
    ([("a.png", "")], "must not be empty"),
    ([("", "0")], "must not be empty"),
    ([("a.png", "0", "extra")], "column count"),
    ([("a.png",)], "column count"),
    ([], "no annotated images"),
])
def test_invalid_csv_records(tmp_path, rows, message):
    picture(tmp_path / "a.png")
    table(tmp_path / "metadata.csv", rows)
    with pytest.raises(DatasetValidationError, match=message):
        load_image_dataset(tmp_path)


@pytest.mark.parametrize("headers", [("other", "label"), ("file_name", "label", "label"),
                                      ("file_name", "label", "")])
def test_invalid_headers_do_not_fall_back_to_folders(tmp_path, headers):
    picture(tmp_path / "class" / "a.png")
    table(tmp_path / "metadata.csv", [], headers)
    with pytest.raises(DatasetValidationError, match="header|column names"):
        load_image_dataset(tmp_path)


def test_errors_include_csv_row_and_filename_and_allow_retry(tmp_path):
    (tmp_path / "broken.png").write_bytes(b"corrupt")
    table(tmp_path / "metadata.csv", [("broken.png", "label")])
    with pytest.raises(DatasetValidationError, match="row 2: broken.png"):
        load_image_dataset(tmp_path)
    picture(tmp_path / "broken.png", 17)
    assert load_image_dataset(tmp_path).X[0, 0, 0, 0] == 17


def test_mismatched_size_and_bilinear_resize(tmp_path):
    picture(tmp_path / "class" / "a.png", 1)
    picture(tmp_path / "class" / "b.png", 2, (5, 4))
    with pytest.raises(DatasetValidationError, match="common target_size"):
        load_image_dataset(tmp_path)
    result = load_image_dataset(tmp_path, target_size=(6, 7), color_mode="grayscale")
    assert result.X.shape == (2, 6, 7, 1)
    assert result.X[:, 0, 0, 0].tolist() == [1, 2]


@pytest.mark.parametrize("extension", ["jpg", "jpeg", "png", "bmp", "tif", "tiff", "webp"])
def test_supported_formats(tmp_path, extension):
    picture(tmp_path / "class" / f"sample.{extension}")
    assert load_image_dataset(tmp_path).X.shape == (1, 2, 3, 3)


def test_rejects_multiframe_and_disguised_unsupported_formats(tmp_path):
    directory = tmp_path / "class"
    directory.mkdir()
    first = Image.new("L", (3, 2), 10)
    second = Image.new("L", (3, 2), 20)
    first.save(directory / "multi.tiff", save_all=True, append_images=[second])
    with pytest.raises(DatasetValidationError, match="multi-frame"):
        load_image_dataset(tmp_path)
    (directory / "multi.tiff").unlink()
    first.save(directory / "disguised.png", format="GIF")
    with pytest.raises(DatasetValidationError, match="unsupported image format"):
        load_image_dataset(tmp_path)


def test_grayscale_preserves_16_bit_pixels(tmp_path):
    directory = tmp_path / "class"
    directory.mkdir()
    pixels = np.asarray([[0, 512], [1024, 65535]], dtype=np.uint16)
    Image.fromarray(pixels).save(directory / "depth.png")
    result = load_image_dataset(tmp_path, color_mode="grayscale")
    np.testing.assert_array_equal(result.X[0, ..., 0], pixels.astype(np.float32))
    resized = load_image_dataset(tmp_path, color_mode="grayscale", target_size=(4, 4))
    assert resized.X.max() == 65535


def test_rgba_retains_alpha_channel(tmp_path):
    directory = tmp_path / "class"
    directory.mkdir()
    Image.new("RGBA", (3, 2), (10, 20, 30, 40)).save(directory / "alpha.png")
    result = load_image_dataset(tmp_path, color_mode="rgba")
    assert result.X.shape == (1, 2, 3, 4)
    assert result.X[0, 0, 0].tolist() == [10, 20, 30, 40]


@pytest.mark.parametrize("value", [np.nan, np.inf, -np.inf])
@pytest.mark.parametrize("bad_index", [0, 1])
@pytest.mark.parametrize("color_mode", ["rgb", "grayscale"])
def test_nonfinite_float_pixels_rejected_in_every_sample(tmp_path, value, bad_index, color_mode):
    directory = tmp_path / "class"
    directory.mkdir()
    for index in range(2):
        pixels = np.full((2, 3), value if index == bad_index else 1, dtype=np.float32)
        Image.fromarray(pixels).save(directory / f"{index}.tiff")
    with pytest.raises(DatasetValidationError, match="NaN or infinite"):
        load_image_dataset(tmp_path, color_mode=color_mode)


@pytest.mark.parametrize("classes", [[], ["a", "a"], [""], [1], "a", 2])
def test_invalid_class_order(tmp_path, classes):
    picture(tmp_path / "a" / "sample.png")
    with pytest.raises(DatasetValidationError, match="class_names"):
        load_image_dataset(tmp_path, class_names=classes)


def test_unknown_label_and_empty_or_unannotated_dataset(tmp_path):
    with pytest.raises(DatasetValidationError, match="no annotated images"):
        load_image_dataset(tmp_path)
    picture(tmp_path / "a.png")
    with pytest.raises(DatasetValidationError, match="requires CSV"):
        load_image_dataset(tmp_path)
    table(tmp_path / "metadata.csv", [("a.png", "new")])
    with pytest.raises(DatasetValidationError, match="unknown class 'new'"):
        load_image_dataset(tmp_path, class_names=["known"])


@pytest.mark.parametrize("size", [(0, 0), (1, 0), (-1, 2), (1.5, 2), (True, 2), (1,), "3,2"])
def test_invalid_size(tmp_path, size):
    with pytest.raises(DatasetValidationError, match="target_size"):
        load_image_dataset(tmp_path, target_size=size)


def test_reject_external_paths_and_duplicate_symlinks(tmp_path):
    root = tmp_path / "dataset"
    root.mkdir()
    picture(tmp_path / "external.png")
    table(root / "metadata.csv", [("../external.png", "0")])
    with pytest.raises(DatasetValidationError, match="outside dataset root"):
        load_image_dataset(root)
    table(root / "metadata.csv", [(str(tmp_path / "external.png"), "0")])
    with pytest.raises(DatasetValidationError, match="must be relative"):
        load_image_dataset(root)
    table(tmp_path / "external.csv", [])
    with pytest.raises(DatasetValidationError, match="outside dataset root"):
        load_image_dataset(root, metadata_file=tmp_path / "external.csv")
    picture(root / "a.png")
    (root / "alias.png").symlink_to(root / "a.png")
    table(root / "metadata.csv", [("a.png", "0"), ("alias.png", "0")])
    with pytest.raises(DatasetValidationError, match="duplicate image"):
        load_image_dataset(root)


@pytest.mark.parametrize("kwargs,message", [
    ({"color_mode": "unknown"}, "color_mode"),
    ({"delimiter": "::"}, "delimiter"),
    ({"path_column": "label"}, "distinct"),
    ({"label_column": ""}, "distinct"),
])
def test_invalid_configuration(tmp_path, kwargs, message):
    with pytest.raises(DatasetValidationError, match=message):
        load_image_dataset(tmp_path, **kwargs)
