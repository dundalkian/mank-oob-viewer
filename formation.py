from typing import List
import traceback

formations = {}

class Formation:
    def __init__(self, drill: List[str]):
        self.definition = drill[0].split(',')
        self.layout = drill[1:]

        self.name = self.definition[0].strip()
        self.drill_id = self.definition[1].strip()
        self.rows = int(self.definition[2])  # number of rows in the formation
        self.columns = int(self.definition[3])  # number of units in each row
        self.row_dist = self.definition[4].strip()  # distance in yards between rows. Can have "+" to indicate dependence on child unit size.
        self.col_dist = self.definition[5].strip()  # distance in yards between units in the same row.  Can have "+" to indicate dependence on child unit size.
        self.sub_form = self.definition[6].strip()
        self.keep_form = self.definition[7].strip()
        self.can_wheel = self.definition[8].strip()
        self.can_fight = self.definition[9].strip()
        self.move_rate_mod = self.definition[10].strip()
        self.about_face = self.definition[11].strip()
        self.arty_form = self.definition[12].strip()
        self.min_enemy = self.definition[13].strip()
        self.fire_mod = self.definition[14].strip()
        self.melee_mod = self.definition[15].strip()
        self.cant_move = self.definition[16].strip()
        self.cant_counter_charge = self.definition[17].strip()
        self.cant_flank = self.definition[18].strip()
        self.cant_take_cover = self.definition[19].strip()
        self.notes = self.definition[20].strip()

    def parse_position_entry(self, entry: str) -> dict:
        """Parses a single position within a layout."""
        entry = entry.strip()
        if not entry:
            return {}

        # 1. Separate the optional parentheses group from the sequence number
        if ')' in entry:
            inner_str, seq_str = entry.rsplit(')', 1)
            seq_str = seq_str.strip()
            # Remove the opening parenthesis if present
            if inner_str.startswith('('):
                inner_str = inner_str[1:]
        else:
            # No parentheses: the entire string is just the sequence number
            inner_str = ""
            seq_str = entry.strip()

        parts = inner_str.split('-') if inner_str else []

        return {
            'row_dist':       parts[0].strip() if len(parts) > 0 else "0", # Place a '+' after row or column distance to have the distance dependent on reg size, the distance that you add will be between reg's
            'col_dist':       parts[1].strip() if len(parts) > 1 else "0", # Place a '+' after row or column distance to have the distance dependent on reg size, the distance that you add will be between reg's
            'sprite':    parts[2].strip() if len(parts) > 2 else None, #  indexes into the unitglobal.csv file as to what specific sprite to use, leave 0 for default, valid values are currently 1-6
            'facing':    parts[3].strip() if len(parts) > 3 else None, # integer specifying the number of degrees that the unit should face off of the flag bearer
            'subformation': parts[4].strip() if len(parts) > 4 else None, # id of the sub formation to use for this slot, if it's not set, it uses the default for the formation
            'subtype': parts[5].strip() if len(parts) > 5 else None, # 1-Inf,2-Cav,3-Art, leave blank or zero for any
            'lock':      parts[6].strip() if len(parts) > 6 else None, # lock the position to be the exact place, they will never trail behind
            'seq':       seq_str # 1 - flagbearer, 2-300 men"
        }

    def dependent_distance(self, dist_str: str, subformation: str) -> float:
        """Calculates the actual distance based on the distance string, which may have a '+' indicating dependence on subformation size."""
        if dist_str.endswith('+'):
            base_dist = float(dist_str[:-1])
            if self.sub_form and self.sub_form in formations:
                sub_formation = formations[self.sub_form]
                return base_dist + max(sub_formation.length_yards, sub_formation.depth_yards)
            else:
                return base_dist
        else:
            return float(dist_str)
    
    def __str__(self):
        return f"Formation: {self.name}, ID: {self.drill_id}"

