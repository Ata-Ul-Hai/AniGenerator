"""Graph topology validation helpers for workflow animations."""

from collections import deque
from typing import Optional

from app.models import Graph


Adjacency = dict[str, list[tuple[str, Optional[str]]]]


def build_adjacency(graph: Graph) -> tuple[Adjacency, Adjacency]:
	"""Return forward and reverse adjacency lists."""
	adjacency: Adjacency = {node.id: [] for node in graph.nodes}
	reverse_adjacency: Adjacency = {node.id: [] for node in graph.nodes}

	for edge in graph.edges:
		adjacency[edge.from_node].append((edge.to_node, edge.label))
		reverse_adjacency[edge.to_node].append((edge.from_node, edge.label))

	return adjacency, reverse_adjacency


def compute_degrees(graph: Graph) -> tuple[dict[str, int], dict[str, int]]:
	"""Return in-degree and out-degree maps for all nodes."""
	in_degree = {node.id: 0 for node in graph.nodes}
	out_degree = {node.id: 0 for node in graph.nodes}

	for edge in graph.edges:
		out_degree[edge.from_node] += 1
		in_degree[edge.to_node] += 1

	return in_degree, out_degree


def validate_start_end_nodes(graph: Graph) -> list[str]:
	"""Validate exactly one start and exactly one end node.

	Rules enforced:
	- Exactly one start node, with in-degree = 0 and at least one outgoing edge.
	- Exactly one end node, with out-degree = 0.
	"""
	errors: list[str] = []
	in_degree, out_degree = compute_degrees(graph)

	start_nodes = [node for node in graph.nodes if node.type == "start"]
	end_nodes = [node for node in graph.nodes if node.type == "end"]

	if len(start_nodes) != 1:
		errors.append("Graph must contain exactly one start node")
	else:
		start_id = start_nodes[0].id
		# Issue 4: start node must have in-degree = 0 (nothing points to it)
		if in_degree[start_id] != 0:
			errors.append(f"Start node '{start_id}' must have in-degree 0 (no incoming edges)")
		if out_degree[start_id] == 0:
			errors.append(f"Start node '{start_id}' must have at least one outgoing edge")

	if len(end_nodes) != 1:
		errors.append("Graph must contain exactly one end node")
	else:
		end_id = end_nodes[0].id
		# Issue 5: end node must have out-degree = 0 (no edges leave it)
		if out_degree[end_id] != 0:
			errors.append(f"End node '{end_id}' must have out-degree 0 (no outgoing edges)")

	return errors


def _reachable_nodes(source: str, adjacency: Adjacency) -> set[str]:
	"""Return all nodes reachable from source, including source."""
	visited: set[str] = set()
	queue = deque([source])

	while queue:
		current = queue.popleft()
		if current in visited:
			continue
		visited.add(current)

		for neighbor, _ in adjacency.get(current, []):
			if neighbor not in visited:
				queue.append(neighbor)

	return visited


def _find_bfs_merge_node(
	yes_target: str,
	no_target: str,
	adjacency: Adjacency,
) -> Optional[str]:
	"""Return the first common reachable node (merge node) via BFS from yes-branch.

	BFS over the yes-branch in insertion order; the first node that is also
	reachable from the no-branch is returned. This is the single source of truth
	for merge-node resolution used by both the validator and graph_utils.
	"""
	no_reachable = _reachable_nodes(no_target, adjacency)

	visited: set[str] = set()
	queue: deque[str] = deque([yes_target])

	while queue:
		current = queue.popleft()
		if current in visited:
			continue
		visited.add(current)

		if current in no_reachable:
			return current

		for neighbor, _ in adjacency.get(current, []):
			if neighbor not in visited:
				queue.append(neighbor)

	return None


def _nodes_before_merge(
	start: str,
	stop_at: Optional[str],
	adjacency: Adjacency,
) -> set[str]:
	"""Return all node IDs reachable from *start* before reaching *stop_at*.

	Used by the nested-decision check to identify every node that lies inside
	a single branch before the merge point.
	"""
	visited: set[str] = set()
	queue: deque[str] = deque([start])

	while queue:
		current = queue.popleft()
		if current == stop_at or current in visited:
			continue
		visited.add(current)
		for neighbor, _ in adjacency.get(current, []):
			if neighbor not in visited:
				queue.append(neighbor)

	return visited


