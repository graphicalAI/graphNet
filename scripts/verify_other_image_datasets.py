"""Verify real JPEG datasets from PyTorch and TensorFlow (archives downloaded separately)."""

import argparse
import csv
import hashlib
import json
from pathlib import Path
import random
import sys
import tarfile
import zipfile

import numpy as np
from PIL import Image

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))
from Src.image_dataset import DatasetValidationError, load_image_dataset

FLOWERS_SHA256 = "4c54ace7911aaffe13a365c34f650e71dd5bf1be0a58b464e5a7183e3e595d9c"


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def verify(folder, classes=None):
    result = load_image_dataset(folder, color_mode="rgb", target_size=(64, 64), class_names=classes)
    assert result.X.dtype == np.float32 and result.y.dtype == np.int64
    assert result.X.shape == (len(result.samples), 64, 64, 3)
    counts = dict.fromkeys(result.class_names, 0)
    for index, sample in enumerate(result.samples):
        label = Path(sample.relative_path).parts[0]
        assert sample.label == label == result.class_names[int(result.y[index])]
        # This reference decode does not call the loader's private helpers.
        with Image.open(folder / sample.relative_path) as original:
            with original.convert("RGB") as rgb:
                with rgb.resize((64, 64), Image.Resampling.BILINEAR) as resized:
                    expected = np.asarray(resized, dtype=np.float32)
        np.testing.assert_array_equal(result.X[index], expected)
        counts[label] += 1
    paths = [sample.relative_path for sample in result.samples]
    assert paths == sorted(paths)
    try:
        load_image_dataset(folder)
    except DatasetValidationError as error:
        size_error = str(error)
        assert "image shape" in size_error
    else:
        raise AssertionError("Mixed original sizes must require an explicit target_size")
    return result, {
        "count": len(result.samples), "shape": list(result.X.shape),
        "classes": result.class_names, "class_counts": counts,
        "all_pixels_and_labels_match": True, "default_size_error": size_error,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=PROJECT / ".cache/image-dataset-report")
    args = parser.parse_args()
    root = args.root.resolve()
    hymenoptera_archive = root / "datasets/hymenoptera_data.zip"
    flowers_archive = root / "flowers/flower_photos.tgz"
    if not hymenoptera_archive.is_file() or not flowers_archive.is_file():
        parser.error("Download the two official archives first; see docs/image-dataset.md")
    assert digest(flowers_archive) == FLOWERS_SHA256, "Flowers SHA-256 mismatch"
    with zipfile.ZipFile(hymenoptera_archive) as archive:
        destination = root / "datasets"
        for member in archive.infolist():
            if not (destination / member.filename).resolve().is_relative_to(destination):
                raise ValueError(f"Archive path escapes destination: {member.filename}")
        archive.extractall(destination)
    with tarfile.open(flowers_archive, "r:gz") as archive:
        archive.extractall(root / "flowers", filter="data")

    data = root / "datasets/hymenoptera_data"
    train, train_info = verify(data / "train")
    val, val_info = verify(data / "val", train.class_names)
    assert len(train.samples) == 244 and len(val.samples) == 153
    annotations = data / "train/annotations"
    annotations.mkdir(exist_ok=True)
    metadata = annotations / "labels.csv"
    rows = [["../" + sample.relative_path, sample.label, "original:" + sample.relative_path]
            for sample in train.samples]
    random.Random(913).shuffle(rows)
    with metadata.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.writer(stream, delimiter=";")
        writer.writerow(["path", "target", "origin"])
        writer.writerows(rows)
    joined = load_image_dataset(
        data / "train", metadata_file=metadata, path_column="path", label_column="target",
        delimiter=";", target_size=(64, 64), class_names=train.class_names,
    )
    np.testing.assert_array_equal(joined.X, train.X)
    np.testing.assert_array_equal(joined.y, train.y)
    assert [sample.relative_path for sample in joined.samples] == [sample.relative_path for sample in train.samples]
    assert all(sample.metadata["origin"] == "original:" + sample.relative_path for sample in joined.samples)
    bad_metadata = annotations / "bad_labels.csv"
    bad_metadata.write_text("file_name,label\n../does-not-exist.jpg,ants\n", encoding="utf-8")
    try:
        load_image_dataset(data / "train", metadata_file=bad_metadata)
    except DatasetValidationError as error:
        missing_error = str(error)
        assert "row 2" in missing_error and "does not exist" in missing_error
    else:
        raise AssertionError("A missing CSV image must fail")

    output = {"hymenoptera": {
        "archive_sha256_local": digest(hymenoptera_archive),
        "published_checksum_verified": False,
        "train": train_info, "val": val_info,
        "excluded_gif": sorted(path.relative_to(data).as_posix() for path in data.rglob("*.gif")),
        "csv": {"count": len(joined.samples), "shuffled_seed": 913,
                "same_pixels_labels_paths": True, "metadata_preserved": True,
                "missing_file_error": missing_error},
    }}
    del train, val, joined
    flowers, flowers_info = verify(root / "flowers/flower_photos")
    assert len(flowers.samples) == 3670
    output["flowers"] = {"archive_sha256": FLOWERS_SHA256, "published_checksum_verified": True,
                         **flowers_info}
    report = root / "evidence/other-datasets-repro.json"
    report.parent.mkdir(exist_ok=True)
    report.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Verified 397 Hymenoptera JPEGs, 244 CSV rows, 3670 Flowers JPEGs. Report: {report}")


if __name__ == "__main__":
    main()
