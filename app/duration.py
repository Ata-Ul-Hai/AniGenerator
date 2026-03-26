"""
Duration resolution for workflow animation nodes.

Pure function — no I/O, no rendering logic, no external dependencies.

Each node's animation duration is resolved in priority order:
1. Node's declared `duration` field (if explicitly set by the LLM).
2. Type-based default (fallback when duration is None).

Default durations by node type:
    start    → 3 seconds
    process  → 5 seconds
    decision → 4 seconds
    end      → 3 seconds
"""

from app.graph_utils import SceneStep
from app.models import Graph
from app.schemas import NodeDuration


# Type-based defaults

_DEFAULT_DURATION: dict[str, int] = {
    "start":    3,
    "process":  5,
    "decision": 4,
    "end":      3,
}


# Public API

def resolve_durations(steps: list[SceneStep], graph: Graph) -> list[NodeDuration]:
    """Resolve animation duration for each step in the sequence.

    Args:
        steps: Ordered list of SceneStep objects from transform_graph().
        graph: The validated Graph instance (used to look up declared durations).

    Returns:
        A list of NodeDuration objects, one per step, in the same order as *steps*.
    """
    # Build a fast lookup: node_id → declared duration (may be None)
    declared: dict[str, int | None] = {node.id: node.duration for node in graph.nodes}

    result: list[NodeDuration] = []
    for step in steps:
        node_duration = declared.get(step.node_id)
        if node_duration is not None:
            duration = node_duration
        else:
            duration = _DEFAULT_DURATION[step.type]

        result.append(NodeDuration(node_id=step.node_id, duration=duration))

    return result