def validate_decision_nodes(graph: Graph, adjacency: Adjacency) -> list[str]:
	"""Validate decision rules and non-decision outgoing-edge limits.

	Rules enforced:
	- Decision nodes: exactly 2 outgoing edges labeled 'yes' and 'no'.
	- Decision branches must converge to exactly one BFS-merge node.
	- No nested decision nodes within a branch before the merge (Issue 3).
	- Non-decision nodes: at most 1 outgoing edge.
	"""
	errors: list[str] = []
	node_types = {node.id: node.type for node in graph.nodes}

	for node in graph.nodes:
		outgoing = adjacency.get(node.id, [])

		# Decision nodes must branch yes/no with two outgoing edges.
		if node.type == "decision":
			if len(outgoing) != 2:
				errors.append(f"Decision node '{node.id}' must have exactly 2 outgoing edges")
				continue

			labels = {label for _, label in outgoing}
			if labels != {"yes", "no"}:
				errors.append(f"Decision node '{node.id}' must have edges labeled 'yes' and 'no'")
				continue

			yes_targets = [target for target, label in outgoing if label == "yes"]
			no_targets = [target for target, label in outgoing if label == "no"]

			if len(yes_targets) != 1 or len(no_targets) != 1:
				errors.append(f"Decision node '{node.id}' must have one 'yes' edge and one 'no' edge")
				continue

			yes_target = yes_targets[0]
			no_target = no_targets[0]

			# Issue 1: Use BFS-merge algorithm to find the single merge node.
			merge_node = _find_bfs_merge_node(yes_target, no_target, adjacency)
			if merge_node is None:
				errors.append(
					f"Decision branches from node '{node.id}' must converge to a single merge node"
				)
				continue

			# Issue 3: No nested decisions — neither branch may contain another
			# decision node between the branch entry and the merge node.
			yes_branch_nodes = _nodes_before_merge(yes_target, merge_node, adjacency)
			no_branch_nodes = _nodes_before_merge(no_target, merge_node, adjacency)

			for branch_name, branch_nodes in (("yes", yes_branch_nodes), ("no", no_branch_nodes)):
				nested = [
					nid for nid in branch_nodes if node_types.get(nid) == "decision"
				]
				if nested:
					errors.append(
						f"Decision node '{node.id}': {branch_name}-branch contains nested "
						f"decision node(s) {nested} before merge node '{merge_node}'"
					)

		# Non-decision nodes can have at most one outgoing edge.
		else:
			if len(outgoing) > 1:
				errors.append(
					f"Non-decision node '{node.id}' must have at most 1 outgoing edge"
				)

	return errors


def validate_edge_labels(graph: Graph, adjacency: Adjacency) -> list[str]:
	"""Validate that labeled edges (yes/no) only originate from decision nodes.

	Issue 6: A label on an edge from a non-decision node is an illegal graph.
	"""
	errors: list[str] = []
	node_types = {node.id: node.type for node in graph.nodes}

	for edge in graph.edges:
		if edge.label is not None and node_types.get(edge.from_node) != "decision":
			errors.append(
				f"Edge from non-decision node '{edge.from_node}' must not carry a "
				f"label (found label='{edge.label}')"
			)

	return errors


def _canonical_cycle(cycle_nodes: list[str]) -> tuple[str, ...]:
	"""Normalize a cycle path so duplicates from different start points collapse."""
	rotations = [tuple(cycle_nodes[i:] + cycle_nodes[:i]) for i in range(len(cycle_nodes))]
	return min(rotations)


def detect_cycles(graph: Graph) -> list[str]:
	"""Detect directed cycles and return cycle-related errors."""
	adjacency, _ = build_adjacency(graph)
	errors: list[str] = []

	WHITE, GRAY, BLACK = 0, 1, 2
	state = {node.id: WHITE for node in graph.nodes}
	stack: list[str] = []
	index_in_stack: dict[str, int] = {}
	found_cycles: set[tuple[str, ...]] = set()

	def dfs(node_id: str) -> None:
		state[node_id] = GRAY
		index_in_stack[node_id] = len(stack)
		stack.append(node_id)

		for neighbor, _ in adjacency[node_id]:
			if state[neighbor] == WHITE:
				dfs(neighbor)
			elif state[neighbor] == GRAY:
				start_idx = index_in_stack[neighbor]
				cycle_nodes = stack[start_idx:]
				found_cycles.add(_canonical_cycle(cycle_nodes))

		stack.pop()
		index_in_stack.pop(node_id, None)
		state[node_id] = BLACK

	for node in graph.nodes:
		if state[node.id] == WHITE:
			dfs(node.id)

	for cycle in sorted(found_cycles):
		cycle_path = " -> ".join(list(cycle) + [cycle[0]])
		errors.append(f"Cycle detected: {cycle_path}")

	return errors


def check_reachability(graph: Graph) -> list[str]:
	"""Ensure every node is reachable from the start node."""
	errors: list[str] = []
	adjacency, _ = build_adjacency(graph)

	start_nodes = [node for node in graph.nodes if node.type == "start"]
	if len(start_nodes) != 1:
		errors.append("Reachability check skipped: graph must contain exactly one start node")
		return errors

	start_id = start_nodes[0].id
	visited = _reachable_nodes(start_id, adjacency)

	for node in graph.nodes:
		if node.id not in visited:
			errors.append(f"Node '{node.id}' is not reachable from start node '{start_id}'")

	return errors


def validate_graph(graph: Graph) -> list[str]:
	"""Run all graph-structure validations and return every error found.

	Validation order:
	1. Start / end node structural rules (in/out-degree, count)
	2. Decision node rules (branching, merge, no nested decisions)
	3. Edge label rules (labels only on edges from decision nodes)
	4. Cycle detection
	5. Reachability from start
	"""
	errors: list[str] = []
	adjacency, _ = build_adjacency(graph)

	errors.extend(validate_start_end_nodes(graph))
	errors.extend(validate_decision_nodes(graph, adjacency))
	errors.extend(validate_edge_labels(graph, adjacency))
	errors.extend(detect_cycles(graph))
	errors.extend(check_reachability(graph))

	return errors
