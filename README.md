# Nis2Check

> NIS2 is grotendeels organisatorisch. Nis2Check verzamelt alleen technisch verifieerbaar bewijs uit Microsoft 365 en geeft **geen** conformiteitsverklaring.

Nis2Check heeft één pure, open-source collector en optionele gehoste interfaces. De collector
doet uitsluitend GET-verzoeken naar Microsoft Graph en verandert nooit tenantconfiguratie.

## Controls

36 controls, samen goed voor elk van de tien maatregelen van NIS2 artikel 21(2). Elke control
draagt naast de bevinding ook `remediation_steps`: de stappen waarmee de tenantbeheerder het
zelf oplost. De collector voert die stappen nooit uit — hij leest alleen.

| ID | NIS2 | Control | Vereiste scope(s) | Belangrijkste beperking |
|---|---|---|---|---|
| C01 | 21(2)(j) | MFA voor alle gebruikers | Policy.Read.All | Geen validatie van break-glass-legitimiteit. |
| C02 | 21(2)(j) | Phishing-resistente adminauth | Policy.Read.All | Adminscope niet volledig bewijsbaar. |
| C03 | 21(2)(j) | Legacy-auth blokkeren | Policy.Read.All | Alleen CA-bewijs. |
| C04 | 21(2)(j) | Per-user MFA-restanten | User.Read.All | Beta endpoint, gelimiteerde inventaris. |
| C05 | 21(2)(i) | Global Administrator-limiet | RoleManagement.Read.Directory | Geen zakelijke rechtvaardiging. |
| C06 | 21(2)(i) | Emergency-accessuitsluitingen | Policy.Read.All | Alleen object-ID's. |
| C07 | 21(2)(i) | Gastuitnodigingen beperken | Policy.Read.All | Alleen tenantbeleid. |
| C08 | 21(2)(i) | Inactieve accounts | AuditLog.Read.All, User.Read.All | Vereist Entra P1-sign-indata. |
| C09 | 21(2)(g) | Schijfversleuteling | DeviceManagementManagedDevices.Read.All | Alleen beheerde devices. |
| C10 | 21(2)(g) | Update-ringdeadline | DeviceManagementConfiguration.Read.All | Installatie niet bewijsbaar. |
| C11 | 21(2)(g) | ASR block mode | DeviceManagementConfiguration.Read.All | Profielvormen verschillen. |
| C12 | 21(2)(b) | Directory audit logs | AuditLog.Read.All | Nooit PASS: Unified Audit is niet via Graph verifieerbaar. |
| C13 | 21(2)(b) | Security contact | Organization.Read.All | Monitoring niet gevalideerd. |
| C14 | 21(2)(d) | Third-party apps met hoge rechten | Directory.Read.All | Alleen geselecteerde delegated scopes. |
| C15 | 21(2)(d) | User consent beperken | Policy.Read.All | Alleen standaardbeleid. |
| C16 | 21(2)(a) | Risicovolle gebruikers opgevolgd | IdentityRiskyUser.Read.All | Alleen de risicostatus van Entra ID Protection (P2). |
| C17 | 21(2)(c) | OneDrive-retentie na vertrek | SharePointTenantSettings.Read.All | Alleen OneDrive, geen mailbox- of siteretentie. |
| C18 | 21(2)(e) | App-credentials kort en geldig | Application.Read.All | Alleen registraties van deze tenant. |
| C19 | 21(2)(f) | Access reviews op privileged access | AccessReview.Read.All | Bestaan en scope, geen genomen beslissingen. |
| C20 | 21(2)(h) | Zwakke authenticatiemethodes uit | Policy.Read.All | Methodes kunnen op groepen gescopet zijn. |
| C21 | 21(2)(h) | Legacy-auth uit voor SharePoint | SharePointTenantSettings.Read.All | Alleen de tenantinstelling. |
| C22 | 21(2)(i) | Externe deling beperkt | SharePointTenantSettings.Read.All | Alleen het tenantniveau, geen site-uitzonderingen. |
| C23 | 21(2)(i) | Standaardrechten van gebruikers beperkt | Policy.Read.All | Alleen de default user role, geen individuele roltoekenningen. |
| C24 | 21(2)(i) | Gasten krijgen de restricted rol | Policy.Read.All | Alleen de directoryrol, niet wat een gast in SharePoint of Teams ziet. |
| C25 | 21(2)(d) | Apps met hoge Graph-applicatierechten | Application.Read.All | Alleen Graph-rechten; delegated consent zit in C14. |
| C26 | 21(2)(d) | Delegated admin access van partners | DelegatedAdminRelationship.Read.All | Toont de relatie, niet wat de partner ermee deed. |
| C27 | 21(2)(f) | Activatie van Global Administrator | RoleManagement.Read.Directory | Alleen het beleid van die ene rol; vereist PIM (P2). |
| C28 | 21(2)(a) | Risicogebaseerd Conditional Access | Policy.Read.All | Bestaan van het beleid, niet hoe vaak het vuurde. |
| C29 | 21(2)(i) | Leaver-workflows trekken toegang in | LifecycleWorkflows.Read.All | Toont het bestaan, niet of elke vertrekker bereikt werd. |
| C30 | 21(2)(j) | Gebruikers hebben MFA echt geregistreerd | AuditLog.Read.All | Telt registratie, geen gebruik. Vereist Entra P1. |
| C31 | 21(2)(h) | Domeinen authenticeren in de tenant zelf | Domain.Read.All | Bij federatie beslist een externe IdP; dit rapport reikt daar niet. |
| C32 | 21(2)(b) | Incidenten worden opgevolgd en afgesloten | SecurityIncident.Read.All | Vereist Defender XDR. Lege wachtrij = INCONCLUSIVE, geen PASS. |
| C33 | 21(2)(g) | Compliance-policies bestaan én zijn toegewezen | DeviceManagementConfiguration.Read.All | Leest de policy, niet de compliance-status per toestel. |
| C34 | 21(2)(e) | Nieuwe apps lopen via admin consent request | Policy.Read.All | Alleen het aanvraagbeleid, niet hoe aanvragen beslist werden. |
| C35 | 21(2)(d) | Externe organisaties worden bij naam toegelaten | Policy.Read.All | Alleen het toelatingsbeleid, niet wie vandaag toegang heeft. |
| C36 | 21(2)(c) | Retentiebeleid beschermt data tegen verwijdering | RecordsManagement.Read.All | Retentie is geen back-up. Beta endpoint, Purview-licentie nodig. |

