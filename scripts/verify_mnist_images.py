#!/usr/bin/env python3
"""Verify every MNIST PNG/label loaded by GraphNet against the verified source archive."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import numpy as np

from prepare_mnist_images import DEFAULT_ROOT, MNIST_SHA256, check_archive

# Allow running this script by absolute path from any working directory.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from Src.image_dataset import load_image_dataset  # noqa: E402


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def verify_split(root: Path, name: str, source, classes: list[str]) -> dict:
    result = load_image_dataset(root / name, color_mode="grayscale", class_names=classes)
    images, labels = source[f"x_{name}"], source[f"y_{name}"]
    count = len(images)
    require(result.X.shape == (count, 28, 28, 1), f"{name}: incorrect X shape")
    require(result.y.shape == (count,), f"{name}: incorrect y shape")
    require(result.X.dtype == np.float32 and result.y.dtype == np.int64, f"{name}: incorrect dtypes")
    require(result.shape == (28, 28, 1), f"{name}: incorrect sample shape")
    require(result.class_names == classes, f"{name}: changed class mapping")
    require(not result.warnings, f"{name}: unexpected warnings: {result.warnings}")
    require(len(result.samples) == count, f"{name}: incorrect sample count")
    seen = set()
    paths = []
    for position, sample in enumerate(result.samples):
        source_id = int(sample.metadata["source_id"])
        require(source_id not in seen and 0 <= source_id < count, f"{name}: invalid/duplicate source_id {source_id}")
        seen.add(source_id)
        require(sample.relative_path == f"images/{source_id}.png", f"{name}: wrong path at {position}")
        paths.append(sample.relative_path)
        require(np.array_equal(result.X[position, :, :, 0], images[source_id]), f"{name}: pixel mismatch for {source_id}")
        require(sample.label == str(labels[source_id]), f"{name}: label mismatch for {source_id}")
        require(classes[result.y[position]] == sample.label, f"{name}: encoded label mismatch for {source_id}")
    require(paths == sorted(paths), f"{name}: records are not sorted by relative path")
    print(f"{name}: all {count} images and labels match source", flush=True)
    return {"count": count, "shape": list(result.X.shape), "pixels_and_labels_match": True}


def verify_folders(root: Path, source) -> dict:
    train = load_image_dataset(root / "folders-train", color_mode="grayscale")
    classes = [str(value) for value in range(10)]
    require(train.class_names == classes, "Folder training classes differ")
    test = load_image_dataset(root / "folders-test-missing-class", color_mode="grayscale", class_names=train.class_names)
    require(test.class_names == classes, "Missing-class subset lost shared class mapping")
    require(9 not in test.y, "Missing-class subset unexpectedly contains class 9")
    for result, split, count in ((train, "train", 50), (test, "test", 45)):
        require(len(result.samples) == count, f"Folder {split}: wrong count")
        for position, sample in enumerate(result.samples):
            source_id = int(Path(sample.relative_path).stem)
            require(np.array_equal(result.X[position, :, :, 0], source[f"x_{split}"][source_id]), f"Folder {split}: pixel mismatch")
            require(sample.label == str(source[f"y_{split}"][source_id]), f"Folder {split}: label mismatch")
            require(classes[result.y[position]] == sample.label, f"Folder {split}: wrong encoded label")
    print("Class folders: 50 training + 45 test images match; absent class 9 preserves mapping", flush=True)
    return {"train_count": 50, "test_count": 45, "missing_class": "9", "shared_mapping_preserved": True}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--report", type=Path, help="JSON report path; defaults to ROOT/verification.json")
    args = parser.parse_args()
    root = args.root.resolve()
    archive = root / "mnist.npz"
    check_archive(archive)
    report = {"archive_sha256": MNIST_SHA256, "class_names": [str(value) for value in range(10)]}
    with np.load(archive, allow_pickle=False) as source:
        for name in ("train", "test"):
            report[name] = verify_split(root, name, source, report["class_names"])
        report["folders"] = verify_folders(root, source)
    destination = args.report or root / "verification.json"
    destination.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Verification report: {destination}", flush=True)


if __name__ == "__main__":
    main()
