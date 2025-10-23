from PySide6.QtCore import QPropertyAnimation, QEasingCurve, Signal
from PySide6.QtWidgets import QStackedWidget, QWidget, QGraphicsOpacityEffect

class AnimatedStackedWidget(QStackedWidget):
    animation_finished = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.duration = 250
        self.next_index = -1
        self.is_animating = False
        self.animation_out = QPropertyAnimation()
        self.animation_in = QPropertyAnimation()

    def setCurrentIndex(self, index: int):
        if self.currentIndex() == index or self.is_animating:
            return
        self.is_animating = True
        self.next_index = index
        previous_widget = self.currentWidget()
        self._setup_animation(self.animation_out, previous_widget, 1.0, 0.0)
        self.animation_out.finished.connect(self._on_fade_out_finished)
        self.animation_out.start()

    def _on_fade_out_finished(self):
        self.animation_out.finished.disconnect(self._on_fade_out_finished)
        self.currentWidget().setGraphicsEffect(None)
        super().setCurrentIndex(self.next_index)
        next_widget = self.currentWidget()
        self._setup_animation(self.animation_in, next_widget, 0.0, 1.0)
        self.animation_in.finished.connect(self._on_fade_in_finished)
        self.animation_in.start()

    def _on_fade_in_finished(self):
        self.animation_in.finished.disconnect(self._on_fade_in_finished)
        self.currentWidget().setGraphicsEffect(None)
        self.is_animating = False
        self.animation_finished.emit()

    def _setup_animation(self, animation: QPropertyAnimation, widget: QWidget, start: float, end: float):
        effect = QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(effect)
        animation.setTargetObject(effect)
        animation.setPropertyName(b"opacity")
        animation.setDuration(self.duration)
        animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        animation.setStartValue(start)
        animation.setEndValue(end)