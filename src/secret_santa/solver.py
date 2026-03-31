from typing import Dict

import networkx as nx

from .exceptions import NoValidAssignment
from .graph import build_graph
from .models import Participant


def _solve(G: nx.DiGraph, participants: Dict[str, Participant]) -> Dict[str, str]:
    matching = nx.algorithms.bipartite.maximum_matching(
        G, top_nodes={n for n in G if n.startswith("g:")}
    )

    result = {}
    for g, r in matching.items():
        if g.startswith("g:"):
            result[g[2:]] = r[2:]

    if len(result) != len(participants):
        raise NoValidAssignment(
            "No valid Secret Santa assignment possible with given constraints"
        )

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
