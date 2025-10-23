import logging
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta
from functools import partial
from pathlib import Path
from PySide6.QtCore import Qt, QThread, QObject, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton,
    QComboBox, QFileDialog, QScrollArea, QFrame, QLineEdit,
    QMessageBox
)
from src.core import database_manager as db
from src.core import exam_processor
from src.views.components.loading_overlay import LoadingOverlay

class Worker(QObject):
    finished = Signal(object, int, int, object)
    error = Signal(str)
    def __init__(self, df_exames, data_ref, rotina, df_mov, df_internacoes, overrides):
        super().__init__()
        self.df_exames = df_exames
        self.data_ref = data_ref
        self.rotina = rotina
        self.df_mov = df_mov
        self.df_internacoes = df_internacoes
        self.overrides = overrides
    def run(self):
        try:
            total_pacientes = self.df_exames.groupby(['Nome', 'CNS']).ngroups
            resultados, num_ativos = exam_processor.processar_dados_exames(
                self.df_exames, self.data_ref, self.rotina, self.df_mov, self.df_internacoes, self.overrides
            )
            self.finished.emit(resultados, num_ativos, total_pacientes, None)
        except Exception as e:
            logging.error("Erro detalhado no worker:", exc_info=True)
            self.error.emit(f"Erro no processamento: {e}")

class CollapsibleSection(QWidget):
    def __init__(self, title="", parent=None):
        super().__init__(parent)
        self.toggle_button = QPushButton(title)
        self.toggle_button.setCheckable(True)
        self.content_area = QFrame()
        self.content_layout = QVBoxLayout(self.content_area)
        self.content_layout.setContentsMargins(10, 5, 5, 5)
        self.content_layout.setSpacing(8)
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setSpacing(5)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.addWidget(self.toggle_button)
        self.main_layout.addWidget(self.content_area)
        self.toggle_button.toggled.connect(self.toggle)
        self.toggle(False)
    def toggle(self, checked):
        self.content_area.setVisible(checked)
        icon = "▼" if checked else "►"
        base_text = self.toggle_button.text().strip('►▼ ')
        self.toggle_button.setText(f"{icon} {base_text}")
    def add_widget(self, widget):
        self.content_layout.addWidget(widget)

class PatientResultWidget(QFrame):
    request_refresh = Signal()
    def __init__(self, patient_tuple, info, analysis_period, parent=None):
        super().__init__(parent)
        self.patient_cns = patient_tuple[1]
        self.analysis_period = analysis_period
        status = info.get('status', 'N/A')
        self.setObjectName(f"PatientCard-{status.replace(' ', '-').replace('?', '')}")
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        header_frame = QFrame(objectName="CardHeader")
        header_layout = QHBoxLayout(header_frame)
        status_map = {'Em dia': '✔', 'Pendente': '⚠️', 'Pendência de Coleta': '❓', 'Internado': '🏥'}
        icon_label = QLabel(status_map.get(status, '●'), objectName="CardIcon")
        nome, cns = patient_tuple
        patient_name_label = QLabel(f'{nome}<br><span style="font-size: 9pt; font-weight: 500;">CNS: {cns}</span>')
        status_label = QLabel(status.upper(), objectName="PatientStatusLabel")
        header_layout.addWidget(icon_label)
        header_layout.addWidget(patient_name_label, 1)
        header_layout.addWidget(status_label)
        body_frame = QFrame(objectName="CardBody")
        body_layout = QVBoxLayout(body_frame)
        body_layout.setSpacing(10)
        if summary_text := info.get('exames_faltantes', ''):
            body_layout.addWidget(QLabel(summary_text, objectName="SummaryLabel"))
        if motivo_internacao := info.get('motivo_internacao'):
            body_layout.addWidget(QLabel(f"<b>Motivo da Internação:</b> {motivo_internacao}"))
        if obrigatorios := info.get('detalhes_obrigatorios', []):
            section = CollapsibleSection(f"Exames Obrigatórios Pendentes ({len(obrigatorios)})")
            for exame in obrigatorios:
                exame_layout = QHBoxLayout()
                label = QLabel(f"<b>{exame['exame']}</b> (Freq: {exame['frequencia']})<br><small>Último: {exame['ultimo_realizado']} | Próximo: {exame['proxima_data']}</small>")
                # CORREÇÃO AQUI
                ok_button = QPushButton("OK", objectName="okButton")
                ok_button.setFixedSize(45, 26)
                ok_button.clicked.connect(partial(self.mark_as_ok, exame['exame']))
                exame_layout.addWidget(label, 1)
                exame_layout.addWidget(ok_button)
                container = QWidget()
                container.setLayout(exame_layout)
                section.add_widget(container)
            body_layout.addWidget(section)
        if resolvidos := info.get('detalhes_resolvidos', []):
            section = CollapsibleSection(f"Exames Resolvidos Manualmente ({len(resolvidos)})")
            for item in resolvidos:
                section.add_widget(QLabel(f"• <b>{item['exame']}</b>: {item['status']}"))
            body_layout.addWidget(section)
        main_layout.addWidget(header_frame)
        main_layout.addWidget(body_frame)
    def mark_as_ok(self, exame_nome):
        db.add_override(self.patient_cns, exame_nome, self.analysis_period)
        self.request_refresh.emit()

