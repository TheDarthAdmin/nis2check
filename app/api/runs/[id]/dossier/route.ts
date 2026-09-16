import { getSession } from "@/lib/auth";
import { fetchDossier, HostedApiError } from "@/lib/hosted-api";

export const runtime = "nodejs";
export const maxDuration = 120;

/**
 * Streams the evidence dossier straight through, so the file never lands in this process.
 * `format=pdf` is drawn with ReportLab and `format=html` comes from the Jinja template.
 */
export async function GET(request: Request, { params }: { params: Promise<{ id: string }> }) {
  const session = await getSession();
  if (!session) return Response.json({ detail: "Sign in required." }, { status: 401 });
  const { id } = await params;
  const requested = new URL(request.url).searchParams.get("format");
  const format = requested === "html" ? "html" : "pdf";
  try {
    const upstream = await fetchDossier(session.tenantId, id, format);
    return new Response(upstream.body, {
      headers: {
        "Content-Type": upstream.headers.get("Content-Type") || "application/octet-stream",
        "Content-Disposition": upstream.headers.get("Content-Disposition") || `attachment; filename="nis2check-dossier.${format}"`,
        "Cache-Control": "no-store",
      },
    });
  } catch (error) {
    const detail = error instanceof HostedApiError ? error.message : "The dossier could not be built.";
    return Response.json({ detail }, { status: error instanceof HostedApiError ? error.status || 503 : 503 });
  }
}
