from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QListWidget, QLineEdit, QMessageBox,
    QAbstractItemView, QFrame, QGridLayout
)
from src.core import database_manager as db
from src.core.notification_service import NotificationService

class ClinicasView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setSpacing(15)
        self._setup_ui()
        self._load_clinicas()

    def _setup_ui(self):
        title = QLabel("Gerenciar Clínicas")
        title.setObjectName("viewTitle")

        # --- Formulário de Adição ---
        add_frame = QFrame()
        add_layout = QGridLayout(add_frame)
        add_layout.setContentsMargins(15, 15, 15, 15)
        
        self.new_clinica_input = QLineEdit()
        self.new_clinica_input.setPlaceholderText("Nome da nova clínica")
        self.add_btn = QPushButton("Adicionar")
        
        add_layout.addWidget(QLabel("Nova Clínica:"), 0, 0)
        add_layout.addWidget(self.new_clinica_input, 0, 1)
        add_layout.addWidget(self.add_btn, 0, 2)
        add_layout.setColumnStretch(1, 1)

        # --- Lista de Clínicas ---
        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)

        # --- Botão de Remoção ---
        remove_layout = QHBoxLayout()
        self.remove_btn = QPushButton("Remover Clínica(s) Selecionada(s)")
        self.remove_btn.setEnabled(False)
        self.remove_btn.setObjectName("removeButton")
        remove_layout.addStretch()
        remove_layout.addWidget(self.remove_btn)

        # --- Layout Principal ---
        self.main_layout.addWidget(title)
        self.main_layout.addWidget(add_frame)
        self.main_layout.addWidget(self.list_widget, 1) # Stretch factor de 1 para a lista
        self.main_layout.addLayout(remove_layout)
        
        # --- Conexões ---
        self.add_btn.clicked.connect(self._add_clinica)
        self.new_clinica_input.returnPressed.connect(self._add_clinica)
        self.remove_btn.clicked.connect(self._remove_clinicas)
        self.list_widget.itemSelectionChanged.connect(self._update_remove_button_state)

    def _load_clinicas(self):
        self.list_widget.clear()
        clinicas = db.get_clinicas()
        self.list_widget.addItems(clinicas)
        self._update_remove_button_state()

    def _add_clinica(self):
        new_name = self.new_clinica_input.text().strip()
        if not new_name:
            QMessageBox.warning(self, "Atenção", "O nome da clínica não pode ser vazio.")
            return

        current_items = [self.list_widget.item(i).text() for i in range(self.list_widget.count())]
        if new_name in current_items:
            QMessageBox.warning(self, "Atenção", f"A clínica '{new_name}' já está cadastrada.")
            return

        current_items.append(new_name)
        db.save_clinicas(sorted(current_items))
        self._load_clinicas()
        self.new_clinica_input.clear()
        NotificationService.show(f"Clínica '{new_name}' adicionada com sucesso.")

    def _remove_clinicas(self):
        selected_items = self.list_widget.selectedItems()
        if not selected_items:
            return

        reply = QMessageBox.question(self, "Confirmar Remoção",
                                     f"Tem certeza que deseja remover {len(selected_items)} clínica(s)?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                     QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.No:
            return

        current_items = [self.list_widget.item(i).text() for i in range(self.list_widget.count())]
        items_to_remove = {item.text() for item in selected_items}
        updated_list = [item for item in current_items if item not in items_to_remove]
        
        db.save_clinicas(updated_list)
        self._load_clinicas()
        NotificationService.show(f"{len(selected_items)} clínica(s) removida(s) com sucesso.", "info")

    def _update_remove_button_state(self):
        self.remove_btn.setEnabled(len(self.list_widget.selectedItems()) > 0)