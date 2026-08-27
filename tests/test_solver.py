import pytest
from faker import Faker

from secret_santa import Participant, solve  # type: ignore[import-untyped]
from secret_santa.exceptions import (  # type: ignore[import-untyped]
    FullyExcludedParticipant,
    InclusionExclusionConflict,
    MutualExclusionGroup,
    NotEnoughParticipants,
    NoValidAssignment,
    UnknownParticipantReferenced,
)

fake = Faker()


def test_basic():
    participants = {
        "Alice": Participant("Alice"),
        "Bob": Participant("Bob"),
        "Charlie": Participant("Charlie"),
    }

    result = solve(participants)

    assert len(result) == 3
    for giver, receiver in result.items():
        assert giver != receiver


def assert_valid_result(result: dict[str, str]) -> None:
    # everyone gives to exactly one
    assert len(result) == len(set(result.keys()))

    # everyone receives from exactly one
    assert len(set(result.values())) == len(result)

    # no self assignment
    for giver, receiver in result.items():
        assert giver != receiver


# -----------------------------------------------------------
# 1. Exactly two participants (valid)
# -----------------------------------------------------------


def test_two_participants_valid():
    participants = {
        "Alice": Participant("Alice"),
        "Bob": Participant("Bob"),
    }

    result = solve(participants)
    assert_valid_result(result)


# -----------------------------------------------------------
# 2. Two participants but one excludes the other (impossible)
# -----------------------------------------------------------


def test_two_participants_exclusion_failure():
    participants = {
        "Alice": Participant("Alice", exclude={"Bob"}),
        "Bob": Participant("Bob"),
    }

    with pytest.raises(MutualExclusionGroup):
        solve(participants)


# -----------------------------------------------------------
# 3. One participant (invalid)
# -----------------------------------------------------------


def test_single_participant_failure():
    participants = {
        "Alice": Participant("Alice"),
    }

    with pytest.raises(NotEnoughParticipants):
        solve(participants)


# -----------------------------------------------------------
# 4. Randomized large tests using Faker
# -----------------------------------------------------------


@pytest.mark.parametrize("count", [5, 10, 25, 50, 100])
def test_large_random_participants(count: int):
    names = [fake.unique.first_name() + str(i) for i in range(count)]

    participants = {name: Participant(name) for name in names}

    result = solve(participants)
    assert_valid_result(result)


# def assert_valid_result(result: dict[str, str]) -> None:
#     assert len(set(result.keys())) == len(result)
#     assert len(set(result.values())) == len(result)
#     for g, r in result.items():
#         assert g != r


# -----------------------------------------------------------
# Same inclusion for two people — VALID case
# -----------------------------------------------------------


def test_same_inclusion_valid():
    participants = {
        "Alice": Participant("Alice", include={"Bob"}),
        "Charlie": Participant("Charlie", include={"Bob", "Dave"}),
        "Dave": Participant("Dave"),
        "Bob": Participant("Bob"),
    }

    result = solve(participants)
    assert_valid_result(result)


# -----------------------------------------------------------
# Same inclusion for two people — IMPOSSIBLE case
# -----------------------------------------------------------


def test_same_inclusion_impossible():
    participants = {
        "Alice": Participant("Alice", include={"Bob"}),
        "Charlie": Participant("Charlie", include={"Bob"}),
        "Bob": Participant("Bob"),
    }

    with pytest.raises(NoValidAssignment):
        solve(participants)


# -----------------------------------------------------------
# Inclusion + exclusion interplay (valid)
# -----------------------------------------------------------


def test_inclusion_and_exclusion_valid():
    participants = {
        "Alice": Participant("Alice", include={"Bob", "Charlie"}, exclude={"Charlie"}),
        "Bob": Participant("Bob"),
        "Charlie": Participant("Charlie"),
    }

    # Alice effectively can only give to Bob
    # result = solve(participants)
    with pytest.raises(InclusionExclusionConflict):
        solve(participants)


# -----------------------------------------------------------
# Inclusion + exclusion conflict (impossible)
# -----------------------------------------------------------


def test_inclusion_and_exclusion_conflict():
    participants = {
        "Alice": Participant("Alice", include={"Bob"}, exclude={"Bob"}),
        "Bob": Participant("Bob"),
        "Charlie": Participant("Charlie"),
    }

    with pytest.raises(Exception):
        solve(participants)


# -----------------------------------------------------------
# Chain of inclusions that is solvable
# -----------------------------------------------------------


def test_chain_inclusions_valid():
    participants = {
        "A": Participant("A", include={"B"}),
        "B": Participant("B", include={"C"}),
        "C": Participant("C"),
    }

    result = solve(participants)
    assert_valid_result(result)
    assert result["A"] == "B"
    assert result["B"] == "C"


# -----------------------------------------------------------
# Inclusion cycle of size 2 (impossible)
# -----------------------------------------------------------


