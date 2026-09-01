# Secret Santa Graph

Constraint-based Secret Santa solver using bipartite graph matching.

## Install

pip install -e .

## Usage

```python
from secret_santa import Participant, solve

participants = {
    "Alice": Participant("Alice", exclude={"Bob"}),
    "Bob": Participant("Bob"),
    "Charlie": Participant("Charlie", include={"Alice", "Bob"}),
}

print(solve(participants))
```

`solve()` honours both inclusions and exclusions. Three relaxed variants are
available for retrying a roster that won't solve:

| Function | Inclusions | Exclusions |
|---|---|---|
| `solve` | applied | applied |
| `solve_ignore_inclusions` | ignored | applied |
| `solve_ignore_exclusions` | applied | ignored |
| `solve_ignore_all_constraints` | ignored | ignored |

## When there is no valid assignment

Every failure raises a `SecretSantaError` subclass naming the specific cause.
The solver never returns an invalid assignment, never refuses a roster that
does have a solution, and never fails with an untyped error.

| Exception | Cause |
|---|---|
| `NotEnoughParticipants` | fewer than 2 people |
| `UnknownParticipantReferenced` | an include/exclude names someone not on the roster |
| `InclusionExclusionConflict` | one person both includes and excludes the same name |
| `MutualExclusionGroup` | someone has no possible recipient at all |
| `FullyExcludedParticipant` | someone can never receive — nobody is able to give to them |
| `NoValidAssignment` | no single person is stuck, but some group collectively is |

### Diagnosing `NoValidAssignment`

`NoValidAssignment` identifies the exact group that cannot all be satisfied,
rather than reporting a generic failure:

```python
from secret_santa import Participant, solve
from secret_santa.exceptions import NoValidAssignment

participants = {
    "A": Participant("A", include={"X", "Y"}),
    "B": Participant("B", include={"X", "Y"}),
    "C": Participant("C", include={"X", "Y"}),
    "X": Participant("X"),
    "Y": Participant("Y"),
    "Z": Participant("Z"),
}

try:
    solve(participants)
except NoValidAssignment as e:
    print(e)
    # No valid assignment: the group [A, B, C] (3 people) can only give to
    # [X, Y] (2 option(s)) between them, which isn't enough for everyone in
    # the group to receive a distinct gift (Hall's condition violated).

    print(e.deficient_givers)      # {'A', 'B', 'C'}
    print(e.reachable_receivers)   # {'X', 'Y'}
    print(e.deficient_groups)      # every independent over-constrained group
    print(e.culprit_exclusions)    # [] — this failure is driven by inclusions
```

`culprit_exclusions` holds `(giver, excluded)` pairs whose removal would
genuinely widen the group's options. It is empty when there is no such rule to
relax — as above, where the inclusion lists are what constrain the group, and
whenever exclusions are not in force. On an exclusion-driven failure it lists
the rules worth revisiting:

```python
participants = {
    "A": Participant("A", exclude={"B", "C"}),
    "B": Participant("B", exclude={"A", "C"}),
    "C": Participant("C", exclude={"A", "B"}),
    "X": Participant("X"),
    "Y": Participant("Y"),
}
# culprit_exclusions -> [('A', 'B'), ('A', 'C'), ('B', 'A'), ...]
# dropping any single one of these makes the roster solvable
```

When several unrelated groups are over-constrained, each is reported
separately in `deficient_groups`; the single-group attributes above front the
smallest one.

## Scenarios

| Scenario | N | Outcome | Reported as |
|---|---|---|---|
| No rules at all | 4 | solves | — |
| Minimum roster | 2 | solves | — |
| 2 couples, each excludes their partner | 6 | solves | — |
| Everyone excludes 2 others | 6 | solves | — |
| 3 people with 1 inclusion each, all distinct | 5 | solves | — |
| Everyone includes 3 others, spread out | 5 | solves | — |
| Self-exclusion only (no-op) | 5 | solves | — |
| A and B locked to each other, C/D/E free | 5 | solves | — |
| One person | 1 | fails | `NotEnoughParticipants` |
| A excludes a name not on the roster | 5 | fails | `UnknownParticipantReferenced` |
| A both includes and excludes B | 5 | fails | `InclusionExclusionConflict` |
| A excludes all 4 others | 5 | fails | `MutualExclusionGroup` |
| A includes only themselves | 5 | fails | `MutualExclusionGroup` |
| Everyone excludes E | 5 | fails | `FullyExcludedParticipant` |
| 5 of 6 people all exclude F | 6 | fails | `FullyExcludedParticipant` |
| Nobody's inclusion list mentions D or E | 5 | fails | `FullyExcludedParticipant` |
| 2 people include only Bob | 4 | fails | `NoValidAssignment` |
| 3 people include the same 2 | 6 | fails | `NoValidAssignment` |
| 3 people mutually exclude each other | 5 | fails | `NoValidAssignment` |
| Two unrelated over-constrained trios | 11 | fails | `NoValidAssignment` (2 groups) |

Note the same rule can solve or fail depending on roster size — `A` and `B`
locked to each other solves with five people, because C, D and E can cover
each other, but fails with three, because nobody is left to give to C.

## Will a roster solve?

The exact criterion is Hall's condition: it fails when some group of givers
can collectively reach fewer recipients than there are people in the group.
Counts alone don't decide it — three people with one option each solve if
those options differ and fail if they collide.

Counts do decide whether a failure is *possible*. For `N` participants where
`X` of them have constraints:

| Constraint | Always solves when | A failing arrangement exists when |
|---|---|---|
| `Y` inclusions each | `Y >= X` | `X >= Y+2`, or `Y < X` and `X+Y <= N`, or `X >= N-1` and `Y <= N-2` |
| `Z` exclusions each | `Z <= floor(N/2)-1` and `X <= N-2` | `N-(Z+1) < min(X, Z+1)`, or `X >= N-1` and `Z >= 1` |

Both safe bounds follow from the same rule, which covers mixed rosters too:

> everyone must be able to give to at least `ceil(N/2)` people, **and** be
> able to receive from at least `ceil(N/2)` people.

The receiving half is the one that's easy to miss — "everyone only excludes
one person" still breaks if they all exclude the same person.
