"""The ten risk-management measures of NIS2 article 21(2).

Catalogue metadata, like the controls themselves: a report groups findings by the measure they
speak to, so the measure has to be nameable without hard-coding a label in a template.
"""

from collections.abc import Iterable

from .models import ControlDefinition

#: Article 21(2), point by point, in the order the directive lists them.
ARTICLE_21_2: dict[str, str] = {
    "a": "Policies on risk analysis and information system security",
    "b": "Incident handling",
    "c": "Business continuity, such as backup management and disaster recovery, and crisis management",
    "d": "Supply chain security, including the relationships with direct suppliers and service providers",
    "e": "Security in acquisition, development and maintenance, including vulnerability handling and disclosure",
    "f": "Policies and procedures to assess the effectiveness of the risk-management measures",
    "g": "Basic cyber hygiene practices and cybersecurity training",
    "h": "Policies and procedures on the use of cryptography and, where appropriate, encryption",
    "i": "Human resources security, access control policies and asset management",
    "j": "Multifactor or continuous authentication, and secured voice, video, text and emergency communications",
}


def measure_letter(reference: str) -> str | None:
    """The point of article 21(2) a control reference names, as in `21(2)(c)` to `c`."""
    if not reference.endswith(")"):
        return None
    letter = reference[:-1].rsplit("(", 1)[-1]
    return letter if letter in ARTICLE_21_2 else None


def measure_title(reference: str) -> str:
    """The text of the measure a control reference names, or the reference itself."""
    letter = measure_letter(reference)
    return ARTICLE_21_2[letter] if letter is not None else reference


def group_by_measure(
    controls: Iterable[ControlDefinition],
) -> list[tuple[str, str, list[ControlDefinition]]]:
    """Every measure of article 21(2) with the controls that speak to it, in directive order.

    Measures with no control are kept in the list. A dossier that silently dropped them would
    suggest the catalogue covers the article completely, and it does not.
    """
    buckets: dict[str, list[ControlDefinition]] = {letter: [] for letter in ARTICLE_21_2}
    for control in controls:
        letter = measure_letter(control.nis2)
        if letter is not None:
            buckets[letter].append(control)
    return [(letter, ARTICLE_21_2[letter], buckets[letter]) for letter in ARTICLE_21_2]
