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
nis2check run --tenant-id <tenant-id> --client-id <app-id> --device-code
nis2check report nis2check.json
```

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
mypy --strict packages/collector packages/catalog
```

De collector doet uitsluitend GET-verzoeken naar Microsoft Graph. Bij ontoegankelijke of
onvolledige data rapporteert hij `INCONCLUSIVE` en doet hij geen aannames.

## Hosted product

The hosted product is a single-tenant deployment for the tenant named in its environment. Its
web interface authenticates users with Entra; its separate API obtains an application-only,
read-only Graph token and invokes the same Python collector used by the CLI. The web app never
receives a Graph token. The API stores completed runs, verdicts, rationale, control metadata,
counts, and HMAC-keyed object references only. It never stores raw Graph responses, UPNs, email
addresses, access tokens, or refresh tokens.

Runs can be started manually from the hosted UI. `vercel.json` schedules a protected daily run
at 03:00 UTC; change the expression if a different schedule is required. A partial unique index
prevents overlapping runs for the tenant.

### Entra application registration

1. In the [Microsoft Entra admin center](https://entra.microsoft.com/), open **App
   registrations** and choose **New registration**.
2. Select **Accounts in this organizational directory only (single tenant)**. Give it a name
   such as `Nis2Check Hosted`.
3. Under **Redirect URI**, select **Web** and enter
   `https://<your-web-domain>/api/auth/callback/microsoft`.
4. Copy the **Directory (tenant) ID** and **Application (client) ID** from the app's Overview.
5. Under **Certificates & secrets**, create a client secret and copy its **Value** immediately.
   Do not use the secret ID. Add an expiry reminder before its end date.
6. In **API permissions** → **Microsoft Graph** → **Application permissions**, add the union
   of the read-only permissions in the controls table above. Grant admin consent. Do not add
   delegated Graph permissions or any write permission. `openid`, `profile`, and `email` are
   requested only for browser sign-in.
7. For tighter access control, assign users/groups to the Enterprise application and set
   **Assignment required?** to Yes.

### Deployment

Provision a PostgreSQL database (for example through the Neon Vercel Marketplace integration).
Deploy `apps/api/Dockerfile` to a container host that supports long-running HTTP requests, then
set its public HTTPS URL as `NIS2CHECK_API_URL` in the Vercel web project. The API needs its own
environment values from `apps/api/.env.example`; the web project needs `.env.example`. The two
projects must share the same `NIS2CHECK_API_KEY`, but all other generated secrets must be
different.

The API creates its schema on first start. For local development, copy `apps/api/.env.example`
to `apps/api/.env`, then run:

```powershell
docker compose up --build
```

In Vercel, configure the following production variables:

| Variable | Value |
|---|---|
| `APP_URL` | Final Vercel production URL, without a trailing `/` |
| `ENTRA_TENANT_ID` | Directory (tenant) ID |
| `ENTRA_CLIENT_ID` | Application (client) ID |
| `ENTRA_CLIENT_SECRET` | Client secret **value** |
| `AUTH_SECRET` | Random value: `openssl rand -base64 48` |
| `NIS2CHECK_API_URL` | Public base URL of the deployed hosted API |
| `NIS2CHECK_API_KEY` | Same random API key used by the API deployment |
| `CRON_SECRET` | Separate random value protecting the Vercel cron route |

Set `APP_URL` before deploying and make the callback URL in Entra match it exactly. For local
development, add `http://localhost:3000/api/auth/callback/microsoft` as a second Web redirect
URI and use `APP_URL=http://localhost:3000` in `.env.local`. Never commit `.env.local`,
`apps/api/.env`, client secrets, database URLs, or generated keys.
