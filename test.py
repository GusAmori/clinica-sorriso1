import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from datetime import datetime, date

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Consultório Odontológico - Nuvem",
    layout="wide",
    page_icon="🦷"
)

# --- CSS CUSTOMIZADO (Design de Dentista) ---
st.markdown("""
<style>
    .stApp { background-color: #f4f7f6; }
    .titulo-principal { color: #3498db; text-align: center; text-transform: uppercase; letter-spacing: 2px; }
    .stTabs [data-baseweb="tab-list"] { gap: 10px; background-color: #ffffff; padding: 10px; border-radius: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
    [data-testid="stForm"] { background-color: #ffffff; padding: 30px; border-radius: 20px; box-shadow: 0 10px 25px rgba(0,0,0,0.05); border: none; }
    .info-card { background-color: #ffffff; padding: 20px; border-radius: 15px; box-shadow: 0 5px 15px rgba(0,0,0,0.04); margin-bottom: 15px; border-left: 5px solid #3498db; }
    .stButton>button { background-color: #2ecc71; color: white; border-radius: 12px; width: 100%; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

st.markdown('<h1 class="titulo-principal">🦷 GESTÃO CLÍNICA DRA. ISA DE MIRANDA</h1>', unsafe_allow_html=True)

# --- CONEXÃO COM BANCO EXTERNO (SUPABASE / AZURE) ---
def get_connection():
    try:
        # Puxa a URL dos Secrets do Streamlit Cloud
        db_url = st.secrets["DB_URL"]
        engine = create_engine(db_url)
        return engine
    except Exception as e:
        st.error("⚠️ Erro de Conexão: Certifique-se de configurar o 'DB_URL' nos Secrets do Streamlit.")
        st.stop()

engine = get_connection()

tab1, tab2, tab3, tab4 = st.tabs(["📝 Novo Atendimento", "📂 Histórico Digital", "🔔 Alertas e Retornos", "⚙️ Gerenciar"])

# --- ABA 1: CADASTRO ---
with tab1:
    st.markdown("## 🆕 Registrar Novo Procedimento")
    with st.form("form_procedimento", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            nome = st.text_input("👤 Nome Completo do Paciente")
            nascimento = st.date_input("📅 Data de Nascimento", min_value=date(1920, 1, 1), format="DD/MM/YYYY")
            telefone = st.text_input("📞 Telefone (WhatsApp)")
            procedimento = st.selectbox("🦷 Procedimento", ["Limpeza", "Obturação", "Extração", "Canal", "Aparelho", "Clareamento", "Outro"])
        with col2:
            valor = st.number_input("💰 Valor Cobrado (R$)", min_value=0.0, format="%.2f")
            data_atendimento = st.date_input("📆 Data do Atendimento", value=datetime.now(), format="DD/MM/YYYY")
        
        detalhes = st.text_area("📋 Detalhes Clínicos e Observações")
        submit = st.form_submit_button("✅ SALVAR NO BANCO DE DADOS")

        if submit and nome:
            try:
                with engine.begin() as conn:
                    # SQL para PostgreSQL (Supabase)
                    res = conn.execute(
                        text("INSERT INTO Pacientes (nome, data_nascimento, telefone) VALUES (:n, :d, :t) RETURNING id_paciente"),
                        {"n": nome, "d": nascimento, "t": telefone}
                    )
                    id_paciente = res.fetchone()[0]
                    
                    conn.execute(
                        text("INSERT INTO Procedimentos (id_paciente, tipo_procedimento, valor, detalhes, data_realizacao) VALUES (:id, :tp, :v, :dt, :dr)"),
                        {"id": id_paciente, "tp": procedimento, "v": valor, "dt": detalhes, "dr": data_atendimento}
                    )
                st.balloons()
                st.success(f"Prontuário de {nome} salvo com sucesso na nuvem!")
            except Exception as e:
                st.error(f"Erro ao salvar: {e}")

# --- ABA 2: HISTÓRICO ---
with tab2:
    st.markdown("## 📂 Prontuários Registrados")
    try:
        query = "SELECT p.nome, pr.tipo_procedimento, pr.valor, pr.data_realizacao, pr.detalhes FROM Pacientes p JOIN Procedimentos pr ON p.id_paciente = pr.id_paciente ORDER BY pr.data_realizacao DESC"
        df = pd.read_sql(query, engine)
        
        if not df.empty:
            for _, row in df.iterrows():
                data_br = row['data_realizacao'].strftime('%d/%m/%Y')
                st.markdown(f"""
                    <div class="info-card">
                        <b>👨‍⚕️ {row['nome']}</b> - {row['tipo_procedimento']}<br>
                        <small>📅 Data: {data_br} | 💰 Valor: R$ {row['valor']:.2f}</small><br>
                        <p style='font-size: 0.9em; color: #555;'>{row['detalhes'] if row['detalhes'] else 'Sem observações.'}</p>
                    </div>
                """, unsafe_allow_html=True)
        else:
            st.info("Nenhum registro encontrado.")
    except Exception as e:
        st.error(f"Erro ao carregar histórico: {e}")

# --- ABA 3: ALERTAS ---
with tab3:
    st.markdown("## 🔔 Central de Notificações")
    hoje = datetime.now()
    
    col_a, col_b = st.columns(2)
    
    try:
        with engine.connect() as conn:
            with col_a:
                st.markdown("### 🎂 Aniversariantes")
                niver_q = text("SELECT nome, telefone FROM Pacientes WHERE EXTRACT(MONTH FROM data_nascimento) = :m AND EXTRACT(DAY FROM data_nascimento) = :d")
                aniversariantes = conn.execute(niver_q, {"m": hoje.month, "d": hoje.day}).fetchall()
                if aniversariantes:
                    for n in aniversariantes:
                        st.info(f"🎉 **{n[0]}**\n\n📞 {n[1]}")
                else:
                    st.write("Nenhum hoje.")

            with col_b:
                st.markdown("### 📅 Retornos (6 meses)")
                limpeza_q = text("SELECT p.nome, pr.data_realizacao FROM Pacientes p JOIN Procedimentos pr ON p.id_paciente = pr.id_paciente WHERE pr.tipo_procedimento = 'Limpeza' AND pr.data_realizacao <= CURRENT_DATE - INTERVAL '6 months'")
                retornos = conn.execute(limpeza_q).fetchall()
                if retornos:
                    for r in retornos:
                        st.warning(f"⚠️ **{r[0]}**\n\n📅 Última: {r[1].strftime('%d/%m/%Y')}")
                else:
                    st.write("Tudo em dia.")
    except Exception as e:
        st.error(f"Erro nos alertas: {e}")

# --- ABA 4: GERENCIAR ---
with tab4:
    st.markdown("## ⚙️ Manutenção")
    try:
        df_p = pd.read_sql("SELECT id_paciente, nome FROM Pacientes ORDER BY nome", engine)
        if not df_p.empty:
            lista = dict(zip(df_p['nome'], df_p['id_paciente']))
            selecionado = st.selectbox("Selecione para excluir:", options=list(lista.keys()))
            confirmar = st.checkbox("Confirmo que desejo apagar tudo deste paciente.")
            
            if st.button("❌ EXCLUIR DEFINITIVAMENTE") and confirmar:
                with engine.begin() as conn:
                    conn.execute(text("DELETE FROM Pacientes WHERE id_paciente = :id"), {"id": lista[selecionado]})
                st.success("Excluído com sucesso.")
                st.rerun()
        else:
            st.write("Sem pacientes cadastrados.")
    except Exception as e:
        st.error(f"Erro ao gerenciar: {e}")
