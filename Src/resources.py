import sys
from pathlib import Path


def resource_base() -> Path:
    '''Каталог с ресурсами приложения.

    В собранном PyInstaller-приложении это его временная папка (_MEIPASS),
    в остальных случаях — корень пакета (репозитория или site-packages).
    '''
    if hasattr(sys, '_MEIPASS'):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parents[1]


def resource_path(name: str) -> Path:
    '''Путь к файлу внутри папки Assets, не зависящий от рабочего каталога.'''
    return resource_base() / "Assets" / name
