import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta
import logging

def calcular_proxima_data(ultima_data, frequencia):
    if pd.isna(ultima_data):
        return None
    if frequencia == 'Mensal':
        return ultima_data + relativedelta(months=1)
    elif frequencia == 'Trimestral':
        return ultima_data + relativedelta(months=3)
    elif frequencia == 'Semestral':
        return ultima_data + relativedelta(months=6)
    elif frequencia == 'Anual':
        return ultima_data + relativedelta(years=1)
    return None

def get_regra_aplicavel(regras_exame, meses_de_tratamento):
    if not regras_exame:
        return None
    for regra in regras_exame:
        periodo = regra.get('Período')
        if periodo == 'Primeiro Ano' and meses_de_tratamento <= 12:
            return regra
        if periodo == 'Após Primeiro Ano' and meses_de_tratamento > 12:
            return regra
        if periodo == 'Primeiro Mês' and meses_de_tratamento == 1:
            return regra
        if periodo == 'Primeiro Trimestre' and meses_de_tratamento <= 3:
            return regra
    for regra in regras_exame:
        if regra.get('Período') == 'Sempre':
            return regra
    return regras_exame[0]

def processar_dados_exames(df_exames, data_referencia, rotina_exames, df_movimentacoes=None, df_internacoes=None, manual_overrides=None):
    if manual_overrides is None:
        manual_overrides = set()
    df_exames['CNS'] = df_exames['CNS'].astype(str).str.strip().str.zfill(15)
    df_exames['Data'] = pd.to_datetime(df_exames['Data'], dayfirst=True, errors='coerce')
    df_exames.dropna(subset=['Nome', 'CNS', 'Data'], inplace=True)

    # Prepara DF de movimentações
    if df_movimentacoes is not None and not df_movimentacoes.empty:
        df_movimentacoes['CNS'] = df_movimentacoes['CNS'].astype(str).str.strip().str.zfill(15)
        df_movimentacoes['Data'] = pd.to_datetime(df_movimentacoes['Data'], dayfirst=True, errors='coerce')
        df_movimentacoes.dropna(subset=['Data', 'Nome', 'CNS'], inplace=True)
    
    # Prepara DF de internações
    if df_internacoes is not None and not df_internacoes.empty:
        df_internacoes['Nome'] = df_internacoes['Nome'].astype(str).str.strip()
        df_internacoes['Data Internação'] = pd.to_datetime(df_internacoes['Data Internação'], dayfirst=True, errors='coerce')
        df_internacoes['Data Alta'] = pd.to_datetime(df_internacoes['Data Alta'], dayfirst=True, errors='coerce')
        df_internacoes.dropna(subset=['Nome', 'Data Internação'], inplace=True)

    pacientes_ativos = {}
    MOV_SAIDA = ['Óbito', 'Transferência de centro', 'Alta ambulatorial', 'Transplante']
    paciente_identifier = ['Nome', 'CNS']
    unique_patients_exames = df_exames.groupby(paciente_identifier).groups.keys()

    for patient_tuple in unique_patients_exames:
        nome_paciente, cns_paciente = patient_tuple
        
        is_active = True
        if df_movimentacoes is not None and not df_movimentacoes.empty:
            movs_paciente = df_movimentacoes[(df_movimentacoes['CNS'] == cns_paciente)].copy()
            movs_paciente = movs_paciente[movs_paciente['Data'] <= data_referencia].sort_values(by='Data', ascending=False)
            if not movs_paciente.empty and movs_paciente.iloc[0]['Movimentação'] in MOV_SAIDA:
                is_active = False
        
        if not is_active:
            continue

        start_date = None
        patient_df_slice = df_exames[df_exames['CNS'] == cns_paciente]
        start_date_col = 'Data início prog. dial. clínica'
        if start_date_col in patient_df_slice.columns:
            possible_dates = pd.to_datetime(patient_df_slice[start_date_col], dayfirst=True, errors='coerce').dropna()
            if not possible_dates.empty:
                start_date = possible_dates.min()
        
        if start_date is None:
            logging.warning(f"Não foi encontrada 'Data início prog. dial. clínica' para {nome_paciente}. Usando a data do exame mais antigo como fallback.")
            start_date = patient_df_slice['Data'].min()

        pacientes_ativos[patient_tuple] = {'status': 'Ativo', 'inicio_ciclo': start_date}

    resultados = {}
    exames_ordenados_com_regras = []
    for exame, regras in rotina_exames.items():
        if regras and regras[0].get('Frequência') != 'Não Cobra':
            exames_ordenados_com_regras.append((exame, regras))
    exames_ordenados = sorted(exames_ordenados_com_regras, key=lambda item: ['Anual', 'Semestral', 'Trimestral', 'Mensal'].index(item[1][0]['Frequência']))

    for paciente_tuple, info in pacientes_ativos.items():
        nome_paciente, cns_paciente = paciente_tuple
        inicio_ciclo = info['inicio_ciclo']
        df_paciente = df_exames[(df_exames['CNS'] == cns_paciente) & (df_exames['Data'] <= data_referencia)].copy()
        
        if df_internacoes is not None and not df_internacoes.empty:
            internacoes_paciente = df_internacoes[df_internacoes['Nome'] == nome_paciente].sort_values(by='Data Internação', ascending=False)
            if not internacoes_paciente.empty:
                ultima_internacao = internacoes_paciente.iloc[0]
                data_internacao = ultima_internacao['Data Internação']
                data_alta = ultima_internacao['Data Alta']
                if data_internacao <= data_referencia and (pd.isna(data_alta) or data_alta >= data_referencia):
                    resultados[paciente_tuple] = {
                        'status': 'Internado',
                        'exames_faltantes': f"Internado desde {data_internacao.strftime('%d/%m/%Y')}",
                        'motivo_internacao': ultima_internacao.get('Tipo', 'Não especificado'),
                        'detalhes_obrigatorios': [], 'detalhes_opcionais': [], 'detalhes_resolvidos': []
                    }
                    continue

        meses_de_tratamento = (data_referencia.year - inicio_ciclo.year) * 12 + (data_referencia.month - inicio_ciclo.month) + 1
        
        exames_feitos_no_mes = df_paciente[(df_paciente['Data'].dt.year == data_referencia.year) & (df_paciente['Data'].dt.month == data_referencia.month)]
        
        exames_mensais_obrigatorios_rotina = []
        for ex, regras in rotina_exames.items():
            regra_aplicavel = get_regra_aplicavel(regras, meses_de_tratamento)
            if regra_aplicavel and regra_aplicavel.get('Frequência') == 'Mensal' and regra_aplicavel.get('Tipo') == 'Obrigatório':
                exames_mensais_obrigatorios_rotina.append(ex)
        
        teve_mensais_obrigatorios_no_mes = not exames_feitos_no_mes[exames_feitos_no_mes['Exame'].isin(exames_mensais_obrigatorios_rotina)].empty

        if not teve_mensais_obrigatorios_no_mes:
            resultados[paciente_tuple] = {
                'status': 'Pendência de Coleta',
                'exames_faltantes': 'Nenhum exame mensal obrigatório encontrado no mês de referência.',
                'detalhes_obrigatorios': [], 'detalhes_opcionais': [], 'detalhes_resolvidos': []
            }
            continue

        mes_do_ciclo = meses_de_tratamento
        freqs_devidas_teoricas = set()
        if mes_do_ciclo % 12 == 1: freqs_devidas_teoricas.update(['Anual', 'Semestral', 'Trimestral', 'Mensal'])
        elif mes_do_ciclo % 6 == 1: freqs_devidas_teoricas.update(['Semestral', 'Trimestral', 'Mensal'])
        elif mes_do_ciclo % 3 == 1: freqs_devidas_teoricas.update(['Trimestral', 'Mensal'])
        else: freqs_devidas_teoricas.add('Mensal')
        
        obrigatorios_pendentes = []
        opcionais_pendentes = []
        resolvidos_manualmente = []
        for exame, regras in exames_ordenados:
            regra_aplicavel = get_regra_aplicavel(regras, meses_de_tratamento)
            if not regra_aplicavel or regra_aplicavel.get('Frequência') == 'Não Cobra':
                continue
            frequencia = regra_aplicavel['Frequência']
            tipo = regra_aplicavel['Tipo']
            if frequencia not in freqs_devidas_teoricas: continue
            if not exames_feitos_no_mes[exames_feitos_no_mes['Exame'] == exame].empty: continue
            if (cns_paciente, exame) in manual_overrides:
                resolvidos_manualmente.append({'exame': exame, 'status': 'Resolvido manualmente'})
                continue
            ultimo_exame_registro = df_paciente[df_paciente['Exame'] == exame].sort_values(by='Data', ascending=False)
            ultimo_realizado_data = pd.NaT
            if not ultimo_exame_registro.empty:
                ultimo_realizado_data = ultimo_exame_registro['Data'].iloc[0]
            proxima_data_devida = calcular_proxima_data(ultimo_realizado_data, frequencia)
            if pd.isna(ultimo_realizado_data) or (proxima_data_devida and proxima_data_devida <= data_referencia):
                detalhe_pendencia = {'exame': exame, 'frequencia': f"{frequencia} ({regra_aplicavel['Período']})", 'ultimo_realizado': 'Nunca realizado' if pd.isna(ultimo_realizado_data) else ultimo_realizado_data.strftime('%d/%m/%Y'), 'proxima_data': 'Pendente' if pd.isna(proxima_data_devida) else proxima_data_devida.strftime('%d/%m/%Y')}
                if tipo == 'Obrigatório':
                    obrigatorios_pendentes.append(detalhe_pendencia)
                else:
                    opcionais_pendentes.append(detalhe_pendencia)
        status_final = 'Pendente' if obrigatorios_pendentes else 'Em dia'
        resumo = f"{len(obrigatorios_pendentes)} exame(s) obrigatório(s) pendente(s)."
        if opcionais_pendentes: resumo += f" {len(opcionais_pendentes)} opcional(is) sugerido(s)."
        if resolvidos_manualmente: resumo += f" {len(resolvidos_manualmente)} resolvido(s) manualmente."
        if status_final == 'Em dia': resumo = "Nenhum exame pendente para este mês."
        resultados[paciente_tuple] = {'status': status_final, 'exames_faltantes': resumo, 'detalhes_obrigatorios': obrigatorios_pendentes, 'detalhes_opcionais': opcionais_pendentes, 'detalhes_resolvidos': resolvidos_manualmente}
    return resultados, len(pacientes_ativos)