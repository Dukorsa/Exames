from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QMovie, QColor, QPainter
from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout

class LoadingOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.spinner_label = QLabel(self)
        self.movie = QMovie("src/resources/images/loading_spinner.gif")
        self.movie.setScaledSize(QSize(60, 60))
        self.spinner_label.setMovie(self.movie)

        self.loading_text = QLabel("Processando Análise...", self)
        self.loading_text.setStyleSheet("color: #FFFFFF; font-weight: bold; font-size: 12pt;")

        layout.addWidget(self.spinner_label)
        layout.addWidget(self.loading_text)

        self.setVisible(False)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 150))

    def showEvent(self, event):
        super().showEvent(event)
        if self.parentWidget():
            self.resize(self.parentWidget().size())
        self.movie.start()

    def hideEvent(self, event):
        super().hideEvent(event)
        self.movie.stop()