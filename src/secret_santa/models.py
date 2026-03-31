from dataclasses import dataclass, field
from typing import Set


@dataclass
class Participant:
    name: str
    include: Set[str] = field(default_factory=set)
    exclude: Set[str] = field(default_factory=set)