## Valt u onder NIS2?

Dat is een andere vraag dan wat de tenant kan aantonen, en het antwoord komt niet uit Graph.
`packages/scoping` classificeert een organisatie als **essentieel**, **belangrijk** of **niet in
scope** op basis van sector (bijlage I of II), personeelsbestand, omzet en balanstotaal.

```powershell
nis2check sectors
nis2check scope --sector health.provider --employees 400 --turnover 90000000 --balance 60000000 --output profiel.json
```

Wat het strenger maakt dan een vragenlijst met twee vragen:

- Het balanstotaal telt mee. Onder 250 werknemers alleen kan een onderneming nog steeds groot
  zijn, want de KMO-aanbeveling vraagt dat omzet **en** balanstotaal beide de grens passeren.
- Sectoren van artikel 2(2)(a) — DNS, TLD-registries, vertrouwensdiensten, openbare elektronische
  communicatie — vallen in scope ongeacht hun omvang.
- CER-aanduiding, positie als enige aanbieder en aanduiding door een overheid gaan voor op de
  omvangsdrempel.
- Ontbreken de cijfers, dan is het resultaat `UNDETERMINED` met vermelding van welk cijfer
  ontbreekt. Dezelfde regel als `INCONCLUSIVE`: niet raden.

Scoping is zelfgerapporteerd en wordt daarom nooit een `Finding`. Het staat naast de collector,
niet erin.

## Het dossier als PDF

```powershell
pip install "nis2check[pdf]"
nis2check report nis2check.json --pdf dossier.pdf --profile profiel.json
nis2check run --tenant-id <id> --client-id <id> --device-code --pdf dossier.pdf --profile profiel.json
```

Eén PDF die een auditor kan krijgen: omslag met classificatie, de dekking van artikel 21(2)
maatregel per maatregel, elke bevinding met rationale, remediatiestappen en beperkingen, en twee
bijlagen — wat het dossier *niet* bewijst (de `limits` van élke control, ook de geslaagde) en elk
Graph-endpoint dat gelezen werd. Geen totaalscore, geen percentage.

