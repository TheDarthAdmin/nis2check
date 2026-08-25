# Nis2Check

NIS2-bewijsverzameling voor Microsoft 365-tenants. Python monorepo.

Eén collector, twee voordeuren:
- **CLI/container** — de klant draait het zelf, niets komt bij ons terecht. Gratis, open source.
- **Hosted** — FastAPI + Next.js, multi-tenant, gepland, met historiek. Betaald.

Het verzamelt technisch bewijs voor NIS2 artikel 21 via Microsoft Graph. Het levert bewijsmateriaal, geen conformiteitsverklaring.

## Harde regels

1. **De collector is puur.** `packages/collector` krijgt credentials en een catalogus binnen en geeft bevindingen terug. Hij weet niets van databases, gebruikers, HTTP-servers of hosting. Een import van SQLAlchemy of FastAPI in dat package is een bug, geen keuze.
2. **Read-only.** Alleen GET naar Graph. Geen write-scope in enige app-registratie, geen write-pad in de code. Vereist een feature schrijven, dan hoort die feature hier niet.
3. **Raden mag niet.** Kan data niet gelezen worden, dan `INCONCLUSIVE` met de reden erbij. Nooit een aanname als bevinding presenteren.
4. **Geen totaalscore.** Een percentage nodigt uit tot cijferjagen. Bewust weggelaten.
5. **Ruwe data en interpretatie gescheiden.** `raw_evidence` bevat wat Graph zei, `rationale` wat wij ervan maken. Nooit door elkaar.
6. **Controls zijn data.** Metadata in YAML, evaluatie in een geregistreerde Python-handler.
7. **Geen klantdata, nergens.** Niet in de repo, niet in tests, niet in logs. Testdata is altijd fixture-data. De hosted database slaat geen UPN's of e-mailadressen op.
8. **De CLI werkt zonder de rest.** `pip install nis2check && nis2check run` volstaat: geen database, geen account, geen verbinding met ons.

## Structuur

```
packages/collector/   auth, graph-client, engine, handlers, rapportage
packages/catalog/     controls/*.yaml + schema.json
apps/cli/             Typer-CLI, HTML/JSON-uitvoer, Dockerfile
apps/api/             FastAPI, SQLAlchemy, Alembic, arq
apps/web/             Next.js
tests/                pytest + respx, geen netwerk
```

## Verdicts

`PASS` · `PARTIAL` · `FAIL` · `NOT_APPLICABLE` · `INCONCLUSIVE`

`INCONCLUSIVE` bestaat omdat een tool die gokt voor een auditor erger is dan nutteloos.

## Definition of done per control

- Draait tegen fixture-data in de tests, alle relevante verdict-paden gedekt
- Zinnige rationale in elk mogelijk verdict
- Faalt naar `INCONCLUSIVE`, nooit naar een crash
- Beperkingen gedocumenteerd in het `limits`-veld van de catalogus-entry

## Werkwijze

- Eén commit per afgerond controleblok, met groene tests.
- `ruff check` en `mypy --strict` zijn onderdeel van done, niet van later.
- Bij twijfel over scope: vraag het, bouw niet vooruit.
- Raak `apps/api` en `apps/web` niet aan tot fase 3.
