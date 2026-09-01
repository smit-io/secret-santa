import pytest
from faker import Faker

from secret_santa import (  # type: ignore[import-untyped]
    Participant,
    solve,
    solve_ignore_all_constraints,
    solve_ignore_exclusions,
    solve_ignore_inclusions,
)
from secret_santa.exceptions import (  # type: ignore[import-untyped]
    FullyExcludedParticipant,
    InclusionExclusionConflict,
    MutualExclusionGroup,
    NotEnoughParticipants,
    NoValidAssignment,
    SecretSantaError,
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

    # A and B are locked into each other, so neither can give to C and C
    # cannot give to themselves — C can never receive.
    with pytest.raises(FullyExcludedParticipant) as exc_info:
        solve(participants)

    assert "C" in str(exc_info.value)


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


# -----------------------------------------------------------
# Diagnosis: NoValidAssignment carries the concrete Hall-violating
# group and reachable set, not just a generic failure message.
# -----------------------------------------------------------


def test_diagnosis_identifies_deficient_group_via_include():
    # A, B, C can only give to X, Y between them (3 givers, 2 receivers)
    participants = {
        "A": Participant("A", include={"X", "Y"}),
        "B": Participant("B", include={"X", "Y"}),
        "C": Participant("C", include={"X", "Y"}),
        "X": Participant("X"),
        "Y": Participant("Y"),
        "Z": Participant("Z"),
    }

    with pytest.raises(NoValidAssignment) as exc_info:
        solve(participants)

    err = exc_info.value
    assert err.deficient_givers == {"A", "B", "C"}
    assert err.reachable_receivers == {"X", "Y"}


def test_diagnosis_identifies_deficient_group_via_exclude():
    participants = {
        "A": Participant("A", exclude={"B", "C", "D", "E"}),
        "B": Participant("B", exclude={"A", "C", "D", "E"}),
        "C": Participant("C", exclude={"A", "B", "D", "E"}),
        "X": Participant("X"),
        "Y": Participant("Y"),
        "D": Participant("D"),
        "E": Participant("E"),
    }

    with pytest.raises(NoValidAssignment) as exc_info:
        solve(participants)

    err = exc_info.value
    assert err.deficient_givers == {"A", "B", "C"}
    assert err.reachable_receivers == {"X", "Y"}
    # every suggestion comes from inside the group and points at someone the
    # group can't currently reach — D and E, or each other
    assert err.culprit_exclusions
    assert all(giver in {"A", "B", "C"} for giver, _ in err.culprit_exclusions)
    assert all(
        target in {"A", "B", "C", "D", "E"} for _, target in err.culprit_exclusions
    )
    assert ("A", "D") in err.culprit_exclusions


def test_diagnosis_message_is_informative():
    participants = {
        "Alice": Participant("Alice", include={"Bob"}),
        "Charlie": Participant("Charlie", include={"Bob"}),
        "Bob": Participant("Bob"),
    }

    with pytest.raises(NoValidAssignment) as exc_info:
        solve(participants)

    message = str(exc_info.value)
    assert "Alice" in message
    assert "Charlie" in message
    assert "Bob" in message


def test_diagnosis_suggests_relaxing_an_exclusion_inside_the_group():
    # A, B, C only exclude each other. The single fix is to let one of them
    # give to another, so the suggestion must point inside the group.
    participants = {
        "A": Participant("A", exclude={"B", "C"}),
        "B": Participant("B", exclude={"A", "C"}),
        "C": Participant("C", exclude={"A", "B"}),
        "X": Participant("X"),
        "Y": Participant("Y"),
    }

    with pytest.raises(NoValidAssignment) as exc_info:
        solve(participants)

    err = exc_info.value
    assert err.deficient_givers == {"A", "B", "C"}
    assert err.culprit_exclusions

    # acting on any single suggestion really does resolve the failure
    giver, target = err.culprit_exclusions[0]
    relaxed = dict(participants)
    relaxed[giver] = Participant(giver, exclude=participants[giver].exclude - {target})
    assert solve(relaxed)


def test_diagnosis_does_not_suggest_exclusions_masked_by_inclusions():
    # Each giver has an include list, so build_graph never consults their
    # exclude set — relaxing it would change nothing.
    participants = {
        "A": Participant("A", include={"X", "Y"}, exclude={"Q"}),
        "B": Participant("B", include={"X", "Y"}, exclude={"Q"}),
        "C": Participant("C", include={"X", "Y"}, exclude={"Q"}),
        "X": Participant("X"),
        "Y": Participant("Y"),
        "Q": Participant("Q"),
    }

    with pytest.raises(NoValidAssignment) as exc_info:
        solve(participants)

    assert exc_info.value.culprit_exclusions == []


def test_diagnosis_suggests_nothing_when_exclusions_are_ignored():
    participants = {
        "A": Participant("A", include={"X", "Y"}, exclude={"Q"}),
        "B": Participant("B", include={"X", "Y"}, exclude={"Q"}),
        "C": Participant("C", include={"X", "Y"}, exclude={"Q"}),
        "X": Participant("X"),
        "Y": Participant("Y"),
        "Q": Participant("Q"),
    }

    with pytest.raises(NoValidAssignment) as exc_info:
        solve_ignore_exclusions(participants)

    assert exc_info.value.culprit_exclusions == []


def test_unreceivable_via_inclusions_is_named_directly():
    # Nobody can give to B: A and E exclude B, D excludes B, and C has an
    # inclusion list B isn't on. No single exclude rule covers everyone, so
    # this is only visible from the built graph.
    participants = {
        "A": Participant("A", exclude={"B", "C", "E"}),
        "B": Participant("B"),
        "C": Participant("C", include={"D", "E"}),
        "D": Participant("D", exclude={"A", "B", "C"}),
        "E": Participant("E", exclude={"B"}),
    }

    with pytest.raises(FullyExcludedParticipant) as exc_info:
        solve(participants)

    assert "B" in str(exc_info.value)


def test_unreceivable_when_everyone_omits_them_from_inclusions():
    participants = {
        "A": Participant("A", include={"B", "C"}),
        "B": Participant("B", include={"A", "C"}),
        "C": Participant("C", include={"A", "B"}),
        "D": Participant("D", include={"A", "B"}),
        "E": Participant("E", include={"A", "B"}),
    }

    with pytest.raises(FullyExcludedParticipant) as exc_info:
        solve(participants)

    # D and E are on nobody's inclusion list
    message = str(exc_info.value)
    assert "D" in message and "E" in message


def test_unreceivable_check_respects_ignored_inclusions():
    # Same roster, but with inclusions switched off everyone can reach
    # everyone, so it must solve rather than report an unreceivable person.
    participants = {
        "A": Participant("A", include={"B", "C"}),
        "B": Participant("B", include={"A", "C"}),
        "C": Participant("C", include={"A", "B"}),
        "D": Participant("D", include={"A", "B"}),
        "E": Participant("E", include={"A", "B"}),
    }

    assert solve_ignore_inclusions(participants)


def test_diagnosis_reports_independent_groups_separately():
    # Two unrelated over-constrained trios; they must not be merged into one
    # six-person "group" that never actually interacts.
    participants = {
        "A": Participant("A", include={"X", "Y"}),
        "B": Participant("B", include={"X", "Y"}),
        "C": Participant("C", include={"X", "Y"}),
        "P": Participant("P", include={"M", "N"}),
        "Q": Participant("Q", include={"M", "N"}),
        "R": Participant("R", include={"M", "N"}),
        "X": Participant("X"),
        "Y": Participant("Y"),
        "M": Participant("M"),
        "N": Participant("N"),
        "Z": Participant("Z"),
    }

    with pytest.raises(NoValidAssignment) as exc_info:
        solve(participants)

    err = exc_info.value
    groups = {frozenset(g.givers) for g in err.deficient_groups}
    assert groups == {frozenset({"A", "B", "C"}), frozenset({"P", "Q", "R"})}
    # the single-group attributes front one real group, not the union
    assert err.deficient_givers in ({"A", "B", "C"}, {"P", "Q", "R"})
    assert len(err.reachable_receivers) == 2


# -----------------------------------------------------------
# Rosters that solve. These are the shapes people most often assume
# are impossible, and they guard the documented scenario table.
# -----------------------------------------------------------


def test_couples_do_not_gift_their_partner():
    participants = {
        "A": Participant("A", exclude={"B"}),
        "B": Participant("B", exclude={"A"}),
        "C": Participant("C", exclude={"D"}),
        "D": Participant("D", exclude={"C"}),
        "E": Participant("E"),
        "F": Participant("F"),
    }

    result = solve(participants)

    assert_valid_result(result)
    assert result["A"] != "B" and result["B"] != "A"
    assert result["C"] != "D" and result["D"] != "C"


def test_everyone_excludes_two_others():
    # Z=2 is below floor(N/2)=3, so this solves whatever the arrangement.
    participants = {
        "A": Participant("A", exclude={"B", "C"}),
        "B": Participant("B", exclude={"C", "D"}),
        "C": Participant("C", exclude={"D", "E"}),
        "D": Participant("D", exclude={"E", "F"}),
        "E": Participant("E", exclude={"F", "A"}),
        "F": Participant("F", exclude={"A", "B"}),
    }

    result = solve(participants)

    assert_valid_result(result)
    for giver, receiver in result.items():
        assert receiver not in participants[giver].exclude


def test_everyone_includes_three_others():
    participants = {
        "A": Participant("A", include={"B", "C", "D"}),
        "B": Participant("B", include={"C", "D", "E"}),
        "C": Participant("C", include={"D", "E", "A"}),
        "D": Participant("D", include={"E", "A", "B"}),
        "E": Participant("E", include={"A", "B", "C"}),
    }

    result = solve(participants)

    assert_valid_result(result)
    for giver, receiver in result.items():
        assert receiver in participants[giver].include


def test_self_exclusion_is_a_no_op():
    # Nobody gives to themselves anyway, so excluding yourself changes nothing.
    participants = {
        "A": Participant("A", exclude={"A"}),
        "B": Participant("B"),
        "C": Participant("C"),
    }

    assert_valid_result(solve(participants))


def test_locked_pair_solves_when_others_can_cover_each_other():
    # Same A<->B lock as test_inclusion_cycle_two_people, which fails with
    # three people because nobody is left to give to C. With five it solves,
    # because C, D and E can cover each other.
    participants = {
        "A": Participant("A", include={"B"}),
        "B": Participant("B", include={"A"}),
        "C": Participant("C"),
        "D": Participant("D"),
        "E": Participant("E"),
    }

    result = solve(participants)

    assert_valid_result(result)
    assert result["A"] == "B"
    assert result["B"] == "A"


def test_include_only_self_leaves_no_recipients():
    participants = {
        "A": Participant("A", include={"A"}),
        "B": Participant("B"),
        "C": Participant("C"),
    }

    with pytest.raises(MutualExclusionGroup) as exc_info:
        solve(participants)

    assert "A" in str(exc_info.value)


def test_solve_ignore_all_constraints():
    # Impossible under its own rules, trivial once every rule is dropped.
    participants = {
        "A": Participant("A", include={"B"}),
        "B": Participant("B", include={"A"}),
        "C": Participant("C", exclude={"A", "B"}),
    }

    with pytest.raises(SecretSantaError):
        solve(participants)

    assert_valid_result(solve_ignore_all_constraints(participants))


# -----------------------------------------------------------
# Diagnosis internals
# -----------------------------------------------------------


def test_culprits_skip_self_exclusions_and_already_reachable_targets():
    # A, B and C reach only D and E between them — three givers, two
    # receivers. A excludes both itself and E; neither is worth suggesting.
    # Excluding yourself is a no-op, and B and C already reach E, so letting
    # A reach it too would not widen the group's options.
    participants = {
        "A": Participant("A", exclude={"A", "B", "C", "E"}),
        "B": Participant("B", exclude={"A", "C"}),
        "C": Participant("C", exclude={"A", "B"}),
        "D": Participant("D"),
        "E": Participant("E"),
    }

    with pytest.raises(NoValidAssignment) as exc_info:
        solve(participants)

    err = exc_info.value
    assert err.deficient_givers == {"A", "B", "C"}
    assert err.reachable_receivers == {"D", "E"}

    culprits = err.culprit_exclusions
    assert culprits
    # never suggest relaxing a self-exclusion
    assert all(giver != target for giver, target in culprits)
    # never suggest a target the group can already reach
    assert all(target not in err.reachable_receivers for _, target in culprits)
    assert ("A", "E") not in culprits
    # the exclusions that would genuinely widen the group are suggested
    assert ("A", "B") in culprits


def test_each_unmatched_giver_yields_a_minimal_group():
    # Three givers restricted to one receiver leaves two unmatched givers.
    # Each reports its own minimal witness — a pair sharing the one receiver
    # — rather than one merged group of all three.
    participants = {
        "A": Participant("A", include={"D"}),
        "B": Participant("B", include={"D"}),
        "C": Participant("C", include={"D"}),
        "D": Participant("D"),
        "E": Participant("E"),
    }

    with pytest.raises(NoValidAssignment) as exc_info:
        solve(participants)

    err = exc_info.value
    assert len(err.deficient_groups) == 2
    for group in err.deficient_groups:
        # every group is a genuine Hall violation on its own
        assert len(group.givers) > len(group.receivers)
        assert group.givers <= {"A", "B", "C"}
        assert group.receivers == {"D"}


def test_long_group_message_is_truncated():
    # Nine givers sharing the same eight receivers. The reported group is all
    # nine, so the message must summarise rather than list every name.
    targets = [f"R{i}" for i in range(8)]
    givers = [f"G{i}" for i in range(9)]

    participants = {name: Participant(name, include=set(targets)) for name in givers}
    for name in targets:
        participants[name] = Participant(name)
    for name in ("X1", "X2", "X3"):
        participants[name] = Participant(name)

    with pytest.raises(NoValidAssignment) as exc_info:
        solve(participants)

    err = exc_info.value
    message = str(err)
    assert err.deficient_givers == set(givers)
    assert "and 1 more" in message
    # only the first eight names are spelled out
    assert sum(name in message for name in givers) == 8


def test_message_handles_a_group_that_reaches_no_one():
    # solve() cannot produce this state — a giver reaching nobody is caught
    # earlier as MutualExclusionGroup — but the exception is public, so its
    # message must still read correctly when constructed directly.
    err = NoValidAssignment(deficient_givers={"A", "B"}, reachable_receivers=set())

    assert "no one" in str(err)
