# CI: `develop` @ `f7aa4396` — PASS

| Параметр | Значение |
|---|---|
| Ветка | `develop` |
| Коммит | [`f7aa4396`](https://github.com/graphicalAI/graphNet/commit/f7aa439633fcc7f9c2f7c99e782a50cedd4fc14c) — Merge pull request #192 from graphicalAI/fix/191-separable-conv2d |
| Автор | Gosha Volovikov, 2026-09-04 21:47:00 +0800 |
| Прогон | 2026-10-19 05:14 UTC, 153 с |
| Тесты | 105 passed, 1 warning in 132.41s (0:02:12) |
| Покрытие | 92% (порог 80%) |

## Хвост лога
```
Tests/test_themes.py::test_load_themes PASSED                            [ 84%]
Tests/test_themes.py::test_apply_theme PASSED                            [ 85%]
Tests/test_themes.py::test_add_theme PASSED                              [ 86%]
Tests/test_themes.py::test_remove_theme PASSED                           [ 87%]
Tests/test_themes.py::test_get_theme PASSED                              [ 88%]
Tests/test_themes.py::test_theme_combination_override PASSED             [ 89%]
Tests/test_themes.py::test_apply_theme_replaces_previous PASSED          [ 90%]
Tests/test_themes.py::test_get_theme_returns_valid_dpg_item PASSED       [ 91%]
Tests/test_themes.py::test_get_component PASSED                          [ 92%]
Tests/test_themes.py::test_get_element PASSED                            [ 93%]
Tests/test_themes.py::test_combined_theme_component_and_element PASSED   [ 94%]
Tests/test_userdata.py::test_set_get_userdata_integer_id PASSED          [ 95%]
Tests/test_userdata.py::test_set_get_userdata_string_id_and_alias PASSED [ 96%]
Tests/test_userdata.py::test_clear_userdata_no_children PASSED           [ 97%]
Tests/test_userdata.py::test_clear_userdata_with_children PASSED         [ 98%]
Tests/test_userdata.py::test_clear_userdata_string_id_alias PASSED       [ 99%]
Tests/test_userdata.py::test_get_userdata_invalid_id PASSED              [100%]

=============================== warnings summary ===============================
Src/Nodes/layer_node.py:29
  /home/hermes/ci/graphnet/repo/Src/Nodes/layer_node.py:29: SyntaxWarning: invalid escape sequence '\ '
    Фабрика функций, для новых INPUT \ OUTPUT,

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
================== 105 passed, 1 warning in 132.41s (0:02:12) ==================
```
