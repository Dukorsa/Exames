from PySide6.QtCore import Qt
from PySide6.QtGui import QFontMetrics
from PySide6.QtWidgets import QStyledItemDelegate, QComboBox, QStyle


class ComboBoxDelegate(QStyledItemDelegate):
    
    def __init__(self, items, parent=None):
        super().__init__(parent)
        self.items = items

    def createEditor(self, parent, option, index):
        editor = QComboBox(parent)
        editor.addItems(self.items)

        font_metrics = QFontMetrics(editor.font())
        max_width = 0
        for item in self.items:
            width = font_metrics.horizontalAdvance(item)
            if width > max_width:
                max_width = width

        extra_space = editor.style().pixelMetric(QStyle.PixelMetric.PM_ScrollBarExtent) + 40
        editor.view().setMinimumWidth(max_width + extra_space)
        
        return editor

    def setEditorData(self, editor, index):
        value = index.model().data(index, Qt.ItemDataRole.DisplayRole)
        
        if value and value in self.items:
            editor.setCurrentText(str(value))
        elif self.items:
            editor.setCurrentIndex(0)

    def setModelData(self, editor, model, index):
        value = editor.currentText()
        
        model.setData(index, value, Qt.ItemDataRole.EditRole)

    def updateEditorGeometry(self, editor, option, index):
        editor.setGeometry(option.rect)