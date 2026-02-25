import streamlit as st
import pandas as pd
from datetime import datetime


# Configuração de Layout Profissional
st.set_page_config(page_title="Gestão de Crédito 360", layout="wide", initial_sidebar_state="expanded")


def clean_val(val):
    if pd.isna(val) or val == "":
        return 0.0
    s = str(val).upper().strip()
    if any(x in s for x in ["COMPARTILHA", "MATRIZ", "RETIRADO", "FALTA", "DRE", "CONTRATO"]):
        return 0.0
    s = s.replace("R$", "").replace(".", "").replace(",", ".").replace(" ", "").strip()
    try:
        return float(s)
    except Exception:
        return 0.0


@st.cache_data
def load_excel(uploaded):
    try:
        xl = pd.ExcelFile(uploaded)
        sheets = {s.upper(): s for s in xl.sheet_names}

        # localizar a aba Report (caso insensível)
        report_sheet = None
        for key in sheets:
            if "REPORT" in key or "BOLETOS" in key or "RECEB" in key:
                report_sheet = sheets[key]
                break
        if report_sheet is None and len(xl.sheet_names) > 0:
            report_sheet = xl.sheet_names[0]

        # localizar aba Limite
        limite_sheet = None
        for key in sheets:
            if "LIMITE" in key:
                limite_sheet = sheets[key]
                break
        if limite_sheet is None and len(xl.sheet_names) > 1:
            limite_sheet = xl.sheet_names[1]

        df_report = xl.parse(report_sheet)
        df_limites = xl.parse(limite_sheet) if limite_sheet else pd.DataFrame()
        return df_report, df_limites
    except Exception as e:
        st.error(f"Erro ao ler o arquivo Excel: {e}")
        return pd.DataFrame(), pd.DataFrame()


def find_consultor_column(df):
    candidates = [c for c in df.columns if any(k in str(c).upper() for k in ("CONSULTOR", "VENDEDOR", "REPRESENTANTE", "RESPONSAVEL", "AGENTE"))]
    if candidates:
        return candidates[0]
    # fallback: segunda coluna se existir
    if df.shape[1] >= 2:
        return df.columns[1]
    return None


