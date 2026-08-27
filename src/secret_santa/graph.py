from typing import Dict, Set

import networkx as nx

from .exceptions import (
    FullyExcludedParticipant,
    InclusionExclusionConflict,
    MutualExclusionGroup,
    NotEnoughParticipants,
    UnknownParticipantReferenced,
)
from .models import Participant


def _detect_mutual_exclusion_groups(participants: Dict[str, Participant]) -> None:
    names: Set[str] = set(participants.keys())

    allowed: Dict[str, Set[str]] = {
        p.name: names - {p.name} - p.exclude for p in participants.values()
    }

    # Case 1 — no recipients at all
    for giver, recips in allowed.items():
        if not recips:
            raise MutualExclusionGroup({giver})

    # Case 2 — mutual pair trap (very common real bug)
    for a in names:
        for b in names:
            if a >= b:
                continue

            pair = {a, b}

            # both restricted to the pair
            if allowed[a] <= pair and allowed[b] <= pair:
                # but the internal cycle is impossible
                if b not in allowed[a] or a not in allowed[b]:
                    raise MutualExclusionGroup(pair)


def _precheck_participants(participants: Dict[str, Participant]) -> None:
    names = set(participants.keys())

    # 1. Unknown names in include/exclude
    for p in participants.values():
        unknown = (p.include | p.exclude) - names
        if unknown:
            raise UnknownParticipantReferenced(p.name, unknown)

    # 2. Inclusion and exclusion conflict
    for p in participants.values():
        conflict = p.include & p.exclude
        if conflict:
            raise InclusionExclusionConflict(p.name, conflict)

    # 3. Detect givers left with no possible recipient
    _detect_mutual_exclusion_groups(participants)

    # 4. Detect participants excluded by every *other* participant.
    # A participant never gives to themselves, so their own exclude set says
    # nothing about whether they can receive.
    excluded_by_all = []
    for candidate in names:
        givers = [p for name, p in participants.items() if name != candidate]
        if all(candidate in p.exclude for p in givers):
            excluded_by_all.append(candidate)

    if excluded_by_all:
        raise FullyExcludedParticipant(excluded_by_all)


def build_graph(
    participants: Dict[str, Participant],
    use_inclusions: bool,
    use_exclusions: bool,
) -> nx.DiGraph:
    if len(participants) < 2:
        raise NotEnoughParticipants("At least 2 participants required")

    _precheck_participants(participants)

    G: nx.DiGraph = nx.DiGraph()

    givers = {f"g:{p}" for p in participants}
    receivers = {f"r:{p}" for p in participants}

    G.add_nodes_from(givers, bipartite=0)
    G.add_nodes_from(receivers, bipartite=1)

    for name, p in participants.items():
        giver = f"g:{name}"

        for other in participants:
            if other == name:
                continue

            if use_inclusions and p.include and other not in p.include:
                continue

            if use_exclusions and other in p.exclude:
                continue

            G.add_edge(giver, f"r:{other}")

        if G.out_degree(giver) == 0:
            raise MutualExclusionGroup(
                {name},
                f"{name} has no valid recipients under current rules",
            )

    return G