class AnalysisView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.df_exames, self.df_mov, self.df_internacoes = None, pd.DataFrame(), pd.DataFrame()
        self.analysis_results = None
        self.thread, self.worker = None, None
        self.metric_labels = {}
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)
        main_layout.addWidget(self._create_header_panel())
        main_layout.addWidget(self._create_metrics_panel())
        main_layout.addWidget(self._create_results_panel(), 1)
        self._load_profiles()
        self._reset_metrics()

    def _create_header_panel(self):
        header_frame = QFrame(objectName="HeaderFrame")
        header_layout = QVBoxLayout(header_frame)
        header_layout.setSpacing(15)
        top_controls_layout = QGridLayout()
        top_controls_layout.setColumnStretch(1, 1)
        top_controls_layout.setColumnStretch(3, 1)
        self.profile_combo = QComboBox()
        self.month_combo, self.year_combo = QComboBox(), QComboBox()
        current_year, current_month = datetime.now().year, datetime.now().month
        self.month_combo.addItems([datetime(2000, i, 1).strftime('%B') for i in range(1, 13)])
        self.year_combo.addItems([str(y) for y in range(current_year - 5, current_year + 2)])
        self.month_combo.setCurrentIndex(current_month - 1)
        self.year_combo.setCurrentText(str(current_year))
        # CORREÇÃO AQUI
        self.analyze_btn = QPushButton("Analisar Exames", objectName="AnalyzeButton")
        self.analyze_btn.setFixedHeight(40)
        top_controls_layout.addWidget(QLabel("<b>Perfil da Clínica:</b>"), 0, 0)
        top_controls_layout.addWidget(self.profile_combo, 0, 1)
        top_controls_layout.addWidget(QLabel("<b>Período de Análise:</b>"), 0, 2, Qt.AlignmentFlag.AlignRight)
        top_controls_layout.addWidget(self.month_combo, 0, 3)
        top_controls_layout.addWidget(self.year_combo, 0, 4)
        top_controls_layout.addWidget(self.analyze_btn, 0, 5)
        header_layout.addLayout(top_controls_layout)
        header_layout.addWidget(self._create_upload_panel())
        self.analyze_btn.clicked.connect(self._start_analysis)
        return header_frame

    def _create_upload_panel(self):
        upload_frame = QFrame(objectName="UploadFrame")
        upload_layout = QGridLayout(upload_frame)
        upload_layout.setSpacing(10)
        upload_layout.setContentsMargins(15, 15, 15, 15)
        self.upload_exames_btn = QPushButton("Carregar Exames")
        self.upload_mov_btn = QPushButton("Carregar Movimentações")
        self.upload_internacoes_btn = QPushButton("Carregar Internações")
        self.exames_file_label = QLabel("Nenhum arquivo selecionado.", objectName="ExamesFileLabel")
        self.mov_file_label = QLabel("Nenhum arquivo selecionado.", objectName="MovFileLabel")
        self.internacoes_file_label = QLabel("Nenhum arquivo selecionado.", objectName="InternacoesFileLabel")
        upload_layout.addWidget(self.upload_exames_btn, 0, 0)
        upload_layout.addWidget(self.exames_file_label, 0, 1)
        upload_layout.addWidget(self.upload_mov_btn, 1, 0)
        upload_layout.addWidget(self.mov_file_label, 1, 1)
        upload_layout.addWidget(self.upload_internacoes_btn, 2, 0)
        upload_layout.addWidget(self.internacoes_file_label, 2, 1)
        upload_layout.setColumnStretch(1, 1)
        self.upload_exames_btn.clicked.connect(partial(self._handle_file_dialog, 'exames'))
        self.upload_mov_btn.clicked.connect(partial(self._handle_file_dialog, 'mov'))
        self.upload_internacoes_btn.clicked.connect(partial(self._handle_file_dialog, 'internacoes'))
        return upload_frame

    def _create_metrics_panel(self):
        metrics_panel = QFrame(objectName="MetricsPanel")
        layout = QHBoxLayout(metrics_panel)
        for key in ["Total", "Ativos", "Em Dia", "Pendentes", "Internados", "Pend. Coleta"]:
            card = QFrame(objectName="MetricCard")
            card_layout = QVBoxLayout(card)
            value_label = QLabel("-", objectName="MetricValue", alignment=Qt.AlignmentFlag.AlignCenter)
            title_label = QLabel(key.upper(), objectName="MetricTitle", alignment=Qt.AlignmentFlag.AlignCenter)
            card_layout.addWidget(value_label)
            card_layout.addWidget(title_label)
            self.metric_labels[key] = value_label
            layout.addWidget(card)
        return metrics_panel

    def _create_results_panel(self):
        results_frame = QFrame(objectName="ResultsFrame")
        results_layout = QVBoxLayout(results_frame)
        results_layout.setContentsMargins(15, 15, 15, 15)
        results_layout.setSpacing(15)
        filters_layout = QHBoxLayout()
        self.search_input = QLineEdit(placeholderText="Buscar por Nome ou CNS...")
        self.status_filter_combo = QComboBox()
        self.status_filter_combo.addItems(["Todos", "Em dia", "Pendente", "Pendência de Coleta", "Internado"])
        filters_layout.addWidget(QLabel("<b>Filtros:</b>"))
        filters_layout.addWidget(self.search_input, 1)
        filters_layout.addWidget(self.status_filter_combo)
        results_layout.addLayout(filters_layout)
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.results_content = QWidget()
        self.results_layout = QVBoxLayout(self.results_content)
        self.results_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.scroll_area.setWidget(self.results_content)
        results_layout.addWidget(self.scroll_area, 1)
        self.loading_overlay = LoadingOverlay(results_frame)
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
        try: df = pd.read_csv(filepath, sep=';', encoding='utf-8-sig', dtype={'CNS': str})
        except Exception:
            try: df = pd.read_csv(filepath, sep=';', encoding='latin-1', dtype={'CNS': str})
            except Exception as e:
                QMessageBox.critical(self, "Erro de Leitura", f"Não foi possível ler o arquivo CSV.\nErro: {e}")
                return
        label_map = {'exames': self.exames_file_label, 'mov': self.mov_file_label, 'internacoes': self.internacoes_file_label}
        setattr(self, f"df_{file_type}", df)
        label_map[file_type].setText(Path(filepath).name)
        label_map[file_type].setStyleSheet("font-style: normal;")

    def _start_analysis(self):
        if self.df_exames is None:
            QMessageBox.warning(self, "Atenção", "Por favor, carregue um arquivo de exames.")
            return
        self.analyze_btn.setEnabled(False)
        self.loading_overlay.setVisible(True)
        self._reset_metrics()
        self._clear_results_layout()
        selected_profile = self.profile_combo.currentText()
        profile_data = self.profiles.get(selected_profile, {})
        rotina_nome = profile_data.get('rotina')
        rotina_usada = db.get_rotina_details(rotina_nome) if rotina_nome else {}
        clinicas_perfil = profile_data.get('clinicas', [])
        mes, ano = self.month_combo.currentIndex() + 1, int(self.year_combo.currentText())
        data_referencia = datetime(ano, mes, 1) + relativedelta(months=1, days=-1)
        analysis_period_str = f"{ano}-{mes:02d}"
        df_analise = self.df_exames.copy()
        if 'Clinica' in df_analise.columns and clinicas_perfil:
            df_analise = df_analise[df_analise['Clinica'].isin(clinicas_perfil)]
        df_analise.rename(columns={'Data exame': 'Data'}, inplace=True)
        id_vars = [c for c in ['Nome', 'CNS', 'Data', 'Clinica'] if c in df_analise.columns]
        df_analise = df_analise.melt(id_vars=id_vars, var_name='Exame', value_name='Resultado').dropna(subset=['Resultado'])
        df_analise = df_analise[df_analise['Resultado'].astype(str).str.strip() != '']
        exames_mapeados = db.get_exames_with_aliases()
        name_mapping = {a: n for n, d in exames_mapeados.items() for a in d.get('aliases', []) + [n]}
        df_analise['Exame'] = df_analise['Exame'].replace(name_mapping)
        df_analise = df_analise[df_analise['Exame'].isin(exames_mapeados.keys())]
        if df_analise.empty:
            QMessageBox.information(self, "Análise Concluída", "Nenhum dado de exame relevante foi encontrado.")
            self._reset_ui_state()
            return
        manual_overrides = db.get_overrides_for_period(analysis_period_str)
        self.thread = QThread()
        self.worker = Worker(df_analise, data_referencia, rotina_usada, self.df_mov, self.df_internacoes, manual_overrides)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self._on_analysis_finished)
        self.worker.error.connect(self._on_analysis_error)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.start()

    def _on_analysis_finished(self, resultados, num_ativos, total_pacientes, _):
        self.loading_overlay.setVisible(False)
        self.analysis_results = resultados
        stats = { 'Pendentes': sum(1 for r in resultados.values() if r['status'] == 'Pendente'),
                  'Internados': sum(1 for r in resultados.values() if r['status'] == 'Internado'),
                  'Pend. Coleta': sum(1 for r in resultados.values() if r['status'] == 'Pendência de Coleta')}
        stats['Em Dia'] = num_ativos - sum(stats.values())
        stats.update({'Total': total_pacientes, 'Ativos': num_ativos})
        for key, label in self.metric_labels.items():
            label.setText(str(stats.get(key, 0)))
        self._reset_ui_state()
        self._filter_results()

    def _on_analysis_error(self, error_msg):
        self.loading_overlay.setVisible(False)
        self._reset_ui_state()
        QMessageBox.critical(self, "Erro de Análise", error_msg)
    
    def _reset_metrics(self):
        for label in self.metric_labels.values(): label.setText("-")

    def _reset_ui_state(self):
        self.analyze_btn.setEnabled(True)
        self.analyze_btn.setText("Analisar Exames")

    def _filter_results(self):
        if not self.analysis_results:
            return

        search_query = self.search_input.text().lower().strip()
        status_query = self.status_filter_combo.currentText()
        
        filtered_results = {}
        for patient, info in self.analysis_results.items():
            patient_status = info.get('status', '').strip() 
            
            status_match = (status_query == "Todos" or patient_status == status_query)
            if not status_match:
                continue

            patient_name, patient_cns = patient
            search_match = (not search_query or 
                            search_query in patient_name.lower() or 
                            search_query in patient_cns)
            if not search_match:
                continue
            
            filtered_results[patient] = info
            
        self._populate_results_layout(filtered_results)
    
    def _clear_results_layout(self):
        for i in reversed(range(self.results_layout.count())): 
            widget_item = self.results_layout.itemAt(i)
            if widget_item:
                widget = widget_item.widget()
                if widget:
                    widget.deleteLater()

    def _populate_results_layout(self, results_to_display):
        self._clear_results_layout()
        if not results_to_display:
            self.results_layout.addWidget(QLabel("Nenhum paciente encontrado com os filtros atuais."))
            return
        mes, ano = self.month_combo.currentIndex() + 1, int(self.year_combo.currentText())
        analysis_period_str = f"{ano}-{mes:02d}"
        status_order = {'Internado': 0, 'Pendência de Coleta': 1, 'Pendente': 2, 'Em dia': 3}
        sorted_results = sorted(results_to_display.items(), key=lambda i: (status_order.get(i[1]['status'], 99), i[0][0]))
        for patient, info in sorted_results:
            widget = PatientResultWidget(patient, info, analysis_period_str)
            widget.request_refresh.connect(self._start_analysis)
            self.results_layout.addWidget(widget)