`--profile` is optioneel; zonder profiel vervalt het scopinghoofdstuk en blijft de rest gelijk.

## In de gehoste werkruimte

Dezelfde twee dingen, achter de Entra-login:

- **Scope** — `/scope` stelt dezelfde vragen en bewaart het antwoord per tenant. Het profiel
  bevat sector, personeelsbestand, omzet, balanstotaal en de twee uitzonderingsvinkjes.
  **Geen bedrijfsnaam en geen ondernemingsnummer**: die identificeren de klant, en deze
  database bewaart daar niets van. Een gehost dossier draagt daarom het tenant-ID als hoofding.
- **Dossier** — elke afgeronde run heeft een downloadknop. `GET /v1/runs/{id}/dossier?format=pdf`
  levert de PDF, `format=html` hetzelfde document als HTML.

Let op bij Vercel: WeasyPrint heeft systeembibliotheken nodig die daar niet beschikbaar zijn.
De PDF-route antwoordt dan `503` met de ontbrekende pakketten erin, en de interface biedt
automatisch het HTML-dossier aan, dat een browser naar dezelfde pagina's afdrukt. Draait de API
in een container of op een VM, installeer dan de pakketten hierboven en werkt de PDF wel.

PDF-uitvoer vereist WeasyPrint met zijn systeembibliotheken. Op Debian of Ubuntu:

```bash
sudo apt-get install libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz0b libfontconfig1
```

Ontbreken die, dan blijven `run` en `report` gewoon werken en zegt `--pdf` precies wat er mist.

## Toestemming en permissies

De vereiste Graph-permissies volgen uit de catalogus (`required_scopes`). Komt er een control
bij die een nieuwe permissie nodig heeft, dan moet een tenantbeheerder opnieuw goedkeuren:

1. Voeg de permissie toe aan de app-registratie in Entra (application permission, read-only).
2. De hosted workspace vergelijkt per tenant de goedgekeurde scopes met wat de catalogus
   vraagt en toont een banner met precies de ontbrekende permissies.
3. Tot die goedkeuring rapporteren de betrokken controls `INCONCLUSIVE` — nooit een aanname.

Tenants die goedkeurden vóór deze vergelijking bestond, hebben een lege lijst en krijgen de
banner dus sowieso te zien. De CLI vraagt bij device-code-authenticatie elke run de actuele
scopes op en heeft geen herregistratie nodig.

## CLI en container

```powershell
pip install nis2check
nis2check run --tenant-id <tenant-id> --client-id <app-id> --device-code --html rapport.html
nis2check report nis2check.json
```

`run` schrijft het JSON-resultaat, toont een samenvatting per verdict met de controls die
opvolging vragen, en rendert met `--html` meteen het rapport. `report` maakt hetzelfde
zelfstandige HTML-rapport uit een bestaand JSON-resultaat: filterbaar per verdict en domein,
zonder externe bronnen, printbaar.

Gebruik een klantgecontroleerde Entra-appregistratie met uitsluitend de read scopes uit de
tabel. Gebruik voor certificaatauthenticatie `--certificate key.pem --thumbprint <thumbprint>`.

```powershell
docker build -f apps/cli/Dockerfile -t nis2check .
docker run --rm -it -v ${PWD}:/output nis2check run --tenant-id <tenant-id> --client-id <app-id> --device-code --output /output/nis2check.json
```

## Development

```powershell
python -m pip install -e ".[dev]"
pytest
ruff check .
mypy --strict packages/collector packages/catalog packages/scoping apps/cli
```

De collector doet uitsluitend GET-verzoeken naar Microsoft Graph. Bij ontoegankelijke of
onvolledige data rapporteert hij `INCONCLUSIVE` en doet hij geen aannames.

## Hosted product

The hosted product is multitenant. A user signs in with their own Entra organization; the
verified token tenant ID selects that organization’s Nis2Check workspace. A tenant administrator
then grants the read-only Microsoft Graph application permissions. Microsoft creates the
Nis2Check Enterprise Application in that tenant as part of this consent. The web app never
receives a Graph token. The API stores completed runs, verdicts, rationale, control metadata,
counts, and HMAC-keyed object references only. It never stores raw Graph responses, UPNs, email
addresses, access tokens, or refresh tokens.