def test_inclusion_cycle_two_people():
    participants = {
        "A": Participant("A", include={"B"}),
        "B": Participant("B", include={"A"}),
        "C": Participant("C"),
    }

    # A<->B forms a 2-cycle, but both can't receive from each other and
    # also satisfy giving constraints simultaneously with C in the system
    with pytest.raises(NoValidAssignment):
        solve(participants)


# -----------------------------------------------------------
# Larger mixed case with inclusions and exclusions
# -----------------------------------------------------------


def test_complex_mixed_constraints():
    participants = {
        "Alice": Participant("Alice", include={"Bob", "Charlie"}),
        "Bob": Participant("Bob", exclude={"Charlie"}),
        "Charlie": Participant("Charlie"),
        "Dave": Participant("Dave", exclude={"Alice"}),
        "Eve": Participant("Eve"),
    }

    result = solve(participants)
    assert_valid_result(result)


# -----------------------------------------------------------
# Everyone excludes the same ONE person — impossible
# -----------------------------------------------------------


def test_everyone_excludes_one_person_impossible():
    names = ["A", "B", "C", "D"]

    participants = {name: Participant(name, exclude={"D"}) for name in names}

    with pytest.raises(FullyExcludedParticipant):
        solve(participants)


def test_unknown_reference():
    participants = {
        "Alice": Participant("Alice", include={"Bob"}),
        "Bob": Participant("Bob", exclude={"Charlie"}),  # Charlie doesn't exist
    }

    with pytest.raises(UnknownParticipantReferenced):
        solve(participants)


def test_include_exclude_conflict():
    participants = {
        "Alice": Participant("Alice", include={"Bob"}, exclude={"Bob"}),
        "Bob": Participant("Bob"),
    }

    with pytest.raises(InclusionExclusionConflict):
        solve(participants)


def test_fully_excluded_single():
    participants = {
        "A": Participant("A", exclude={"D"}),
        "B": Participant("B", exclude={"D"}),
        "C": Participant("C", exclude={"D"}),
        "D": Participant("D", exclude={"D"}),
    }

    with pytest.raises(FullyExcludedParticipant):
        solve(participants)


def test_not_fully_excluded_multiple_valid():
    participants = {
        "A": Participant("A", exclude={"D", "E"}),
        "B": Participant("B", exclude={"D", "E"}),
        "C": Participant("C", exclude={"D", "E"}),
        "D": Participant("D"),
        "E": Participant("E"),
    }

    result = solve(participants)
    assert len(result) == 5


def test_fully_excluded_without_self_exclusion():
    # D is unreachable: every other participant excludes them. D does not
    # exclude themselves, and should not need to for this to be detected.
    participants = {
        "A": Participant("A", exclude={"D"}),
        "B": Participant("B", exclude={"D"}),
        "C": Participant("C", exclude={"D"}),
        "D": Participant("D"),
    }

    with pytest.raises(FullyExcludedParticipant):
        solve(participants)


def test_mutual_pair_exclusion():
    participants = {
        "A": Participant("A", exclude={"B"}),
        "B": Participant("B", exclude={"A"}),
    }

    with pytest.raises(MutualExclusionGroup):
        solve(participants)


def test_mutual_triple_exclusion():
    participants = {
        "A": Participant("A", exclude={"B", "C"}),
        "B": Participant("B", exclude={"A", "C"}),
        "C": Participant("C", exclude={"A", "B"}),
    }

    with pytest.raises(MutualExclusionGroup):
        solve(participants)


def test_subtle_hall_violation():
    participants = {
        "A": Participant("A", exclude={"C"}),
        "B": Participant("B", exclude={"C"}),
        "C": Participant("C", exclude={"A", "B"}),
    }

    with pytest.raises(MutualExclusionGroup):
        solve(participants)


def test_no_valid_recipients_due_to_exclusions():
    participants = {
        "Alice": Participant("Alice", exclude={"Bob", "Charlie"}),
        "Bob": Participant("Bob"),
        "Charlie": Participant("Charlie"),
    }

    with pytest.raises(MutualExclusionGroup):
        solve(participants)


def test_inclusion_and_exclusion_still_valid_cycle():
    participants = {
        "Alice": Participant("Alice", include={"Bob"}),
        "Bob": Participant("Bob", exclude={"Alice"}),
        "Charlie": Participant("Charlie"),
    }

    result = solve(participants)
    assert len(result) == 3


def test_no_valid_recipients_include_and_exclude():
    participants = {
        "Alice": Participant("Alice", include={"Bob"}, exclude={"Bob"}),
        "Bob": Participant("Bob"),
    }

    with pytest.raises(InclusionExclusionConflict):
        solve(participants)


def test_multiple_inclusions_same_single_person_impossible():
    participants = {
        "Alice": Participant("Alice", include={"Bob"}),
        "Charlie": Participant("Charlie", include={"Bob"}),
        "Bob": Participant("Bob"),
        "John": Participant("John", include={"Alice"}),
    }

    with pytest.raises(NoValidAssignment):
        solve(participants)
