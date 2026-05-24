import sys
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QFileDialog,
    QLabel,
    QPushButton,
    QSplitter,
    QMessageBox,
)
from PySide6.QtCore import Qt

from oob_model import OOBData
from oob_validation import OOBValidator
from oob_tree_view import OOBTreeWidget
from oob_details_view import OOBDetailsWidget
from oob_visual_view import OOBVisualWidget



class OOBViewer(QMainWindow):
    def __init__(self, csv_path=None):
        super().__init__()

        self.setWindowTitle("Order of Battle Viewer")
        self.resize(1400, 900)

        # Initialize data model
        self.data = OOBData()
        self.validator = OOBValidator(self.data)

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

        # Main content splitter (tree, visual, details stacked vertically)
        self.splitter = QSplitter(Qt.Vertical)

        # Tree view
        self.tree = OOBTreeWidget(self.data)
        self.tree.unit_selected.connect(self.on_unit_selected)
        self.tree.unit_deleted.connect(self.on_unit_deleted)

        # Visual view (formations visualization)
        self.visual = OOBVisualWidget(self.data)

        # Details view
        self.details = OOBDetailsWidget(self.data)

        self.splitter.addWidget(self.tree)
        self.splitter.addWidget(self.visual)
        self.splitter.addWidget(self.details)
        self.splitter.setStretchFactor(0, 3)  # tree
        self.splitter.setStretchFactor(1, 1)  # visual
        self.splitter.setStretchFactor(2, 2)  # details

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
            self.data.load_csv(path)

            # Validate unit stats and print warnings to console
            warnings = self.validator.validate_unit_stats()
            if warnings:
                print("OOB Validation Warnings:")
                for warning in warnings:
                    print(f"  {warning}\n")

            # Populate tree and details views
            self.tree.populate()
            self.details.clear()
            self.visual.clear()

            self.status_label.setText(path)
            self.save_button.setEnabled(True)

        except Exception as e:
            QMessageBox.critical(
                self,
                "Load Error",
                str(e)
            )

    def save_csv(self, path):
        try:
            self.data.save_csv(path)
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

    def on_unit_selected(self, row_index: int):
        """Handle unit selection from tree."""
        self.details.populate(row_index)
        self.visual.populate(row_index)

    def on_unit_deleted(self, num_deleted: int):
        """Handle unit deletion from tree."""
        # Details and visual are automatically cleared by tree's populate() call
        # which is called from action_delete()
        pass


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
