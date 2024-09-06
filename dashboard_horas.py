import streamlit as st
import pandas as pd
from datetime import datetime, timedelta


# Função para converter string de horas no formato HH:MM:SS ou -HH:MM para número de horas
def convert_time_string_to_hours_v2(time_value):
    try:
        # Se for uma string, realiza a conversão
        if isinstance(time_value, str):
            # Verificar se a hora é negativa
            negative = time_value.startswith('-')
            time_value = time_value.replace('-', '').strip()

            # Separar as partes de horas, minutos e segundos
            time_parts = time_value.split(':')
            
            # Caso o formato seja HH ou HH:MM, completar os segundos
            if len(time_parts) == 1:
                time_parts.append('00')
                time_parts.append('00')
            elif len(time_parts) == 2:
                time_parts.append('00')

            # Converter as partes para inteiros
            time_parts = list(map(int, time_parts))

            # Calcular as horas totais
            total_hours = time_parts[0] + time_parts[1] / 60 + time_parts[2] / 3600
            return -total_hours if negative else total_hours
        
        # Caso contrário, retorna 0
        return 0

    except Exception as e:
        return f"Erro: {e}"


# Função para calcular dias úteis dentro de um período
def calculate_working_days(start_date, end_date):
    return pd.date_range(start=start_date, end=end_date, freq='B')  # 'B' considera apenas dias úteis


# Função para distribuir as horas com equilíbrio entre positivos e negativos
def distribute_hours_equally(df, working_days):
    for _, row in df.iterrows():
        employee_hours = row['Horas Totais']
        days_needed = row['Dias para Compensar']

        if days_needed > 0:
            # Se as horas forem positivas, dividimos pelos dias para criar uma carga negativa por dia
            if employee_hours > 0:
                hours_per_day = -employee_hours / days_needed
            # Se as horas forem negativas, dividimos para gerar uma carga positiva por dia
            else:
                hours_per_day = -employee_hours / days_needed

            assigned_days = working_days[:days_needed]
            df.at[row.name, 'Horas por Dia'] = convert_hours_to_hhmm(hours_per_day)
            df.at[row.name, 'Dias Sugeridos'] = ", ".join([day.strftime('%d/%m/%Y') for day in assigned_days])

    return df


# Função para converter horas totais para formato HH:mm
def convert_hours_to_hhmm(total_hours):
    hours = int(total_hours)
    minutes = abs(int((total_hours - hours) * 60))
    sign = "-" if total_hours < 0 else ""
    return f"{sign}{abs(hours):02d}:{minutes:02d}"


# Cabeçalho do dashboard
st.title("Controle de Horas Extras e Negativas")

st.markdown("""
    ### Informações
    - O gestor pode escolher o número de dias para a compensação.
    
    A estrutura da tabela a ser carregada é: **Nome do Empregado (str)| Horas Totais (HH:MM:SS ou -HH:MM)| Data Inicial (date, formato DD/MM/AAAA)| Data Final (date, formato DD/MM/AAAA)| Equipe (str)**

    """)

# Carregar planilha
uploaded_file = st.file_uploader("Carregue a planilha de controle de horas (.xlsx ou .csv)", type=['xlsx', 'csv'])

if uploaded_file:
    # Carregar a planilha
    if uploaded_file.name.endswith('.xlsx'):
        df = pd.read_excel(uploaded_file, dtype={'Horas Totais': str})
    elif uploaded_file.name.endswith('.csv'):
        df = pd.read_csv(uploaded_file, dtype={'Horas Totais': str})

    # Convertendo horas para número de horas
    df['Horas Totais'] = df['Horas Totais'].apply(convert_time_string_to_hours_v2)

    # Convertendo datas para o formato correto
    df['Data Inicial'] = pd.to_datetime(df['Data Inicial'], format='%Y-%m-%d', errors='coerce')
    df['Data Final'] = pd.to_datetime(df['Data Final'], format='%Y-%m-%d', errors='coerce')

    # Obter a menor data de início e a maior data de término
    menor_data_inicio = df['Data Inicial'].min()
    maior_data_termino = df['Data Final'].max()

    # Criar seletores para o período de apuração (Mês/Ano concatenado)
    st.write("### Selecione o Período de Apuração")
    
    # Criar lista de períodos baseados nas datas da planilha
    lista_periodos = pd.date_range(start=menor_data_inicio, end=maior_data_termino, freq='MS').strftime('%m/%Y').tolist()

    # Seletor de período de início
    periodo_inicio = st.selectbox("Período Início", lista_periodos, index=0)
    
    # Seletor de período de término
    periodo_termino = st.selectbox("Período Término", lista_periodos, index=len(lista_periodos) - 1)

    # Converter os valores dos períodos selecionados em ano e mês
    ano_inicio, mes_inicio = periodo_inicio.split('/')[1], periodo_inicio.split('/')[0]
    ano_termino, mes_termino = periodo_termino.split('/')[1], periodo_termino.split('/')[0]

    # Filtrar dados pelo período selecionado
    periodo_inicio_dt = pd.to_datetime(f"01/{mes_inicio}/{ano_inicio}", format='%d/%m/%Y')
    periodo_termino_dt = pd.to_datetime(f"01/{mes_termino}/{ano_termino}", format='%d/%m/%Y') + pd.offsets.MonthEnd(0)

    df_filtrado = df[(df['Data Inicial'] >= periodo_inicio_dt) & (df['Data Final'] <= periodo_termino_dt)]

    # Seletor de Equipe
    st.write("### Selecione a Equipe")

    equipes = df['Equipe'].unique().tolist()
    equipes.insert(0, 'Selecionar Todos')  # Adicionar a opção "Selecionar Todos"

    equipe_selecionada = st.selectbox("Equipe", equipes)

    # Filtro de equipe
    if equipe_selecionada != 'Selecionar Todos':
        df_filtrado = df_filtrado[df_filtrado['Equipe'] == equipe_selecionada]

    # Verificar se há dados no DataFrame filtrado
    if df_filtrado.empty:
        st.warning("Não existem dados correspondentes")
    else:
        # Calcular dias úteis entre a data de início e término filtradas
        working_days = calculate_working_days(periodo_inicio_dt, periodo_termino_dt)

        # Exibir a tabela filtrada com os empregados
        st.write(f"**Período Selecionado: {periodo_inicio} até {periodo_termino}**")
        st.write(f"**Equipe Selecionada: {equipe_selecionada}**")
        st.write("**Dados filtrados:**")
        st.dataframe(df_filtrado)

        # Seletor para número de dias a serem compensados por empregado
        st.write("### Selecione o número de dias para compensação por empregado")
        if 'Dias para Compensar' not in df_filtrado.columns:
            df_filtrado['Dias para Compensar'] = 1  # Valor padrão de 1 dia para compensar

        for i, row in df_filtrado.iterrows():
            df_filtrado.at[i, 'Dias para Compensar'] = st.slider(f"{row['Nome do Empregado']}",
                                                                 min_value=1,
                                                                 max_value=len(working_days),
                                                                 value=int(row['Dias para Compensar']))

        # Distribuir horas entre os dias úteis
        df_filtrado = distribute_hours_equally(df_filtrado, working_days)

        # Exibir a tabela atualizada com as horas distribuídas
        st.write("### Sugerido de Horas por Dia")
        st.dataframe(df_filtrado[['Nome do Empregado', 'Horas Totais', 'Dias para Compensar', 'Horas por Dia', 'Dias Sugeridos']])

else:
    st.write("Por favor, carregue um arquivo para iniciar.")
