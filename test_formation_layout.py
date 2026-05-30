"""
Test script for formation layout calculations.

Tests road and line formation algorithms with sample hierarchies.
"""

from formation_layout import (
    calculate_road_formation,
    calculate_line_formation,
)


def test_road_formation():
    """Test road formation with a simple hierarchy."""
    print("=" * 60)
    print("TEST: Road Formation")
    print("=" * 60)
    
    # Create a sample hierarchy:
    # Level 3 parent (1,1,2,0,0,0)
    #  └─ Level 4 child 1 (1,1,2,1,0,0)
    #      └─ Level 5 child 1.1 (1,1,2,1,1,0)
    #  └─ Level 4 child 2 (1,1,2,2,0,0)
    #      └─ Level 5 child 2.1 (1,1,2,2,1,0)
    
    parent_pos = (1000.0, 1000.0)
    parent_rotation = 0.0  # Facing north
    
    children_keys = [
        (1, 1, 2, 1, 0, 0),  # L4 child 1
        (1, 1, 2, 1, 1, 0),  # L5 child 1.1
        (1, 1, 2, 2, 0, 0),  # L4 child 2
        (1, 1, 2, 2, 1, 0),  # L5 child 2.1
    ]
    
    all_units_by_key = {key: {"row_index": i} for i, key in enumerate(children_keys)}
    
    positions = calculate_road_formation(
        parent_pos,
        parent_rotation,
        children_keys,
        all_units_by_key,
        spacing=100.0
    )
    
    print(f"Parent: {(1,1,2,0,0,0)} at {parent_pos}")
    print(f"Formation positions (DFT order, 0° = north):")
    
    # Sort by order in children_keys
    sorted_keys = [k for k in children_keys if k in positions] + [k for k in positions if k not in children_keys]
    for i, key in enumerate(sorted_keys):
        print(f"  {i+1}. {key}: {positions[key]}")
    
    # Verify spacing
    pos_list = [positions[k] for k in sorted_keys]
    for i in range(len(pos_list) - 1):
        dist = ((pos_list[i+1][0] - pos_list[i][0])**2 + 
                (pos_list[i+1][1] - pos_list[i][1])**2)**0.5
        print(f"  Distance {i+1}→{i+2}: {dist:.1f}")
    
    print()


def test_road_formation_rotated():
    """Test road formation with rotation."""
    print("=" * 60)
    print("TEST: Road Formation (90° rotation)")
    print("=" * 60)
    
    parent_pos = (1000.0, 1000.0)
    parent_rotation = 90.0  # Facing east
    
    children_keys = [
        (1, 1, 2, 1, 0, 0),
        (1, 1, 2, 2, 0, 0),
    ]
    
    all_units_by_key = {key: {"row_index": i} for i, key in enumerate(children_keys)}
    
    positions = calculate_road_formation(
        parent_pos,
        parent_rotation,
        children_keys,
        all_units_by_key,
        spacing=100.0
    )
    
    print(f"Parent at {parent_pos}, facing 90° (east)")
    for key, pos in positions.items():
        print(f"  {key}: {pos}")
    print()


def test_line_formation():
    """Test line formation with balanced children."""
    print("=" * 60)
    print("TEST: Line Formation (2 children)")
    print("=" * 60)
    
    parent_pos = (1000.0, 1000.0)
    parent_rotation = 0.0  # Facing north
    
    # Parent with 2 children, each with 1 grandchild
    children_keys = [
        (1, 1, 2, 1, 0, 0),  # L4 child 1
        (1, 1, 2, 1, 1, 0),  # L5 child 1.1
        (1, 1, 2, 2, 0, 0),  # L4 child 2
        (1, 1, 2, 2, 1, 0),  # L5 child 2.1
    ]
    
    all_units_by_key = {key: {"row_index": i} for i, key in enumerate(children_keys)}
    
    positions = calculate_line_formation(
        parent_pos,
        parent_rotation,
        children_keys,
        all_units_by_key,
        spacing=100.0
    )
    
    print(f"Parent at {parent_pos}, facing north")
    print("Positions:")
    for key, pos in positions.items():
        offset_x = pos[0] - parent_pos[0]
        offset_y = pos[1] - parent_pos[1]
        print(f"  {key}: {pos} (offset: {offset_x:.1f}, {offset_y:.1f})")
    
    print()


def test_line_formation_unbalanced():
    """Test line formation with unbalanced children."""
    print("=" * 60)
    print("TEST: Line Formation (3 children, unequal subtrees)")
    print("=" * 60)
    
    parent_pos = (1000.0, 1000.0)
    parent_rotation = 0.0
    
    # Parent with 3 children: child1 has 2 grandchildren, child2 has 1, child3 has 0
    children_keys = [
        (1, 1, 2, 1, 0, 0),  # L4 child 1
        (1, 1, 2, 1, 1, 0),  # L5 child 1.1
        (1, 1, 2, 1, 2, 0),  # L5 child 1.2
        (1, 1, 2, 2, 0, 0),  # L4 child 2
        (1, 1, 2, 2, 1, 0),  # L5 child 2.1
        (1, 1, 2, 3, 0, 0),  # L4 child 3 (no children)
    ]
    
    all_units_by_key = {key: {"row_index": i} for i, key in enumerate(children_keys)}
    
    positions = calculate_line_formation(
        parent_pos,
        parent_rotation,
        children_keys,
        all_units_by_key,
        spacing=100.0
    )
    
    print(f"Parent at {parent_pos}")
    print("Hierarchy structure:")
    print("  L4 Child 1: 2 grandchildren")
    print("  L4 Child 2: 1 grandchild")
    print("  L4 Child 3: 0 grandchildren")
    print()
    print("Positions:")
    for key, pos in positions.items():
        offset_x = pos[0] - parent_pos[0]
        offset_y = pos[1] - parent_pos[1]
        print(f"  {key}: offset ({offset_x:.1f}, {offset_y:.1f})")
    
    print()


if __name__ == "__main__":
    test_road_formation()
    test_road_formation_rotated()
    test_line_formation()
    test_line_formation_unbalanced()
    print("=" * 60)
    print("All tests completed!")
    print("=" * 60)
