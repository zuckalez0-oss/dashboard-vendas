# dashboard.py

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import folium
from streamlit_folium import st_folium
from groq import Groq
import random
import re
from datetime import datetime, timedelta

# =============================================================================
# 1. CONFIGURAÇÃO DA PÁGINA E ESTILO
# =============================================================================
st.set_page_config(
    page_title="Dashboard de Vendas de Aço",
    page_icon="🏗️",
    layout="wide"
)

# CSS customizado para polir o design
st.markdown("""
<style>
    /* Estilo para abas */
    button[data-baseweb="tab"] {
        font-size: 16px; font-weight: bold; background-color: transparent;
        border-radius: 8px 8px 0 0; padding: 10px 15px;
    }
    button[data-baseweb="tab"][aria-selected="true"] {
        background-color: #1C1F26; border-bottom: 2px solid #FFA500;
    }
    /* Estiliza os containers de métricas */
    div[data-testid="metric-container"] {
        background-color: #1C1F26; border: 1px solid #2e333d;
        padding: 15px; border-radius: 10px; color: white;
    }
    /* Garante que o contêiner do formulário use o tema escuro */
    .stForm {
        background-color: #1C1F26; padding: 20px; border-radius: 10px;
    }
</style>
""", unsafe_allow_html=True)


# =============================================================================
# 2. FUNÇÕES, DADOS E INICIALIZAÇÃO
# =============================================================================
def gerar_cnpj():
    """Gera um número de CNPJ fictício formatado."""
    return f"{random.randint(10,99)}.{random.randint(100,999)}.{random.randint(100,999)}/0001-{random.randint(10,99)}"

@st.cache_resource
def get_groq_client():
    """Retorna um cliente Groq, usando cache."""
    try:
        return Groq(api_key=st.secrets["GROQ_API_KEY"])
    except Exception:
        return None

def gerar_dados_ficticios_corrigidos():
    """Gera dados com lógica de faturamento e carregamento realistas."""
    clientes_data = {'Construtora Alfa': ('São Paulo', -23.5505, -46.6333, gerar_cnpj(), 'Sim'), 'Metalúrgica Beta': ('Rio de Janeiro', -22.9068, -43.1729, gerar_cnpj(), 'Sim'), 'Serralheria Gama': ('Belo Horizonte', -19.9167, -43.9345, gerar_cnpj(), 'Não'), 'Engenharia Delta': ('Curitiba', -25.4284, -49.2733, gerar_cnpj(), 'Sim'), 'Estruturas Épsilon': ('Porto Alegre', -30.0346, -51.2177, gerar_cnpj(), 'Sim')}
    df_clientes = pd.DataFrame.from_dict(clientes_data, orient='index', columns=['Cidade', 'Latitude', 'Longitude', 'CNPJ', 'Contribuinte'])
    df_clientes.index.name = 'Cliente'
    df_clientes.reset_index(inplace=True)
    
    produtos = ['Viga W', 'Viga I', 'Cantoneira L', 'Barra Chata', 'Tubo Quadrado', 'Tubo Redondo', 'Perfil U']
    vendas_data = []
    lista_clientes_nomes = df_clientes['Cliente'].tolist()
    
    for i in range(200):
        data_venda = pd.to_datetime(np.random.choice(pd.date_range(start='2024-01-01', end=datetime.now() - timedelta(days=15))))
        data_faturamento, data_carregamento = None, None
        if random.random() < 0.9:
            data_faturamento = data_venda + timedelta(days=random.randint(1, 5))
            if random.random() < 0.8:
                data_carregamento = data_faturamento + timedelta(days=random.randint(1, 10))
        
        vendas_data.append({'ID_Venda': 1000 + i, 'Data_Venda': data_venda, 'Produto': random.choice(produtos), 'Cliente': random.choice(lista_clientes_nomes), 'Quantidade (Ton)': round(random.uniform(1, 15), 2), 'Valor (R$)': round(random.uniform(5000, 75000), 2), 'Data_Faturamento': data_faturamento, 'Data_Carregamento': data_carregamento})
    df_vendas = pd.DataFrame(vendas_data)
    return df_clientes, df_vendas

