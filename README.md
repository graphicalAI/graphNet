# Как запустить приложение?
(для тестировщиков)

1. Скачайте его с github
```
git clone https://github.com/jezvgg/graphNet.git
cd graphNet
```

2. Установите все зависимости
```
pip install -r requirements.txt
```

3. Запустите приложение
```
python3 main.py
```

Приложение кросс-платформеное, но основная платформа - Windows 10\11


# Компиляция приложения в exe 

## С использованием auto-py-to-exe

1. Скачайте его с github
```
git clone https://github.com/jezvgg/graphNet.git
cd graphNet
```

2. Установите все зависимости
```
pip install -r requirements.txt
```

3. Установите auto-py-to-exe
```
pip install auto-py-to-exe
```

4. Запустите auto-py-to-exe
```
auto-py-to-exe
```

5. Произведите настройку
  - Укажите положение скрипта
    - В поле Script Location нажмите BROWSE и выберите ваш главный файл (например, main.py).
  - Выберите тип компиляции
    - Выберите One File для создания одного исполняемого файла или One Directory для создания папки с .exe и всеми зависимостями.
  - Для графического приложения укажите Window based
    - В секции Console Window выберите опцию Window Based (hide the console). Это уберет черное окно терминала при запуске приложения.
  - Добавьте файлы не являющиеся кодом (Additional Files)
    - Нажмите на кнопку Additional Files.
    - С помощью кнопок Add Folder или Add File добавьте необходимые ресурсы (например, папку assets или файл config.json).
    - Для каждого добавленного элемента убедитесь, что путь назначения (справа) указан корректно. Например, чтобы папка assets оказалась в корне сборки, путь назначения должен быть assets.
  - Опционально настроить Advanced настройки
    - Перейдите на вкладку Settings.
    - В поле --name можно задать имя для вашего итогового .exe файла.
    - В поле Output Directory можно указать, куда сохранить готовую сборку. По умолчанию это папка output в каталоге вашего проекта.
<img width="959" height="712" alt="image" src="https://github.com/user-attachments/assets/08d11998-91a9-427d-8b8e-bfd6cd4e285c" />


6. Запустите приложение

## С использованием makefile'а

1. Выполните шаги 1 и 2 из инструкции "Как запустить приложение"

2. Выполните комманду `make build` или `make`

3. Запустите исполняемый файл из директории dist
