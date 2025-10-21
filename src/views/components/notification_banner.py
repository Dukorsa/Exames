from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QTimer, QPoint
from PySide6.QtWidgets import QFrame, QLabel, QHBoxLayout

class NotificationBanner(QFrame):
    """Um widget de banner para exibir notificações que desaparecem automaticamente."""
    
    def __init__(self, message: str, notification_type: str = 'success', parent=None):
        super().__init__(parent)

        self.setObjectName("NotificationBanner")
        self.setProperty("notification_type", notification_type)

        # --- Layout e Conteúdo ---
        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 10, 15, 10)
        layout.setSpacing(10)

        icon_map = {
            'success': '✔️',
            'info': 'ℹ️',
            'warning': '⚠️',
            'error': '❌'
        }
        icon_label = QLabel(icon_map.get(notification_type, 'ℹ️'))
        message_label = QLabel(message)

        layout.addWidget(icon_label)
        layout.addWidget(message_label, 1)

        # --- Animação e Posicionamento ---
        self.animation = self._setup_animation()
        self._reposition()

        # Inicia a animação de entrada
        self.show()
        self.animation.start()

        # Agenda o desaparecimento
        QTimer.singleShot(5000, self.hide_banner)

    def _setup_animation(self) -> QPropertyAnimation:
        """Configura a animação de slide e fade."""
        anim = QPropertyAnimation(self, b"pos")
        anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
        anim.setDuration(300)
        return anim

    def _reposition(self):
        """Posiciona o banner na parte inferior central do parente."""
        if not self.parent():
            return
        
        parent_rect = self.parent().rect()
        self.resize(self.sizeHint().width(), self.sizeHint().height())
        target_x = (parent_rect.width() - self.width()) // 2
        self.start_pos = QPoint(target_x, parent_rect.height())
        self.end_pos = QPoint(target_x, parent_rect.height() - self.height() - 15)
        
        self.move(self.start_pos)

    def showEvent(self, event):
        """Garante o reposicionamento quando o banner é mostrado."""
        super().showEvent(event)
        self._reposition()
        self.animation.setStartValue(self.start_pos)
        self.animation.setEndValue(self.end_pos)

    def hide_banner(self):
        """Inicia a animação de saída e agenda a exclusão do widget."""
        self.animation.setDirection(QPropertyAnimation.Direction.Backward)
        self.animation.finished.connect(self.deleteLater)
        self.animation.start()

    def resizeEvent(self, event):
        """Reposiciona o banner se o parente for redimensionado."""
        super().resizeEvent(event)
        self._reposition()