# Inicialização do session_state
if 'dados_carregados' not in st.session_state:
    st.session_state.df_clientes, st.session_state.df_vendas = gerar_dados_ficticios_corrigidos()
    st.session_state.dados_carregados = True
    st.session_state.prospects = []

client = get_groq_client()
perfis_lista = ['Viga W', 'Viga I', 'Cantoneira L', 'Barra Chata', 'Perfil U', 'Tubo Quadrado']
telhas_lista = ['Telha Trapézio 25 (TR-25)', 'Telha Trapézio 40 (TR-40)', 'Telha Trapézio 100 (TR-100)']
tipos_corte_material = ['Aço Carbono A36', 'Aço Inoxidável 304', 'Alumínio Naval 5052']


# =============================================================================
# 3. BARRA LATERAL (SIDEBAR)
# =============================================================================
st.sidebar.image("https://i.imgur.com/7b2n3sC.png", width=150)
st.sidebar.title("Filtros e Ferramentas")

st.sidebar.subheader("Filtro de Período")
anos_disponiveis = ["Todos"] + sorted(st.session_state.df_vendas['Data_Venda'].dt.year.unique(), reverse=True)
ano_selecionado = st.sidebar.selectbox("Ano:", anos_disponiveis)
meses_nomes = ["Todos", "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
mes_selecionado_nome = st.sidebar.selectbox("Mês:", meses_nomes)

df_vendas_filtrado_global = st.session_state.df_vendas.copy()
if ano_selecionado != "Todos":
    df_vendas_filtrado_global = df_vendas_filtrado_global[df_vendas_filtrado_global['Data_Venda'].dt.year == ano_selecionado]
if mes_selecionado_nome != "Todos":
    mes_num = meses_nomes.index(mes_selecionado_nome)
    df_vendas_filtrado_global = df_vendas_filtrado_global[df_vendas_filtrado_global['Data_Venda'].dt.month == mes_num]

st.sidebar.subheader("Filtro de Clientes")
clientes_disponiveis_filtrados = df_vendas_filtrado_global['Cliente'].unique()
clientes_selecionados = st.sidebar.multiselect("Selecione Clientes:", options=clientes_disponiveis_filtrados, default=list(clientes_disponiveis_filtrados))
df_vendas_final = df_vendas_filtrado_global[df_vendas_filtrado_global['Cliente'].isin(clientes_selecionados)]
df_clientes_final = st.session_state.df_clientes[st.session_state.df_clientes['Cliente'].isin(clientes_selecionados)]

st.sidebar.markdown("---")

with st.sidebar.expander("🤖 IA para Prospecção de Clientes", expanded=True):
    localidade_pesquisa = st.text_input("Digite cidade/estado para prospecção:", "Campinas, SP")
    if st.button("Buscar Novos Clientes", use_container_width=True):
        if not client:
            st.error("A chave da API da Groq não está configurada.")
        else:
            with st.spinner("A IA está buscando..."):
                prompt = f"""Atue como um assistente de vendas sênior para uma distribuidora de aço. Sua tarefa é encontrar 3 potenciais clientes reais na região de {localidade_pesquisa}. Foque em construtoras, metalúrgicas ou engenharias de estruturas. Para cada cliente, forneça: NOME, DESCRIÇÃO, LATITUDE e LONGITUDE. Retorne os dados estritamente no formato: - (NOME; DESCRIÇÃO; LATITUDE; LONGITUDE). Exemplo: - (Gerdau Aços Longos; Produz aço para construção civil; -23.55; -46.63)"""
                try:
                    chat_completion = client.chat.completions.create(messages=[{"role": "user", "content": prompt}], model="llama3-8b-8192")
                    response_text = chat_completion.choices[0].message.content
                    st.session_state.prospects = []
                    pattern = r'-\s*\((.*?);\s*(.*?);\s*(-?\d+\.?\d+);\s*(-?\d+\.?\d+)\)'
                    matches = re.findall(pattern, response_text)
                    if matches:
                        for match in matches:
                            st.session_state.prospects.append({"nome": match[0].strip(), "desc": match[1].strip(), "lat": float(match[2]), "lon": float(match[3])})
                        st.success(f"{len(st.session_state.prospects)} prospects encontrados! Veja-os na aba 'Mapa Geográfico'.")
                        st.rerun()
                    else:
                        st.warning("Não foi possível extrair os dados da resposta da IA.")
                except Exception as e:
                    st.error(f"Ocorreu um erro: {e}")

# =============================================================================
# 4. ESTRUTURA PRINCIPAL COM ABAS
# =============================================================================
st.title("🏗️ Dashboard de Vendas de Aço Estrutural")

tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Visão Geral", "🗺️ Mapa Geográfico", "👥 Gestão de Clientes", "🏷️ Análise de Preços", "⚙️ Serviços de Corte"])

with tab1:
    st.header("Análise de Performance de Vendas e Logística")
    with st.container(border=True):
        total_faturado = df_vendas_final[df_vendas_final['Data_Faturamento'].notna()]['Valor (R$)'].sum()
        total_carregado = df_vendas_final[df_vendas_final['Data_Carregamento'].notna()]['Valor (R$)'].sum()
        toneladas_vendidas = df_vendas_final[df_vendas_final['Data_Faturamento'].notna()]['Quantidade (Ton)'].sum()
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Faturado", f"R$ {total_faturado:,.2f}")
        col2.metric("Total Carregado", f"R$ {total_carregado:,.2f}")
        col3.metric("Total de Toneladas Faturadas", f"{toneladas_vendidas:,.2f} Ton")

    st.markdown("---")
    st.subheader("Últimas Transações Faturadas")
    ultimas_vendas = df_vendas_final[df_vendas_final['Data_Faturamento'].notna()].sort_values(by='Data_Faturamento', ascending=False).head(5)
    if ultimas_vendas.empty:
        st.info("Nenhuma venda faturada encontrada no período selecionado.")
    else:
        for _, venda in ultimas_vendas.iterrows():
            col1, col2, col3 = st.columns([1, 2, 1])
            with col1: st.text(venda['Data_Faturamento'].strftime('%d/%m/%Y'))
            with col2: st.text(f"{venda['Cliente']} - {venda['Produto']}")
            with col3: st.markdown(f"<p style='text-align: right; color: #28a745; font-weight: bold;'>R$ {venda['Valor (R$)']:,.2f}</p>", unsafe_allow_html=True)
        st.markdown("<hr style='margin-top: 0; margin-bottom: 0;'>", unsafe_allow_html=True)

    st.markdown("---")
    df_vendas_final['Mes_Faturamento'] = pd.to_datetime(df_vendas_final['Data_Faturamento']).dt.to_period('M').astype(str)
    col_graf1, col_graf2 = st.columns(2)
    with col_graf1:
        st.subheader("Vendas Faturadas por Mês")
        vendas_faturadas = df_vendas_final[df_vendas_final['Mes_Faturamento'] != 'NaT'].groupby('Mes_Faturamento')['Valor (R$)'].sum().reset_index()
        fig_faturado = px.bar(vendas_faturadas, x='Mes_Faturamento', y='Valor (R$)', text_auto=True, color_discrete_sequence=['#FFA500'])
        fig_faturado.update_traces(texttemplate='%{y:.2s}', textposition='outside')
        fig_faturado.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font_color='white', uniformtext_minsize=8, uniformtext_mode='hide')
        st.plotly_chart(fig_faturado, use_container_width=True)
        
    with col_graf2:
        st.subheader("Toneladas Carregadas por Produto")
        vendas_carregadas = df_vendas_final[df_vendas_final['Data_Carregamento'].notna()].groupby('Produto')['Quantidade (Ton)'].sum().reset_index()
        if not vendas_carregadas.empty:
            fig_carregado = px.pie(vendas_carregadas, names='Produto', values='Quantidade (Ton)', hole=.4, color_discrete_sequence=px.colors.sequential.Oranges_r)
            fig_carregado.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font_color='white')
            st.plotly_chart(fig_carregado, use_container_width=True)
        else:
            st.info("Nenhum produto carregado no período selecionado.")

