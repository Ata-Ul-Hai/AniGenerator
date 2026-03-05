"""
Pydantic models for workflow animation system.

This module defines the core data structures for representing a workflow graph
that will be rendered into an animation. It includes validation for node types,
field lengths, and duration constraints.
"""

from typing import Literal, Optional
from pydantic import BaseModel, Field, field_validator, model_validator


# ============================================================================
# Node Model
# ============================================================================

class Node(BaseModel):
    """
    Represents a single node in a workflow graph.
    
    A node is a step or decision point in the workflow that will be animated.
    Each node contains content for both visual display and narration.
    """
    
    id: str = Field(
        ...,
        description="Unique string identifier for the node",
        min_length=1,
        max_length=100
    )
    
    type: Literal["start", "process", "decision", "end"] = Field(
        ...,
        description="Type of node in the workflow diagram"
    )
    
    heading: str = Field(
        ...,
        description="Short title displayed on the node (max 100 characters)",
        max_length=100,
        min_length=1
    )
    
    text: str = Field(
        ...,
        description="Onscreen explanation text visible in animation (max 500 characters)",
        max_length=500,
        min_length=1
    )
    
    narration: str = Field(
        ...,
        description="Voiceover narration text for the node (max 1000 characters)",
        max_length=1000,
        min_length=1
    )
    
    duration: Optional[int] = Field(
        default=None,
        description="Animation duration for this node in seconds (1-15)",
        ge=1,
        le=15
    )
    
    @field_validator("id")
    @classmethod
    def validate_id_format(cls, v: str) -> str:
        """Ensure ID is not empty after stripping whitespace."""
        if not v.strip():
            raise ValueError("ID cannot be empty or whitespace only")
        return v.strip()
    
    @field_validator("heading", "text", "narration")
    @classmethod
    def validate_no_leading_trailing_whitespace(cls, v: str) -> str:
        """Strip leading and trailing whitespace from text fields."""
        return v.strip()


# ============================================================================
# Edge Model
# ============================================================================

class Edge(BaseModel):
    """
    Represents a connection between two nodes in a workflow graph.
    
    An edge defines the flow from one node to another, optionally labeled
    with "yes" or "no" for decision branches.
    """
    
    from_node: str = Field(
        ...,
        description="ID of the source node",
        min_length=1
    )
    
    to_node: str = Field(
        ...,
        description="ID of the destination node",
        min_length=1
    )
    
    label: Optional[Literal["yes", "no"]] = Field(
        default=None,
        description="Optional label for decision branches (yes/no)"
    )
    
    @field_validator("from_node", "to_node")
    @classmethod
    def validate_node_ids(cls, v: str) -> str:
        """Ensure node IDs are not empty after stripping."""
        if not v.strip():
            raise ValueError("Node ID cannot be empty or whitespace only")
        return v.strip()
    
    @model_validator(mode="after")
    def validate_different_nodes(self) -> "Edge":
        """Ensure edge connects different nodes."""
        if self.from_node == self.to_node:
            raise ValueError("An edge cannot connect a node to itself")
        return self


# ============================================================================
# Graph Model
# ============================================================================

class Graph(BaseModel):
    """
    Represents a complete workflow graph.
    
    A workflow graph consists of nodes and edges that together define
    the structure of a business process or workflow to be animated.
    
    Constraints:
    - Minimum 2 nodes required
    - Maximum 15 nodes allowed
    """
    
    nodes: list[Node] = Field(
        ...,
        description="List of nodes in the workflow",
        min_length=2,
        max_length=15
    )
    
    edges: list[Edge] = Field(
        default_factory=list,
        description="List of edges connecting nodes in the workflow"
    )
    
    """Pydantic configuration for Graph model."""
    model_config = {
    "str_strip_whitespace": True
}
    
    @model_validator(mode="after")
    def validate_graph_consistency(self) -> "Graph":
        """
        Validate that the graph structure is internally consistent.
        
        This validator checks:
        - All edges reference valid node IDs
        - No duplicate node IDs exist
        - Total duration does not exceed limit
        - Duplicate edges are not present
        """
        # Collect all valid node IDs
        valid_node_ids = {node.id for node in self.nodes}
        
        # Check for duplicate node IDs
        if len(valid_node_ids) != len(self.nodes):
            raise ValueError("Duplicate node IDs found in graph")

        # Enforce total animation duration limit
        total_duration = sum(node.duration or 0 for node in self.nodes)
        if total_duration > 180:
            raise ValueError("Total animation duration cannot exceed 180 seconds")

        # Prevent duplicate edges based on (from_node, to_node, label)
        edge_signatures = {(edge.from_node, edge.to_node, edge.label) for edge in self.edges}
        if len(edge_signatures) != len(self.edges):
            raise ValueError("Duplicate edges detected in graph")
        
        # Validate edge node references
        for edge in self.edges:
            if edge.from_node not in valid_node_ids:
                raise ValueError(
                    f"Edge references non-existent source node: {edge.from_node}"
                )
            if edge.to_node not in valid_node_ids:
                raise ValueError(
                    f"Edge references non-existent destination node: {edge.to_node}"
                )
        
        return self
