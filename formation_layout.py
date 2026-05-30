"""
Formation layout calculation module - decoupled from map view.

Provides spatial layout algorithms for unit formations (road, line) given
parent unit position, children, and parent rotation. Returns world space
coordinates for all units in the formation.
"""

import math
from typing import Dict, List, Tuple, Optional


def calculate_road_formation(
    parent_position: Tuple[float, float],
    parent_rotation: float,
    children_hierarchy_keys: List[Tuple],
    all_units_by_key: Dict[Tuple, Dict],
    spacing: float = 100.0,
) -> Dict[Tuple, Tuple[float, float]]:
    """
    Calculate road formation: units in a line behind parent in DFT order.
    
    Args:
        parent_position: (world_x, world_y) of parent unit
        parent_rotation: Rotation angle in degrees (0 = north/up, 90 = east/right)
        children_hierarchy_keys: List of (level1, level2, level3, level4, level5, level6) tuples
                                for children to arrange
        all_units_by_key: Dict mapping hierarchy keys to unit data dicts
        spacing: Distance in world units between consecutive units (default 100)
    
    Returns:
        Dict mapping hierarchy key -> (world_x, world_y) position for each unit
    """
    positions = {}
    positions[_get_parent_key(children_hierarchy_keys[0])] = parent_position
    
    # Depth-first traversal of unit hierarchy
    dft_order = _depth_first_order(children_hierarchy_keys, all_units_by_key)
    
    # Convert rotation angle to direction vector (in world space)
    # 0 degrees = north (+y), 90 degrees = east (+x)
    angle_rad = math.radians(parent_rotation)
    dx = math.sin(angle_rad)  # East component
    dy = math.cos(angle_rad)  # North component
    
    # Place units behind parent along direction vector
    parent_x, parent_y = parent_position
    for i, unit_key in enumerate(dft_order, start=1):
        distance = i * spacing
        world_x = parent_x + dx * distance
        world_y = parent_y + dy * distance
        positions[unit_key] = (world_x, world_y)
    
    #print(f"Calculated road formation positions: {positions} for parent at {parent_position} facing {parent_rotation}°:")
    return positions


def calculate_line_formation(
    parent_position: Tuple[float, float],
    parent_rotation: float,
    children_hierarchy_keys: List[Tuple],
    all_units_by_key: Dict[Tuple, Dict],
    spacing: float = 100.0,
) -> Dict[Tuple, Tuple[float, float]]:
    """
    Calculate line formation: units spread horizontally with parent at center.
    
    Each child subtree is centered around its commander. Children are placed
    left-to-right based on hierarchy order. Parent sits at center of entire formation.
    
    Args:
        parent_position: (world_x, world_y) of parent unit
        parent_rotation: Rotation angle in degrees
        children_hierarchy_keys: List of hierarchy keys for children
        all_units_by_key: Dict mapping hierarchy keys to unit data
        spacing: Distance in world units (default 100)
    
    Returns:
        Dict mapping hierarchy key -> (world_x, world_y) position
    """
    positions = {}
    parent_key = _get_parent_key(children_hierarchy_keys[0])
    positions[parent_key] = parent_position
    
    # Calculate subtree widths for all units in formation
    subtree_widths = {}
    _calculate_subtree_widths(
        parent_key, children_hierarchy_keys, all_units_by_key, subtree_widths
    )
    
    # Convert rotation to perpendicular direction vector (horizontal spacing)
    # Perpendicular to parent's facing: 90 degrees rotated
    angle_rad = math.radians(parent_rotation)
    perp_dx = math.cos(angle_rad)  # Perpendicular east
    perp_dy = -math.sin(angle_rad)  # Perpendicular south
    
    # Place children horizontally around parent (at center of their subtrees)
    total_width = subtree_widths.get(parent_key, spacing)
    start_offset = -total_width / 2.0
    
    current_offset = start_offset
    for child_key in children_hierarchy_keys:
        if child_key not in subtree_widths:
            continue
        child_width = subtree_widths[child_key]
        child_offset = current_offset + child_width / 2.0
        
        parent_x, parent_y = parent_position
        child_x = parent_x + perp_dx * child_offset
        child_y = parent_y + perp_dy * child_offset
        positions[child_key] = (child_x, child_y)
        
        # Recursively position children of this child
        _place_line_children(
            child_key, (child_x, child_y), parent_rotation,
            all_units_by_key, subtree_widths, spacing, positions
        )
        
        current_offset += child_width
    
    return positions