# class FightingFormation(Formation):
#     """Fighting formations are the lowest echelon formations that directly engage in combat. Lvl6 Units: Regiments, Batteries, and Squadrons are all fighting formations.
#         Relies only on the definition line, the layout is mostly irrelevant as we are not interested in sprite positions, just the bounding box."""
#     def __init__(self, drill):
#         super().__init__(drill)
#         # Minimum of 10 yards to prevent single column formations having zero length.
#         self.length_yards = max(10, self.columns * float(self.col_dist))
#         self.depth_yards = max(10, self.rows * float(self.row_dist))
#         formations[self.drill_id] = self

#     def __str__(self):
#         return (f"Fighting Formation: {self.name}, ID: {self.drill_id}, "
#                 f"Length: {self.length_yards} yards, Depth: {self.depth_yards} yards")

class CommandFormation(Formation):
    """Command formations are higher echelon formations that may command other formations. Lvl5 and above Units: Brigades, Divisions, and Corps are all command formations."""
    def __init__(self, drill):
        super().__init__(drill)
        layout_2d = [x.split(',') for x in self.layout]
        
        # Parse all positions from the layout
        self.all_positions = {}  # All positions defined in the formation
        for x, line in enumerate(layout_2d):
            for y, position in enumerate(line):
                pos_info = self.parse_position_entry(position)
                if pos_info.get("seq"):
                    self.all_positions[pos_info['seq']] = (x, y, pos_info)
        # Calculate positions in yards for all defined positions
        self._calculate_positions_in_yards(layout_2d)
        
        # Add to list of all loaded formations.
        formations[self.drill_id] = self

    def _calculate_positions_in_yards(self, layout_2d):
        """Calculate the x,y positions in yards for each sequence, normalized to seq 1 at (0,0).
        
        Uses a 2D grid approach where columns are aligned across all rows, accounting for empty positions.
        """
        self.positions = {}  # {seq: (x_yards, y_yards)}
        
        # Step 1: Build a position map (row, col) -> seq_info
        position_map = {}  # {(row, col): pos_info}
        max_cols = 0
        for row, line in enumerate(layout_2d):
            max_cols = max(max_cols, len(line))
            for col, position in enumerate(line):
                pos_info = self.parse_position_entry(position)
                if pos_info.get("seq"):
                    position_map[(row, col)] = pos_info
        
        # Step 2: Calculate column widths (based on all entries in each column, not just sequences)
        col_widths = [0.0] * max_cols
        for row, line in enumerate(layout_2d):
            for col, position in enumerate(line):
                pos_info = self.parse_position_entry(position)
                if pos_info.get("seq"):
                    calculated_width = self.dependent_distance(pos_info['col_dist'], pos_info['subformation']) + self.dependent_distance(self.col_dist, self.sub_form)
                    col_widths[col] = max(col_widths[col], calculated_width)
        
        # Step 3: Calculate row heights
        row_heights = [0.0] * len(layout_2d)
        for row, line in enumerate(layout_2d):
            for col, position in enumerate(line):
                pos_info = self.parse_position_entry(position)
                if pos_info.get("seq"):
                    calculated_height = self.dependent_distance(pos_info['row_dist'], pos_info['subformation']) + self.dependent_distance(self.row_dist, self.sub_form)
                    row_heights[row] = max(row_heights[row], calculated_height)
        
        # Step 4: Calculate cumulative x and y for each column and row
        col_cumulative_x = [0.0]
        for width in col_widths:
            col_cumulative_x.append(col_cumulative_x[-1] + width)
        
        row_cumulative_y = [0.0]
        for height in row_heights:
            row_cumulative_y.append(row_cumulative_y[-1] + height)
        
        # Step 5: Assign positions based on 2D grid
        for (row, col), pos_info in position_map.items():
            seq = pos_info['seq']
            x = col_cumulative_x[col]
            y = row_cumulative_y[row]
            self.positions[seq] = (x, y)
        
        # Normalize all positions relative to seq 1 at (0, 0)
        if '1' in self.positions:
            ref_x, ref_y = self.positions['1']
            self.positions = {seq: (x - ref_x, y - ref_y) for seq, (x, y) in self.positions.items()}
        
        # Calculate overall formation dimensions
        if self.positions:
            all_x = [pos[0] for pos in self.positions.values()]
            all_y = [pos[1] for pos in self.positions.values()]
            self.length_yards = max(all_x) - min(all_x) if all_x else 10
            self.depth_yards = max(all_y) - min(all_y) if all_y else 10
            self.length_yards = max(10, self.length_yards)
            self.depth_yards = max(10, self.depth_yards)
        else:
            self.length_yards = 10
            self.depth_yards = 10

    def get_positions_for_strength(self, strength) -> dict:
        """
        Get the positions for a given strength (number of sub-units).
        Returns only the positions for seq 1 through strength.
        
        Args:
            strength (int): Number of sub-units to include (1-indexed)
            
        Returns:
            dict: {seq: (x_yards, y_yards)} for seq 1 through strength
        """
        layout = {}
        for seq, pos in self.positions.items():
            try:
                if int(seq) <= strength:
                    layout[seq] = pos
            except ValueError:
                # Non-numeric sequence, skip
                pass
        return layout

    def get_dimensions_at_strength(self, strength) -> tuple:
        """
        Get the actual dimensions (length, depth) of this formation at a given strength.
        
        For fighting formations: strength is an integer, returns bounding box of first N positions.
        For command formations: strength is an integer (number of sub-units), returns bounding box accordingly.
        
        Args:
            strength (int): The strength/number of positions to include
            
        Returns:
            tuple: (length_yards, depth_yards) - the actual dimensions at this strength
        """
        layout = self.get_positions_for_strength(strength)
        
        if not layout:
            return (10, 10)
        
        all_x = [pos[0] for pos in layout.values()]
        all_y = [pos[1] for pos in layout.values()]
        
        length = max(all_x) - min(all_x) if all_x else 10
        depth = max(all_y) - min(all_y) if all_y else 10
        
        return (max(10, length), max(10, depth))

    def __str__(self):
        return (f"Command Formation: {self.name}, ID: {self.drill_id}")

