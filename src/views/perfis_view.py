from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QComboBox, QLineEdit, QListWidget,
    QMessageBox, QFrame, QGridLayout, QFormLayout,
    QAbstractItemView
)
from src.core import database_manager as db
from src.core.notification_service import NotificationService

class PerfisView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_profile_name = None
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(15)
        self._setup_ui()
        self.load_initial_data()

    def _setup_ui(self):
        title = QLabel("Gerenciar Perfis de Análise")
        title.setObjectName("viewTitle")
        
        # --- Seleção e Detalhes do Perfil ---
        details_frame = QFrame()
        details_frame.setObjectName("detailsFrame")
        details_layout = QFormLayout(details_frame)
        details_layout.setContentsMargins(15, 15, 15, 15)
        details_layout.setSpacing(10)
        self.profile_selector_combo = QComboBox()
        self.profile_name_input = QLineEdit()
        self.rotina_selector_combo = QComboBox()
        details_layout.addRow("<b>Selecionar Perfil:</b>", self.profile_selector_combo)
        details_layout.addRow("Nome do Perfil:", self.profile_name_input)
        details_layout.addRow("Rotina de Exames:", self.rotina_selector_combo)

        # --- Clínicas do Perfil ---
        clinics_frame = QFrame()
        clinics_frame.setObjectName("clinicsFrame")
        clinics_layout = QGridLayout(clinics_frame)
        clinics_layout.setContentsMargins(15, 15, 15, 15)
        clinics_layout.setSpacing(10)
        self.available_clinics_list = QListWidget()
        self.available_clinics_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.assigned_clinics_list = QListWidget()
        self.assigned_clinics_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.add_clinic_btn = QPushButton("➡️")
        self.remove_clinic_btn = QPushButton("⬅️")
        buttons_layout = QVBoxLayout()
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.add_clinic_btn)
        buttons_layout.addWidget(self.remove_clinic_btn)
        buttons_layout.addStretch()
        clinics_layout.addWidget(QLabel("<b>Clínicas Disponíveis</b>"), 0, 0)
        clinics_layout.addWidget(QLabel("<b>Clínicas no Perfil</b>"), 0, 2)
        clinics_layout.addWidget(self.available_clinics_list, 1, 0)
        clinics_layout.addLayout(buttons_layout, 1, 1)
        clinics_layout.addWidget(self.assigned_clinics_list, 1, 2)
        clinics_layout.setColumnStretch(0, 1)
        clinics_layout.setColumnStretch(2, 1)

        # --- Botões de Ação ---
        action_layout = QHBoxLayout()
        self.delete_btn = QPushButton("Deletar Perfil")
        self.delete_btn.setObjectName("removeButton")
        self.save_btn = QPushButton("Salvar Perfil")
        self.save_btn.setObjectName("saveButton")
        action_layout.addWidget(self.delete_btn)
        action_layout.addStretch()
        action_layout.addWidget(self.save_btn)

        # --- Layout Principal ---
        self.main_layout.addWidget(title)
        self.main_layout.addWidget(details_frame)
        self.main_layout.addWidget(clinics_frame, 1)
        self.main_layout.addLayout(action_layout)

        # --- Conexões ---
        self.profile_selector_combo.currentTextChanged.connect(self._on_profile_selected)
        self.add_clinic_btn.clicked.connect(self._move_clinicas_add)
        self.remove_clinic_btn.clicked.connect(self._move_clinicas_remove)
        self.save_btn.clicked.connect(self._save_profile)
        self.delete_btn.clicked.connect(self._delete_profile)

    def load_initial_data(self):
        self._populate_profile_selector()
        self._populate_rotina_selector()
        self._populate_clinics_lists()

    def _populate_profile_selector(self):
        self.profile_selector_combo.blockSignals(True)
        current_selection = self.profile_selector_combo.currentText()
        self.profile_selector_combo.clear()
        self.profiles = db.get_perfis()
        self.profile_selector_combo.addItem("-- Criar Novo Perfil --")
        self.profile_selector_combo.addItems(sorted(self.profiles.keys()))
        if current_selection in self.profiles.keys():
            self.profile_selector_combo.setCurrentText(current_selection)
        self.profile_selector_combo.blockSignals(False)
        self._on_profile_selected(self.profile_selector_combo.currentText())

    def _populate_rotina_selector(self):
        self.rotina_selector_combo.clear()
        self.rotina_selector_combo.addItems(["-- Nenhuma --"] + db.get_rotina_names())

    def _populate_clinics_lists(self, assigned_clinics=None):
        assigned_clinics = assigned_clinics or []
        all_clinics = db.get_clinicas()
        available_clinics = [c for c in all_clinics if c not in assigned_clinics]
        self.available_clinics_list.clear()
        self.available_clinics_list.addItems(sorted(available_clinics))
        self.assigned_clinics_list.clear()
        self.assigned_clinics_list.addItems(sorted(assigned_clinics))

    def _on_profile_selected(self, profile_name):
        is_new_profile = (profile_name == "-- Criar Novo Perfil --")
        if is_new_profile:
            self.current_profile_name = None
            self.profile_name_input.clear()
            self.profile_name_input.setEnabled(True)
            self.rotina_selector_combo.setCurrentIndex(0)
            self._populate_clinics_lists()
            self.delete_btn.setEnabled(False)
        else:
            self.current_profile_name = profile_name
            profile_data = self.profiles.get(profile_name, {})
            self.profile_name_input.setText(profile_name)
            self.profile_name_input.setEnabled(True)
            self.rotina_selector_combo.setCurrentText(profile_data.get('rotina', '-- Nenhuma --'))
            self._populate_clinics_lists(profile_data.get('clinicas', []))
            self.delete_btn.setEnabled(True)

    def _move_clinicas(self, source_list, dest_list):
        for item in source_list.selectedItems():
            dest_list.addItem(source_list.takeItem(source_list.row(item)))
        dest_list.sortItems()

    def _move_clinicas_add(self):
        self._move_clinicas(self.available_clinics_list, self.assigned_clinics_list)
        
    def _move_clinicas_remove(self):
        self._move_clinicas(self.assigned_clinics_list, self.available_clinics_list)

    def _save_profile(self):
        new_profile_name = self.profile_name_input.text().strip()
        if not new_profile_name:
            QMessageBox.warning(self, "Atenção", "O nome do perfil não pode ser vazio.")
            return
        is_creating_new = self.current_profile_name is None
        is_renaming = not is_creating_new and new_profile_name != self.current_profile_name
        if (is_creating_new or is_renaming) and new_profile_name in self.profiles:
            QMessageBox.warning(self, "Atenção", f"O perfil '{new_profile_name}' já existe.")
            return
        selected_rotina = self.rotina_selector_combo.currentText()
        if selected_rotina == "-- Nenhuma --":
            selected_rotina = ""
        assigned_clinics = [self.assigned_clinics_list.item(i).text() for i in range(self.assigned_clinics_list.count())]
        try:
            db.save_perfil(self.current_profile_name, new_profile_name, selected_rotina, assigned_clinics)
            NotificationService.show(f"Perfil '{new_profile_name}' salvo com sucesso!")
            self._populate_profile_selector()
            self.profile_selector_combo.setCurrentText(new_profile_name)
        except Exception as e:
            QMessageBox.critical(self, "Erro ao Salvar", f"Não foi possível salvar o perfil.\n\nErro: {e}")

    def _delete_profile(self):
        if not self.current_profile_name: return
        reply = QMessageBox.question(self, "Confirmar Remoção",
                                     f"Tem certeza que deseja deletar o perfil '{self.current_profile_name}'?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                     QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            try:
                db.delete_perfil(self.current_profile_name)
                NotificationService.show(f"Perfil '{self.current_profile_name}' deletado.", "info")
                self.load_initial_data()
            except Exception as e:
                QMessageBox.critical(self, "Erro ao Deletar", f"Não foi possível deletar o perfil.\n\nErro: {e}")