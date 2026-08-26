from pathlib import Path

import pytest
from nis2check_catalog import CatalogValidationError, load_catalog, load_control
from nis2check_catalog.loader import _schema_path


def test_loads_c01_catalogue() -> None:
    controls = load_catalog(Path("packages/catalog/controls"))

    assert [control.id for control in controls] == [f"C{number:02d}" for number in range(1, 16)]
    assert controls[0].queries["policies"].paged is True
    assert controls[11].queries["logs"].paged is False
    assert _schema_path().is_file()


def test_high_privilege_app_control_uses_application_compatible_read_scope() -> None:
    controls = {item.id: item for item in load_catalog(Path("packages/catalog/controls"))}

    assert controls["C14"].requires.scopes == ["Directory.Read.All"]


def test_rejects_invalid_catalogue_document(tmp_path: Path) -> None:
    invalid = tmp_path / "C99.yaml"
    invalid.write_text("id: C99\ntitle: incomplete\n", encoding="utf-8")

    with pytest.raises(CatalogValidationError, match="required"):
        load_control(invalid)
