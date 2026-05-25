from PySide6.QtWidgets import QGraphicsItem
from PySide6.QtCore import Qt, QRect, QPointF, QSize
from PySide6.QtGui import QPainter, QPen, QBrush, QColor, QFont, QTextDocument, QTextOption
import math


def draw_star(painter: QPainter, center: QPointF, size: float, color: QColor, border_color: QColor) -> None:
    """
    Draw a single 5-pointed star.
    
    Args:
        painter: QPainter object to draw with
        center: Center point of the star
        size: Radius of the star
        color: Fill color
        border_color: Border color
    """
    # Calculate 5-pointed star points
    points = []
    for i in range(10):
        angle = math.pi / 2 + i * math.pi / 5
        if i % 2 == 0:
            # Outer point
            r = size
        else:
            # Inner point
            r = size * 0.4
        x = center.x() + r * math.cos(angle)
        y = center.y() - r * math.sin(angle)
        points.append(QPointF(x, y))
    
    painter.setBrush(QBrush(color))
    painter.setPen(QPen(border_color, 1.5))
    painter.drawPolygon(points)


class UnitGraphicsItem(QGraphicsItem):
    """
    Base class for visual unit representations.
    
    Each unit is rendered as star(s) with a text label. Supports selection,
    hovering, and stores the row index for selection tracking.
    """
    
    
    # Star size constants (in logical units)
    STAR_SIZE = 20
    BASE_SIZE = 100  # Base size for non-star shapes
    
    # Color constants
    COLOR_SIDE_1 = QColor("#2c5aa0")  # Blue for French
    COLOR_SIDE_2 = QColor("#a02c2c")  # Red for Allied
    COLOR_BORDER_NORMAL = QColor("#aaaaaa")
    COLOR_BORDER_SELECTED = QColor("#ffff00")  # Yellow highlight
    COLOR_BORDER_HOVER = QColor("#64b5f6")     # Light blue hover
    COLOR_BORDER_HIGHLIGHTED = QColor("#ffffff")  # White for highlighted (but not selected)
    COLOR_TEXT = QColor("#ffffff")
    
    def __init__(self, name: str, unit_row_index: int, side: int, level: int, parent=None):
        """
        Initialize a unit graphics item.
        
        Args:
            name: Display name of the unit
            unit_row_index: Index in the dataframe (for selection tracking)
            side: 1 or 2 (French or Allied)
            level: Hierarchy level (1-6)
            parent: Parent QGraphicsItem
        """
        super().__init__(parent)
        
        self.name = name
        self.unit_row_index = unit_row_index
        self.side = side
        self.level = level
        self.is_selected = False
        self.is_highlighted = False # When highlighted due to parent unit selection.
        self.is_hovered = False
        
        # Store row index as item data for easy retrieval
        self.setData(Qt.UserRole, unit_row_index)
        
        # Make item selectable
        self.setAcceptHoverEvents(True)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        
        # Set bounding rect for hit detection
        self.setPos(0, 0)
    
    def get_side_color(self) -> QColor:
        """Return the color for this unit's side."""
        base_color = self.COLOR_SIDE_1 if self.side == 1 else self.COLOR_SIDE_2
        if self.is_selected:
            return base_color.lighter(150)  # Lighten color when selected
        elif self.is_hovered:
            return base_color.lighter(120)  # Slightly lighten on hover
        elif self.is_highlighted:
            return base_color.lighter(130)  # Lighten when highlighted
        else:
            return base_color
    
    def get_border_color(self) -> QColor:
        """Return the border color based on selection/hover state."""
        if self.is_selected:
            return self.COLOR_BORDER_SELECTED
        elif self.is_hovered:
            return self.COLOR_BORDER_HOVER
        elif self.is_highlighted:
            return self.COLOR_BORDER_HIGHLIGHTED
        else:
            return self.COLOR_BORDER_NORMAL
    
    def paint(self, painter: QPainter, option, widget=None):
        """Override to paint the shape and text label."""
        # Draw the shape (implemented by subclasses)
        self.draw_shape(painter)
        
        # Draw text label
        self.draw_text(painter)
    
    def draw_shape(self, painter: QPainter):
        """Draw the unit shape. Override in subclasses."""
        raise NotImplementedError("Subclasses must implement draw_shape")
    
    def draw_text(self, painter: QPainter):
        """Draw the unit name as text below the shape with word wrapping."""
        font = QFont("Arial", 8)
        painter.setFont(font)
        painter.setPen(QPen(self.COLOR_TEXT))
        
        # Get bounding rect for text
        rect = self.boundingRect()
        
        # Use QTextDocument for word wrapping
        doc = QTextDocument()
        doc.setPlainText(self.name)
        doc.setDefaultFont(font)
        
        # Set text options for word wrapping
        text_option = QTextOption()
        text_option.setWrapMode(QTextOption.WordWrap)
        text_option.setAlignment(Qt.AlignCenter)
        doc.setDefaultTextOption(text_option)
        
        # Layout the document to fit the rect width
        doc.setTextWidth(rect.width() - 4)
        
        # Draw text below the shape
        painter.save()
        
        # Position text below the shape
        text_height = doc.size().height()
        text_x = rect.left()
        text_y = rect.bottom()  # 2 pixels below the shape
        
        painter.translate(text_x, text_y)
        doc.drawContents(painter, QRect(0, 0, int(rect.width() - 4), int(text_height)))
        
        painter.restore()
    
    def _draw_stars(self, painter: QPainter, n: int):
        """Draw n stars in a horizontal line."""
        center = QPointF(0, 0)
        spacing = self.STAR_SIZE * 1.3
        color = self.get_side_color()
        border_color = self.get_border_color()
        
        # Arrange n stars horizontally
        for i in range(n):
            x = center.x() + (i - (n - 1) / 2) * spacing
            y = center.y()
            draw_star(painter, QPointF(x, y), self.STAR_SIZE, color, border_color)
    
    def boundingRect(self):
        """Return the bounding rectangle (for all star shapes)."""
        size = self.STAR_SIZE * 3.5
        return QRect(-int(size*2), -int(size/3), int(size * 4), int(size/2))

    def mousePressEvent(self, event):
        """Handle mouse click on the item."""
        self.is_selected = True
        self.update()
        super().mousePressEvent(event)
    
    def hoverEnterEvent(self, event):
        """Handle mouse hover enter."""
        self.is_hovered = True
        self.update()
    
    def hoverLeaveEvent(self, event):
        """Handle mouse hover leave."""
        self.is_hovered = False
        self.update()
    
    def set_selected(self, selected: bool):
        """Set selection state (called from external selection sync)."""
        self.is_selected = selected
        self.update()
    
    def set_highlighted(self, highlighted: bool):
        """Set highlight state (called from external selection sync)."""
        self.is_highlighted = highlighted
        self.update()


