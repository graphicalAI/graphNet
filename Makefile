# Имя приложения
APP_NAME = GraphNet

# Главный исполняемый скрипт
MAIN_SCRIPT = main.py

# Исполняемый файл PyInstaller
PYINSTALLER = pyinstaller

# Опции для PyInstaller
# --noconfirm: не запрашивать подтверждение на перезапись
# --onefile: собрать всё в один .exe файл
# --windowed: убрать окно консоли при запуске GUI-приложения
PYINSTALLER_OPTS = \
	--noconfirm \
	--onefile \
	--windowed \
	--name $(APP_NAME)

# Дополнительные файлы для включения в сборку
# Формат для Windows: --add-data "ИСТОЧНИК;НАЗНАЧЕНИЕ"
# ; - разделитель
ADD_DATA = \
	--add-data "Assets;Assets"

# Команда по умолчанию, выполняется при вызове "make" без аргументов
all: build

# Сборка .exe файла
build:
	@echo "==> Building $(APP_NAME).exe..."
	$(PYINSTALLER) $(PYINSTALLER_OPTS) $(ADD_DATA) $(MAIN_SCRIPT)
	@echo "==> Build finished. The executable is located in the 'dist/' directory."


.PHONY: all build