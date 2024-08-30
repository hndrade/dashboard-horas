import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px


# Função para calcular os dias úteis restantes
def calculate_working_days(start_date, end_date):
    return pd.date_range(start=start_date, end=end_date, freq='B')


# Função para converter horas totais para formato HH:mm
def convert_hours_to_hhmm(total_hours):
    hours = int(total_hours)
    minutes = abs(int((total_hours - hours) * 60))
    sign = "-" if total_hours < 0 else ""
    return f"{sign}{abs(hours):02d}:{minutes:02d}"


# Função para calcular o último dia útil do trimestre atual
def last_business_day_of_quarter(date):
    quarter = (date.month - 1) // 3 + 1
    last_month_of_quarter = quarter * 3
    last_day = pd.Timestamp(date.year, last_month_of_quarter, 1) + pd.offsets.MonthEnd(0)
    while last_day.weekday() >= 5:  # Se cair em fim de semana, ajusta para o último dia útil anterior
        last_day -= timedelta(days=1)
    return last_day


# Função para distribuir as horas com equilíbrio entre positivos e negativos
def distribute_hours_equally(df, working_days):
    gantt_data = []
    kanban_data = {}
    kanban_dates = []

    for _, row in df.iterrows():
        employee_hours = row['Horas Totais']
        days_needed = row['Dias para Compensar']

        if days_needed > 0:
            if employee_hours > 0:  # Para horas positivas, horas por dia será negativa
                hours_per_day = -employee_hours / days_needed
            else:  # Para horas negativas, horas por dia será positiva
                hours_per_day = -employee_hours / days_needed

            assigned_days = working_days[:days_needed]
            df.at[row.name, 'Horas por Dia'] = convert_hours_to_hhmm(hours_per_day)
            df.at[row.name, 'Dias Sugeridos'] = ", ".join([day.strftime('%d/%m/%Y') for day in assigned_days])

            for day in assigned_days:
                gantt_data.append({
                    'Nome do Empregado': row['Nome do Empregado'],
                    'Start': day,
                    'Finish': day + pd.DateOffset(days=1),
                    'Horas por Dia': df.at[row.name, 'Horas por Dia']
                })

                day_str = day.strftime('%d/%m/%Y')
                if day_str not in kanban_data:
                    kanban_data[day_str] = []
                    kanban_dates.append(day_str)
                kanban_data[day_str].append(row['Nome do Empregado'])

    return df, gantt_data, kanban_data, kanban_dates


# Cabeçalho do dashboard
st.title("Controle de Horas Extras e Negativas")

st.markdown("""
    ### Informações
    - O gestor pode escolher o número de dias para a compensação.
    
    A estrutura da tabela a ser carregada é: **Nome do Empregado (str)| Horas Totais	(int)| Data Inicial	(date)| Data Final (date)**

    """)

uploaded_file = st.file_uploader("Carregue a planilha de controle de horas (.xlsx ou .csv)", type=['xlsx', 'csv'])

if uploaded_file:
    # Carregar a planilha
    if uploaded_file.name.endswith('.xlsx'):
        df = pd.read_excel(uploaded_file)
    elif uploaded_file.name.endswith('.csv'):
        df = pd.read_csv(uploaded_file)

    st.write("**Planilha carregada com sucesso!**")
    st.dataframe(df)

    # Seletor de Período de Apuração (Mês e Ano)
    st.write("### Selecione o Período de Apuração")

    # Se a coluna 'Dias para Compensar' não existir, cria uma coluna padrão
    if 'Dias para Compensar' not in df.columns:
        df['Dias para Compensar'] = 1  # Valor padrão de 1 dia para compensar

    # Seletor para a data de início
    start_date = st.date_input("Data Início", datetime.today(), format="DD/MM/YYYY")

    # Seletor para a data de término
    default_end_date = last_business_day_of_quarter(start_date)
    end_date = st.date_input("Data Término", default_end_date, format="DD/MM/YYYY")

    # Recalcular os dias úteis sempre que as datas mudarem
    working_days = calculate_working_days(start_date, pd.Timestamp(end_date))
    total_working_days = len(working_days)

    # Preservar as seleções de dias para compensar utilizando o st.session_state
    if 'dias_para_compensar' not in st.session_state:
        st.session_state.dias_para_compensar = df['Dias para Compensar'].tolist()

    # Seletor para o número de dias desejados para a compensação
    st.write("### Selecione o número de dias para compensação")
    for i, row in df.iterrows():
        st.session_state.dias_para_compensar[i] = st.slider(f"{row['Nome do Empregado']}",
                                                            min_value=1,
                                                            max_value=total_working_days,
                                                            value=st.session_state.dias_para_compensar[i])
        df.at[i, 'Dias para Compensar'] = st.session_state.dias_para_compensar[i]

    # Distribuir as horas com equilíbrio
    df, gantt_data, kanban_data, kanban_dates = distribute_hours_equally(df, working_days)

    # Exibir a tabela com as horas sugeridas por dia e dias sugeridos
    st.write("### Sugerido de Horas por Dia")
    st.dataframe(df[['Nome do Empregado', 'Horas Totais', 'Dias para Compensar', 'Horas por Dia', 'Dias Sugeridos']],
                 width=1000)

    # Criar o gráfico de Gantt
    if len(gantt_data) > 0:
        gantt_df = pd.DataFrame(gantt_data)

        if 'Nome do Empregado' in gantt_df.columns:
            fig = px.timeline(
                gantt_df,
                x_start="Start",
                x_end="Finish",
                y="Nome do Empregado",
                title="Gráfico de Gantt - Dias de Compensação",
                color="Nome do Empregado",  # Adiciona cores diferentes para cada empregado
                text="Horas por Dia"  # Adiciona o texto das horas por dia no gráfico
            )
            fig.update_yaxes(categoryorder="total ascending")
            st.plotly_chart(fig)
        else:
            st.error("A coluna 'Nome do Empregado' não foi encontrada no DataFrame para o gráfico de Gantt.")
    else:
        st.warning("Nenhum dado disponível para gerar o gráfico de Gantt.")

    # Exibir o Kanban corretamente
    st.write("### Kanban de Dias Sugeridos")

    # Criar DataFrame Kanban com todos os empregados e datas necessárias
    kanban_df = pd.DataFrame(index=df['Nome do Empregado'].unique(), columns=kanban_dates)
    kanban_df = kanban_df.fillna('')  # Preencher com string vazia

    # Preencher o Kanban com os dados de cada dia
    for date_str, employees in kanban_data.items():
        for emp in employees:
            kanban_df.at[emp, date_str] = emp

    st.table(kanban_df)

else:
    st.write("Por favor, carregue um arquivo para iniciar.")
