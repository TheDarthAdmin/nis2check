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
| C14 | Third-party apps met hoge rechten | DelegatedPermissionGrant.Read.All | Alleen geselecteerde delegated scopes. |
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

## Hosted interface: Microsoft Entra sign-in

The Next.js hosted interface now uses a tenant-restricted Microsoft Entra authorization-code
flow. It validates the Microsoft ID token signature, issuer, audience, nonce and tenant ID;
uses PKCE and a state cookie; and stores only a signed, eight-hour application session. It
does not store a Microsoft access or refresh token. The collector remains separate and only
uses its documented read-only Microsoft Graph scopes.

1. In the [Microsoft Entra admin center](https://entra.microsoft.com/), open **App
   registrations** and choose **New registration**.
2. Select **Accounts in this organizational directory only (single tenant)**. Give it a name
   such as `Nis2Check Hosted`.
3. Under **Redirect URI**, select **Web** and enter
   `https://<your-production-domain>/api/auth/callback/microsoft`.
4. Copy the **Directory (tenant) ID** and **Application (client) ID** from the app's Overview.
5. Under **Certificates & secrets**, create a client secret and copy its **Value** immediately.
   Do not use the secret ID. Add an expiry reminder before its end date.
6. No Microsoft Graph API permission is needed merely to sign in. `openid`, `profile`, and
   `email` are OpenID Connect scopes requested by the application. For tighter access control,
   assign users/groups to the Enterprise application and set **Assignment required?** to Yes.

In Vercel, set the following production environment variables (see `.env.example`):

| Variable | Value |
|---|---|
| `APP_URL` | Your final Vercel production URL, without a trailing `/` |
| `ENTRA_TENANT_ID` | Directory (tenant) ID |
| `ENTRA_CLIENT_ID` | Application (client) ID |
| `ENTRA_CLIENT_SECRET` | The client secret **value** |
| `AUTH_SECRET` | A new random value, e.g. `openssl rand -base64 48` |

Set `APP_URL` before deploying and make the callback URL in Entra match it exactly. For local
development, add `http://localhost:3000/api/auth/callback/microsoft` as a second Web redirect
URI and use `APP_URL=http://localhost:3000` in `.env.local`. Never commit `.env.local` or the
client secret.