def get_layout(unit: dict) -> dict:
    """
    Given a unit (regiment, brigade, division, etc.) with a formation and strength, 
    return the layout of positions with their coordinates in yards relative to seq 1 (flag bearer).
    
    For fighting formations (Lvl6): strength is an integer (number of units)
    For command formations (Lvl5-2): strength is a list of sub-unit strengths OR list of sub-units dicts
    
    Args:
        unit (dict): {'formation': formation_id, 'strength': strength_value}
        
    Returns:
        dict: Positioned units with their coordinates in yards
        - For Lvl6: {seq: (x_yards, y_yards)} 
        - For Lvl5+: {seq: {'position': (x, y), 'unit': sub_unit_dict}} or similar structure
    """
    formation_id = unit['formation']
    strength = unit['strength']
    
    if formation_id not in formations:
        raise ValueError(f"Formation ID {formation_id} not found.")
    
    formation = formations[formation_id]
    print(formation)
    
    # Handle integer strength (fighting formation or simplified layout)
    if isinstance(strength, int):
        layout = {}
        for seq, pos in formation.positions.items():
            try:
                if int(seq) <= strength:
                    layout[seq] = pos
            except ValueError:
                # Non-numeric sequence, skip
                pass
        return layout
    
    # Handle list strength (command formation with multiple sub-units)
    elif isinstance(strength, list):
        layout = {}
        
        # Check if items are dicts (nested units) or ints (strengths)
        sub_unit_dicts = []
        for idx, item in enumerate(strength):
            seq = str(idx + 1)
            
            if isinstance(item, dict):
                # It's a sub-unit dict like {'formation': 'DRIL_Lvl5_...', 'strength': [...]}
                sub_unit_dicts.append((seq, item))
            else:
                # TODO: remove this case, this should not be used, pass in sub unit dicts for all command formations.
                print("SHOULD NOT BE USING INTEGER STRENGTHS IN A LIST.")
                # It's a strength value (int), create a basic sub-unit dict
                if seq in formation.positions:
                    sub_unit_dicts.append((seq, {'strength': item}))
        print(sub_unit_dicts)
        # Calculate positions with actual sub-unit dimensions
        layout = _calculate_positioned_subunits(formation, sub_unit_dicts)
        return layout
    
    else:
        raise ValueError(f"Strength must be int or list, got {type(strength)}")

