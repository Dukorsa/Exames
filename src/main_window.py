import sys
from pathlib import Path
from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)
from src.core.notification_service import NotificationService
from src.views.components.notification_banner import NotificationBanner
from src.views.components.animated_stacked_widget import AnimatedStackedWidget
from src.views.analysis_view import AnalysisView
from src.views.rotinas_view import RotinasView
from src.views.exames_view import ExamesView
from src.views.clinicas_view import ClinicasView
from src.views.perfis_view import PerfisView

def resource_path(relative_path: str) -> Path:
    try:
        base_path = Path(sys._MEIPASS)
    except Exception:
        base_path = Path(__file__).resolve().parent.parent
    return base_path / relative_path

ICONS_DIR = resource_path("src/resources/images")

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("NefronApp - Gerenciador de Análise de Exames")
        self.setMinimumSize(1200, 768)
        self.setWindowIcon(QIcon(str(ICONS_DIR / "app_icon.png")))
        self.stacked_widget = AnimatedStackedWidget()
        self.view_map = {}
        self._setup_ui()
        self._setup_notifications()

    def _setup_ui(self):
        main_widget = QWidget()
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # CORREÇÃO: Criar a área de conteúdo antes do painel de navegação
        self._create_content_area()
        nav_panel = self._create_nav_panel()
        
        main_layout.addWidget(nav_panel)
        main_layout.addWidget(self.stacked_widget)
        self.setCentralWidget(main_widget)

    def _setup_notifications(self):
        NotificationService.show_notification_signal.connect(self._show_notification)

    def _show_notification(self, message: str, notification_type: str):
        NotificationBanner(
            message=message, notification_type=notification_type, parent=self.stacked_widget.currentWidget()
        )

    def _create_content_area(self):
        self.stacked_widget.setObjectName("contentArea")
        self.view_map = {
            "Análise": AnalysisView(),
            "Rotinas": RotinasView(),
            "Exames": ExamesView(),
            "Clínicas": ClinicasView(),
            "Perfis": PerfisView(),
        }
        for view in self.view_map.values():
            self.stacked_widget.addWidget(view)
        self.view_map["Exames"].exames_changed.connect(self.view_map["Rotinas"].refresh_data)

    def _create_nav_panel(self) -> QFrame:
        nav_panel = QFrame()
        nav_panel.setObjectName("navPanel")
        nav_panel.setFixedWidth(240)
        nav_layout = QVBoxLayout(nav_panel)
        nav_layout.setContentsMargins(0, 0, 0, 10)
        nav_layout.setSpacing(10)
        nav_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        logo_label = QLabel()
        logo_path = resource_path("src/resources/images/logo_grupo_nefron.png")
        if logo_path.exists():
            pixmap = QPixmap(str(logo_path))
            logo_label.setPixmap(pixmap.scaled(
                180, 100, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
            ))
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_label.setContentsMargins(0, 20, 0, 15)
        nav_layout.addWidget(logo_label)
        self.nav_list = QListWidget()
        self.nav_list.setObjectName("navlist")
        self.nav_list.setIconSize(QSize(22, 22))
        nav_items_data = [
            {"text": "Análise", "icon": "analysis_icon.svg", "view": self.view_map["Análise"]},
            {"text": "Rotinas", "icon": "rotinas_icon.svg", "view": self.view_map["Rotinas"]},
            {"text": "Exames", "icon": "exames_icon.svg", "view": self.view_map["Exames"]},
            {"text": "Clínicas", "icon": "clinicas_icon.svg", "view": self.view_map["Clínicas"]},
            {"text": "Perfis", "icon": "perfis_icon.svg", "view": self.view_map["Perfis"]},
        ]
        for item_data in nav_items_data:
            icon_path = ICONS_DIR / item_data["icon"]
            icon = QIcon(str(icon_path)) if icon_path.exists() else QIcon()
            list_item = QListWidgetItem(icon, item_data["text"])
            list_item.setData(Qt.ItemDataRole.UserRole, item_data["view"])
            self.nav_list.addItem(list_item)
        self.nav_list.currentItemChanged.connect(self.on_nav_item_changed)
        nav_layout.addWidget(self.nav_list)
        nav_layout.addStretch()
        self.nav_list.setCurrentRow(0)
        return nav_panel

    def on_nav_item_changed(self, current_item: QListWidgetItem, previous_item: QListWidgetItem):
        if current_item:
            view_widget = current_item.data(Qt.ItemDataRole.UserRole)
            if view_widget:
                index = self.stacked_widget.indexOf(view_widget)
                if index != -1:
                    self.stacked_widget.setCurrentIndex(index)