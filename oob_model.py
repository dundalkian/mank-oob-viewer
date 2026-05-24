import pandas as pd
from typing import Tuple, List, Optional, Dict


class OOBData:
    """
    Handles CSV I/O, dataframe management, and hierarchy operations for Order of Battle data.
    """
    
    def __init__(self):
        self.df: Optional[pd.DataFrame] = None
        self.filepath: Optional[str] = None
    
    def load_csv(self, path: str) -> None:
        """
        Load CSV file into dataframe.
        
        Args:
            path: Path to CSV file
            
        Raises:
            ValueError: If file is missing required columns
        """
        # Read CSV as strings, then convert numeric columns specifically to integers
        self.df = pd.read_csv(path, encoding="cp1252", dtype=str).fillna("")
        
        int_columns = [
            "SIDE 1", "ARMY 2", "CORPS 3", "DIV 4", "BGDE 5", "BTN 6",
            "Head Count", "Experience", "Fatigue", "Morale", "Close",
            "Open", "Edged", "Firearm", "Marksmanship", "Horsemanship",
            "Surgeon", "Calisthenics", "Ability", "Command", "Control",
            "Leadership", "Style"
        ]
        
        for col in int_columns:
            if col in self.df.columns:
                self.df[col] = pd.to_numeric(self.df[col], errors="coerce").astype("Int64")
        
        required_columns = ["NAME1", "Head Count", "SIDE 1", "ARMY 2", "CORPS 3", "DIV 4", "BGDE 5", "BTN 6"]
        missing = [c for c in required_columns if c not in self.df.columns]
        
        if missing:
            raise ValueError(f"CSV is missing required columns: {missing}")
        
        self.filepath = path
    
    def save_csv(self, path: str) -> None:
        """
        Save dataframe to CSV file.
        
        Args:
            path: Path to save CSV file to
            
        Raises:
            ValueError: If no dataframe is loaded
        """
        if self.df is None:
            raise ValueError("No data loaded")
        
        self.df.to_csv(path, encoding="cp1252", index=False)
        self.filepath = path
    
    def get_row(self, row_index: int) -> pd.Series:
        """Get a single row by index."""
        if self.df is None:
            raise ValueError("No data loaded")
        return self.df.iloc[row_index]
    
    def set_cell(self, row_index: int, column: str, value) -> None:
        """Update a cell value in the dataframe."""
        if self.df is None:
            raise ValueError("No data loaded")
        self.df.at[row_index, column] = value
    
    def get_level_from_hierarchy(self, row: pd.Series) -> Optional[int]:
        """
        Determine hierarchy level from SIDE, ARMY, CORPS, DIV, BGDE, BTN columns.
        
        Returns the level (1-6) based on the deepest non-zero column:
        - Level 1: SIDE only
        - Level 2: SIDE + ARMY
        - Level 3: SIDE + ARMY + CORPS
        - Level 4: SIDE + ARMY + CORPS + DIV
        - Level 5: SIDE + ARMY + CORPS + DIV + BGDE (with BTN = 0, brigade commander)
        - Level 6: SIDE + ARMY + CORPS + DIV + BGDE + BTN (regiment/battalion)
        """
        hierarchy_cols = ["SIDE 1", "ARMY 2", "CORPS 3", "DIV 4", "BGDE 5", "BTN 6"]
        
        level = 0
        for col in hierarchy_cols:
            val = row.get(col, 0)
            if pd.notna(val) and val != 0:
                level += 1
            elif pd.notna(val) and val == 0:
                break
        
        return level if level > 0 else None
    
    def get_hierarchy_key(self, row: pd.Series, row_index: int) -> Tuple[int, ...]:
        """
        Get a unique hierarchical key for a unit based on SIDE, ARMY, CORPS, DIV, BGDE, BTN.
        
        Returns a tuple like (1, 1, 2, 3, 4, 0) representing the full hierarchical path.
        
        Raises:
            ValueError: If any hierarchy column contains invalid data
        """
        hierarchy_cols = ["SIDE 1", "ARMY 2", "CORPS 3", "DIV 4", "BGDE 5", "BTN 6"]
        key = []
        
        for col in hierarchy_cols:
            val = row.get(col, 0)
            
            # Handle NaN or None
            if pd.isna(val):
                raise ValueError(f"Line {row_index + 2}: Column '{col}' is missing or empty (expected an integer)")
            
            # Try to convert to int
            try:
                int_val = int(val)
                key.append(int_val)
            except (ValueError, TypeError):
                raise ValueError(f"Line {row_index + 2}: Column '{col}' has invalid value '{val}' (expected an integer)")
        
        return tuple(key)
    
    def get_parent_key(self, hierarchy_key: Tuple[int, ...]) -> Tuple[int, ...]:
        """
        Get the parent's hierarchy key by setting the last non-zero value to 0.
        
        For example: (1, 1, 2, 3, 4, 1) -> (1, 1, 2, 3, 4, 0)
                     (1, 1, 2, 3, 4, 0) -> (1, 1, 2, 3, 0, 0)
        """
        key = list(hierarchy_key)
        for i in range(len(key) - 1, -1, -1):
            if key[i] != 0:
                key[i] = 0
                break
        return tuple(key)
    
    def get_hierarchy_level_name_and_index(self, hierarchy_key: Tuple[int, ...]) -> str:
        """
        Get the hierarchy level name and its index.
        
        For example: (1, 1, 2, 3, 4, 0) -> "Brigade (4)"
                     (1, 1, 2, 0, 0, 0) -> "Corps (2)"
        """
        level_names = ["Side", "Army", "Corps", "Division", "Brigade", "Regiment"]
        
        # Find the last non-zero value
        for i in range(len(hierarchy_key) - 1, -1, -1):
            if hierarchy_key[i] != 0:
                index = hierarchy_key[i]
                name = level_names[i]
                return f"{name} ({index})"
        
        return "Unknown"
    
    def delete_unit(self, row_index: int) -> int:
        """
        Delete a unit and all its subordinates from the dataframe.
        
        Args:
            row_index: Index of the unit to delete
            
        Returns:
            Number of units deleted (including subordinates)
            
        Raises:
            ValueError: If row_index is invalid or hierarchy data is corrupted
        """
        if self.df is None:
            raise ValueError("No data loaded")
        
        row = self.df.iloc[row_index]
        hierarchy_key_to_delete = self.get_hierarchy_key(row, row_index)
        level_to_delete = self.get_level_from_hierarchy(row)
        
        if level_to_delete is None:
            raise ValueError(f"Line {row_index + 2}: Cannot determine hierarchy level")
        
        # Find all rows to delete (the unit itself and all its subordinates)
        rows_to_delete = []
        
        for idx, df_row in self.df.iterrows():
            try:
                df_hierarchy_key = self.get_hierarchy_key(df_row, idx)
                
                # Check if this row is a subordinate or the unit itself
                # by comparing the first N positions of the hierarchy key
                is_match = True
                for i in range(level_to_delete):
                    if hierarchy_key_to_delete[i] != df_hierarchy_key[i]:
                        is_match = False
                        break
                
                if is_match:
                    rows_to_delete.append(idx)
            except ValueError:
                # Skip rows with invalid hierarchy data
                pass
        
        # Delete rows from dataframe (in reverse order to maintain indices)
        for idx in sorted(rows_to_delete, reverse=True):
            self.df.drop(idx, inplace=True)
        
        # Reset the dataframe index to be continuous
        self.df.reset_index(drop=True, inplace=True)
        
        return len(rows_to_delete)
    
    def insert_unit_template(self, parent_row_index: int, unit_name: str) -> int:
        """
        Insert a new unit template under the given parent unit.
        
        Args:
            parent_row_index: Index of the parent unit
            unit_name: Name for the new unit
            
        Returns:
            Index of the newly inserted unit
            
        Raises:
            ValueError: If parent_row_index is invalid or hierarchy is at max depth
        """
        # TODO: Implement unit template insertion
        raise NotImplementedError("Unit template insertion not yet implemented")
    
    def copy_unit(self, row_index: int) -> dict:
        """
        Copy a unit's data to an internal clipboard.
        
        Args:
            row_index: Index of the unit to copy
            
        Returns:
            Dictionary containing the copied unit data
        """
        # TODO: Implement unit copying
        raise NotImplementedError("Unit copy not yet implemented")
    
    def paste_unit(self, parent_row_index: int, clipboard_data: dict) -> int:
        """
        Paste a unit from clipboard as a duplicate under the given parent.
        
        Args:
            parent_row_index: Index of the parent unit
            clipboard_data: Data from copy_unit()
            
        Returns:
            Index of the newly pasted unit
        """
        # TODO: Implement unit pasting
        raise NotImplementedError("Unit paste not yet implemented")