# ============================================================================
# Private Helper Functions
# ============================================================================

def _get_parent_key(unit_key: Tuple) -> Tuple:
    """Get parent's hierarchy key from a unit's hierarchy key."""
    # Parent key has the last non-zero value set to zero
    key_list = list(unit_key)
    for i in range(len(key_list) - 1, -1, -1):
        if key_list[i] != 0:
            key_list[i] = 0
            break
    return tuple(key_list)


def _get_children(unit_key: Tuple, all_hierarchy_keys: List[Tuple]) -> List[Tuple]:
    """Get direct children of a unit from list of keys."""
    children = []
    for key in all_hierarchy_keys:
        if _get_parent_key(key) == unit_key:
            children.append(key)
    return children


def _depth_first_order(
    unit_keys: List[Tuple],
    all_units_by_key: Dict[Tuple, Dict]
) -> List[Tuple]:
    """
    Return units in depth-first order for road formation.
    
    Classic DFT: visit children of first unit completely before second unit.
    """
    visited = set()
    result = []
    
    for key in unit_keys:
        if key not in visited:
            _dft_visit(key, unit_keys, visited, result)
    
    return result


def _dft_visit(
    unit_key: Tuple,
    all_unit_keys: List[Tuple],
    visited: set,
    result: List[Tuple]
) -> None:
    """Recursive DFT visit helper."""
    if unit_key in visited:
        return
    visited.add(unit_key)
    result.append(unit_key)
    
    # Get direct children of this unit
    children = _get_children(unit_key, all_unit_keys)
    for child in children:
        _dft_visit(child, all_unit_keys, visited, result)


def _calculate_subtree_widths(
    unit_key: Tuple,
    all_unit_keys: List[Tuple],
    all_units_by_key: Dict[Tuple, Dict],
    subtree_widths: Dict[Tuple, float],
    spacing: float = 100.0,
) -> float:
    """
    Recursively calculate total width needed for a unit's entire subtree.
    
    Returns the width in world units.
    """
    children = _get_children(unit_key, all_unit_keys)
    
    if not children:
        # Leaf node: just the unit itself
        width = spacing
    else:
        # Width is sum of children widths
        width = 0.0
        for child in children:
            child_width = _calculate_subtree_widths(
                child, all_unit_keys, all_units_by_key, subtree_widths, spacing
            )
            width += child_width
    
    subtree_widths[unit_key] = width
    return width


def _place_line_children(
    parent_key: Tuple,
    parent_position: Tuple[float, float],
    parent_rotation: float,
    all_units_by_key: Dict[Tuple, Dict],
    subtree_widths: Dict[Tuple, float],
    spacing: float,
    positions: Dict[Tuple, Tuple[float, float]],
) -> None:
    """
    Recursively place children of a unit in line formation around it.
    
    Parent unit is assumed to already be positioned. Its children are placed
    horizontally (perpendicular to parent's facing direction), each centered
    on their subtree.
    """
    # Find children in the all_units_by_key data
    children = []
    for key, unit_data in all_units_by_key.items():
        if _get_parent_key(key) == parent_key:
            children.append(key)
    
    if not children:
        return
    
    # Calculate perpendicular direction
    angle_rad = math.radians(parent_rotation)
    perp_dx = math.cos(angle_rad)
    perp_dy = -math.sin(angle_rad)
    
    # Total width of all children
    total_width = sum(subtree_widths.get(child, spacing) for child in children)
    start_offset = -total_width / 2.0
    
    parent_x, parent_y = parent_position
    current_offset = start_offset
    
    for child_key in children:
        child_width = subtree_widths.get(child_key, spacing)
        child_offset = current_offset + child_width / 2.0
        
        child_x = parent_x + perp_dx * child_offset
        child_y = parent_y + perp_dy * child_offset
        positions[child_key] = (child_x, child_y)
        
        # Recursively place grandchildren
        _place_line_children(
            child_key, (child_x, child_y), parent_rotation,
            all_units_by_key, subtree_widths, spacing, positions
        )
        
        current_offset += child_width
