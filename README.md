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
