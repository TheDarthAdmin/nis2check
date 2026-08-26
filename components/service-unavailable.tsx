import { HostedApiError } from "@/lib/hosted-api";

/**
 * Says what actually went wrong. "Check the connection and try again" sent readers looking at
 * the network for what is usually a missing setting or a service that answered with an error.
 */
export function describeHostedFailure(error: unknown): { title: string; detail: string; hint: string } {
  if (!(error instanceof HostedApiError)) {
    return {
      title: "Evidence cannot be loaded.",
      detail: "This deployment hit an unexpected error before it could reach the collection service.",
      hint: "The deployment logs of this web application name the cause.",
    };
  }
  if (error.kind === "unconfigured") {
    return {
      title: "This deployment is not connected to a collection service.",
      detail: error.message,
      hint: "Set both variables on the web deployment, using the same API key as the collection service, and redeploy.",
    };
  }
  if (error.kind === "unreachable") {
    return {
      title: "The collection service did not answer.",
      detail: "The request to NIS2CHECK_API_URL failed before a response arrived.",
      hint: "Check that the service is running and that its URL is reachable from this deployment; a cold start can also take a moment.",
    };
  }
  if (error.status === 401) {
    return {
      title: "The collection service rejected this deployment.",
      detail: "The API key sent with the request was not accepted (401).",
      hint: "NIS2CHECK_API_KEY must be identical on the web deployment and on the collection service.",
    };
  }
  if (error.status === 403) {
    return {
      title: "Administrator approval is missing.",
      detail: error.message,
      hint: "A tenant administrator has to approve the read-only Microsoft Graph permissions before evidence can be read.",
    };
  }
  return {
    title: "The collection service returned an error.",
    detail: error.message,
    hint: "Its own logs name the cause; a schema change that has not reached the database is a common one.",
  };
}

export function ServiceUnavailable({ error, eyebrow = "Collection service" }: { error: unknown; eyebrow?: string }) {
  const { title, detail, hint } = describeHostedFailure(error);
  return <section className="empty-state">
    <div className="eyebrow">{eyebrow}</div>
    <h1>{title}</h1>
    <p>{detail}</p>
    <p className="muted">{hint}</p>
  </section>;
}
