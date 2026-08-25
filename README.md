# Nis2Check

> NIS2 is grotendeels organisatorisch. Nis2Check verzamelt alleen technisch verifieerbaar bewijs uit Microsoft 365 en geeft **geen** conformiteitsverklaring.

Dit project begint met een read-only collector. De eerste control (C01) controleert of een
Conditional Access-policy MFA voor alle gebruikers afdwingt.

## Development

```powershell
python -m pip install -e ".[dev]"
pytest
ruff check .
mypy --strict packages/collector packages/catalog
```

De collector doet uitsluitend GET-verzoeken naar Microsoft Graph. Bij ontoegankelijke of
onvolledige data rapporteert hij `INCONCLUSIVE` en doet hij geen aannames.
