import json
from pathlib import Path

import pytest
from nis2check_catalog import CatalogValidationError, load_catalog, load_control
from nis2check_catalog.loader import _schema_path

CONTROLS = Path("packages/catalog/controls")
#: Every measure of NIS2 article 21(2) must be reachable by at least one control.
ARTICLE_MEASURES = {f"21(2)({letter})" for letter in "abcdefghij"}


def test_loads_the_catalogue() -> None:
    controls = load_catalog(CONTROLS)

    assert [control.id for control in controls] == [f"C{number:02d}" for number in range(1, 23)]
    assert controls[0].queries["policies"].paged is True
    assert controls[11].queries["logs"].paged is False
    assert _schema_path().is_file()


def test_every_article_21_measure_has_a_control() -> None:
    covered = {control.nis2 for control in load_catalog(CONTROLS)}

    assert ARTICLE_MEASURES <= covered, f"no control covers {sorted(ARTICLE_MEASURES - covered)}"


def test_every_control_explains_how_to_remediate() -> None:
    for control in load_catalog(CONTROLS):
        assert control.remediation_steps, control.id
        assert all(step.strip() for step in control.remediation_steps), control.id
        assert str(control.remediation).startswith("https://"), control.id


def test_bundled_schema_matches_the_published_schema() -> None:
    published = json.loads(Path("packages/catalog/schema.json").read_text(encoding="utf-8"))

    assert json.loads(_schema_path().read_text(encoding="utf-8")) == published


def test_high_privilege_app_control_uses_application_compatible_read_scope() -> None:
    controls = {item.id: item for item in load_catalog(Path("packages/catalog/controls"))}

    assert controls["C14"].requires.scopes == ["Directory.Read.All"]


def test_rejects_invalid_catalogue_document(tmp_path: Path) -> None:
    invalid = tmp_path / "C99.yaml"
    invalid.write_text("id: C99\ntitle: incomplete\n", encoding="utf-8")

    with pytest.raises(CatalogValidationError, match="required"):
        load_control(invalid)