# ### INÍCIO DO CÓDIGO CORRIGIDO E APRIMORADO PARA A ABA DO MAPA ###
with tab2:
    st.header("🗺️ Mapa Geográfico de Clientes e Prospects")
    st.info("Visualize a localização dos seus clientes atuais (laranja) e dos prospects encontrados pela IA (verde).")
    
    # Lógica de centralização robusta
    all_coords = []
    # Adiciona coordenadas de clientes válidas
    for _, row in df_clientes_final.iterrows():
        # Verifica se lat/lon não são 0 e são números válidos
        if pd.notna(row['Latitude']) and pd.notna(row['Longitude']) and row['Latitude'] != 0.0:
            all_coords.append([row['Latitude'], row['Longitude']])
            
    # Adiciona coordenadas de prospects
    for prospect in st.session_state.get('prospects', []):
        all_coords.append([prospect['lat'], prospect['lon']])

    if not all_coords:
        # Ponto padrão (São Paulo) se não houver coordenadas
        lat_center, lon_center = -23.55, -46.64
        zoom_start = 8
        st.warning("Nenhum cliente ou prospect com coordenadas válidas para exibir no mapa.")
    else:
        # Calcula o centro a partir de todos os pontos
        mean_lat = np.mean([coord[0] for coord in all_coords])
        mean_lon = np.mean([coord[1] for coord in all_coords])
        lat_center, lon_center = mean_lat, mean_lon
        zoom_start = 6

    # Cria o objeto do mapa com o novo tema claro
    mapa = folium.Map(location=[lat_center, lon_center], zoom_start=zoom_start, tiles="CartoDB positron")
    
    # Adiciona marcadores de clientes ao mapa
    for _, row in df_clientes_final.iterrows():
        if pd.notna(row['Latitude']) and pd.notna(row['Longitude']) and row['Latitude'] != 0.0:
            folium.Marker([row['Latitude'], row['Longitude']], popup=f"<b>Cliente:</b> {row['Cliente']}", tooltip=row['Cliente'], icon=folium.Icon(color="orange", icon="industry", prefix="fa")).add_to(mapa)
    
    # Adiciona marcadores de prospects ao mapa
    for prospect in st.session_state.get('prospects', []):
        folium.Marker([prospect['lat'], prospect['lon']], popup=f"<b>Prospect:</b> {prospect['nome']}<br>{prospect['desc']}", tooltip=prospect['nome'], icon=folium.Icon(color="green", icon="star", prefix="fa")).add_to(mapa)
    
    # Renderiza o mapa no Streamlit
    st_folium(mapa, use_container_width=True, height=600)
