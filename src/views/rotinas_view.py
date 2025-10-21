from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QComboBox, QLineEdit, QTableWidget,
    QTableWidgetItem, QHeaderView, QMessageBox, QFrame,
    QGridLayout
)
from src.core import database_manager as db
from src.core.notification_service import NotificationService
from .delegates import ComboBoxDelegate


class RotinasView(QWidget):
    """View para gerenciar rotinas de exames."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_rotina_name = None
        self.all_exames = []
        self.main_layout = QVBoxLayout(self)
        self._setup_ui()
        self.load_initial_data()

    def _setup_ui(self):
        """Configura a interface do usuário."""
        self.main_layout.setSpacing(15)

        title = QLabel("Gerenciar Rotinas de Exames")
        title.setObjectName("viewTitle")

        # --- Controles Superiores ---
        top_frame = QFrame()
        top_layout = QGridLayout(top_frame)
        top_layout.setSpacing(10)

        self.rotina_selector_combo = QComboBox()
        self.new_rotina_name_input = QLineEdit()
        self.base_rotina_combo = QComboBox()
        self.create_rotina_btn = QPushButton("Criar Nova")

        top_layout.addWidget(QLabel("<b>Editar Rotina:</b>"), 0, 0, 1, 3)
        top_layout.addWidget(self.rotina_selector_combo, 1, 0, 1, 3)
        top_layout.addWidget(QLabel("<b>Criar Nova Rotina:</b>"), 2, 0, 1, 3)
        top_layout.addWidget(QLabel("Nome:"), 3, 0)
        top_layout.addWidget(self.new_rotina_name_input, 3, 1)
        top_layout.addWidget(QLabel("Com Base em:"), 4, 0)
        top_layout.addWidget(self.base_rotina_combo, 4, 1)
        top_layout.addWidget(self.create_rotina_btn, 4, 2)
        top_layout.setColumnStretch(1, 1)

        # --- Tabela e Filtro ---
        table_area_layout = QVBoxLayout()
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Filtrar Exame na Tabela:"))
        self.filter_input = QLineEdit()
        self.filter_input.setPlaceholderText("Digite para buscar...")
        filter_layout.addStretch()
        filter_layout.addWidget(self.filter_input)

        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Exame", "Frequência", "Tipo"])

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        self.table.setColumnWidth(1, 160)
        self.table.setColumnWidth(2, 160)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.DoubleClicked | QTableWidget.EditTrigger.SelectedClicked)

        self.freq_options = ["Mensal", "Trimestral", "Semestral", "Anual", "Não Cobra"]
        self.tipo_options = ["Obrigatório", "Opcional"]
        self.freq_delegate = ComboBoxDelegate(self.freq_options, self.table)
        self.tipo_delegate = ComboBoxDelegate(self.tipo_options, self.table)
        self.table.setItemDelegateForColumn(1, self.freq_delegate)
        self.table.setItemDelegateForColumn(2, self.tipo_delegate)

        table_area_layout.addLayout(filter_layout)
        table_area_layout.addWidget(self.table)

        # --- Botões de Ação ---
        action_layout = QHBoxLayout()
        self.delete_btn = QPushButton("Deletar Rotina Selecionada")
        self.delete_btn.setObjectName("removeButton")
        self.save_btn = QPushButton("Salvar Alterações na Rotina")
        self.save_btn.setObjectName("saveButton")
        action_layout.addWidget(self.delete_btn)
        action_layout.addStretch()
        action_layout.addWidget(self.save_btn)

        # --- Layout Principal ---
        self.main_layout.addWidget(title)
        self.main_layout.addWidget(top_frame)
        self.main_layout.addLayout(table_area_layout, 1) # Stretch factor
        self.main_layout.addLayout(action_layout)

        # --- Conexões ---
        self.rotina_selector_combo.currentTextChanged.connect(self._on_rotina_selected)
        self.create_rotina_btn.clicked.connect(self._create_new_rotina)
        self.save_btn.clicked.connect(self._save_rotina_changes)
        self.delete_btn.clicked.connect(self._delete_rotina)
        self.filter_input.textChanged.connect(self._filter_table)

    def load_initial_data(self):
        """Carrega dados iniciais."""
        self._load_rotina_names()
        self.all_exames = sorted(db.get_exames_with_aliases().keys())
        self._on_rotina_selected(self.rotina_selector_combo.currentText())

    def _load_rotina_names(self):
        """Carrega nomes das rotinas nos comboboxes."""
        self.rotina_selector_combo.blockSignals(True)
        self.base_rotina_combo.blockSignals(True)
        
        current_selection = self.rotina_selector_combo.currentText()
        self.rotina_selector_combo.clear()
        self.base_rotina_combo.clear()
        
        rotina_names = db.get_rotina_names()
        if not rotina_names:
            rotina_names = ["Padrão"]
        
        self.rotina_selector_combo.addItems(rotina_names)
        self.base_rotina_combo.addItems(rotina_names)
        
        if current_selection in rotina_names:
            self.rotina_selector_combo.setCurrentText(current_selection)
        
        self.rotina_selector_combo.blockSignals(False)
        self.base_rotina_combo.blockSignals(False)

    def _on_rotina_selected(self, rotina_name):
        """Chamado quando uma rotina é selecionada."""
        self.current_rotina_name = rotina_name
        is_valid_rotina = bool(rotina_name)
        
        self.save_btn.setEnabled(is_valid_rotina)
        self.delete_btn.setEnabled(is_valid_rotina)
        
        if not is_valid_rotina:
            self.table.setRowCount(0)
            return
        
        rotina_details = db.get_rotina_details(rotina_name)
        self._populate_table(rotina_details)

    def _populate_table(self, rotina_details):
        """Popula a tabela com os dados da rotina."""
        self.table.setRowCount(len(self.all_exames))
        
        for row, exame_nome in enumerate(self.all_exames):
            # Obter configuração do exame ou usar padrão
            config = rotina_details.get(
                exame_nome, 
                {"Frequência": "Não Cobra", "Tipo": "Opcional"}
            )
            
            # Criar items da tabela
            item_exame = QTableWidgetItem(exame_nome)
            item_freq = QTableWidgetItem(config["Frequência"])
            item_tipo = QTableWidgetItem(config["Tipo"])
            
            # Coluna 0 (Exame) não é editável
            item_exame.setFlags(item_exame.flags() & ~Qt.ItemFlag.ItemIsEditable)
            
            # Adicionar items à tabela
            self.table.setItem(row, 0, item_exame)
            self.table.setItem(row, 1, item_freq)
            self.table.setItem(row, 2, item_tipo)
        
        # Aplicar filtro atual
        self._filter_table(self.filter_input.text())
        
        # Ajustar largura das colunas
        self.table.resizeColumnsToContents()

    def _filter_table(self, text):
        """Filtra a tabela baseado no texto de busca."""
        search_term = text.lower()
        
        for row in range(self.table.rowCount()):
            exame_item = self.table.item(row, 0)
            if exame_item:
                match = search_term in exame_item.text().lower()
                self.table.setRowHidden(row, not match)

    def _create_new_rotina(self):
        """Cria uma nova rotina."""
        new_name = self.new_rotina_name_input.text().strip()
        base_name = self.base_rotina_combo.currentText()
        
        if not new_name:
            QMessageBox.warning(
                self, 
                "Atenção", 
                "O nome da nova rotina não pode ser vazio."
            )
            return
        
        if new_name in db.get_rotina_names():
            QMessageBox.warning(
                self, 
                "Atenção", 
                f"A rotina '{new_name}' já existe."
            )
            return
        
        try:
            db.create_rotina(new_name, base_name)
            NotificationService.show(f"Nova rotina '{new_name}' criada com sucesso!")
            self.new_rotina_name_input.clear()
            self._load_rotina_names()
            self.rotina_selector_combo.setCurrentText(new_name)
        except Exception as e:
            QMessageBox.critical(
                self, 
                "Erro", 
                f"Não foi possível criar a rotina.\n\nErro: {e}"
            )

    def _save_rotina_changes(self):
        """Salva as alterações da rotina atual."""
        if not self.current_rotina_name:
            return
        
        config_dict = {}
        
        for row in range(self.table.rowCount()):
            exame_nome_item = self.table.item(row, 0)
            frequencia_item = self.table.item(row, 1)
            tipo_item = self.table.item(row, 2)
            
            if not exame_nome_item or not frequencia_item or not tipo_item:
                continue
            
            exame_nome = exame_nome_item.text()
            frequencia = frequencia_item.text()
            tipo = tipo_item.text()
            
            config_dict[exame_nome] = {
                "Frequência": frequencia, 
                "Tipo": tipo
            }
        
        try:
            db.save_rotina(self.current_rotina_name, config_dict)
            NotificationService.show(f"Rotina '{self.current_rotina_name}' atualizada com sucesso!")
        except Exception as e:
            QMessageBox.critical(
                self, 
                "Erro ao Salvar", 
                f"Não foi possível salvar a rotina.\n\nErro: {e}"
            )

    def _delete_rotina(self):
        """Deleta a rotina atual."""
        if not self.current_rotina_name:
            return
        
        reply = QMessageBox.question(
            self, 
            "Confirmar Remoção",
            f"Tem certeza que deseja deletar a rotina '{self.current_rotina_name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                db.delete_rotina(self.current_rotina_name)
                NotificationService.show(f"Rotina '{self.current_rotina_name}' deletada.", "info")
                self.load_initial_data()
            except Exception as e:
                QMessageBox.critical(
                    self, 
                    "Erro ao Deletar", 
                    f"Não foi possível deletar a rotina.\n\nErro: {e}"
                )