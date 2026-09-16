"""Evaluators for whether the measures are worked, not only configured.

An incident queue nobody empties, a compliance policy assigned to nothing, a consent request
that reaches no reviewer: each is a control that exists on paper and does nothing in practice.
"""

from datetime import UTC, datetime, timedelta
from typing import Any

from ..models import HandlerResult, Verdict
from .registry import register
from .support import Results, integer_param, result, single_object, timestamp, unreadable

ACTIVE_STATUSES = frozenset({"active", "inProgress"})
UNCLASSIFIED = frozenset({"unknown"})
#: Stand-in for a retention label that never releases its content.
FOREVER_DAYS = 36_500


@register("security_incident_followup")
def security_incident_followup(results: Results, params: dict[str, object]) -> HandlerResult:
    """C32 — incidents that were worked and closed with a verdict, rather than left to age."""
    incidents = results["incidents"]
    if not incidents:
        return unreadable("No incident was returned. An empty queue cannot be told apart from a tenant where Defender XDR was never deployed, so no conclusion is drawn.", results)
    stale_days = integer_param(params, "stale_days", 30)
    cutoff = datetime.now(UTC) - timedelta(days=stale_days)
    active = [item for item in incidents if item.get("status") in ACTIVE_STATUSES]
    stale = [item for item in active if _untouched_since(item, cutoff)]
    resolved = [item for item in incidents if item.get("status") == "resolved"]
    unclassified = [
        item for item in resolved if item.get("classification") in (None, *UNCLASSIFIED)
    ]
    if stale:
        return result(Verdict.FAIL, f"{len(stale)} of {len(active)} active incident(s) have not been touched for more than {stale_days} days.", results)
    if unclassified:
        return result(Verdict.PARTIAL, f"{len(unclassified)} of {len(resolved)} resolved incident(s) were closed without a classification, so a true positive cannot be told from a false one afterwards.", results)
    return result(Verdict.PASS, f"{len(incidents)} incident(s) were read: {len(active)} active and worked within {stale_days} days, {len(resolved)} closed with a classification.", results)


def _untouched_since(incident: dict[str, Any], cutoff: datetime) -> bool:
    updated = timestamp(incident.get("lastUpdateDateTime")) or timestamp(
        incident.get("createdDateTime")
    )
    return updated is not None and updated < cutoff


@register("device_compliance_policies")
def device_compliance_policies(results: Results, _: dict[str, object]) -> HandlerResult:
    """C33 — a compliance policy assigned to nobody judges nothing."""
    policies = results["policies"]
    if not policies:
        return result(Verdict.FAIL, "No device compliance policy is defined, so Intune has no standard to judge a device against.", results)
    assigned = [policy for policy in policies if policy.get("assignments")]
    if not assigned:
        return result(Verdict.FAIL, f"All {len(policies)} compliance policy(ies) are unassigned, so not one of them evaluates a device.", results)
    if len(assigned) < len(policies):
        return result(Verdict.PARTIAL, f"{len(assigned)} of {len(policies)} compliance policy(ies) are assigned to at least one group; the remainder evaluate nothing.", results)
    return result(Verdict.PASS, f"All {len(policies)} compliance policy(ies) are assigned to at least one group.", results)


@register("admin_consent_workflow")
def admin_consent_workflow(results: Results, _: dict[str, object]) -> HandlerResult:
    """C34 — a governed route for a user who needs an application they may not consent to."""
    policy = single_object(results, "policy")
    if policy is None:
        return unreadable("The tenant did not return an admin consent request policy, so the workflow could not be read.", results)
    if policy.get("isEnabled") is not True:
        return result(Verdict.FAIL, "The admin consent request workflow is off, so a user who needs an application has no governed way to ask for one and the request is handled where this report cannot see it.", results)
    reviewers = policy.get("reviewers")
    count = len(reviewers) if isinstance(reviewers, list) else 0
    if count == 0:
        return result(Verdict.PARTIAL, "The admin consent request workflow is on, but no reviewer is named, so a request reaches nobody.", results)
    if policy.get("notifyReviewers") is not True:
        return result(Verdict.PARTIAL, f"The workflow is on with {count} reviewer(s), but they are not notified when a request arrives.", results)
    return result(Verdict.PASS, f"The admin consent request workflow is on, with {count} reviewer(s) who are notified of new requests.", results)


@register("cross_tenant_access")
def cross_tenant_access(results: Results, _: dict[str, object]) -> HandlerResult:
    """C35 — whether an unknown external tenant is admitted without anyone deciding so."""
    default_policy = single_object(results, "default_policy")
    if default_policy is None:
        return unreadable("The tenant did not return its default cross-tenant access policy.", results)
    partners = results.get("partners") or []
    inbound = default_policy.get("b2bCollaborationInbound")
    users = inbound.get("usersAndGroups") if isinstance(inbound, dict) else None
    access = users.get("accessType") if isinstance(users, dict) else None
    if not isinstance(access, str):
        return unreadable("The default policy did not state an inbound B2B collaboration access type, so admission could not be read.", results)
    named = f"{len(partners)} organisation(s) are configured by name"
    if access == "blocked":
        return result(Verdict.PASS, f"Inbound B2B collaboration is blocked by default, so no unknown tenant is admitted; {named}.", results)
    trust = default_policy.get("inboundTrust")
    accepts_external_mfa = isinstance(trust, dict) and trust.get("isMfaAccepted") is True
    if accepts_external_mfa:
        return result(Verdict.FAIL, f"Inbound B2B collaboration is open to every external tenant by default, and this tenant accepts their own multifactor claim, so an unknown organisation decides how its users authenticate here; {named}.", results)
    if partners:
        return result(Verdict.PARTIAL, f"Inbound B2B collaboration is open to every external tenant by default; {named}, which narrows nothing as long as the default admits the rest.", results)
    return result(Verdict.FAIL, "Inbound B2B collaboration is open to every external tenant by default and no organisation is configured by name.", results)


@register("retention_labels")
def retention_labels(results: Results, params: dict[str, object]) -> HandlerResult:
    """C36 — content held against deletion by a published label, which is not the same as backup."""
    labels = results["labels"]
    if not labels:
        return result(Verdict.FAIL, "No retention label is defined, so no content in this tenant is held against deletion by policy.", results)
    published = [label for label in labels if label.get("isInUse") is True]
    if not published:
        return result(Verdict.FAIL, f"All {len(labels)} retention label(s) exist but none is published or applied, so not one of them protects anything.", results)
    minimum = integer_param(params, "minimum_days", 365)
    durations = [_retention_days(label) for label in published]
    unknown = sum(1 for days in durations if days is None)
    if unknown == len(published):
        return unreadable(f"None of the {len(published)} published retention label(s) returned a readable retention duration.", results)
    short = sum(1 for days in durations if days is not None and days < minimum)
    if short:
        return result(Verdict.PARTIAL, f"{short} of {len(published)} published retention label(s) keep content for less than the {minimum}-day threshold used here.", results)
    if unknown:
        return result(Verdict.PARTIAL, f"{len(published) - unknown} published retention label(s) keep content for at least {minimum} days; the duration of {unknown} other(s) could not be read.", results)
    return result(Verdict.PASS, f"All {len(published)} published retention label(s) keep content for at least {minimum} days.", results)


def _retention_days(label: dict[str, Any]) -> int | None:
    """The retention period in days, treating an indefinite hold as the longest possible."""
    duration = label.get("retentionDuration")
    if not isinstance(duration, dict):
        return None
    if "Forever" in str(duration.get("@odata.type", "")):
        return FOREVER_DAYS
    days = duration.get("days")
    return days if isinstance(days, int) else None
