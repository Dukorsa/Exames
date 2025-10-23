from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QComboBox, QLineEdit, QTreeWidget,
    QTreeWidgetItem, QHeaderView, QMessageBox, QFrame,
    QGridLayout
)
from src.core import database_manager as db
from src.core.notification_service import NotificationService
from .delegates import ComboBoxDelegate

class RotinasView(QWidget):
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_rotina_name = None
        self.all_exames = []
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(15)
        self._setup_ui()
        self.load_initial_data()

    def _setup_ui(self):
        title = QLabel("Gerenciar Rotinas de Exames")
        title.setObjectName("viewTitle")
        
        top_frame = QFrame()
        top_frame.setObjectName("topFrame")
        top_layout = QGridLayout(top_frame)
        top_layout.setContentsMargins(15, 15, 15, 15)
        top_layout.setSpacing(10)
        self.rotina_selector_combo = QComboBox()
        self.new_rotina_name_input = QLineEdit()
        self.new_rotina_name_input.setPlaceholderText("Ex: Rotina Padrão HD")
        self.base_rotina_combo = QComboBox()
        self.create_rotina_btn = QPushButton("Criar Nova Rotina")
        top_layout.addWidget(QLabel("<b>Editar Rotina Existente:</b>"), 0, 0, 1, 2)
        top_layout.addWidget(self.rotina_selector_combo, 1, 0, 1, 2)
        top_layout.addWidget(QLabel("<b>Criar Nova Rotina:</b>"), 2, 0, 1, 2)
        top_layout.addWidget(QLabel("Nome da Nova Rotina:"), 3, 0)
        top_layout.addWidget(self.new_rotina_name_input, 3, 1)
        top_layout.addWidget(QLabel("Copiar regras de:"), 4, 0)
        top_layout.addWidget(self.base_rotina_combo, 4, 1)
        top_layout.addWidget(self.create_rotina_btn, 5, 0, 1, 2)
        top_layout.setColumnStretch(1, 1)

        table_frame = QFrame()
        table_frame.setObjectName("tableFrame")
        table_layout = QVBoxLayout(table_frame)
        table_layout.setContentsMargins(15, 15, 15, 15)
        filter_layout = QHBoxLayout()
        self.filter_input = QLineEdit()
        self.filter_input.setPlaceholderText("Buscar exame na lista...")
        filter_layout.addWidget(QLabel("<b>Filtro:</b>"))
        filter_layout.addWidget(self.filter_input)
        
        self.tree = QTreeWidget()
        self.tree.setColumnCount(4)
        self.tree.setHeaderLabels(["Exame / Regra", "Período", "Frequência", "Tipo"])
        self.tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.tree.setAlternatingRowColors(True)
        self.periodo_options = ["Sempre", "Primeiro Ano", "Após Primeiro Ano", "Primeiro Mês", "Primeiro Trimestre"]
        self.freq_options = ["Mensal", "Trimestral", "Semestral", "Anual", "Não Cobra"]
        self.tipo_options = ["Obrigatório", "Opcional"]
        self.tree.setItemDelegateForColumn(1, ComboBoxDelegate(self.periodo_options, self.tree))
        self.tree.setItemDelegateForColumn(2, ComboBoxDelegate(self.freq_options, self.tree))
        self.tree.setItemDelegateForColumn(3, ComboBoxDelegate(self.tipo_options, self.tree))

        rule_buttons_layout = QHBoxLayout()
        self.add_rule_btn = QPushButton("Adicionar Regra")
        self.remove_rule_btn = QPushButton("Remover Regra")
        rule_buttons_layout.addStretch()
        rule_buttons_layout.addWidget(self.add_rule_btn)
        rule_buttons_layout.addWidget(self.remove_rule_btn)

        table_layout.addLayout(filter_layout)
        table_layout.addWidget(self.tree)
        table_layout.addLayout(rule_buttons_layout)

        action_layout = QHBoxLayout()
        self.delete_btn = QPushButton("Deletar Rotina")
        self.delete_btn.setObjectName("removeButton")
        self.save_btn = QPushButton("Salvar Alterações")
        self.save_btn.setObjectName("saveButton")
        action_layout.addWidget(self.delete_btn)
        action_layout.addStretch()
        action_layout.addWidget(self.save_btn)

        self.main_layout.addWidget(title)
        self.main_layout.addWidget(top_frame)
        self.main_layout.addWidget(table_frame, 1) 
        self.main_layout.addLayout(action_layout)

        self.rotina_selector_combo.currentTextChanged.connect(self._on_rotina_selected)
        self.create_rotina_btn.clicked.connect(self._create_new_rotina)
        self.save_btn.clicked.connect(self._save_rotina_changes)
        self.delete_btn.clicked.connect(self._delete_rotina)
        self.filter_input.textChanged.connect(self._filter_tree)
        self.add_rule_btn.clicked.connect(self._add_rule)
        self.remove_rule_btn.clicked.connect(self._remove_rule)

    @Slot()
    def refresh_data(self):
        self.load_initial_data()

    def load_initial_data(self):
        self._load_rotina_names()
        self.all_exames = sorted(db.get_exames_with_aliases().keys())
        if self.rotina_selector_combo.count() > 0:
            self._on_rotina_selected(self.rotina_selector_combo.currentText())
        else:
            self.tree.clear()
            self.save_btn.setEnabled(False)
            self.delete_btn.setEnabled(False)

    def _load_rotina_names(self):
        self.rotina_selector_combo.blockSignals(True)
        self.base_rotina_combo.blockSignals(True)
        current_selection = self.rotina_selector_combo.currentText()
        self.rotina_selector_combo.clear()
        self.base_rotina_combo.clear()
        rotina_names = db.get_rotina_names()
        if rotina_names:
            self.rotina_selector_combo.addItems(rotina_names)
            self.base_rotina_combo.addItems(["-- Em Branco --"] + rotina_names)
            if current_selection in rotina_names:
                self.rotina_selector_combo.setCurrentText(current_selection)
        self.rotina_selector_combo.blockSignals(False)
        self.base_rotina_combo.blockSignals(False)

    def _on_rotina_selected(self, rotina_name):
        self.current_rotina_name = rotina_name
        is_valid_rotina = bool(rotina_name)
        self.save_btn.setEnabled(is_valid_rotina)
        self.delete_btn.setEnabled(is_valid_rotina)
        self.tree.setEnabled(is_valid_rotina)
        if not is_valid_rotina:
            self.tree.clear()
            return
        rotina_details = db.get_rotina_details(rotina_name)
        self._populate_tree(rotina_details)

    def _populate_tree(self, rotina_details):
        self.tree.clear()
        for exame_nome in self.all_exames:
            rules = rotina_details.get(exame_nome, [])
            parent_item = QTreeWidgetItem(self.tree, [exame_nome])
            parent_item.setData(0, Qt.ItemDataRole.UserRole, "exame")
            parent_item.setFlags(parent_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            if not rules:
                child_item = QTreeWidgetItem(parent_item, ["Regra 1", "Sempre", "Não Cobra", "Opcional"])
                child_item.setData(0, Qt.ItemDataRole.UserRole, "regra")
                child_item.setFlags(child_item.flags() | Qt.ItemFlag.ItemIsEditable)
            else:
                for i, rule in enumerate(rules):
                    child_item = QTreeWidgetItem(parent_item, [f"Regra {i+1}", rule["Período"], rule["Frequência"], rule["Tipo"]])
                    child_item.setData(0, Qt.ItemDataRole.UserRole, "regra")
                    child_item.setFlags(child_item.flags() | Qt.ItemFlag.ItemIsEditable)
        self._filter_tree(self.filter_input.text())

    def _filter_tree(self, text):
        search_term = text.lower()
        for i in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(i)
            item.setHidden(search_term not in item.text(0).lower())

    def _add_rule(self):
        selected_item = self.tree.currentItem()
        if not selected_item:
            QMessageBox.warning(self, "Atenção", "Selecione um exame para adicionar uma regra.")
            return
        parent_item = selected_item if selected_item.data(0, Qt.ItemDataRole.UserRole) == "exame" else selected_item.parent()
        rule_count = parent_item.childCount()
        new_rule_item = QTreeWidgetItem(parent_item, [f"Regra {rule_count + 1}", "Sempre", "Mensal", "Opcional"])
        new_rule_item.setData(0, Qt.ItemDataRole.UserRole, "regra")
        new_rule_item.setFlags(new_rule_item.flags() | Qt.ItemFlag.ItemIsEditable)
        parent_item.setExpanded(True)

    def _remove_rule(self):
        selected_item = self.tree.currentItem()
        if not selected_item or selected_item.data(0, Qt.ItemDataRole.UserRole) != "regra":
            QMessageBox.warning(self, "Atenção", "Selecione uma regra para remover.")
            return
        parent_item = selected_item.parent()
        if parent_item.childCount() <= 1:
            QMessageBox.warning(self, "Ação não permitida", "Cada exame deve ter pelo menos uma regra. Edite-a para 'Não Cobra' se necessário.")
            return
        parent_item.removeChild(selected_item)
        for i in range(parent_item.childCount()):
            parent_item.child(i).setText(0, f"Regra {i+1}")

    def _create_new_rotina(self):
        new_name = self.new_rotina_name_input.text().strip()
        if not new_name:
            QMessageBox.warning(self, "Atenção", "O nome da nova rotina é obrigatório.")
            return
        if new_name in db.get_rotina_names():
            QMessageBox.warning(self, "Atenção", f"A rotina '{new_name}' já existe.")
            return
        base_name = self.base_rotina_combo.currentText()
        if base_name == "-- Em Branco --": base_name = None
        try:
            db.create_rotina(new_name, base_name)
            NotificationService.show(f"Nova rotina '{new_name}' criada com sucesso!")
            self.new_rotina_name_input.clear()
            self._load_rotina_names()
            self.rotina_selector_combo.setCurrentText(new_name)
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Não foi possível criar a rotina.\n\nErro: {e}")

    def _save_rotina_changes(self):
        if not self.current_rotina_name: return
        config_dict = {}
        for i in range(self.tree.topLevelItemCount()):
            parent_item = self.tree.topLevelItem(i)
            exame_nome = parent_item.text(0)
            rules_list = []
            for j in range(parent_item.childCount()):
                child_item = parent_item.child(j)
                rules_list.append({"Período": child_item.text(1), "Frequência": child_item.text(2), "Tipo": child_item.text(3)})
            config_dict[exame_nome] = rules_list
        try:
            db.save_rotina(self.current_rotina_name, config_dict)
            NotificationService.show(f"Rotina '{self.current_rotina_name}' atualizada com sucesso!")
        except Exception as e:
            QMessageBox.critical(self, "Erro ao Salvar", f"Não foi possível salvar a rotina.\n\nErro: {e}")

    def _delete_rotina(self):
        if not self.current_rotina_name: return
        if self.rotina_selector_combo.count() <= 1:
            QMessageBox.warning(self, "Ação não permitida", "Não é possível remover a última rotina do sistema.")
            return
        usage = db.check_rotina_usage(self.current_rotina_name)
        if usage:
            QMessageBox.warning(self, "Rotina em Uso", f"A rotina '{self.current_rotina_name}' não pode ser deletada pois está em uso pelo(s) perfil(is): {', '.join(usage)}.")
            return
        reply = QMessageBox.question(self, "Confirmar Remoção", f"Tem certeza que deseja deletar a rotina '{self.current_rotina_name}'?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            try:
                db.delete_rotina(self.current_rotina_name)
                NotificationService.show(f"Rotina '{self.current_rotina_name}' deletada.", "info")
                self.load_initial_data()
            except Exception as e:
                QMessageBox.critical(self, "Erro ao Deletar", f"Não foi possível deletar a rotina.\n\nErro: {e}")