import pandas as pd
from typing import List
from oob_model import OOBData


class OOBValidator:
    """
    Validates Order of Battle data for consistency and correctness.
    """
    
    def __init__(self, data: OOBData):
        """
        Initialize validator with OOBData instance.
        
        Args:
            data: OOBData instance containing the dataframe to validate
        """
        self.data = data
    
    def check_unit_stats_conflict(self) -> List[str]:
        """
        Check if any unit has both maneuver and command stats.
        
        A unit can have EITHER maneuver stats OR command stats, not both. 
        Experience appears in both, so is not included here.
        - Maneuver stats: Fatigue, Morale, Close, Open, Edged, Firearm, Marksmanship, 
          Horsemanship, Surgeon, Calisthenics
        - Command stats: Ability, Command, Control, Leadership, Style
        
        Returns:
            List of error messages
        """
        if self.data.df is None:
            return []
        
        maneuver_stats = ["Fatigue", "Morale", "Close", "Open", "Edged", "Firearm", 
                         "Marksmanship", "Horsemanship", "Surgeon", "Calisthenics"]
        command_stats = ["Ability", "Command", "Control", "Leadership", "Style"]
        
        # Get columns that exist in the dataframe
        maneuver_cols = [col for col in maneuver_stats if col in self.data.df.columns]
        command_cols = [col for col in command_stats if col in self.data.df.columns]
        
        errors = []
        
        for idx, row in self.data.df.iterrows():
            # Check if row has any maneuver stats (non-NaN values)
            has_some_maneuver = any(pd.notna(row.get(col)) for col in maneuver_cols)
            
            # Check if row has any command stats (non-NaN values)
            has_some_command = any(pd.notna(row.get(col)) for col in command_cols)
            
            # Check if row has all maneuver stats (non-NaN values)
            has_all_maneuver = all(pd.notna(row.get(col)) for col in maneuver_cols)
            
            # Check if row has all command stats (non-NaN values)
            has_all_command = all(pd.notna(row.get(col)) for col in command_cols)
            
            # If row has both types of stats, or no complete set, it's an error. 
            # Unless it's a supply wagon.
            if (has_some_maneuver and has_some_command) or not (has_all_maneuver or has_all_command or 
                                                                  (str(row.get("Formation", "")) == "DRIL_SupplyWagon")):
                unit_name = str(row.get("NAME1", "Unknown"))
                line_num = idx + 2  # +1 for header, +1 for 1-based indexing
                errors.append(
                    f"Line {line_num}: '{unit_name}' has both maneuver and command stats.\n"
                    f"Maneuver stats present: {has_some_maneuver}, Command stats present: {has_some_command}.\n"
                    f"Maneuver stats complete: {has_all_maneuver}, Command stats complete: {has_all_command}.\n"
                    f"Units should have either maneuver stats (Fatigue, Morale, Close, Open, Edged, Firearm, "
                    f"Marksmanship, Horsemanship, Surgeon, Calisthenics) or command stats (Ability, Command, "
                    f"Control, Leadership, Style), but not both."
                )
        
        return errors
    
    def check_hierarchy_conflicts(self) -> List[str]:
        """
        Check for hierarchy conflicts, such as Formation field not matching the derived level.
        
        Formation should contain "lvl#" where # matches the derived hierarchy level.
        Special case: Supply wagons (Formation="DRIL_SupplyWagon") are exceptions 
        and count as level 5.
        
        Returns:
            List of error messages
        """
        if self.data.df is None:
            return []
        
        errors = []
        
        for idx, row in self.data.df.iterrows():
            # Get the derived level from hierarchy columns
            level = self.data.get_level_from_hierarchy(row)
            expected_level = max(3, level) if level else None
            
            # Skip rows with no level
            if level is None:
                continue
            
            formation = str(row.get("Formation", ""))
            unit_name = str(row.get("NAME1", "Unknown"))
            line_num = idx + 2  # +1 for header, +1 for 1-based indexing
            
            # Special case: Supply wagons are valid at level 5 as supply wagons, 
            # or level 3 as couriers. Don't flag in either case.
            if formation == "DRIL_SupplyWagon":
                continue
            
            # Check if formation contains the correct lvl# pattern
            expected_formation_str = f"Lvl{expected_level}"
            if expected_formation_str not in formation:
                errors.append(
                    f"Line {line_num}: '{unit_name}' is level {level} but Formation doesn't contain "
                    f"'{expected_formation_str}'. Formation listed: {formation}"
                )
        
        return errors
    
    def validate_unit_stats(self) -> List[str]:
        """
        Validate that each unit has the correct configuration.
        
        Returns:
            List of all validation warning messages (if any)
        """
        warnings = []
        
        # Check for unit stats conflicts
        warnings.extend(self.check_unit_stats_conflict())
        
        # Check for hierarchy conflicts
        warnings.extend(self.check_hierarchy_conflicts())
        
        return warnings