# ### FIM DO CÓDIGO CORRIGIDO PARA A ABA DO MAPA ###

with tab3:
    st.header("Informações Detalhadas dos Clientes")
    with st.expander("➕ Adicionar Novo Cliente"):
        with st.form("novo_cliente_form", clear_on_submit=True):
            novo_cliente_nome = st.text_input("Nome da Empresa")
            novo_cliente_cnpj = st.text_input("CNPJ", value=gerar_cnpj())
            novo_cliente_cidade = st.text_input("Cidade")
            col_lat, col_lon = st.columns(2)
            novo_cliente_lat = col_lat.number_input("Latitude", format="%.4f")
            novo_cliente_lon = col_lon.number_input("Longitude", format="%.4f")
            novo_cliente_contrib = st.radio("É Contribuinte?", ('Sim', 'Não'), horizontal=True)
            submitted = st.form_submit_button("Adicionar Cliente", use_container_width=True)
            if submitted:
                if novo_cliente_nome:
                    novo_cliente_df = pd.DataFrame([{'Cliente': novo_cliente_nome, 'Cidade': novo_cliente_cidade, 'Latitude': novo_cliente_lat, 'Longitude': novo_cliente_lon, 'CNPJ': novo_cliente_cnpj, 'Contribuinte': novo_cliente_contrib}])
                    st.session_state.df_clientes = pd.concat([st.session_state.df_clientes, novo_cliente_df], ignore_index=True)
                    st.success(f"Cliente '{novo_cliente_nome}' adicionado!")
                    st.rerun()
                else:
                    st.error("O nome da empresa é obrigatório.")
    st.markdown("---")
    df_vendas_com_faturamento = df_vendas_final[df_vendas_final['Data_Faturamento'].notna()]
    if not df_vendas_com_faturamento.empty:
        vendas_totais = df_vendas_com_faturamento.groupby('Cliente')['Valor (R$)'].sum().reset_index().rename(columns={'Valor (R$)': 'Valor Total Vendas'})
        ultima_venda = df_vendas_com_faturamento.sort_values(by='Data_Faturamento', ascending=False).drop_duplicates('Cliente')[['Cliente', 'Data_Faturamento', 'Valor (R$)']].rename(columns={'Data_Faturamento': 'Data Última Venda', 'Valor (R$)': 'Valor Última Venda'})
        df_display = pd.merge(df_clientes_final, vendas_totais, on='Cliente', how='left').merge(ultima_venda, on='Cliente', how='left')
        df_display.fillna({'Valor Total Vendas': 0, 'Valor Última Venda': 0}, inplace=True)
        st.subheader("Lista de Clientes Atuais")
        st.dataframe(df_display, use_container_width=True, hide_index=True, column_config={"Valor Total Vendas": st.column_config.NumberColumn(format="R$ %.2f"), "Valor Última Venda": st.column_config.NumberColumn(format="R$ %.2f"), "Data Última Venda": st.column_config.DateColumn(format="DD/MM/YYYY")})
    else:
        st.warning("Nenhum dado de venda faturada encontrado no período.")
        st.dataframe(df_clientes_final, use_container_width=True, hide_index=True)

