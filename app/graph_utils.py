"""Graph traversal utilities for workflow animation scene generation.

Converts a validated Graph into an ordered list of SceneStep objects that
drive the animation renderer. The traversal is deterministic: decision branches
are always visited yes-first, and both branches converge at the merge node
(the first common reachable node) before the traversal continues.

Assumptions (from Implementation Contracts):
- The graph passed in is already validated; no validation is performed here.
- Merge node = first common reachable node of the two decision branches (BFS).
- Execution order is deterministic (yes before no for decision branches).
"""

from typing import Literal, Optional
from pydantic import BaseModel

from app.models import Graph
from app.validator import build_adjacency, _find_bfs_merge_node


# ---------------------------------------------------------------------------
# SceneStep
# ---------------------------------------------------------------------------

class SceneStep(BaseModel):
    """A single step in the animation sequence."""

    node_id: str
    # Issue 7: strict Literal type instead of loose str
    type: Literal["start", "process", "decision", "end"]
    branch: Optional[Literal["yes", "no"]] = None


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

NodeTypeMap = dict[str, Literal["start", "process", "decision", "end"]]


def _walk(
    node_id: str,
    stop_at: Optional[str],
    adjacency: dict[str, list[tuple[str, Optional[str]]]],
    node_types: NodeTypeMap,
    emitted: set[str],
    branch_label: Optional[str],
) -> list[SceneStep]:
    """Walk the graph from *node_id* up to (but not including) *stop_at*.

    Args:
        node_id:      The current node to process.
        stop_at:      Stop before visiting this node ID (the merge node when
                      walking inside a branch).
        adjacency:    Forward adjacency list.
        node_types:   Mapping of node ID → node type (Issue 2: no global state).
        emitted:      Set of already-emitted node IDs (mutated in place).
        branch_label: "yes" or "no" for the entry node of a branch, else None.

    Returns:
        Ordered list of SceneStep objects for this sub-walk.
    """
    steps: list[SceneStep] = []
    current: Optional[str] = node_id

    while current is not None:
        # Stop before the merge node or any already-emitted node.
        if current == stop_at or current in emitted:
            break

        node_type = node_types[current]

        step = SceneStep(node_id=current, type=node_type, branch=branch_label)
        steps.append(step)
        emitted.add(current)

        # Branch label only annotates the entry node of the branch.
        branch_label = None

        outgoing = adjacency.get(current, [])

        if node_type == "decision":
            # Identify yes/no targets (validated to exist).
            yes_target = next(t for t, lbl in outgoing if lbl == "yes")
            no_target = next(t for t, lbl in outgoing if lbl == "no")

            # Resolve merge node using the same BFS rule as the validator.
            merge_node = _find_bfs_merge_node(yes_target, no_target, adjacency)

            # Guard: should never happen on a validated graph, but protects
            # against any gap between validator rules and traversal assumptions.
            if merge_node is None:
                raise RuntimeError(
                    f"Invalid graph: no merge node found for decision node '{current}'"
                )

            # Walk yes-branch first (determinism guarantee).
            steps.extend(
                _walk(yes_target, merge_node, adjacency, node_types, emitted, "yes")
            )
            # Walk no-branch second.
            steps.extend(
                _walk(no_target, merge_node, adjacency, node_types, emitted, "no")
            )

            # Continue from the merge node.
            current = merge_node

        elif len(outgoing) == 1:
            neighbor, _ = outgoing[0]
            current = neighbor

        else:
            # End node or isolated tail — traversal complete.
            current = None

    return steps


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def transform_graph(graph: Graph) -> list[SceneStep]:
    """Transform a validated Graph into an ordered list of SceneStep objects.

    The list represents the deterministic animation sequence:
    - Nodes are visited in topological / flow order from the start node.
    - At each decision node, the yes-branch is walked first, then the no-branch.
    - Both branches converge at the BFS-merge node before traversal continues.
    - Each SceneStep carries the node ID, its strict type literal, and (for the
      first node of a branch) a branch label of "yes" or "no".

    Args:
        graph: A fully validated Graph instance. Validation must be performed
               by the caller via validator.validate_graph before calling this.

    Returns:
        A list of SceneStep objects in animation order.
    """
    adjacency, _ = build_adjacency(graph)

    # Issue 2: node_types passed explicitly — no global / module-level state.
    node_types: NodeTypeMap = {node.id: node.type for node in graph.nodes}  # type: ignore[misc]

    # Single start node is guaranteed by validation.
    start_node = next(node for node in graph.nodes if node.type == "start")

    emitted: set[str] = set()
    return _walk(start_node.id, None, adjacency, node_types, emitted, None)
