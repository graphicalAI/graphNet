from Src.Nodes.data_node import DataNode
from Src.Enums import Themes
from Src.Utils import Backfield
from Src.image_dataset import load_image_dataset, DatasetValidationError


class ImageDatasetNode(DataNode):
    """Images and labels joined by file path, from a CSV or class directories.

    Connect X/y to Fit model, shape to Input. For another split, connect
    class_names to its classes input to preserve the class codes.
    """

    theme_name = Themes.DATASET
    shape = Backfield()
    preview = Backfield()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._cleanups = []
        self.X = self.y = None
        self.class_names = []
        self._shape = (0, 0, 0)
        self._preview = None

    def register_cleanup(self, callback):
        self._cleanups.append(callback)

    @staticmethod
    def open_data(root, metadata_file="", path_column="file_name", label_column="label",
                  delimiter=",", color_mode="rgb", target_size=(0, 0), classes=None):
        try:
            size = tuple(target_size) if target_size is not None else None
            if size == (0, 0):
                size = None
            if isinstance(classes, list) and not classes:
                classes = None
            return load_image_dataset(
                root, metadata_file=metadata_file or None, path_column=path_column,
                label_column=label_column, delimiter="\t" if delimiter == r"\t" else delimiter,
                color_mode=color_mode, target_size=size, class_names=classes)
        except DatasetValidationError as error:
            raise AttributeError(str(error)) from error

    def _clear(self):
        self.OUTPUT = self.X = self.y = None
        self.class_names = []
        self.shape = (0, 0, 0)
        self.preview = None

    def compile(self, kwargs=None):
        self._clear()
        self.default_theme()
        try:
            if not super().compile(kwargs):
                self._clear()
                return False
            result = self.OUTPUT
            self.X, self.y, self.class_names = result.X, result.y, result.class_names
            self.shape = result.shape
            self.preview = result
            return True
        except Exception as error:
            self._clear()
            self.raise_error(error, "Ошибка загрузки датасета")
            return False

    def dispose(self):
        for cleanup in reversed(self._cleanups):
            cleanup()
        self._cleanups.clear()
        self.OUTPUT = self.X = self.y = None
        self.class_names = []
        self._preview = None
