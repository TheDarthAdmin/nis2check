# Nis2Check

> NIS2 is grotendeels organisatorisch. Nis2Check verzamelt alleen technisch verifieerbaar bewijs uit Microsoft 365 en geeft **geen** conformiteitsverklaring.

Nis2Check heeft één pure, open-source collector en optionele gehoste interfaces. De collector
doet uitsluitend GET-verzoeken naar Microsoft Graph en verandert nooit tenantconfiguratie.

## Controls

| ID | Control | Vereiste scope(s) | Belangrijkste beperking |
|---|---|---|---|
| C01 | MFA voor alle gebruikers | Policy.Read.All | Geen validatie van break-glass-legitimiteit. |
| C02 | Phishing-resistente adminauth | Policy.Read.All | Adminscope niet volledig bewijsbaar. |
| C03 | Legacy-auth blokkeren | Policy.Read.All | Alleen CA-bewijs. |
| C04 | Per-user MFA-restanten | User.Read.All | Beta endpoint, gelimiteerde inventaris. |
| C05 | Global Administrator-limiet | RoleManagement.Read.Directory | Geen zakelijke rechtvaardiging. |
| C06 | Emergency-accessuitsluitingen | Policy.Read.All | Alleen object-ID's. |
| C07 | Gastuitnodigingen beperken | Policy.Read.All | Alleen tenantbeleid. |
| C08 | Inactieve accounts | AuditLog.Read.All, User.Read.All | Vereist Entra P1-sign-indata. |
| C09 | Schijfversleuteling | DeviceManagementManagedDevices.Read.All | Alleen beheerde devices. |
| C10 | Update-ringdeadline | DeviceManagementConfiguration.Read.All | Installatie niet bewijsbaar. |
| C11 | ASR block mode | DeviceManagementConfiguration.Read.All | Profielvormen verschillen. |
| C12 | Directory audit logs | AuditLog.Read.All | Nooit PASS: Unified Audit is niet via Graph verifieerbaar. |
| C13 | Security contact | Organization.Read.All | Monitoring niet gevalideerd. |
| C14 | Third-party apps met hoge rechten | Directory.Read.All | Alleen geselecteerde delegated scopes. |
| C15 | User consent beperken | Policy.Read.All | Alleen standaardbeleid. |

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
mypy --strict packages/collector packages/catalog apps/cli
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
