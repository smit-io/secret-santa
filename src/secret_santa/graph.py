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


def _alternating_reach(
    G: nx.DiGraph, receiver_to_giver: Dict[str, str], seed: str
) -> tuple[Set[str], Set[str]]:
    """Walk the alternating tree rooted at one unmatched giver: follow
    non-matching edges giver->receiver, then the matching edge back
    receiver->giver, repeating. Returns (givers reached, receivers
    reached).
    """
    seen_givers: Set[str] = {seed}
    seen_receivers: Set[str] = set()
    queue = [seed]

    while queue:
        g = queue.pop()
        for r in G.successors(g):
            if r in seen_receivers:
                continue
            seen_receivers.add(r)
            # If r is matched, its partner giver is also "reachable" in
            # the alternating sense; follow the matching edge back.
            partner = receiver_to_giver.get(r)
            if partner is not None and partner not in seen_givers:
                seen_givers.add(partner)
                queue.append(partner)

    return seen_givers, seen_receivers


def find_deficient_sets(
    G: nx.DiGraph, matching: Dict[str, str], givers: Set[str]
) -> list[tuple[Set[str], Set[str]]]:
    """Given a max matching that fails to be perfect, find concrete
    Hall-violating sets: groups of givers S whose combined reachable
    receivers N(S) are fewer than |S|.

    One tree is grown per unmatched giver rather than one tree seeded
    from all of them at once, so two independent over-constrained groups
    are reported as two groups instead of being merged into a single
    confusing blob. Because a maximum matching admits no augmenting
    path, every receiver reached is matched to a giver in S, so each
    group has deficiency exactly 1. Duplicates are collapsed and the
    smallest (most actionable) group comes first. Runs in O(V*(V+E))
    worst case, O(V+E) for the common single-group failure.
    """
    receivers = {n for n in G if n not in givers}

    # matching maps both directions (g -> r and r -> g); normalize to
    # giver -> receiver and receiver -> giver lookups.
    giver_to_receiver = {g: r for g, r in matching.items() if g in givers}
    receiver_to_giver = {r: g for g, r in matching.items() if r in receivers}

    groups: list[tuple[Set[str], Set[str]]] = []
    seen_keys: Set[tuple[frozenset[str], frozenset[str]]] = set()

    for seed in sorted(givers - set(giver_to_receiver.keys())):
        group_givers, group_receivers = _alternating_reach(
            G, receiver_to_giver, seed
        )
        key = (frozenset(group_givers), frozenset(group_receivers))
        if key in seen_keys:
            continue
        seen_keys.add(key)
        groups.append((group_givers, group_receivers))

    groups.sort(key=lambda gr: (len(gr[0]), sorted(gr[0])))
    return groups


def find_deficient_set(
    G: nx.DiGraph, matching: Dict[str, str], givers: Set[str]
) -> tuple[Set[str], Set[str]]:
    """The smallest Hall-violating group, or empty sets if the matching
    is in fact perfect. See find_deficient_sets().
    """
    groups = find_deficient_sets(G, matching, givers)
    return groups[0] if groups else (set(), set())


def find_culprit_exclusions(
    participants: Dict[str, Participant],
    deficient_givers: Set[str],
    reachable_receivers: Set[str],
    use_inclusions: bool = True,
    use_exclusions: bool = True,
) -> list[tuple[str, str]]:
    """Among givers in the deficient set, find exclude-rules whose removal
    would actually grow N(S) — i.e. rules that are in force and that point
    at someone the group cannot currently reach.

    A rule only qualifies if relaxing it changes the graph:

    - exclusions must be in force at all (`use_exclusions`);
    - the giver must not have an inclusion list, since build_graph applies
      inclusions first and an exclusion on top of one is inert;
    - the target must not already be reachable by the group.

    Members of the deficient set are valid targets: a giver in S is
    typically *not* in N(S) — the rest of S excludes them — so opening a
    path to them does grow N(S).
    """
    if not use_exclusions:
        return []

    culprits = []
    reachable_names = {r[2:] for r in reachable_receivers}

    for name in sorted(deficient_givers):
        p = participants[name]
        if use_inclusions and p.include:
            # inclusions already restrict this giver; the exclude set is
            # never consulted, so relaxing it would change nothing.
            continue
        for excluded in sorted(p.exclude):
            if excluded == name:
                continue
            if excluded in reachable_names:
                continue
            culprits.append((name, excluded))

    return culprits


def build_graph(
    participants: Dict[str, Participant],
    use_inclusions: bool,
    use_exclusions: bool,
) -> nx.DiGraph:
    if len(participants) < 2:
        raise NotEnoughParticipants("At least 2 participants required")

    _precheck_participants(participants)

    G: nx.DiGraph = nx.DiGraph()

    # Recorded so failure diagnosis knows which rules were actually in
    # force, rather than assuming both were.
    G.graph["use_inclusions"] = use_inclusions
    G.graph["use_exclusions"] = use_exclusions

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

    # Mirror of the out-degree check above. The exclude-only form of this is
    # caught in the precheck, but someone can also be unreachable because the
    # people who could give to them all have inclusion lists they aren't on —
    # which no amount of exclusion analysis would surface. Reading it off the
    # built graph catches every variant and stays true to whichever rules are
    # actually in force.
    unreceivable = sorted(
        name for name in participants if G.in_degree(f"r:{name}") == 0
    )
    if unreceivable:
        raise FullyExcludedParticipant(
            unreceivable,
            "No one can give to these participants under the current rules: "
            + ", ".join(unreceivable),
        )

    return G