class StarLevel1Item(UnitGraphicsItem):
    """Level 1 (Side): 5 stars arranged in a tight circle."""
    
    def draw_shape(self, painter: QPainter):
        self._draw_stars(painter, 5)
        # """Draw 5 stars in a tight circle."""
        # center = QPointF(0, 0)
        # radius = self.STAR_SIZE * 1.2
        # color = self.get_side_color()
        # border_color = self.get_border_color()
        
        # # Arrange 5 stars in a circle
        # for i in range(5):
        #     angle = (2 * math.pi * i) / 5 - math.pi / 2
        #     x = center.x() + radius * math.cos(angle)
        #     y = center.y() + radius * math.sin(angle)
        #     draw_star(painter, QPointF(x, y), self.STAR_SIZE, color, border_color)


class StarLevel2Item(UnitGraphicsItem):
    """Level 2 (Army): 4 stars in a tight horizontal line."""
    
    def draw_shape(self, painter: QPainter):
        self._draw_stars(painter, 4)


class StarLevel3Item(UnitGraphicsItem):
    """Level 3 (Corps): 3 stars in a tight horizontal line."""
    
    def draw_shape(self, painter: QPainter):
        self._draw_stars(painter, 3)


class StarLevel4Item(UnitGraphicsItem):
    """Level 4 (Division): 2 stars in a tight horizontal line."""

    def draw_shape(self, painter: QPainter):
        self._draw_stars(painter, 2)


class StarLevel5Item(UnitGraphicsItem):
    """Level 5 (Brigade): 1 star."""
    
    def draw_shape(self, painter: QPainter):
        self._draw_stars(painter, 1)


