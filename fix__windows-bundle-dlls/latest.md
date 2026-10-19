# CI: `fix/windows-bundle-dlls` @ `8e12bc5b` — PASS

| Параметр | Значение |
|---|---|
| Ветка | `fix/windows-bundle-dlls` |
| Коммит | [`8e12bc5b`](https://github.com/graphicalAI/graphNet/commit/8e12bc5b2daf7e068f6b492d7cbd580fc1e8ecb6) — app: let the build check run without creating a window |
| Автор | Gosha Volovikov, 2026-10-16 07:03:26 +0000 |
| Прогон | 2026-10-19 05:22 UTC, 176 с |
| Тесты | 117 passed, 1 warning in 156.55s (0:02:36) |
| Покрытие | 92% (порог 80%) |

## Хвост лога
```
Tests/test_themes.py::test_combined_theme_component_and_element PASSED   [ 86%]
Tests/test_userdata.py::test_set_get_userdata_integer_id PASSED          [ 87%]
Tests/test_userdata.py::test_set_get_userdata_string_id_and_alias PASSED [ 88%]
Tests/test_userdata.py::test_clear_userdata_no_children PASSED           [ 88%]
Tests/test_userdata.py::test_clear_userdata_with_children PASSED         [ 89%]
Tests/test_userdata.py::test_clear_userdata_string_id_alias PASSED       [ 90%]
Tests/test_userdata.py::test_get_userdata_invalid_id PASSED              [ 91%]
Tests/test_verify_bundle.py::test_pe_imports_reads_the_import_directory PASSED [ 92%]
Tests/test_verify_bundle.py::test_pe_imports_ignores_files_that_are_not_pe PASSED [ 93%]
Tests/test_verify_bundle.py::test_fails_when_a_runtime_library_directory_is_missing PASSED [ 94%]
Tests/test_verify_bundle.py::test_passes_when_every_import_is_satisfied PASSED [ 94%]
Tests/test_verify_bundle.py::test_reports_an_unsatisfied_import PASSED   [ 95%]
Tests/test_verify_bundle.py::test_whitelists_windows_and_vcredist_libraries PASSED [ 96%]
Tests/test_verify_bundle.py::test_common_controls_count_as_a_system_library PASSED [ 97%]
Tests/test_verify_bundle.py::test_optional_libraries_are_reported_but_do_not_fail PASSED [ 98%]
Tests/test_verify_bundle.py::test_reports_a_bundled_asset_that_is_missing PASSED [ 99%]
Tests/test_verify_bundle.py::test_reports_a_missing_executable PASSED    [100%]

=============================== warnings summary ===============================
Src/Nodes/layer_node.py:29
  /home/hermes/ci/graphnet/repo/Src/Nodes/layer_node.py:29: SyntaxWarning: invalid escape sequence '\ '
    Фабрика функций, для новых INPUT \ OUTPUT,

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
================== 117 passed, 1 warning in 156.55s (0:02:36) ==================
```
