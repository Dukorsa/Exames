from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QLineEdit, QAbstractItemView, QFrame, QGridLayout
)
from src.core import database_manager as db
from src.core.notification_service import NotificationService

class ExamesView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setSpacing(15) # Adiciona espaçamento geral
        self._setup_ui()
        self._load_exames()

    def _setup_ui(self):
        title = QLabel("Gerenciar Exames e Seus Apelidos")
        title.setObjectName("viewTitle")

        # --- Formulário de Adição ---
        add_frame = QFrame()
        add_frame.setObjectName("addExamFrame")
        add_layout = QGridLayout(add_frame)
        add_layout.setContentsMargins(15, 15, 15, 15)
        add_layout.setSpacing(10)

        add_title = QLabel("<b>Adicionar Novo Exame</b>")
        add_layout.addWidget(add_title, 0, 0, 1, 3)

        self.nome_input = QLineEdit()
        self.nome_input.setPlaceholderText("Ex: Hemoglobina")
        self.aliases_input = QLineEdit()
        self.aliases_input.setPlaceholderText("Ex: HB, Hemo")
        self.add_btn = QPushButton("Adicionar à Lista")

        add_layout.addWidget(QLabel("Nome Padrão:"), 1, 0)
        add_layout.addWidget(self.nome_input, 1, 1)
        add_layout.addWidget(QLabel("Apelidos (separados por vírgula):"), 2, 0)
        add_layout.addWidget(self.aliases_input, 2, 1)
        add_layout.addWidget(self.add_btn, 2, 2)
        add_layout.setColumnStretch(1, 1) # Faz a coluna do input esticar

        # --- Tabela de Exames ---
        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["Nome Padrão", "Apelidos (separados por vírgula)"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)

        # --- Layout dos Botões de Ação ---
        buttons_layout = QHBoxLayout()
        self.remove_btn = QPushButton("Remover Selecionado(s)")
        self.remove_btn.setObjectName("removeButton")
        self.remove_btn.setEnabled(False)
        self.save_btn = QPushButton("Salvar Todas as Alterações")
        self.save_btn.setObjectName("saveButton")
        
        buttons_layout.addWidget(self.remove_btn)
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.save_btn)
        
        # --- Montagem do Layout Principal ---
        self.main_layout.addWidget(title)
        self.main_layout.addWidget(add_frame)
        self.main_layout.addWidget(self.table, 1) # O 1 faz a tabela esticar
        self.main_layout.addLayout(buttons_layout)
        
        # --- Conexões ---
        self.add_btn.clicked.connect(self._add_row_to_table)
        self.save_btn.clicked.connect(self._save_changes)
        self.remove_btn.clicked.connect(self._remove_selected_rows)
        self.table.itemSelectionChanged.connect(self._update_button_state)
    
    def _load_exames(self):
        self.table.blockSignals(True)
        self.table.setRowCount(0)
        exames_dict = db.get_exames_with_aliases()
        
        for nome_padrao, details in sorted(exames_dict.items()):
            row_position = self.table.rowCount()
            self.table.insertRow(row_position)
            
            nome_item = QTableWidgetItem(nome_padrao)
            aliases_str = ", ".join(details.get('aliases', []))
            aliases_item = QTableWidgetItem(aliases_str)
            
            self.table.setItem(row_position, 0, nome_item)
            self.table.setItem(row_position, 1, aliases_item)
        
        self.table.blockSignals(False)
        self._update_button_state()

    def _add_row_to_table(self):
        nome_padrao = self.nome_input.text().strip()
        if not nome_padrao:
            QMessageBox.warning(self, "Atenção", "O Nome Padrão do Exame é obrigatório.")
            return

        for row in range(self.table.rowCount()):
            if self.table.item(row, 0) and self.table.item(row, 0).text() == nome_padrao:
                QMessageBox.warning(self, "Atenção", f"O exame '{nome_padrao}' já existe na lista.")
                return

        row_position = self.table.rowCount()
        self.table.insertRow(row_position)
        
        nome_item = QTableWidgetItem(nome_padrao)
        aliases_item = QTableWidgetItem(self.aliases_input.text().strip())
        self.table.setItem(row_position, 0, nome_item)
        self.table.setItem(row_position, 1, aliases_item)
        
        self.nome_input.clear()
        self.aliases_input.clear()

    def _remove_selected_rows(self):
        selected_rows = sorted(list(set(item.row() for item in self.table.selectedItems())), reverse=True)
        if not selected_rows:
            return
        
        reply = QMessageBox.question(self, "Confirmar Remoção",
                                     f"Tem certeza que deseja remover {len(selected_rows)} exame(s) da lista?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                     QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            for row in selected_rows:
                self.table.removeRow(row)

    def _save_changes(self):
        novos_exames_dict = {}
        nomes_vistos = set()

        for row in range(self.table.rowCount()):
            nome_item = self.table.item(row, 0)
            nome_padrao = nome_item.text().strip() if nome_item else ""
            
            if not nome_padrao:
                QMessageBox.critical(self, "Erro de Validação", f"Erro na linha {row + 1}: O Nome Padrão não pode ser vazio.")
                return
            if nome_padrao in nomes_vistos:
                QMessageBox.critical(self, "Erro de Validação", f"Erro: O nome '{nome_padrao}' está duplicado na lista.")
                return
            
            nomes_vistos.add(nome_padrao)
            aliases_item = self.table.item(row, 1)
            aliases_str = aliases_item.text() if aliases_item else ""
            aliases = sorted(list(set(alias.strip() for alias in aliases_str.split(',') if alias.strip())))
            novos_exames_dict[nome_padrao] = {"aliases": aliases}
        
        try:
            db.save_exames_from_dict(novos_exames_dict)
            NotificationService.show("Exames e apelidos salvos com sucesso!")
            self._load_exames()
        except Exception as e:
            QMessageBox.critical(self, "Erro ao Salvar", f"Não foi possível salvar os dados no banco de dados.\n\nErro: {e}")

    def _update_button_state(self):
        self.remove_btn.setEnabled(len(self.table.selectedItems()) > 0)