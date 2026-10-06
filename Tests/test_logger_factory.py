import logging
from pathlib import Path

import pytest

from Src.Logging.logger_factory import Logger_factory


@pytest.mark.parametrize(
    "config",
    [
        {},
        {"level": logging.INFO},
        {"filename": "nested/deeper/log.log", "datefmt": "%Y"},
        {"filename": "nested/dated_{curdata}.log", "datefmt": "%Y"},
    ],
)
def test_logger_initialization(config, tmp_path, monkeypatch):
    cls = Logger_factory.__wrapped__
    original_handlers = logging.root.handlers[:]
    original_level = logging.root.level
    monkeypatch.delattr(cls, "__instance", raising=False)
    logging.root.handlers = []
    settings = dict(config)
    if "filename" in settings:
        settings["filename"] = str(tmp_path / settings["filename"])
    try:
        factory = Logger_factory(settings)
        assert Logger_factory({}) is factory
        logging.warning("initialization regression check")
        if "filename" in settings:
            assert Path(factory.config["filename"]).is_file()
        else:
            assert logging.root.handlers
            assert all(not isinstance(h, logging.FileHandler) for h in logging.root.handlers)
    finally:
        for handler in logging.root.handlers:
            handler.close()
        logging.root.handlers = original_handlers
        logging.root.setLevel(original_level)