def main():
    st.sidebar.image("https://cdn-icons-png.flaticon.com/512/5760/5760114.png", width=100)
    st.sidebar.title("Painel de Controle")
    uploaded_file = st.sidebar.file_uploader("📂 Anexe o Excel Geral aqui", type=["xlsx"])

    if not uploaded_file:
        st.warning("Por favor, anexe o arquivo Excel para iniciar o sistema.")
        st.info("O sistema lerá automaticamente as abas 'Report' e 'Limite de crédito' para gerar o CRM.")
        return

    df_report, df_limites = load_excel(uploaded_file)

    if df_report.empty:
        st.error("A aba 'Report' não foi encontrada ou está vazia.")
        return

    # Padroniza colunas
    df_report.columns = [str(c).upper().strip() for c in df_report.columns]
    df_limites.columns = [str(c).upper().strip() for c in df_limites.columns]

    # Tratamento financeiro
    if 'SALDO' in df_report.columns:
        df_report['SALDO_VAL'] = df_report['SALDO'].apply(clean_val)
    else:
        df_report['SALDO_VAL'] = 0.0

    if 'VENCIMENTO' in df_report.columns:
        df_report['VENC_DT'] = pd.to_datetime(df_report['VENCIMENTO'], errors='coerce')
    else:
        df_report['VENC_DT'] = pd.NaT

    hoje = datetime.now()
    df_report['DIAS_ATRASO'] = (hoje - df_report['VENC_DT']).dt.days.clip(lower=0)
    df_report.loc[df_report['SALDO_VAL'] <= 0, 'DIAS_ATRASO'] = 0

    # limite
    if not df_limites.empty:
        col_limite = next((c for c in df_limites.columns if 'LIMITE' in c), df_limites.columns[0])
        df_limites['LIMITE_NUM'] = df_limites[col_limite].apply(clean_val)
    else:
        df_limites = pd.DataFrame()

    # coluna cliente
    cliente_col = 'CLIENTE' if 'CLIENTE' in df_report.columns else df_report.columns[0]

    # coluna consultor (da tabela de limites)
    consultor_col = None
    if not df_limites.empty:
        consultor_col = find_consultor_column(df_limites)

    # filtro por consultor
    if consultor_col is not None and consultor_col in df_limites.columns:
        consultores = ["Todos"] + sorted(df_limites[consultor_col].dropna().unique().tolist())
    else:
        consultores = ["Todos"]

    selecionado = st.sidebar.selectbox("Filtro por Consultor", consultores)

    if selecionado != "Todos" and consultor_col is not None:
        clientes_alvo = df_limites[df_limites[consultor_col] == selecionado].iloc[:, 0].unique()
        df_final_limites = df_limites[df_limites[consultor_col] == selecionado]
        df_final_report = df_report[df_report[cliente_col].isin(clientes_alvo)]
    else:
        df_final_limites = df_limites
        df_final_report = df_report

    # consolidação
    resumo_clientes = df_final_report.groupby(cliente_col).agg({'SALDO_VAL': 'sum', 'DIAS_ATRASO': 'max'}).reset_index()
    if not df_final_limites.empty:
        df_analise = pd.merge(resumo_clientes, df_final_limites, left_on=cliente_col, right_on=df_final_limites.columns[0], how='left')
        df_analise['LIMITE_NUM'] = df_analise.get('LIMITE_NUM', 0.0).fillna(0.0)
    else:
        df_analise = resumo_clientes.copy()
        df_analise['LIMITE_NUM'] = 0.0

    df_analise['SALDO_DISPONIVEL'] = df_analise['LIMITE_NUM'] - df_analise['SALDO_VAL']

    # Navegação
    aba1, aba2, aba3 = st.tabs(["📊 Dashboard Geral", "📑 Boletos em Aberto", "💳 Controle de Limites"])

    with aba1:
        st.subheader(f"Análise de Risco - Consultor: {selecionado}")
        c1, c2, c3, c4 = st.columns(4)

        total_carteira = df_final_report['SALDO_VAL'].sum()
        vencido = df_final_report[df_final_report['DIAS_ATRASO'] > 0]['SALDO_VAL'].sum()
        estourados = int((df_analise['SALDO_DISPONIVEL'] < 0).sum())

        c1.metric("Saldo em Aberto", f"R$ {total_carteira:,.2f}")
        delta_pct = f"{(vencido/total_carteira*100):.1f}%" if total_carteira > 0 else "0%"
        c2.metric("Saldo Vencido", f"R$ {vencido:,.2f}", delta=delta_pct, delta_color="inverse")
        c3.metric("Clientes c/ Limite Estourado", estourados)
        c4.metric("Limite Total Concedido", f"R$ {df_analise['LIMITE_NUM'].sum():,.2f}")

        st.markdown("---")
        st.write("### Distribuição de Atrasos (Aging)")
        aging = df_final_report[df_final_report['DIAS_ATRASO'] > 0].groupby('DIAS_ATRASO')['SALDO_VAL'].sum()
        if not aging.empty:
            st.bar_chart(aging)
        else:
            st.info("Nenhum título vencido para exibir.")

    with aba2:
        st.subheader("Lista Completa de Boletos (Report)")
        cols_show = [col for col in [cliente_col, 'NF', 'VENCIMENTO', 'SALDO', 'DIAS_ATRASO'] if col in df_final_report.columns]
        st.dataframe(df_final_report[cols_show], use_container_width=True)

    with aba3:
        st.subheader("Gestão de Crédito e CRM")
        for _, row in df_analise.iterrows():
            disponivel = row['SALDO_DISPONIVEL']
            status_label = '⚠️ BLOQUEADO' if disponivel < 0 else '✅ OK'
            with st.expander(f"🏢 {row[cliente_col]} | Status: {status_label}"):
                col_left, col_right = st.columns(2)
                with col_left:
                    st.write(f"**CNPJ:** {row.get('CNPJ', 'Não informado')}")
                    st.write(f"**Consultor:** {selecionado if selecionado != 'Todos' else 'Vários'}")
                    st.metric("Limite de Crédito", f"R$ {row['LIMITE_NUM']:,.2f}")
                with col_right:
                    st.metric("Saldo Devedor Atual", f"R$ {row['SALDO_VAL']:,.2f}")
                    st.metric("Disponível", f"R$ {disponivel:,.2f}", delta=(f"Estourado em R$ {abs(disponivel):,.2f}" if disponivel < 0 else None))
                st.write("---")
                st.write("**Histórico de Títulos:**")
                hist_cols = [col for col in ['NF', 'VENCIMENTO', 'SALDO', 'DIAS_ATRASO'] if col in df_final_report.columns]
                st.table(df_final_report[df_final_report[cliente_col] == row[cliente_col]][hist_cols])


if __name__ == '__main__':
    main()