def _calculate_positioned_subunits(formation: 'CommandFormation', sub_unit_dicts: list) -> dict:
    """
    Calculate positions for sub-units accounting for their actual dimensions at their given strengths.
    
    Args:
        formation: The parent formation (Lvl5, Lvl4, etc.)
        sub_unit_dicts: List of (seq, sub_unit_dict) tuples
        
    Returns:
        dict: {seq: positioned_info} with actual positions based on sub-unit sizes
    """
    layout = {}
    
    # Get sub-formation for size calculations
    sub_form_id = formation.sub_form
    if not sub_form_id or sub_form_id not in formations:
        # Fallback: use standard positions if no sub-formation defined
        for seq, sub_unit_dict in sub_unit_dicts:
            if seq in formation.positions:
                layout[seq] = formation.positions[seq]
        return layout
    
    sub_formation = formations[sub_form_id]
    
    # Calculate actual dimensions for each sub-unit at its strength
    sub_unit_sizes = {}  # {seq: (length, depth)}
    for seq, sub_unit_dict in sub_unit_dicts:
        strength = sub_unit_dict.get('strength', 100)
        if isinstance(strength, int):
            # Get actual size of sub-formation at this strength
            actual_dims = sub_formation.get_dimensions_at_strength(strength)
            sub_unit_sizes[seq] = actual_dims
        else:
            # Complex nested strength, use default sub-formation size
            sub_unit_sizes[seq] = (sub_formation.length_yards, sub_formation.depth_yards)
    
    # Re-calculate positions using actual sub-unit sizes
    # Build a position map like before
    position_map = {}
    max_cols = 0
    for row, line in enumerate(formation.layout):
        parts = line.split(',')
        max_cols = max(max_cols, len(parts))
        for col, position in enumerate(parts):
            pos_info = formation.parse_position_entry(position)
            if pos_info.get("seq"):
                position_map[(row, col)] = pos_info
    
    # Calculate column widths using actual sub-unit sizes + spacing
    col_widths = [0.0] * max_cols
    for (row, col), pos_info in position_map.items():
        seq = pos_info['seq']
        
        # Get the base col_dist for this position
        col_dist_str = pos_info['col_dist'] if pos_info['col_dist'] != "0" else formation.col_dist
        
        # Calculate actual width: if col_dist has '+', add actual sub-unit size
        if col_dist_str.endswith('+'):
            base_dist = float(col_dist_str[:-1])
            if seq in sub_unit_sizes:
                actual_width = base_dist + sub_unit_sizes[seq][0]  # length of sub-unit
            else:
                actual_width = base_dist
        else:
            actual_width = float(col_dist_str)
        
        col_widths[col] = max(col_widths[col], actual_width)
    
    # Calculate row heights using actual sub-unit sizes + spacing
    row_heights = [0.0] * len(formation.layout)
    for (row, col), pos_info in position_map.items():
        seq = pos_info['seq']
        
        # Get the base row_dist for this position
        row_dist_str = pos_info['row_dist'] if pos_info['row_dist'] != "0" else formation.row_dist
        
        # Calculate actual height: if row_dist has '+', add actual sub-unit size
        if row_dist_str.endswith('+'):
            base_dist = float(row_dist_str[:-1])
            if seq in sub_unit_sizes:
                actual_height = base_dist + sub_unit_sizes[seq][1]  # depth of sub-unit
            else:
                actual_height = base_dist
        else:
            actual_height = float(row_dist_str)
        
        row_heights[row] = max(row_heights[row], actual_height)
    
    # Calculate cumulative positions
    col_cumulative_x = [0.0]
    for width in col_widths:
        col_cumulative_x.append(col_cumulative_x[-1] + width)
    
    row_cumulative_y = [0.0]
    for height in row_heights:
        row_cumulative_y.append(row_cumulative_y[-1] + height)
    
    # Assign positions
    for (row, col), pos_info in position_map.items():
        seq = pos_info['seq']
        x = col_cumulative_x[col]
        y = row_cumulative_y[row]
        layout[seq] = (x, y)
    
    # Normalize relative to seq 1
    if '1' in layout:
        ref_x, ref_y = layout['1']
        layout = {seq: (x - ref_x, y - ref_y) for seq, (x, y) in layout.items()}
    
    return layout

