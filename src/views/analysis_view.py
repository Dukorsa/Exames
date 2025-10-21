import logging
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta
from functools import partial
from PySide6.QtCore import Qt, QThread, QObject, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton,
    QComboBox, QFileDialog, QScrollArea, QFrame, QLineEdit,
    QSizePolicy, QSpacerItem, QMessageBox
)
from src.core import database_manager as db
from src.core import exam_processor

class Worker(QObject):
    finished = Signal(object, int, int, object)
    error = Signal(str)

    def __init__(self, df_exames, data_ref, rotina, df_mov, overrides):
        super().__init__()
        self.df_exames = df_exames
        self.data_ref = data_ref
        self.rotina = rotina
        self.df_mov = df_mov
        self.overrides = overrides

    def run(self):
        try:
            total_pacientes = self.df_exames.groupby(['Nome', 'CNS']).ngroups
            resultados, num_ativos = exam_processor.processar_dados_exames(
                self.df_exames, self.data_ref, self.rotina, self.df_mov, self.overrides
            )
            self.finished.emit(resultados, num_ativos, total_pacientes, None)
        except Exception as e:
            self.error.emit(f"Erro no processamento: {e}")

class CollapsibleSection(QWidget):
    def __init__(self, title="", parent=None):
        super().__init__(parent)
        self.toggle_button = QPushButton(title)
        self.toggle_button.setCheckable(True)
        self.toggle_button.setStyleSheet("text-align: left; border: none; font-weight: bold;")
        self.content_area = QFrame()
        self.content_layout = QVBoxLayout(self.content_area)
        self.content_layout.setContentsMargins(10, 0, 0, 0)
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setSpacing(0)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.addWidget(self.toggle_button)
        self.main_layout.addWidget(self.content_area)
        self.toggle_button.toggled.connect(self.toggle)
        self.toggle(False)

    def toggle(self, checked):
        self.content_area.setVisible(checked)
        icon = "▼" if checked else "►"
        self.toggle_button.setText(f"{icon} {self.toggle_button.text().strip('►▼ ')}")

    def add_widget(self, widget):
        self.content_layout.addWidget(widget)

class PatientResultWidget(QFrame):
    request_refresh = Signal()
    def __init__(self, patient_tuple, info, analysis_period, parent=None):
        super().__init__(parent)
        self.patient_cns = patient_tuple[1]
        self.analysis_period = analysis_period
        
        status = info.get('status', 'N/A')
        # Define um nome de objeto dinâmico para estilização baseada no status
        self.setObjectName(f"PatientCard-{status.replace(' ', '-').replace('?', '')}")
        self.setFrameShape(QFrame.Shape.StyledPanel)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 10, 15, 10)

        # --- Cabeçalho ---
        header_layout = QGridLayout()
        header_layout.setColumnStretch(1, 1)

        nome, cns = patient_tuple
        patient_name_label = QLabel(f'''<b>{nome}</b><br>
                                     <span style="color: #606266; font-size: 9pt;">CNS: {cns}</span>''')

        # Status com Ícone
        status_map = {
            'Pendente': {'icon': '⚠️', 'label': 'Pendente'},
            'Em dia': {'icon': '✔️', 'label': 'Em Dia'},
            'Internado?': {'icon': '🏥', 'label': 'Internado?'}
        }
        status_info = status_map.get(status, {'icon': '?', 'label': 'N/A'})
        status_label = QLabel(f"<big>{status_info['icon']}</big> {status_info['label']}")
        status_label.setObjectName(f"StatusLabel-{status.replace(' ', '-').replace('?', '')}")
        status_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)

        header_layout.addWidget(patient_name_label, 0, 0, 2, 1)
        header_layout.addWidget(status_label, 0, 1)
        main_layout.addLayout(header_layout)

        # --- Resumo e Seções Retráteis ---
        summary_text = info.get('exames_faltantes', '')
        if summary_text:
            summary_label = QLabel(summary_text)
            summary_label.setObjectName("SummaryLabel")
            main_layout.addWidget(summary_label)
        
        obrigatorios = info.get('detalhes_obrigatorios', [])
        if obrigatorios:
            section = CollapsibleSection(f"Exames OBRIGATÓRIOS Pendentes ({len(obrigatorios)})")
            for exame in obrigatorios:
                exame_layout = QHBoxLayout()
                exame_nome = exame['exame']
                label = QLabel(f"- <b>{exame_nome}</b> (Freq: {exame['frequencia']}) - Último: {exame['ultimo_realizado']} | Próximo: {exame['proxima_data']}")
                ok_button = QPushButton("OK")
                ok_button.setObjectName("okButton")
                ok_button.setFixedSize(40, 24)
                ok_button.clicked.connect(partial(self.mark_as_ok, exame_nome))
                exame_layout.addWidget(label)
                exame_layout.addWidget(ok_button)
                # Usar um QWidget como container para o layout
                container_widget = QWidget()
                container_widget.setLayout(exame_layout)
                section.add_widget(container_widget)
            main_layout.addWidget(section)

        resolvidos = info.get('detalhes_resolvidos', [])
        if resolvidos:
            section = CollapsibleSection(f"Exames Resolvidos Manualmente ({len(resolvidos)})")
            for item in resolvidos:
                section.add_widget(QLabel(f"- <b>{item['exame']}</b>: {item['status']}"))
            main_layout.addWidget(section)

    def mark_as_ok(self, exame_nome):
        db.add_override(self.patient_cns, exame_nome, self.analysis_period)
        self.request_refresh.emit()