Runs can be started manually from the hosted UI. `vercel.json` schedules a protected daily run
at 03:00 UTC; change the expression if a different schedule is required. A partial unique index
prevents overlapping runs for the tenant.

### Entra application registration

1. In the [Microsoft Entra admin center](https://entra.microsoft.com/), open **App
   registrations** and choose **New registration**.
2. Select **Accounts in any organizational directory (Any Microsoft Entra ID tenant -
   Multitenant)**. Give it a name such as `Nis2Check Hosted`.
3. Under **Redirect URI**, select **Web** and enter both:
   - `https://<your-web-domain>/api/auth/callback/microsoft`
   - `https://<your-web-domain>/api/onboarding/callback/microsoft`
4. Copy the **Application (client) ID** from the app's Overview.
5. Under **Certificates & secrets**, create a client secret and copy its **Value** immediately.
   Do not use the secret ID. Add an expiry reminder before its end date.
6. In **API permissions** → **Microsoft Graph** → **Application permissions**, add the union
   of the read-only permissions in the controls table above. Do not grant consent in the
   Nis2Check home tenant on behalf of customers; each customer administrator grants it during
   onboarding. Do not add delegated Graph permissions or any write permission. `openid`,
   `profile`, and `email` are requested only for browser sign-in.
7. Each customer administrator signs in at the hosted front page and selects **Approve
   read-only access**. This provisions the Enterprise Application and consent in their tenant.

### Cloud deployment

The hosted product uses no customer-operated containers. Deploy the same repository to two
managed Vercel projects:

1. Keep this `nis2tool` project as the **Next.js web** project.
2. Create `nis2tool-api` as a second Vercel project from the same repository. Set its Framework
   Preset to **FastAPI** and leave its Root Directory at the repository root. The Python
   entrypoint and dependency build command are declared in `pyproject.toml`.
3. Provision a Neon PostgreSQL database and set the API project URL as `NIS2CHECK_API_URL` in
   the web project. The API creates its schema at its first start.

The API needs `apps/api/.env.example`; the web project needs `.env.example`. Both projects share
`NIS2CHECK_API_KEY` and `CRON_SECRET`, but every other generated secret must differ. The source
includes a protected daily schedule. If both Vercel projects receive the schedule from the shared
`vercel.json`, the API records at most one scheduled run per UTC day.

Docker remains an optional on-prem/self-host deployment path. For local development, copy
`apps/api/.env.example` to `apps/api/.env`, then run:

```powershell
docker compose up --build
```

In Vercel, configure the following production variables:

| Variable | Value |
|---|---|
| `APP_URL` | Final Vercel production URL, without a trailing `/` |
| `ENTRA_CLIENT_ID` | Application (client) ID |
| `ENTRA_CLIENT_SECRET` | Client secret **value** |
| `AUTH_SECRET` | Random value: `openssl rand -base64 48` |
| `NIS2CHECK_API_URL` | Public base URL of the `nis2tool-api` Vercel project |
| `NIS2CHECK_API_KEY` | Same random API key used by the API deployment |
| `CRON_SECRET` | Separate random value protecting the Vercel cron route |

The API Vercel project requires `DATABASE_URL`, `NIS2CHECK_CLIENT_ID`,
`NIS2CHECK_CLIENT_SECRET`, `NIS2CHECK_API_KEY`, `EVIDENCE_HASH_KEY`, and `CRON_SECRET`.
`NIS2CHECK_CLIENT_ID` and `NIS2CHECK_CLIENT_SECRET` are the same Entra application values as
the web project; `NIS2CHECK_API_KEY` and `CRON_SECRET` must match the web project.

Set `APP_URL` before deploying and make both callback URLs in Entra match exactly. For local
development, add `http://localhost:3000/api/auth/callback/microsoft` and
`http://localhost:3000/api/onboarding/callback/microsoft` as Web redirect URIs and use
`APP_URL=http://localhost:3000` in `.env.local`. The API project does not have a tenant ID
environment variable: every tenant ID is verified during sign-in and held as tenant-scoped data.
Never commit `.env.local`, `apps/api/.env`, client secrets, database URLs, or generated keys.