def populate_formations_from_csv(file_path):
    """Parse formation definitions from a CSV file, reading blocks of lines.

    A block starts when column 2 (spec) starts with 'DRIL_'.
    A block ends when a line has 'x' in column 1 or 2, or has no data in any column.
    Each block is passed to FightingFormation to create a formation.
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # Skip the CSV header row
    data_lines = lines[1:]

    lvl6_blocks = []
    lvl5_blocks = []
    lvl4_blocks = []
    lvl3_blocks = []
    lvl2_blocks = []
    misc_blocks = []  # Likely supply wagons, or anything else not in an echelon.

    i = 0
    while i < len(data_lines):
        line = data_lines[i].strip()

        # Skip blank lines
        if not line:
            i += 1
            continue

        parts = line.split(',')

        # Check if this line starts a new formation block:
        # column 2 (index 1) starts with "DRIL_"
        drill_id = parts[1].strip() if len(parts) > 1 else ""
        if not drill_id.startswith("DRIL_"):
            i += 1
            continue

        # Found start of a block — collect lines until termination condition
        block_lines = []
        while i < len(data_lines):
            block_line = data_lines[i].strip()

            # End of block: no data in any column
            if not block_line:
                break

            block_parts = block_line.split(',')
            col1 = block_parts[0].strip() if block_parts else ""
            col2 = block_parts[1].strip() if len(block_parts) > 1 else ""

            # End of block: 'x' in column 1 or 2
            if col1.lower() == 'x' or col2.lower() == 'x' or not any(block_parts):
                break

            block_lines.append(block_line)
            i += 1

        if "DRIL_Lvl6" in block_lines[0].split(',')[1]:
            lvl6_blocks.append(block_lines)
        elif "DRIL_Lvl5" in block_lines[0].split(',')[1]:
            lvl5_blocks.append(block_lines)
        elif "DRIL_Lvl4" in block_lines[0].split(',')[1]:
            lvl4_blocks.append(block_lines)
        elif "DRIL_Lvl3" in block_lines[0].split(',')[1]:
            lvl3_blocks.append(block_lines)
        elif "DRIL_Lvl2" in block_lines[0].split(',')[1]:
            lvl2_blocks.append(block_lines)
        elif "DRIL_" in block_lines[0].split(',')[1]:
            misc_blocks.append(block_lines)
        else:
            print(f"Unrecognized formation type in block starting with: {block_lines[0]}")
    
    # makes sure all lower level formations are parsed before higher level ones that may depend on them.
    for block in lvl6_blocks:
        try:
            #formation = CommandFormation(block)
            formation = CommandFormation(block)
        except Exception as e:
            print(f"Skipping block due to parsing error: {e}")
            print(f"Block lines: {block}")
    for block in lvl5_blocks:
        try:
            formation = CommandFormation(block)
        except Exception as e:
            print(f"Skipping block due to parsing error: {e}")
            print(f"Block lines: {block}")
    for block in lvl4_blocks:
        try:
            formation = CommandFormation(block)
        except Exception as e:
            traceback.print_exc()
            print(f"Skipping block due to parsing error: {e}")
            print(f"Block lines: {block}")
    # for block in lvl3_blocks:
    #     try:
    #         formation = CommandFormation(block)
    #     except Exception as e:
    #         print(f"Skipping block due to parsing error: {e}")
    #         print(f"Block lines: {block}")
    # for block in lvl2_blocks:
    #     try:
    #         formation = CommandFormation(block)
    #     except Exception as e:
    #         print(f"Skipping block due to parsing error: {e}")
    #         print(f"Block lines: {block}")
    #print(formations)