class AnalysisView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.df_exames, self.df_mov = None, pd.DataFrame()
        self.analysis_results = None
        self.thread, self.worker = None, None
        
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(self._create_header_panel())
        main_layout.addWidget(self._create_results_panel())
        self._load_profiles()

    def _create_header_panel(self):
        header_frame = QFrame()
        header_frame.setObjectName("HeaderFrame")
        header_layout = QGridLayout(header_frame)
        
        self.profile_combo = QComboBox()
        self.month_combo = QComboBox()
        self.year_combo = QComboBox()
        current_year, current_month = datetime.now().year, datetime.now().month
        self.month_combo.addItems([datetime(2000, i, 1).strftime('%B') for i in range(1, 13)])
        self.year_combo.addItems([str(y) for y in range(current_year - 5, current_year + 2)])
        self.month_combo.setCurrentIndex(current_month - 1)
        self.year_combo.setCurrentText(str(current_year))
        
        self.upload_exames_btn = QPushButton("Carregar Exames CSV")
        self.upload_mov_btn = QPushButton("Carregar Movimentações CSV")
        self.analyze_btn = QPushButton("Analisar Exames")
        self.analyze_btn.setObjectName("AnalyzeButton")
        self.exames_file_label = QLabel("Nenhum arquivo de exames selecionado.")
        self.mov_file_label = QLabel("Nenhum arquivo de movimentações selecionado.")

        header_layout.addWidget(QLabel("<b>Perfil da Clínica:</b>"), 0, 0)
        header_layout.addWidget(self.profile_combo, 0, 1)
        header_layout.addWidget(QLabel("<b>Período:</b>"), 0, 2)
        header_layout.addWidget(self.month_combo, 0, 3)
        header_layout.addWidget(self.year_combo, 0, 4)
        header_layout.addWidget(self.upload_exames_btn, 1, 0)
        header_layout.addWidget(self.exames_file_label, 1, 1, 1, 2)
        header_layout.addWidget(self.upload_mov_btn, 2, 0)
        header_layout.addWidget(self.mov_file_label, 2, 1, 1, 2)
        header_layout.addWidget(self.analyze_btn, 1, 3, 2, 2)
        header_layout.setColumnStretch(1, 1)

        self.upload_exames_btn.clicked.connect(partial(self._handle_file_dialog, 'exames'))
        self.upload_mov_btn.clicked.connect(partial(self._handle_file_dialog, 'mov'))
        self.analyze_btn.clicked.connect(self._start_analysis)
        return header_frame

    def _create_results_panel(self):
        results_frame = QFrame()
        results_layout = QVBoxLayout(results_frame)
        
        self.metrics_label = QLabel("Aguardando análise...")
        self.metrics_label.setObjectName("MetricsLabel")
        results_layout.addWidget(self.metrics_label)

        filters_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Buscar por Nome ou CNS...")
        self.status_filter_combo = QComboBox()
        self.status_filter_combo.addItems(["Todos", "Pendente", "Em dia", "Internado?"])
        filters_layout.addWidget(self.search_input)
        filters_layout.addWidget(self.status_filter_combo)
        results_layout.addLayout(filters_layout)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.results_content = QWidget()
        self.results_layout = QVBoxLayout(self.results_content)
        self.results_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.scroll_area.setWidget(self.results_content)
        results_layout.addWidget(self.scroll_area)

        self.search_input.textChanged.connect(self._filter_results)
        self.status_filter_combo.currentTextChanged.connect(self._filter_results)
        return results_frame

    def _load_profiles(self):
        self.profiles = db.get_perfis()
        self.profile_combo.clear()
        self.profile_combo.addItems(sorted(self.profiles.keys()))

    def _handle_file_dialog(self, file_type):
        filepath, _ = QFileDialog.getOpenFileName(self, "Selecionar Arquivo CSV", "", "CSV Files (*.csv)")
        if not filepath: return
        encodings = ['utf-8-sig', 'latin-1', 'cp1252']
        df = None
        for enc in encodings:
            try:
                df = pd.read_csv(filepath, sep=';', encoding=enc, dtype={'CNS': str})
                break
            except Exception:
                continue
        if df is None:
            QMessageBox.critical(self, "Erro de Leitura", "Não foi possível ler o arquivo CSV com as codificações comuns.")
            return

        if file_type == 'exames':
            self.df_exames = df
            self.exames_file_label.setText(filepath.split('/')[-1])
        elif file_type == 'mov':
            self.df_mov = df
            self.mov_file_label.setText(filepath.split('/')[-1])

    def _start_analysis(self):
        if self.df_exames is None:
            QMessageBox.warning(self, "Atenção", "Por favor, carregue um arquivo de exames.")
            return

        logging.info("Iniciando a análise...")
        self.analyze_btn.setEnabled(False)
        self.analyze_btn.setText("Analisando...")
        self.metrics_label.setText("Processando dados, por favor aguarde...")
        self._clear_results_layout()

        selected_profile = self.profile_combo.currentText()
        profile_data = self.profiles.get(selected_profile, {})
        rotina_nome = profile_data.get('rotina')
        rotina_usada = db.get_rotina_details(rotina_nome) if rotina_nome else {}
        clinicas_perfil = profile_data.get('clinicas', [])
        
        logging.info(f"Perfil selecionado: '{selected_profile}'. Rotina: '{rotina_nome}'. Clínicas: {clinicas_perfil}")

        mes = self.month_combo.currentIndex() + 1
        ano = int(self.year_combo.currentText())
        data_referencia = datetime(ano, mes, 1) + relativedelta(months=1, days=-1)
        analysis_period_str = f"{ano}-{mes:02d}"
        
        df_analise = self.df_exames.copy()
        logging.info(f"DataFrame inicial com {len(df_analise)} linhas.")

        if 'Clinica' in df_analise.columns and clinicas_perfil:
            df_analise = df_analise[df_analise['Clinica'].isin(clinicas_perfil)]
            logging.info(f"Após filtro de clínicas ({clinicas_perfil}), restam {len(df_analise)} linhas.")
        
        df_analise.rename(columns={'Data exame': 'Data'}, inplace=True)
        id_vars = [col for col in ['Nome', 'CNS', 'Data', 'Clinica'] if col in df_analise.columns]
        value_vars = [col for col in df_analise.columns if col not in id_vars and col not in ['CPF', 'prog. dial']]
        df_analise = df_analise.melt(id_vars=id_vars, value_vars=value_vars, var_name='Exame', value_name='Resultado')
        logging.info(f"Após 'melt', o DataFrame tem {len(df_analise)} linhas.")

        df_analise.dropna(subset=['Resultado'], inplace=True)
        df_analise = df_analise[df_analise['Resultado'].astype(str).str.strip() != '']
        logging.info(f"Após remover resultados vazios, restam {len(df_analise)} linhas.")
        
        exames_mapeados = db.get_exames_with_aliases()
        name_mapping = {alias: nome for nome, details in exames_mapeados.items() for alias in details.get('aliases', []) + [nome]}
        
        # Log de alguns nomes de colunas do CSV para depuração
        logging.info(f"Nomes de colunas de exames no CSV (amostra): {list(self.df_exames.columns[:15])}")
        logging.info(f"Nomes de exames mapeados no DB (amostra): {list(exames_mapeados.keys())[:15]}")

        df_analise['Exame'] = df_analise['Exame'].replace(name_mapping)
        logging.info(f"Após mapeamento de nomes de exames, o DataFrame tem {len(df_analise)} linhas.")
        
        df_analise = df_analise[df_analise['Exame'].isin(exames_mapeados.keys())]
        logging.info(f"Após filtrar por exames conhecidos no DB, restam {len(df_analise)} linhas.")

        if df_analise.empty:
            logging.warning("O DataFrame está vazio antes de iniciar o worker. Nenhum resultado será gerado.")
            self.analyze_btn.setEnabled(True)
            self.analyze_btn.setText("Analisar Exames")
            self.metrics_label.setText("Análise concluída, mas nenhum dado de exame relevante foi encontrado após os filtros.")
            self.results_layout.addWidget(QLabel("Nenhum dado de exame corresponde aos filtros do perfil selecionado.\nVerifique se os nomes dos exames e clínicas no arquivo CSV correspondem à configuração do sistema."))
            return

        manual_overrides = db.get_overrides_for_period(analysis_period_str)

        self.thread = QThread()
        self.worker = Worker(df_analise, data_referencia, rotina_usada, self.df_mov, manual_overrides)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self._on_analysis_finished)
        self.worker.error.connect(self._on_analysis_error)

        # Conexão segura para evitar o crash de conversão de tipo
        # O lambda ignora os argumentos emitidos pelo sinal 'finished'
        self.worker.finished.connect(lambda: self.thread.quit())
        
        # Garante que os objetos sejam deletados apenas depois que a thread realmente terminar
        self.thread.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)

        self.thread.start()

    def _on_analysis_finished(self, resultados, num_ativos, total_pacientes, _):
        self.analysis_results = resultados
        pendentes = sum(1 for res in resultados.values() if res['status'] == 'Pendente')
        internados = sum(1 for res in resultados.values() if res['status'] == 'Internado?')
        em_dia = num_ativos - pendentes - internados
        
        self.metrics_label.setText(
            f"Análise concluída. {total_pacientes} pacientes encontrados, {num_ativos} ativos analisados. | "
            f"<b>Em Dia:</b> {em_dia} | <b>Com Pendências:</b> {pendentes} | <b>Internado?:</b> {internados}"
        )
        self.analyze_btn.setEnabled(True)
        self.analyze_btn.setText("Analisar Exames")
        self._filter_results()

    def _on_analysis_error(self, error_msg):
        self.analyze_btn.setEnabled(True)
        self.analyze_btn.setText("Analisar Exames")
        self.metrics_label.setText("Ocorreu um erro durante a análise.")
        QMessageBox.critical(self, "Erro de Análise", error_msg)

    def _filter_results(self):
        if not self.analysis_results: return
        search_query = self.search_input.text().lower()
        status_query = self.status_filter_combo.currentText()
        filtered = {}
        for patient, info in self.analysis_results.items():
            nome, cns = patient
            if status_query != "Todos" and info['status'] != status_query: continue
            if search_query and not (search_query in nome.lower() or search_query in cns): continue
            filtered[patient] = info
        self._populate_results_layout(filtered)
    
    def _clear_results_layout(self):
        while self.results_layout.count():
            child = self.results_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    def _populate_results_layout(self, results_to_display):
        self._clear_results_layout()
        if not results_to_display:
            self.results_layout.addWidget(QLabel("Nenhum paciente encontrado com os filtros atuais."))
            return
        
        mes = self.month_combo.currentIndex() + 1
        ano = int(self.year_combo.currentText())
        analysis_period_str = f"{ano}-{mes:02d}"
        
        status_order = {'Internado?': 0, 'Pendente': 1, 'Em dia': 2}
        sorted_results = sorted(results_to_display.items(), key=lambda item: (status_order.get(item[1]['status'], 99), item[0][0]))
        
        for patient, info in sorted_results:
            widget = PatientResultWidget(patient, info, analysis_period_str)
            widget.request_refresh.connect(self._start_analysis)
            self.results_layout.addWidget(widget)