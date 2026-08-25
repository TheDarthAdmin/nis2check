from pathlib import Path

import pytest
from nis2check_catalog import CatalogValidationError, load_catalog, load_control


def test_loads_c01_catalogue() -> None:
    controls = load_catalog(Path("packages/catalog/controls"))

    assert [control.id for control in controls] == ["C01"]
    assert controls[0].queries["policies"].paged is True


def test_rejects_invalid_catalogue_document(tmp_path: Path) -> None:
    invalid = tmp_path / "C99.yaml"
    invalid.write_text("id: C99\ntitle: incomplete\n", encoding="utf-8")

    with pytest.raises(CatalogValidationError, match="required"):
        load_control(invalid)
