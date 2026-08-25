from pathlib import Path

from nis2check_catalog import load_catalog

ROOT = Path(__file__).parents[1]


def test_catalogue_never_requests_write_scopes() -> None:
    for control in load_catalog(ROOT / "packages" / "catalog" / "controls"):
        for scope in control.requires.scopes:
            assert "write" not in scope.lower(), f"{control.id} requests a write scope: {scope}"


def test_collector_has_no_hosted_application_imports() -> None:
    forbidden = ("fastapi", "sqlalchemy", "alembic", "arq", "nis2check_api")
    for source in (ROOT / "packages" / "collector").rglob("*.py"):
        text = source.read_text(encoding="utf-8").lower()
        assert not any(term in text for term in forbidden), source


def test_graph_client_exposes_get_only() -> None:
    source = (ROOT / "packages" / "collector" / "nis2check_collector" / "graph.py").read_text(
        encoding="utf-8"
    )
    assert ".post(" not in source
    assert ".put(" not in source
    assert ".patch(" not in source
    assert ".delete(" not in source