with tab4:
    st.header("Análise de Preços de Mercado (Simulação com IA)")
    st.info("Selecione os filtros para que a IA simule o preço de mercado por KG para o item desejado.", icon="🤖")
    with st.form("pricing_form_detalhada"):
        col1, col2 = st.columns(2)
        with col1:
            tipo_produto = st.selectbox("Tipo de Produto:", ["Perfis Estruturais", "Telhas Metálicas"])
            regiao_pesquisa = st.text_input("Região para Análise:", "Região Metropolitana de São Paulo")
        with col2:
            if tipo_produto == "Perfis Estruturais":
                produto_especifico = st.selectbox("Selecione o Perfil:", perfis_lista)
                espessura = st.slider("Espessura (mm):", 2.0, 25.4, 6.35, 0.1, format="%.2f mm")
            else:
                produto_especifico = st.selectbox("Selecione a Telha:", telhas_lista)
                espessura = st.slider("Espessura (mm):", 0.35, 0.95, 0.50, 0.01, format="%.2f mm")
        submit_pricing = st.form_submit_button("Analisar Preços de Mercado", use_container_width=True)
    if submit_pricing:
        if not client: st.error("Chave da API Groq não configurada.")
        else:
            with st.spinner(f"Analisando o mercado..."):
                prompt_pricing = f"""Atue como um analista de preços sênior do setor siderúrgico. Sua tarefa é fornecer uma estimativa de preço para o seguinte item: - Produto: {produto_especifico} - Espessura: {espessura:.2f} mm - Região de Venda: {regiao_pesquisa}. O relatório deve conter: 1. **Preço Estimado por KG:** Uma faixa de preço realista em Reais por quilograma (R$/kg). 2. **Principais Fatores de Influência:** Liste 3 a 4 fatores que impactam esse preço. 3. **Comentário de Mercado:** Um parágrafo curto com sua análise sobre a tendência. Formate a resposta de forma clara e profissional usando Markdown."""
                try:
                    chat_completion = client.chat.completions.create(messages=[{"role": "user", "content": prompt_pricing}], model="llama3-8b-8192")
                    st.markdown("---"); st.subheader(f"Relatório de Mercado: {produto_especifico} ({espessura:.2f}mm)"); st.markdown(chat_completion.choices[0].message.content)
                except Exception as e: st.error(f"Erro na análise: {e}")

