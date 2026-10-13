#!/usr/bin/env python3
"""Download verified MNIST and export actual PNG files with shuffled CSV labels."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
import random
import urllib.request

import numpy as np
from PIL import Image


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ROOT = PROJECT_ROOT / ".cache" / "mnist-images"
MNIST_URL = "https://storage.googleapis.com/tensorflow/tf-keras-datasets/mnist.npz"
# https://github.com/keras-team/keras/blob/master/keras/src/datasets/mnist.py
MNIST_SHA256 = "731c5ac602752760c8e48fbffcf8c3b850d9dc2a2aedcf2cc48468fc17b673d1"
MARKER = ".graphnet-mnist-images.json"
MANIFEST = {"format": "graphnet-mnist-images-v1", "sha256": MNIST_SHA256, "seed": 42}


def check_archive(path: Path) -> None:
    with path.open("rb") as stream:
        actual = hashlib.file_digest(stream, "sha256").hexdigest()
    if actual != MNIST_SHA256:
        raise ValueError(f"SHA-256 mismatch for {path}: {actual}")


def managed_root(path: Path) -> Path:
    """Refuse to reuse arbitrary nonempty directories or follow existing symlinks."""
    if path.is_symlink():
        raise ValueError(f"Output root cannot be a symbolic link: {path}")
    path = path.resolve()
    if path.exists():
        marker = path / MARKER
        if any(path.iterdir()) and (
            not marker.is_file() or json.loads(marker.read_text()) != MANIFEST
        ):
            raise ValueError(f"Refusing to overwrite an unmanaged nonempty directory: {path}")
        for child in path.rglob("*"):
            if child.is_symlink():
                raise ValueError(f"Refusing to write through a symbolic link: {child}")
    path.mkdir(parents=True, exist_ok=True)
    (path / MARKER).write_text(json.dumps(MANIFEST, indent=2) + "\n", encoding="utf-8")
    return path


def download_archive(root: Path) -> Path:
    archive = root / "mnist.npz"
    if archive.exists():
        check_archive(archive)
        return archive
    partial = root / "mnist.npz.part"
    try:
        with urllib.request.urlopen(MNIST_URL, timeout=60) as response, partial.open("wb") as out:
            while block := response.read(1024 * 1024):
                out.write(block)
        check_archive(partial)
        partial.replace(archive)
    finally:
        partial.unlink(missing_ok=True)
    return archive


def export_split(root: Path, name: str, images: np.ndarray, labels: np.ndarray) -> None:
    split = root / name
    image_dir = split / "images"
    image_dir.mkdir(parents=True, exist_ok=True)
    for source_id, pixels in enumerate(images):
        Image.fromarray(pixels).save(image_dir / f"{source_id}.png")
    # Neither lexicographic file order nor source order equals this row order.
    indices = list(range(len(images)))
    random.Random(MANIFEST["seed"]).shuffle(indices)
    with (split / "metadata.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["file_name", "label", "source_id"])
        for source_id in indices:
            writer.writerow([f"images/{source_id}.png", int(labels[source_id]), source_id])
    print(f"{name}: {len(images)} PNG images and shuffled metadata.csv", flush=True)


def export_folders(root: Path, name: str, images: np.ndarray, labels: np.ndarray, classes: range) -> None:
    for label in classes:
        folder = root / name / str(label)
        folder.mkdir(parents=True, exist_ok=True)
        for source_id in np.flatnonzero(labels == label)[:5]:
            Image.fromarray(images[source_id]).save(folder / f"{source_id}.png")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT, help="Managed output directory")
    args = parser.parse_args()
    root = managed_root(args.root)
    archive = download_archive(root)
    print(f"Verified archive SHA-256: {MNIST_SHA256}", flush=True)
    with np.load(archive, allow_pickle=False) as data:
        for name, count in (("train", 60000), ("test", 10000)):
            images, labels = data[f"x_{name}"], data[f"y_{name}"]
            if images.shape != (count, 28, 28) or labels.shape != (count,):
                raise ValueError(f"Unexpected MNIST shapes in {name}")
            export_split(root, name, images, labels)
        export_folders(root, "folders-train", data["x_train"], data["y_train"], range(10))
        export_folders(root, "folders-test-missing-class", data["x_test"], data["y_test"], range(9))
    print(f"Ready: {root}", flush=True)


if __name__ == "__main__":
    main()
