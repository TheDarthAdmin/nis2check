export type Verdict = "PASS" | "PARTIAL" | "FAIL" | "INCONCLUSIVE";
export const findings = [
  { id:"C01", domain:"Authentication", title:"Conditional Access requires MFA for all users", verdict:"PASS" as Verdict, changed:"Unchanged" },
  { id:"C03", domain:"Authentication", title:"Legacy authentication is blocked", verdict:"PASS" as Verdict, changed:"Improved" },
  { id:"C05", domain:"Access management", title:"Global Administrator assignments are limited", verdict:"PARTIAL" as Verdict, changed:"Unchanged" },
  { id:"C09", domain:"Devices", title:"Managed devices are encrypted and compliant", verdict:"PARTIAL" as Verdict, changed:"Changed" },
  { id:"C12", domain:"Incident response", title:"Directory audit logs are available", verdict:"PARTIAL" as Verdict, changed:"Unchanged" },
  { id:"C14", domain:"Supply chain", title:"Third-party apps with high Graph permissions are identified", verdict:"FAIL" as Verdict, changed:"New" },
];