with tab5:
    st.header("Orçamento de Serviços de Corte (Plasma/Laser/Oxicorte)")
    st.info("Preencha os dados da peça para que a IA simule um orçamento de corte.", icon="🤖")
    with st.form("corte_form"):
        st.subheader("Parâmetros da Peça")
        col1, col2, col3 = st.columns(3)
        with col1:
            material_corte = st.selectbox("Material:", tipos_corte_material)
            espessura_corte = st.slider("Espessura (mm):", 0.5, 50.8, 12.7, 0.1, format="%.2f mm")
        with col2:
            comprimento_corte = st.number_input("Comprimento de Corte (mm):", 100, value=2000)
            furos_inicios = st.number_input("Nº de Furos / Inícios:", 1, value=10)
        with col3:
            quantidade = st.number_input("Quantidade de Peças:", 1, value=1)
        submit_corte = st.form_submit_button("Gerar Orçamento Simulado", use_container_width=True)
    if submit_corte:
        if not client: st.error("Chave da API Groq não configurada.")
        else:
            with st.spinner("A IA está calculando o orçamento..."):
                prompt_corte = f"""Atue como um orçamentista de serviços de corte. Calcule o preço para UMA ÚNICA PEÇA com as seguintes especificações: - Material: {material_corte} - Espessura: {espessura_corte:.2f} mm - Comprimento de Corte: {comprimento_corte} mm - Furos: {furos_inicios}. Forneça uma análise de custos e, o mais importante, termine sua resposta com a linha 'PREÇO UNITÁRIO ESTIMADO: R$ XX.XX', substituindo XX.XX pelo valor numérico final."""
                try:
                    chat_completion = client.chat.completions.create(messages=[{"role": "user", "content": prompt_corte}], model="llama3-8b-8192")
                    resposta_ia = chat_completion.choices[0].message.content
                    st.markdown("---"); st.subheader("Análise de Custo da IA"); st.markdown(resposta_ia)
                    preco_unitario_match = re.search(r'R\$\s*(\d+\.?\d*,\d+|\d+,\d+|\d+\.?\d*)', resposta_ia)
                    if preco_unitario_match:
                        preco_str = preco_unitario_match.group(1).replace('.', '').replace(',', '.')
                        preco_unitario = float(preco_str)
                        valor_total = preco_unitario * quantidade
                        st.markdown("---"); st.subheader("Resumo do Orçamento")
                        col_res1, col_res2, col_res3 = st.columns(3)
                        col_res1.metric("Preço Unitário Estimado (IA)", f"R$ {preco_unitario:,.2f}")
                        col_res2.metric("Quantidade Solicitada", f"{quantidade} pç(s)")
                        col_res3.metric("VALOR TOTAL DO PEDIDO", f"R$ {valor_total:,.2f}")
                    else:
                        st.warning("Não foi possível extrair o preço unitário da resposta da IA.")
                except Exception as e:
                    st.error(f"Erro no orçamento: {e}")
