from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QTimer, QPoint, QRect
from PySide6.QtWidgets import QFrame, QLabel, QHBoxLayout

class NotificationBanner(QFrame):
    
    def __init__(self, message: str, notification_type: str = 'success', parent=None):
        super().__init__(parent)
        self.setObjectName("NotificationBanner")
        self.setProperty("notification_type", notification_type)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 10, 15, 10)
        layout.setSpacing(10)
        icon_map = {'success': '✔️', 'info': 'ℹ️', 'warning': '⚠️', 'error': '❌'}
        icon_label = QLabel(icon_map.get(notification_type, 'ℹ️'))
        message_label = QLabel(message)
        layout.addWidget(icon_label)
        layout.addWidget(message_label, 1)
        self.adjustSize()
        self.animation = self._setup_animation()
        self.show()
        QTimer.singleShot(4000, self.hide_banner)

    def _setup_animation(self) -> QPropertyAnimation:
        anim = QPropertyAnimation(self, b"pos")
        anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
        anim.setDuration(400)
        return anim

    def _reposition(self):
        if not self.parent():
            return
        parent_rect = self.parent().rect()
        target_x = (parent_rect.width() - self.width()) // 2
        self.start_pos = QPoint(target_x, parent_rect.height())
        self.end_pos = QPoint(target_x, parent_rect.height() - self.height() - 15)
        self.move(self.start_pos)

    def showEvent(self, event):
        super().showEvent(event)
        self._reposition()
        self.animation.setStartValue(self.start_pos)
        self.animation.setEndValue(self.end_pos)
        self.animation.setDirection(QPropertyAnimation.Direction.Forward)
        self.animation.start()

    def hide_banner(self):
        self.animation.setDirection(QPropertyAnimation.Direction.Backward)
        self.animation.finished.connect(self.deleteLater)
        self.animation.start()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._reposition()