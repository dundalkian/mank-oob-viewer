import sys
import pandas as pd

from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTreeWidget,
    QTreeWidgetItem,
    QTableWidget,
    QTableWidgetItem,
    QFileDialog,
    QLabel,
    QPushButton,
    QSplitter,
    QMessageBox,
    QHeaderView,
    QMenu,
    QInputDialog,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QClipboard


class OOBViewer(QMainWindow):
    def __init__(self, csv_path=None):
        super().__init__()

        self.setWindowTitle("Order of Battle Viewer")
        self.resize(1400, 900)

        self.df = None
        self.current_row_index = None
        self.clipboard_unit = None  # Internal clipboard for cut/copy/paste operations

        self.central = QWidget()
        self.setCentralWidget(self.central)

        self.layout = QVBoxLayout(self.central)

        # Top controls
        controls_layout = QHBoxLayout()

        self.load_button = QPushButton("Load CSV")
        self.load_button.clicked.connect(self.load_csv_dialog)
        controls_layout.addWidget(self.load_button)

        self.save_button = QPushButton("Save CSV")
        self.save_button.clicked.connect(self.save_csv_dialog)
        self.save_button.setEnabled(False)
        controls_layout.addWidget(self.save_button)

        self.status_label = QLabel("No file loaded")
        controls_layout.addWidget(self.status_label)

        controls_layout.addStretch()

        self.layout.addLayout(controls_layout)

        # Splitter
        self.splitter = QSplitter(Qt.Vertical)

        # Tree view
        self.tree = QTreeWidget()
        self.tree.setColumnCount(4)
        self.tree.setHeaderLabels(["Unit", "Level", "Strength", "Line"])
        self.tree.itemSelectionChanged.connect(self.on_selection_changed)
        self.tree.setStyleSheet("""QTreeView::item {
            border: 0;
            }
            QTreeView::item:hover {
            border: 0;
            }
            QTreeView::item:selected {
            background: #42A5F5;
            color: #000000;
            }
            QTreeView::item:!selected {
            background: #FFFFFF;
            color: #000000;
            }
            QTreeView::branch:selected {
            background: #42A5F5;
            }
            QTreeView::branch:!selected {
            background: #FFFFFF;
            }
            QTreeView::branch:has-siblings:!adjoins-item {
                border-image: url(icons/vline.png) 0;
            }

            QTreeView::branch:has-siblings:adjoins-item {
                border-image: url(icons/branch-more.png) 0;
            }

            QTreeView::branch:!has-children:!has-siblings:adjoins-item {
                border-image: url(icons/branch-end.png) 0;
            }

            QTreeView::branch:has-children:!has-siblings:closed,
            QTreeView::branch:closed:has-children:has-siblings {
                    border-image: none;
                    image: url(icons/branch-closed.png);
            }

            QTreeView::branch:open:has-children:!has-siblings,
            QTreeView::branch:open:has-children:has-siblings  {
                    border-image: none;
                    image: url(icons/branch-open.png);
            }""")
        # Expand first column to fit content
        self.tree.header().setSectionResizeMode(0, QHeaderView.Stretch)

        # Enable context menu
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.show_tree_context_menu)

        # Details split view (horizontal)
        self.details_splitter = QSplitter(Qt.Horizontal)
        
        # Left detail view (before Head Count)
        self.details_left = QTableWidget()
        self.details_left.setColumnCount(2)
        self.details_left.setHorizontalHeaderLabels(["Field", "Value"])
        self.details_left.horizontalHeader().setStretchLastSection(True)
        self.details_left.horizontalHeader().setDefaultSectionSize(100)
        self.details_left.verticalHeader().setVisible(False)
        self.details_left.verticalHeader().setDefaultSectionSize(16)
        self.details_left.setShowGrid(False)
        self.details_left.itemChanged.connect(self.on_detail_cell_changed)
        
        # Right detail view (Head Count and after)
        self.details_right = QTableWidget()
        self.details_right.setColumnCount(2)
        self.details_right.setHorizontalHeaderLabels(["Field", "Value"])
        self.details_right.horizontalHeader().setStretchLastSection(True)
        self.details_right.horizontalHeader().setDefaultSectionSize(100)
        self.details_right.verticalHeader().setVisible(False)
        self.details_right.verticalHeader().setDefaultSectionSize(16)
        self.details_right.setShowGrid(False)
        self.details_right.itemChanged.connect(self.on_detail_cell_changed)
        
        self.details_splitter.addWidget(self.details_left)
        self.details_splitter.addWidget(self.details_right)
        self.details_splitter.setStretchFactor(0, 1)
        self.details_splitter.setStretchFactor(1, 1)

        self.splitter.addWidget(self.tree)
        self.splitter.addWidget(self.details_splitter)

        self.splitter.setStretchFactor(0, 3)
        self.splitter.setStretchFactor(1, 2)

        self.layout.addWidget(self.splitter)

        if csv_path:
            self.load_csv(csv_path)

    def load_csv_dialog(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open OOB CSV",
            "",
            "CSV Files (*.csv)"
        )

        if path:
            self.load_csv(path)

    def save_csv_dialog(self):
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save OOB CSV",
            "",
            "CSV Files (*.csv)"
        )

        if path:
            self.save_csv(path)

    def load_csv(self, path):
        try:
            # Read CSV as strings, then convert numeric columns specifically to integers, making sure to avoid automatic float conversion.
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

            # Fill NA values introduced by numeric conversion
            #self.df = self.df.fillna("")

            required_columns = ["NAME1", "Head Count", "SIDE 1", "ARMY 2", "CORPS 3", "DIV 4", "BGDE 5", "BTN 6"]

            missing = [c for c in required_columns if c not in self.df.columns]

            if missing:
                QMessageBox.critical(
                    self,
                    "Missing Columns",
                    f"CSV is missing required columns:\n{missing}"
                )
                return

            # Validate unit stats and print warnings to console
            warnings = self.validate_unit_stats(self.df)
            if warnings:
                print("OOB Validation Warnings:")
                for warning in warnings:
                    print(f"  {warning}\n")

            self.populate_tree()

            self.status_label.setText(path)
            self.save_button.setEnabled(True)

        except Exception as e:
            QMessageBox.critical(
                self,
                "Load Error",
                str(e)
            )

    def check_unit_stats_conflict(self, df):
        """
        Helper function to check if any unit has both maneuver and command stats.
        
        A unit can have EITHER maneuver stats OR command stats, not both. Experience appears in both, so is not included here.
        - Maneuver stats: Fatigue, Morale, Close, Open, Edged, Firearm, Marksmanship, Horsemanship, Surgeon, Calisthenics
        - Command stats: Ability, Command, Control, Leadership, Style
        
        Returns list of error messages.
        """
        maneuver_stats = ["Fatigue", "Morale", "Close", "Open", "Edged", "Firearm", "Marksmanship", "Horsemanship", "Surgeon", "Calisthenics"]
        command_stats = ["Ability", "Command", "Control", "Leadership", "Style"]
        
        # Get columns that exist in the dataframe
        maneuver_cols = [col for col in maneuver_stats if col in df.columns]
        command_cols = [col for col in command_stats if col in df.columns]
        
        errors = []
        
        for idx, row in df.iterrows():
            # Check if row has any maneuver stats (non-NaN values)
            has_some_maneuver = any(pd.notna(row.get(col)) for col in maneuver_cols)
            
            # Check if row has any command stats (non-NaN values)
            has_some_command = any(pd.notna(row.get(col)) for col in command_cols)

            # Check if row has all maneuver stats (non-NaN values)
            has_all_maneuver = all(pd.notna(row.get(col)) for col in maneuver_cols)
            
            # Check if row has all command stats (non-NaN values)
            has_all_command = all(pd.notna(row.get(col)) for col in command_cols)

            # If row has both types of stats, or no complete set, it's an error. Unless it's a supply wagon.
            if (has_some_maneuver and has_some_command) or not (has_all_maneuver or has_all_command or (str(row.get("Formation", "")) == "DRIL_SupplyWagon")):
                unit_name = str(row.get("NAME1", "Unknown"))
                line_num = idx + 2  # +1 for header, +1 for 1-based indexing
                errors.append(
                    f"Line {line_num}: '{unit_name}' has both maneuver and command stats.\n"
                    f"Maneuver stats present: {has_some_maneuver}, Command stats present: {has_some_command}.\n"
                    f"Maneuver stats complete: {has_all_maneuver}, Command stats complete: {has_all_command}.\n"
                    f"Units should have either maneuver stats (Fatigue, Morale, Close, Open, Edged, Firearm, Marksmanship, Horsemanship, Surgeon, Calisthenics) "
                    f"or command stats (Ability, Command, Control, Leadership, Style), but not both."
                )
        
        return errors
    
    # def check_missing_stats(self, df):
    #     """
    #     Helper function to check if any unit has missing stats.
        
    #     A unit should have 
        
    #     Returns list of error messages.
    #     """

    #     return errors

    def check_hierarchy_conflicts(self, df):
        """
        Helper function to check for hierarchy conflicts, such as Formation field not matching the derived level.
        
        Formation should contain "lvl#" where # matches the derived hierarchy level.
        Special case: Supply wagons (Formation="DRIL_SupplyWagon") are exceptions and count as level 5.
        
        Returns list of error messages.
        """
        errors = []
        
        for idx, row in df.iterrows():
            # Get the derived level from hierarchy columns, treat anything higher than 3 as level 3. Army and Side commanders seem to use corps formations in practice.
            level = self.get_level_from_hierarchy(row)
            expected_level = max(3, self.get_level_from_hierarchy(row))
            
            # Skip rows with no level
            if level is None:
                continue
            
            formation = str(row.get("Formation", ""))
            unit_name = str(row.get("NAME1", "Unknown"))
            line_num = idx + 2  # +1 for header, +1 for 1-based indexing
            
            # Special case: Supply wagons are valid at level 5 as supply wagons, or level 3 as couriers. Don't flag in either case.
            if formation == "DRIL_SupplyWagon":
                continue
            
            # Check if formation contains the correct lvl# pattern
            expected_formation_str = f"Lvl{expected_level}"
            if expected_formation_str not in formation:
                errors.append(
                    f"Line {line_num}: '{unit_name}' is level {level} but Formation doesn't contain '{expected_formation_str}'. "
                    f"Formation listed: {formation}"
                )
        
        return errors

    def validate_unit_stats(self, df):
        """
        Validate that each unit has the correct configuration.
        
        Returns list of all validation warning messages (if any).
        """
        warnings = []
        
        # Check for unit stats conflicts
        warnings.extend(self.check_unit_stats_conflict(df))
        
        # Check for hierarchy conflicts
        warnings.extend(self.check_hierarchy_conflicts(df))
        
        return warnings

    def get_level_from_hierarchy(self, row):
        """
        Determine hierarchy level from SIDE, ARMY, CORPS, DIV, BGDE, BTN columns.
        
        Returns the level (1-6) based on the deepest non-zero column:
        - Level 1: SIDE only
        - Level 2: SIDE + ARMY
        - Level 3: SIDE + ARMY + CORPS
        - Level 4: SIDE + ARMY + CORPS + DIV
        - Level 5: SIDE + ARMY + CORPS + DIV + BGDE (with BTN = 0, this is brigade commander)
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

    def get_hierarchy_key(self, row, row_index=None):
        """
        Get a unique hierarchical key for a unit based on SIDE, ARMY, CORPS, DIV, BGDE, BTN.
        
        Returns a tuple like (1, 1, 2, 3, 4, 0) representing the full hierarchical path.
        Raises ValueError if any hierarchy column contains invalid data.
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

    def get_parent_key(self, hierarchy_key):
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

    def get_hierarchy_level_name_and_index(self, hierarchy_key):
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


    def populate_tree(self):
        self.tree.clear()

        # Map hierarchy keys to tree items
        items_by_key = {}
        
        # First pass: collect all items with their hierarchy data
        items_data = []
        for idx, row in self.df.iterrows():
            try:
                level = self.get_level_from_hierarchy(row)

                if level is None:
                    continue

                hierarchy_key = self.get_hierarchy_key(row, idx)
                name = str(row.get("NAME1", "Unknown"))
                strength = row.get("Head Count", "")
                level_info = self.get_hierarchy_level_name_and_index(hierarchy_key)
                line_num = idx + 2  # +1 for header, +1 for 1-based indexing
                
                items_data.append({
                    'idx': idx,
                    'level': level,
                    'hierarchy_key': hierarchy_key,
                    'name': name,
                    'strength': strength,
                    'level_info': level_info,
                    'line_num': line_num
                })
                
            except ValueError as e:
                QMessageBox.critical(
                    self,
                    "CSV Format Error",
                    f"Invalid data in CSV: {str(e)}"
                )
                return
        
        # Second pass: sort by hierarchy level and add to tree
        items_data.sort(key=lambda x: x['level'])
        
        for data in items_data:
            item = QTreeWidgetItem([
                data['name'],
                data['level_info'],
                str(data['strength']),
                str(data['line_num'])
            ])
            
            item.setData(0, Qt.UserRole, data['idx'])
            
            # Get parent hierarchy key
            parent_key = self.get_parent_key(data['hierarchy_key'])
            
            # Find or add to parent
            if parent_key in items_by_key:
                items_by_key[parent_key].addChild(item)
            else:
                # Top-level item (no parent exists)
                self.tree.addTopLevelItem(item)
            
            # Store this item for future children
            items_by_key[data['hierarchy_key']] = item

        # Calculate total strengths for each unit including subordinates
        for i in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(i)
            self.calculate_total_strength(item)

        self.tree.expandToDepth(2)

    def calculate_total_strength(self, item):
        """
        Recursively calculate total strength of a unit and all its subordinates.
        Updates the item's strength display.
        """
        row_index = item.data(0, Qt.UserRole)
        if row_index is None:
            total = 0
        else:
            row = self.df.iloc[row_index]
            try:
                total = float(row.get("Head Count", 0) or 0)
            except (ValueError, TypeError):
                total = 0
        
        # Add strengths from all children
        for i in range(item.childCount()):
            child_item = item.child(i)
            child_total = self.calculate_total_strength(child_item)
            total += child_total
        
        # Update the item's strength display
        display_val = str(int(total)) if total == int(total) else str(total)
        item.setText(2, display_val)
        
        return total

    def on_selection_changed(self):
        items = self.tree.selectedItems()

        if not items:
            return

        item = items[0]

        row_index = item.data(0, Qt.UserRole)

        if row_index is None:
            return

        row = self.df.iloc[row_index]

        self.populate_details(row)

    def populate_details(self, row):
        # Store current row index for later editing
        self.current_row_index = row.name
        
        # Find the index of "Head Count" column
        head_count_idx = None
        for i, col in enumerate(row.index):
            if col == "Head Count":
                head_count_idx = i
                break
        
        if head_count_idx is None:
            head_count_idx = len(row.index)
        
        # Split columns
        left_cols = row.index[:head_count_idx]
        right_cols = row.index[head_count_idx:]
        
        # Populate left table (before Head Count)
        self.details_left.clearContents()
        self.details_left.setRowCount(len(left_cols))
        
        for i, column in enumerate(left_cols):
            field_item = QTableWidgetItem(str(column))
            value_item = QTableWidgetItem(str(row[column]))
            
            field_item.setFlags(field_item.flags() & ~Qt.ItemIsEditable)
            # Make value item editable
            
            self.details_left.setItem(i, 0, field_item)
            self.details_left.setItem(i, 1, value_item)
        
        self.details_left.resizeColumnsToContents()
        self.details_left.resizeRowsToContents()
        
        # Populate right table (Head Count onwards)
        self.details_right.clearContents()
        self.details_right.setRowCount(len(right_cols))
        
        for i, column in enumerate(right_cols):
            field_item = QTableWidgetItem(str(column))
            value_item = QTableWidgetItem(str(row[column]))
            
            field_item.setFlags(field_item.flags() & ~Qt.ItemIsEditable)
            # Make value item editable
            
            self.details_right.setItem(i, 0, field_item)
            self.details_right.setItem(i, 1, value_item)
        
        self.details_right.resizeColumnsToContents()
        self.details_right.resizeRowsToContents()

    def on_detail_cell_changed(self, item):
        """Handle changes to detail table cells and update the dataframe."""
        if self.current_row_index is None or self.df is None:
            return
        
        # Determine which table and get the field name
        table = self.sender()
        row_in_table = item.row()
        col = item.column()
        
        # Only update on value column changes (column 1)
        if col != 1:
            return
        
        field_name = None
        if table == self.details_left:
            field_name = self.details_left.item(row_in_table, 0).text()
        elif table == self.details_right:
            field_name = self.details_right.item(row_in_table, 0).text()
        
        if field_name:
            new_value = item.text()
            if new_value == "<NA>":
                new_value = pd.NA
            else:
                try:
                    new_value = int(new_value)
                except ValueError:
                    pass  # Keep as string if not an integer

            self.df.at[self.current_row_index, field_name] = new_value


    def show_tree_context_menu(self, position):
        """Display context menu at the right-click position."""
        item = self.tree.itemAt(position)
        
        if not item:
            return
        
        menu = QMenu()
        #menu.addAction("Cut", self.action_cut)
        #menu.addAction("Copy", self.action_copy)
        #menu.addAction("Paste", self.action_paste)
        #menu.addSeparator()
        menu.addAction("Delete", self.action_delete)
        menu.addSeparator()
        menu.addAction("Collapse All", self.action_collapse_all)
        menu.addAction("Expand All", self.action_expand_all)
        menu.addSeparator()
        menu.addAction("Insert Unit Template", self.action_insert_template)
        menu.addAction("Copy CSV Format to Clipboard", self.action_copy_csv_format)
        
        menu.exec(self.tree.mapToGlobal(position))

    def action_cut(self):
        """Cut the selected unit to internal clipboard."""
        pass

    def action_copy(self):
        """Copy the selected unit to internal clipboard."""
        pass

    def action_paste(self):
        """Paste the unit from internal clipboard as a duplicate under selected item."""
        pass

    def action_delete(self):
        """Delete the selected unit from tree and dataframe. If unit has subordinates, delete them as well. Update strengths and tree accordingly."""
        items = self.tree.selectedItems()
        
        if not items:
            QMessageBox.warning(self, "Delete Unit", "No unit selected")
            return
        
        item = items[0]
        row_index = item.data(0, Qt.UserRole)
        
        if row_index is None:
            QMessageBox.warning(self, "Delete Unit", "Cannot delete this item")
            return
        
        try:
            # Get the hierarchy key of the unit to delete
            row = self.df.iloc[row_index]
            hierarchy_key_to_delete = self.get_hierarchy_key(row, row_index)
            
            # Determine the level of the unit to delete
            level_to_delete = self.get_level_from_hierarchy(row)
            
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
                        # This row is either the unit to delete or a subordinate
                        rows_to_delete.append(idx)
                except ValueError:
                    # Skip rows with invalid hierarchy data
                    pass
            
            # Delete rows from dataframe (in reverse order to maintain indices)
            for idx in sorted(rows_to_delete, reverse=True):
                self.df.drop(idx, inplace=True)
            
            # Reset the dataframe index to be continuous
            self.df.reset_index(drop=True, inplace=True)
            
            # Refresh the tree
            self.populate_tree()
            
            # Show result message
            num_subordinates = len(rows_to_delete) - 1
            if num_subordinates > 0:
                QMessageBox.information(self, "Delete Unit", f"Deleted unit and {num_subordinates} subordinates")
            else:
                QMessageBox.information(self, "Delete Unit", "Unit deleted")
        except Exception as e:
            QMessageBox.critical(self, "Delete Error", f"Failed to delete unit:\n{str(e)}")

    def action_collapse_all(self):
        """Collapse all items in the tree."""
        self.tree.collapseAll()

    def action_expand_all(self):
        """Expand all items in the tree."""
        self.tree.expandAll()

    def action_insert_template(self):
        """Insert a new unit template under the selected unit."""
        pass

    def action_copy_csv_format(self):
        """Copy the selected unit's data in CSV format to system clipboard."""
        items = self.tree.selectedItems()
        if not items:
            QMessageBox.warning(self, "Copy CSV", "No unit selected")
            return
        
        item = items[0]
        row_index = item.data(0, Qt.UserRole)
        
        if row_index is None:
            QMessageBox.warning(self, "Copy CSV", "Cannot copy this item")
            return
        
        try:
            row = self.df.iloc[row_index]
            
            # Create CSV line (comma-separated values)
            csv_line = ",".join(str(val) if pd.notna(val) else "" for val in row.values)
            
            # Copy to system clipboard
            clipboard = QApplication.clipboard()
            clipboard.setText(csv_line)
            
            QMessageBox.information(self, "Copy CSV", "Unit data copied to clipboard in CSV format")
        except Exception as e:
            QMessageBox.critical(self, "Copy CSV Error", f"Failed to copy: {str(e)}")

    def save_csv(self, path):
        """Save the modified dataframe to a CSV file."""
        try:
            self.df.to_csv(path, encoding="cp1252", index=False)
            QMessageBox.information(
                self,
                "Save Successful",
                f"OOB file saved to:\n{path}"
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Save Error",
                f"Failed to save CSV:\n{str(e)}"
            )


def main():
    app = QApplication(sys.argv)

    # Optional: pass CSV path as command line argument
    csv_path = None

    if len(sys.argv) > 1:
        csv_path = sys.argv[1]

    viewer = OOBViewer(csv_path)
    viewer.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()