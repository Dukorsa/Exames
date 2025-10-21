from PySide6.QtCore import QPropertyAnimation, QEasingCurve, QParallelAnimationGroup, Signal
from PySide6.QtWidgets import QStackedWidget, QGraphicsOpacityEffect

class AnimatedStackedWidget(QStackedWidget):
    """Um QStackedWidget que anima a transição entre widgets com um efeito de fade."""
    
    animation_finished = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.m_duration = 250  # Duração da animação em milissegundos
        self.m_animation_group = QParallelAnimationGroup(self)
        self.m_current_index = -1

    def set_duration(self, duration: int):
        self.m_duration = duration

    def setCurrentIndex(self, index: int):
        """Define o widget atual com uma animação de fade."""
        if self.currentIndex() == index:
            return

        self.m_current_index = index
        
        # Animação de fade-out do widget antigo
        out_anim = self._create_fade_animation(self.currentWidget(), 1.0, 0.0)
        self.m_animation_group.addAnimation(out_anim)

        # Conecta o fim da animação à troca de widget e ao início do fade-in
        self.m_animation_group.finished.connect(self._on_animation_finished)
        self.m_animation_group.start()

    def _create_fade_animation(self, widget, start: float, end: float):
        """Cria uma animação de opacidade para um dado widget."""
        if not widget:
            return None

        effect = QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(effect)
        
        anim = QPropertyAnimation(effect, b"opacity")
        anim.setDuration(self.m_duration)
        anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
        anim.setStartValue(start)
        anim.setEndValue(end)
        
        return anim

    def _on_animation_finished(self):
        """Slot chamado quando a animação de fade-out termina."""
        # Desconecta o sinal para evitar chamadas recursivas
        self.m_animation_group.finished.disconnect(self._on_animation_finished)
        
        # Define o widget atual (sem animação)
        super().setCurrentIndex(self.m_current_index)
        
        # Limpa o grupo de animação e prepara o fade-in
        self.m_animation_group.clear()
        
        # Animação de fade-in do novo widget
        in_anim = self._create_fade_animation(self.currentWidget(), 0.0, 1.0)
        self.m_animation_group.addAnimation(in_anim)
        
        # Conecta o fim da animação ao sinal público
        self.m_animation_group.finished.connect(self.animation_finished.emit)
        self.m_animation_group.start()
