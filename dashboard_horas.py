import streamlit as st
import pandas as pd
from datetime import datetime, timedelta


# Função para encontrar o primeiro dia útil do mês
def first_business_day_of_month(year, month, data_inicial_col):
    # Filtrar as datas do mês e ano selecionado
    data_inicial_col = pd.to_datetime(data_inicial_col, errors='coerce')
    month_data = data_inicial_col[(data_inicial_col.dt.year == year) & (data_inicial_col.dt.month == month)]

    if not month_data.empty:
        first_day = month_data.min()  # Data mais antiga no período selecionado
    else:
        first_day = pd.Timestamp(year, month, 1)

    while first_day.weekday() >= 5:  # Ajusta se cair em fim de semana
        first_day += timedelta(days=1)

    return first_day


# Função para encontrar o último dia útil do mês
def last_business_day_of_month(year, month):
    last_day = pd.Timestamp(year, month, 1) + pd.offsets.MonthEnd(0)

    while last_day.weekday() >= 5:  # Ajusta se cair em fim de semana
        last_day -= timedelta(days=1)

    return last_day


# Função para converter string de horas no formato HH:MM:SS para número de horas
def convert_time_string_to_hours(time_string):
    try:
        negative = time_string.startswith('-')
        time_string = time_string.replace('-', '')
        time_parts = list(map(int, time_string.split(':')))
        total_hours = time_parts[0] + time_parts[1] / 60 + time_parts[2] / 3600
        return -total_hours if negative else total_hours
    except Exception as e:
        st.error(f"Erro ao converter horas: {e}")
        return 0


# Cabeçalho do dashboard
st.title("Controle de Horas Extras e Negativas")

st.markdown("""
    ### Informações
    - O gestor pode escolher o número de dias para a compensação.

    A estrutura da tabela a ser carregada é: **Nome do Empregado (str)| Horas Totais (HH:MM:SS)| Data Inicial (date)| Data Final (date)| Equipe (str)**

    """)

# Carregar planilha
uploaded_file = st.file_uploader("Carregue a planilha de controle de horas (.xlsx ou .csv)", type=['xlsx', 'csv'])

if uploaded_file:
    # Carregar a planilha
    if uploaded_file.name.endswith('.xlsx'):
        df = pd.read_excel(uploaded_file)
    elif uploaded_file.name.endswith('.csv'):
        df = pd.read_csv(uploaded_file)

    # Convertendo horas para número de horas
    df['Horas Totais'] = df['Horas Totais'].apply(convert_time_string_to_hours)

    st.write("**Planilha carregada com sucesso!**")
    st.dataframe(df)

    # Seletor de Período de Apuração (Mês e Ano)
    st.write("### Selecione o Período de Apuração")

    # Criar seletores para mês e ano
    meses = [f"{i:02d}" for i in range(1, 13)]
    anos = [str(i) for i in range(2020, 2031)]

    # Seletor para mês e ano de início
    mes_inicio = st.selectbox("Mês Início", meses)
    ano_inicio = st.selectbox("Ano Início", anos)

    # Seletor para mês e ano de término
    mes_termino = st.selectbox("Mês Término", meses)
    ano_termino = st.selectbox("Ano Término", anos)

    # Filtrar dados pelo período selecionado
    periodo_inicio = f"{ano_inicio}-{mes_inicio}"
    periodo_termino = f"{ano_termino}-{mes_termino}"

    df['Data Inicial'] = pd.to_datetime(df['Data Inicial'], errors='coerce')
    df['Data Final'] = pd.to_datetime(df['Data Final'], errors='coerce')

    df_filtrado = df[(df['Data Inicial'].dt.strftime('%Y-%m') >= periodo_inicio) &
                     (df['Data Final'].dt.strftime('%Y-%m') <= periodo_termino)]

    # Seletor de Equipe
    st.write("### Selecione a Equipe")

    equipes = df['Equipe'].unique().tolist()
    equipes.insert(0, 'Selecionar Todos')  # Adicionar a opção "Selecionar Todos"

    equipe_selecionada = st.selectbox("Equipe", equipes)

    # Filtro de equipe
    if equipe_selecionada != 'Selecionar Todos':
        df_filtrado = df_filtrado[df_filtrado['Equipe'] == equipe_selecionada]

    # Botão para limpar filtro
    if st.button("Limpar Filtro"):
        equipe_selecionada = 'Selecionar Todos'
        df_filtrado = df

    # Definir Data Início padrão
    primeiro_dia_util = first_business_day_of_month(int(ano_inicio), int(mes_inicio), df_filtrado['Data Inicial'])
    data_inicio = st.date_input("Data Início", primeiro_dia_util)

    # Definir Data Término padrão
    ultimo_dia_util = last_business_day_of_month(int(ano_termino), int(mes_termino))
    data_termino = st.date_input("Data Término", ultimo_dia_util)

    # Exibir os dados filtrados
    st.write(f"**Período Selecionado: {mes_inicio}/{ano_inicio} até {mes_termino}/{ano_termino}**")
    st.write(f"**Equipe Selecionada: {equipe_selecionada}**")
    st.write("**Dados filtrados:**")
    st.dataframe(df_filtrado)
else:
    st.write("Por favor, carregue um arquivo para iniciar.")
