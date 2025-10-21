import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta

def calcular_proxima_data(ultima_data, frequencia):
    if frequencia == 'Mensal':
        return ultima_data + relativedelta(months=1)
    elif frequencia == 'Trimestral':
        return ultima_data + relativedelta(months=3)
    elif frequencia == 'Semestral':
        return ultima_data + relativedelta(months=6)
    elif frequencia == 'Anual':
        return ultima_data + relativedelta(years=1)
    return None

def processar_dados_exames(df_exames, data_referencia, rotina_exames, df_movimentacoes=None, manual_overrides=None):
    if manual_overrides is None:
        manual_overrides = set()

    df_exames['CNS'] = df_exames['CNS'].astype(str).str.strip()
    df_exames['Data'] = pd.to_datetime(df_exames['Data'], dayfirst=True, errors='coerce')
    df_exames.dropna(subset=['Nome', 'CNS', 'Data'], inplace=True)

    if df_movimentacoes is not None and not df_movimentacoes.empty:
        df_movimentacoes['CNS'] = df_movimentacoes['CNS'].astype(str).str.strip()
        df_movimentacoes['Data'] = pd.to_datetime(df_movimentacoes['Data'], dayfirst=True, errors='coerce')
        df_movimentacoes.dropna(subset=['Data', 'Nome', 'CNS'], inplace=True)

    pacientes_ativos = {}
    MOV_SAIDA = ['Óbito', 'Transferência de centro', 'Alta ambulatorial', 'Transplante']
    MOV_ENTRADA = ['Início de programa', 'Retorno']
    paciente_identifier = ['Nome', 'CNS']
    unique_patients_exames = df_exames.groupby(paciente_identifier).groups.keys()

    for patient_tuple in unique_patients_exames:
        nome_paciente, cns_paciente = patient_tuple
        is_active = True
        start_date = None

        if df_movimentacoes is not None and not df_movimentacoes.empty:
            movs_paciente = df_movimentacoes[
                (df_movimentacoes['Nome'] == nome_paciente) & (df_movimentacoes['CNS'] == cns_paciente)
            ].copy()
            movs_paciente = movs_paciente[movs_paciente['Data'] <= data_referencia].sort_values(by='Data', ascending=False)
            
            if not movs_paciente.empty:
                ultima_movimentacao = movs_paciente.iloc[0]
                if ultima_movimentacao['Movimentação'] in MOV_SAIDA:
                    is_active = False
                elif ultima_movimentacao['Movimentação'] in MOV_ENTRADA:
                    start_date = ultima_movimentacao['Data']

        if is_active:
            if start_date is None:
                start_date = df_exames[
                    (df_exames['Nome'] == nome_paciente) & (df_exames['CNS'] == cns_paciente)
                ]['Data'].min()
            pacientes_ativos[patient_tuple] = {'status': 'Ativo', 'inicio_ciclo': start_date}

    resultados = {}
    rotina_cobrada = {exame: detalhes for exame, detalhes in rotina_exames.items() if detalhes.get('Frequência') != 'Não Cobra'}
    exames_ordenados = sorted(
        rotina_cobrada.items(),
        key=lambda item: ['Anual', 'Semestral', 'Trimestral', 'Mensal'].index(item[1]['Frequência'])
    )

    for paciente_tuple, info in pacientes_ativos.items():
        nome_paciente, cns_paciente = paciente_tuple
        inicio_ciclo = info['inicio_ciclo']
        df_paciente = df_exames[
            (df_exames['Nome'] == nome_paciente) &
            (df_exames['CNS'] == cns_paciente) &
            (df_exames['Data'] <= data_referencia)
        ].copy()
        
        is_new_patient_this_month = (inicio_ciclo is not pd.NaT and
                                     inicio_ciclo.year == data_referencia.year and
                                     inicio_ciclo.month == data_referencia.month)

        exames_feitos_no_mes = df_paciente[
            (df_paciente['Data'].dt.year == data_referencia.year) &
            (df_paciente['Data'].dt.month == data_referencia.month)
        ]
        exames_mensais_obrigatorios_rotina = [ex for ex, det in rotina_cobrada.items() if det.get('Frequência') == 'Mensal' and det.get('Tipo') == 'Obrigatório']
        teve_mensais_obrigatorios_no_mes = not exames_feitos_no_mes[exames_feitos_no_mes['Exame'].isin(exames_mensais_obrigatorios_rotina)].empty

        if not teve_mensais_obrigatorios_no_mes and not is_new_patient_this_month:
            resultados[paciente_tuple] = {'status': 'Internado?', 'exames_faltantes': 'Nenhum exame mensal obrigatório encontrado no mês de referência. Confirmar status.',
                                          'detalhes_obrigatorios': [], 'detalhes_opcionais': [], 'detalhes_resolvidos': []}
            continue

        data_referencia_efetiva = data_referencia
        total_months = (data_referencia_efetiva.year - inicio_ciclo.year) * 12 + (data_referencia_efetiva.month - inicio_ciclo.month)
        mes_do_ciclo = total_months + 1

        freqs_devidas_teoricas = set()
        if mes_do_ciclo % 12 == 1: freqs_devidas_teoricas.update(['Anual', 'Semestral', 'Trimestral', 'Mensal'])
        elif mes_do_ciclo % 6 == 1: freqs_devidas_teoricas.update(['Semestral', 'Trimestral', 'Mensal'])
        elif mes_do_ciclo % 3 == 1: freqs_devidas_teoricas.update(['Trimestral', 'Mensal'])
        else: freqs_devidas_teoricas.add('Mensal')
        
        rotinas_maiores_teoricas = {'Trimestral', 'Semestral', 'Anual'}.intersection(freqs_devidas_teoricas)
        exames_rotinas_maiores = [ex for ex, det in rotina_cobrada.items() if det['Frequência'] in rotinas_maiores_teoricas]
        
        if rotinas_maiores_teoricas and exames_feitos_no_mes[exames_feitos_no_mes['Exame'].isin(exames_rotinas_maiores)].empty:
            
            possiveis_datas_referencia = []
            
            exames_trimestrais = [ex for ex, det in rotina_cobrada.items() if det['Frequência'] == 'Trimestral']
            ultima_data_trimestral = df_paciente[df_paciente['Exame'].isin(exames_trimestrais)]['Data'].max()
            if pd.notna(ultima_data_trimestral):
                proximo_vencimento = calcular_proxima_data(ultima_data_trimestral, 'Trimestral')
                if proximo_vencimento and proximo_vencimento <= data_referencia:
                    possiveis_datas_referencia.append(proximo_vencimento)
            
            exames_semestrais = [ex for ex, det in rotina_cobrada.items() if det['Frequência'] == 'Semestral']
            ultima_data_semestral = df_paciente[df_paciente['Exame'].isin(exames_semestrais)]['Data'].max()
            if pd.notna(ultima_data_semestral):
                proximo_vencimento = calcular_proxima_data(ultima_data_semestral, 'Semestral')
                if proximo_vencimento and proximo_vencimento <= data_referencia:
                    possiveis_datas_referencia.append(proximo_vencimento)
            
            exames_anuais = [ex for ex, det in rotina_cobrada.items() if det['Frequência'] == 'Anual']
            ultima_data_anual = df_paciente[df_paciente['Exame'].isin(exames_anuais)]['Data'].max()
            if pd.notna(ultima_data_anual):
                proximo_vencimento = calcular_proxima_data(ultima_data_anual, 'Anual')
                if proximo_vencimento and proximo_vencimento <= data_referencia:
                    possiveis_datas_referencia.append(proximo_vencimento)
            
            if possiveis_datas_referencia:
                data_referencia_ajustada = max(possiveis_datas_referencia)
                
                if data_referencia_ajustada.year != data_referencia.year or data_referencia_ajustada.month != data_referencia.month:
                    data_referencia_efetiva = data_referencia_ajustada
                    
                    total_months = (data_referencia_efetiva.year - inicio_ciclo.year) * 12 + (data_referencia_efetiva.month - inicio_ciclo.month)
                    mes_do_ciclo = total_months + 1
                    
                    freqs_devidas_teoricas = set()
                    if mes_do_ciclo % 12 == 1: freqs_devidas_teoricas.update(['Anual', 'Semestral', 'Trimestral', 'Mensal'])
                    elif mes_do_ciclo % 6 == 1: freqs_devidas_teoricas.update(['Semestral', 'Trimestral', 'Mensal'])
                    elif mes_do_ciclo % 3 == 1: freqs_devidas_teoricas.update(['Trimestral', 'Mensal'])
                    else: freqs_devidas_teoricas.add('Mensal')
        
        mes_anterior = data_referencia - relativedelta(months=1)
        exames_mensais_rotina = [ex for ex, det in rotina_cobrada.items() if det['Frequência'] == 'Mensal']
        exames_paciente_mes_anterior = df_paciente[
            (df_paciente['Data'].dt.year == mes_anterior.year) &
            (df_paciente['Data'].dt.month == mes_anterior.month)
        ]
        teve_mensais_mes_passado = not exames_paciente_mes_anterior[exames_paciente_mes_anterior['Exame'].isin(exames_mensais_rotina)].empty

        obrigatorios_pendentes = []
        opcionais_pendentes = []
        resolvidos_manualmente = []

        for exame, detalhes in exames_ordenados:
            frequencia = detalhes['Frequência']
            tipo = detalhes['Tipo']

            if frequencia not in freqs_devidas_teoricas: continue
            if not exames_feitos_no_mes[exames_feitos_no_mes['Exame'] == exame].empty: continue
            if (cns_paciente, exame) in manual_overrides:
                resolvidos_manualmente.append({'exame': exame, 'status': 'Resolvido manualmente'})
                continue

            is_major_routine = frequencia in ['Anual', 'Semestral', 'Trimestral']
            if is_major_routine and teve_mensais_mes_passado:
                exames_da_mesma_frequencia = [ex for ex, det in rotina_cobrada.items() if det['Frequência'] == frequencia]
                df_historico_frequencia = df_paciente[df_paciente['Exame'].isin(exames_da_mesma_frequencia)]

                if not df_historico_frequencia.empty:
                    ultima_data_realizada_no_grupo = df_historico_frequencia['Data'].max()
                    proxima_data_devida_real = calcular_proxima_data(ultima_data_realizada_no_grupo, frequencia)

                    if proxima_data_devida_real and (proxima_data_devida_real.year > data_referencia.year or \
                       (proxima_data_devida_real.year == data_referencia.year and proxima_data_devida_real.month > data_referencia.month)):
                        continue

            ultimo_exame_registro = df_paciente[df_paciente['Exame'] == exame].sort_values(by='Data', ascending=False)
            ultimo_realizado = 'Nunca realizado'
            proxima_data_str = 'Pendente'
            if not ultimo_exame_registro.empty:
                ultima_data = ultimo_exame_registro['Data'].iloc[0]
                ultimo_realizado = ultima_data.strftime('%d/%m/%Y')
                proxima_data_calc = calcular_proxima_data(ultima_data, frequencia)
                if proxima_data_calc: proxima_data_str = proxima_data_calc.strftime('%d/%m/%Y')
            
            detalhe_pendencia = {'exame': exame, 'frequencia': frequencia,
                                 'ultimo_realizado': ultimo_realizado,
                                 'proxima_data': f'{proxima_data_str} (Pendente)'}
            if tipo == 'Obrigatório':
                obrigatorios_pendentes.append(detalhe_pendencia)
            else:
                opcionais_pendentes.append(detalhe_pendencia)
            
        status_final = 'Pendente' if obrigatorios_pendentes else 'Em dia'
        resumo = f"{len(obrigatorios_pendentes)} exame(s) obrigatório(s) pendente(s)."
        if opcionais_pendentes: resumo += f" {len(opcionais_pendentes)} opcional(is) sugerido(s)."
        if resolvidos_manualmente: resumo += f" {len(resolvidos_manualmente)} resolvido(s) manualmente."
        if status_final == 'Em dia': resumo = "Nenhum exame pendente para este mês."

        resultados[paciente_tuple] = {
            'status': status_final, 'exames_faltantes': resumo,
            'detalhes_obrigatorios': obrigatorios_pendentes,
            'detalhes_opcionais': opcionais_pendentes,
            'detalhes_resolvidos': resolvidos_manualmente
        }
    return resultados, len(pacientes_ativos)