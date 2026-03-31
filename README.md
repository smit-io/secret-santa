# Secret Santa Graph

Constraint-based Secret Santa solver using bipartite graph matching.

## Install

pip install -e .

## Usage

from secret_santa import Participant, solve

participants = {
    "Alice": Participant("Alice", exclude={"Bob"}),
    "Bob": Participant("Bob"),
    "Charlie": Participant("Charlie", include={"Alice", "Bob"}),
}

print(solve(participants))