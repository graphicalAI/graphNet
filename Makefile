# Имя приложения
APP_NAME = GraphNet

# Главный исполняемый скрипт
MAIN_SCRIPT = main.py

# Исполняемый файл PyInstaller
PYINSTALLER = uv run --frozen pyinstaller

# Опции для PyInstaller
# --noconfirm: не запрашивать подтверждение на перезапись
# --onedir: собрать приложение и зависимости в одну папку
# --windowed: убрать окно консоли при запуске GUI-приложения
PYINSTALLER_OPTS = \
	--noconfirm \
	--onedir \
	--windowed \
	--name $(APP_NAME)

# Дополнительные файлы для включения в сборку
# Формат PyInstaller: --add-data "ИСТОЧНИК:НАЗНАЧЕНИЕ"
ADD_DATA = \
	--add-data "Assets:Assets"

# Команда по умолчанию, выполняется при вызове "make" без аргументов
all: build

# Сборка .exe файла
build:
	@echo "==> Building $(APP_NAME).exe..."
	$(PYINSTALLER) $(PYINSTALLER_OPTS) $(ADD_DATA) $(MAIN_SCRIPT)
	@echo "==> Build finished. The executable is located in the 'dist/' directory."


.PHONY: all build