from typing import Iterable, NamedTuple


class SecretSantaError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)


class NotEnoughParticipants(SecretSantaError):
    def __init__(self, message: str | None = None) -> None:
        super().__init__(
            message
            or "Secret Santa requires at least two participants to form a valid exchange."
        )


# class NoValidRecipients(SecretSantaError):
#     def __init__(self, participant: str, message: str | None = None) -> None:
#         super().__init__(
#             message
#             or f"{participant} has no valid recipients based on the inclusion/exclusion rules."
#         )


class DeficientGroup(NamedTuple):
    """One over-constrained group: `givers` collectively can only give to
    `receivers`, and there are more of the former than the latter.
    `culprit_exclusions` are (giver, excluded) rules whose removal would
    widen this group's options.
    """

    givers: set[str]
    receivers: set[str]
    culprit_exclusions: list[tuple[str, str]]


def _fmt_names(names: Iterable[str], limit: int = 8) -> str:
    ordered = sorted(names)
    if not ordered:
        return "no one"
    if len(ordered) <= limit:
        return ", ".join(ordered)
    return f"{', '.join(ordered[:limit])}, and {len(ordered) - limit} more"


class NoValidAssignment(SecretSantaError):
    def __init__(
        self,
        message: str | None = None,
        deficient_givers: set[str] | None = None,
        reachable_receivers: set[str] | None = None,
        culprit_exclusions: list[tuple[str, str]] | None = None,
        deficient_groups: list[DeficientGroup] | None = None,
    ) -> None:
        self.deficient_groups = deficient_groups or []

        # The smallest group is the most actionable one, so it fronts the
        # single-group attributes and the message.
        if self.deficient_groups and deficient_givers is None:
            primary = self.deficient_groups[0]
            deficient_givers = primary.givers
            reachable_receivers = primary.receivers
            culprit_exclusions = primary.culprit_exclusions

        self.deficient_givers = deficient_givers or set()
        self.reachable_receivers = reachable_receivers or set()
        self.culprit_exclusions = culprit_exclusions or []

        if message is None and self.deficient_givers:
            message = self._describe()

        super().__init__(
            message
            or "No valid Secret Santa assignment could be found due to conflicting constraints."
        )

    def _describe(self) -> str:
        message = (
            f"No valid assignment: the group [{_fmt_names(self.deficient_givers)}] "
            f"({len(self.deficient_givers)} people) can only give to "
            f"[{_fmt_names(self.reachable_receivers)}] "
            f"({len(self.reachable_receivers)} option(s)) "
            "between them, which isn't enough for everyone in the group "
            "to receive a distinct gift (Hall's condition violated)."
        )

        if self.culprit_exclusions:
            shown = self.culprit_exclusions[:5]
            pairs = ", ".join(f"{g} excludes {r}" for g, r in shown)
            if len(self.culprit_exclusions) > len(shown):
                pairs += f", and {len(self.culprit_exclusions) - len(shown)} more"
            message += f" Relaxing one of these exclusions may fix it: {pairs}."

        others = len(self.deficient_groups) - 1
        if others > 0:
            message += (
                f" {others} other independent group(s) are over-constrained too;"
                " see .deficient_groups."
            )

        return message


class FullyExcludedParticipant(SecretSantaError):
    def __init__(self, names: list[str], message: str | None = None) -> None:
        super().__init__(
            message
            or f"These participants are excluded by everyone and can never receive: {names}"
        )


class InclusionExclusionConflict(SecretSantaError):
    def __init__(
        self, name: str, conflicted: set[str], message: str | None = None
    ) -> None:
        super().__init__(
            message
            or f"{name} both includes and excludes the same participants: {conflicted}"
        )


class UnknownParticipantReferenced(SecretSantaError):
    def __init__(
        self, name: str, unknown: set[str], message: str | None = None
    ) -> None:
        super().__init__(
            message
            or f"{name} references unknown participants in include/exclude: {unknown}"
        )


class MutualExclusionGroup(SecretSantaError):
    def __init__(self, group: set[str], message: str | None = None) -> None:
        names = ", ".join(sorted(group))
        super().__init__(
            message
            or f"These participants mutually exclude each other and cannot form a valid cycle: {names}"
        )