class RectangleItem(UnitGraphicsItem):
    """Rectangle shape for Regiment (Level 6)."""
    
    def boundingRect(self):
        """Return the bounding rectangle."""
        width = self.BASE_SIZE
        height = self.BASE_SIZE * 0.6  # Slightly shorter than wide
        return QRect(-width // 2, -height // 2, width, height)
    
    def draw_shape(self, painter: QPainter):
        """Draw a rectangle."""
        rect = self.boundingRect()
        
        # Fill
        painter.fillRect(rect, QBrush(self.get_side_color()))
        
        # Border
        pen = QPen(self.get_border_color(), 2)
        painter.setPen(pen)
        painter.drawRect(rect)
    
    def draw_text(self, painter: QPainter):
        """Draw the unit name centered on the rectangle."""
        font = QFont("Arial", 8)
        painter.setFont(font)
        painter.setPen(QPen(self.COLOR_TEXT))
        
        # Get bounding rect for text
        rect = self.boundingRect()
        
        # Use QTextDocument for word wrapping
        doc = QTextDocument()
        doc.setPlainText(self.name)
        doc.setDefaultFont(font)
        
        # Set text options for word wrapping
        text_option = QTextOption()
        text_option.setWrapMode(QTextOption.WordWrap)
        text_option.setAlignment(Qt.AlignCenter)
        doc.setDefaultTextOption(text_option)
        
        # Layout the document to fit the rect width
        doc.setTextWidth(rect.width() - 4)
        
        # Center the text vertically and horizontally on the rectangle
        painter.save()
        
        # Calculate offset to center the text block
        text_height = doc.size().height()
        y_offset = -text_height / 2
        
        painter.translate(rect.left(), y_offset)
        doc.drawContents(painter, QRect(0, 0, int(rect.width() - 4), int(text_height)))
        
        painter.restore()

class ArtilleryItem(UnitGraphicsItem):
    """Cannon viewed from above with wheels, connecting pieces, and barrel."""
    
    def boundingRect(self):
        """Return the bounding rectangle."""
        width = self.BASE_SIZE * 1.2
        height = self.BASE_SIZE * 0.7
        return QRect(-width // 2, -height // 2, width, height)
    
    def draw_shape(self, painter: QPainter):
        """Draw a cannon from above: barrel, wheels, and connectors."""
        color = self.get_side_color()
        border_color = self.get_border_color()
        
        # Central long rectangle (barrel)
        barrel_width = 15
        barrel_height = 60
        barrel_rect = QRect(-barrel_width // 2, -barrel_height // 2, barrel_width, barrel_height)
        
        painter.fillRect(barrel_rect, QBrush(color))
        painter.setPen(QPen(border_color, 2))
        painter.drawRect(barrel_rect)
        
        # Left wheel
        wheel_width = 10
        wheel_height = 25
        left_wheel_rect = QRect(-barrel_width // 2 - wheel_width - 5, -wheel_height // 2, wheel_width, wheel_height)
        painter.fillRect(left_wheel_rect, QBrush(color))
        painter.drawRect(left_wheel_rect)
        
        # Right wheel
        right_wheel_rect = QRect(barrel_width // 2 + 5, -wheel_height // 2, wheel_width, wheel_height)
        painter.fillRect(right_wheel_rect, QBrush(color))
        painter.drawRect(right_wheel_rect)
        
        # Left connector
        left_connector_rect = QRect(-barrel_width // 2 - 5, -8, 5, 16)
        painter.fillRect(left_connector_rect, QBrush(color))
        painter.drawRect(left_connector_rect)
        
        # Right connector
        right_connector_rect = QRect(barrel_width // 2, -8, 5, 16)
        painter.fillRect(right_connector_rect, QBrush(color))
        painter.drawRect(right_connector_rect)
    
    def draw_text(self, painter: QPainter):
        """Draw the unit name below the cannon."""
        pass # A little glitchy right now, plus, who cares about cannon names?
        # font = QFont("Arial", 7)
        # painter.setFont(font)
        # painter.setPen(QPen(self.COLOR_TEXT))
        
        # rect = self.boundingRect()
        
        # # Use QTextDocument for word wrapping
        # doc = QTextDocument()
        # doc.setPlainText(self.name)
        # doc.setDefaultFont(font)
        
        # # Set text options for word wrapping
        # text_option = QTextOption()
        # text_option.setWrapMode(QTextOption.WordWrap)
        # text_option.setAlignment(Qt.AlignCenter)
        # doc.setDefaultTextOption(text_option)
        
        # # Layout the document to fit the rect width
        # doc.setTextWidth(rect.width() - 4)
        
        # # Draw text below the shape
        # painter.save()
        # text_height = doc.size().height()
        # text_x = rect.left()
        # text_y = rect.bottom()
        
        # painter.translate(text_x, text_y)
        # doc.drawContents(painter, QRect(0, 0, int(rect.width() - 4), int(text_height)))
        
        # painter.restore()


class WagonItem(UnitGraphicsItem):
    """Wagon with large central rectangle and four small wheels around it."""
    
    def boundingRect(self):
        """Return the bounding rectangle."""
        width = self.BASE_SIZE * 1.1
        height = self.BASE_SIZE * 1.1
        return QRect(-width // 2, -height // 2, width, height)
    
    def draw_shape(self, painter: QPainter):
        """Draw a wagon with central body and four wheels."""
        color = self.get_side_color()
        border_color = self.get_border_color()
        
        # Central large rectangle (wagon body)
        body_width = 36
        body_height = 100
        body_rect = QRect(-body_width // 2, -body_height // 2, body_width, body_height)
        
        painter.fillRect(body_rect, QBrush(color))
        painter.setPen(QPen(border_color, 2))
        painter.drawRect(body_rect)
        
        # Wheel dimensions
        wheel_height = 20
        wheel_width = 8
        wheel_offset_x = body_width // 2 + 8
        wheel_offset_y = body_height // 2 - 8
        
        # Top-left wheel
        tl_wheel = QRect(-wheel_offset_x, -wheel_offset_y, wheel_width, wheel_height)
        painter.fillRect(tl_wheel, QBrush(color))
        painter.drawRect(tl_wheel)
        
        # Top-right wheel
        tr_wheel = QRect(wheel_offset_x - wheel_width, -wheel_offset_y, wheel_width, wheel_height)
        painter.fillRect(tr_wheel, QBrush(color))
        painter.drawRect(tr_wheel)
        
        # Bottom-left wheel
        bl_wheel = QRect(-wheel_offset_x, wheel_offset_y - wheel_height, wheel_width, wheel_height)
        painter.fillRect(bl_wheel, QBrush(color))
        painter.drawRect(bl_wheel)
        
        # Bottom-right wheel
        br_wheel = QRect(wheel_offset_x - wheel_width, wheel_offset_y - wheel_height, wheel_width, wheel_height)
        painter.fillRect(br_wheel, QBrush(color))
        painter.drawRect(br_wheel)
    
    def draw_text(self, painter: QPainter):
        """Draw the unit name centered on the wagon."""
        font = QFont("Arial", 7)
        painter.setFont(font)
        painter.setPen(QPen(self.COLOR_TEXT))
        
        rect = self.boundingRect()
        
        # Use QTextDocument for word wrapping
        doc = QTextDocument()
        doc.setPlainText(self.name)
        doc.setDefaultFont(font)
        
        # Set text options for word wrapping
        text_option = QTextOption()
        text_option.setWrapMode(QTextOption.WordWrap)
        text_option.setAlignment(Qt.AlignCenter)
        doc.setDefaultTextOption(text_option)
        
        # Layout the document to fit the rect width
        doc.setTextWidth(rect.width() - 4)
        
        # Center the text vertically and horizontally on the rectangle
        painter.save()
        
        # Calculate offset to center the text block
        text_height = doc.size().height()
        y_offset = -text_height / 2
        
        painter.translate(rect.left(), y_offset)
        doc.drawContents(painter, QRect(0, 0, int(rect.width() - 4), int(text_height)))
        
        painter.restore()

def get_shape_class_for_level(level: int, formation: str = ""):
    """
    Get the appropriate shape class for a given hierarchy level.
    
    Args:
        level: Hierarchy level (1-6)
        formation: Formation string (optional). For level 6, if formation contains "Art", returns ArtilleryItem.
    
    Returns:
        Shape class for the given level (StarLevel1Item, StarLevel2Item, etc., or RectangleItem for level 6)
    """
    # Special case for level 6: check formation for Artillery
    if level == 6 and "Art" in formation:
        return ArtilleryItem
    elif "SupplyWagon" in formation:
        return WagonItem
    
    shape_map = {
        1: StarLevel1Item,
        2: StarLevel2Item,
        3: StarLevel3Item,
        4: StarLevel4Item,
        5: StarLevel5Item,
        6: RectangleItem,
    }
    return shape_map.get(level, RectangleItem)
