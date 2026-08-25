const requiredKeys = [
  "APP_URL",
  "ENTRA_TENANT_ID",
  "ENTRA_CLIENT_ID",
  "ENTRA_CLIENT_SECRET",
  "AUTH_SECRET",
] as const;

export type AppConfig = Record<(typeof requiredKeys)[number], string>;

export function getConfig(): AppConfig {
  const missing = requiredKeys.filter((key) => !process.env[key]);
  if (missing.length > 0) {
    throw new Error(`Missing required environment variable(s): ${missing.join(", ")}.`);
  }

  const appUrl = process.env.APP_URL!.replace(/\/$/, "");
  if (!/^https?:\/\//.test(appUrl)) {
    throw new Error("APP_URL must start with http:// or https://.");
  }
  if (process.env.AUTH_SECRET!.length < 32) {
    throw new Error("AUTH_SECRET must contain at least 32 characters.");
  }

  return {
    APP_URL: appUrl,
    ENTRA_TENANT_ID: process.env.ENTRA_TENANT_ID!.toLowerCase(),
    ENTRA_CLIENT_ID: process.env.ENTRA_CLIENT_ID!,
    ENTRA_CLIENT_SECRET: process.env.ENTRA_CLIENT_SECRET!,
    AUTH_SECRET: process.env.AUTH_SECRET!,
  };
}

export function isConfigured(): boolean {
  return requiredKeys.every((key) => Boolean(process.env[key]));
}
