from typing import Dict

import networkx as nx

from .exceptions import DeficientGroup, NoValidAssignment
from .graph import build_graph, find_culprit_exclusions, find_deficient_sets
from .models import Participant


def _solve(G: nx.DiGraph, participants: Dict[str, Participant]) -> Dict[str, str]:
    givers = {n for n in G if n.startswith("g:")}
    matching = nx.algorithms.bipartite.maximum_matching(G, top_nodes=givers)

    result = {}
    for g, r in matching.items():
        if g.startswith("g:"):
            result[g[2:]] = r[2:]

    if len(result) != len(participants):
        use_inclusions = G.graph.get("use_inclusions", True)
        use_exclusions = G.graph.get("use_exclusions", True)

        groups = []
        for deficient_givers, reachable_receivers in find_deficient_sets(
            G, matching, givers
        ):
            giver_names = {g[2:] for g in deficient_givers}
            groups.append(
                DeficientGroup(
                    givers=giver_names,
                    receivers={r[2:] for r in reachable_receivers},
                    culprit_exclusions=find_culprit_exclusions(
                        participants,
                        giver_names,
                        reachable_receivers,
                        use_inclusions,
                        use_exclusions,
                    ),
                )
            )

        raise NoValidAssignment(deficient_groups=groups)

    return result


def solve(participants: Dict[str, Participant]) -> Dict[str, str]:
    G = build_graph(participants, True, True)
    return _solve(G, participants)


def solve_ignore_inclusions(participants: Dict[str, Participant]) -> Dict[str, str]:
    G = build_graph(participants, False, True)
    return _solve(G, participants)


def solve_ignore_exclusions(participants: Dict[str, Participant]) -> Dict[str, str]:
    G = build_graph(participants, True, False)
    return _solve(G, participants)


def solve_ignore_all_constraints(
    participants: Dict[str, Participant],
) -> Dict[str, str]:
    G = build_graph(participants, False, False)
    return _solve(G, participants)
