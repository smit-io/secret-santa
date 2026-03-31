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


class NoValidAssignment(SecretSantaError):
    def __init__(self, message: str | None = None) -> None:
        super().__init__(
            message
            or "No valid Secret Santa assignment could be found due to conflicting constraints."
        )


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
