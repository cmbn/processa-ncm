import streamlit as st
import pandas as pd
import os

# Configuração da Página
st.set_page_config(page_title="Processador NCM", layout="wide")

st.title("Processador de Arquivos NCM/CATMAT")
st.markdown("""
Este sistema processa arquivos CSV para vincular NCMs baseados no CATMAT.
Agora com **Relatório de Erros** para itens não identificados.
""")

# --- FUNÇÕES DE PROCESSAMENTO ---

def carregar_arquivo_referencia(nome_base, uploader_label):
    """
    Procura por arquivos locais (ZIP ou CSV).
    Prioriza ZIP por ser mais leve para o GitHub.
    """
    if os.path.exists(f"{nome_base}.zip"):
        return pd.read_csv(f"{nome_base}.zip", sep=';', dtype=str, encoding='utf-8', compression='zip')
    elif os.path.exists(f"{nome_base}.csv"):
        return pd.read_csv(f"{nome_base}.csv", sep=';', dtype=str, encoding='utf-8')
    else:
        uploaded = st.sidebar.file_uploader(uploader_label, type=["csv", "zip"])
        if uploaded:
            if uploaded.name.endswith('.zip'):
                return pd.read_csv(uploaded, sep=';', dtype=str, encoding='utf-8', compression='zip')
            else:
                return pd.read_csv(uploaded, sep=';', dtype=str, encoding='utf-8')
        return None

def etapa1_unir_por_catmat(df1, df2):
    """
    Realiza a junção e separa sucessos de erros.
    Retorna: (df_sucesso, df_erros)
    """
    st.info("--- Iniciando Etapa 1: Junção por CATMAT ---")
    
    # Verifica colunas essenciais
    if 'CATMAT' not in df1.columns or 'Código do Item' not in df2.columns:
        st.error(f"Erro na Etapa 1: Colunas não encontradas. Seu arquivo tem: {list(df1.columns)}")
        return None, None

    # Padronização para evitar erros de texto
    df1['CATMAT'] = df1['CATMAT'].astype(str).str.strip()
    df2['Código do Item'] = df2['Código do Item'].astype(str).str.strip()

    # --- MUDANÇA: Usamos 'left' join com indicator=True para achar o que faltou ---
    df_merged = pd.merge(df1, df2, left_on='CATMAT', right_on='Código do Item', how='left', indicator=True)
    
    # 1. Identificar CATMATs não encontrados
    mask_nao_encontrado = df_merged['_merge'] == 'left_only'
    df_erros_catmat = df_merged[mask_nao_encontrado].copy()
    df_erros_catmat['Motivo_Erro'] = 'CATMAT não encontrado na base de referência'

    # 2. Filtrar os encontrados para verificar NCM
    df_encontrados = df_merged[df_merged['_merge'] == 'both'].copy()
    
    # Verifica validade do NCM (Não nulo, não vazio, não apenas traço)
    if 'Código NCM' in df_encontrados.columns:
        mask_ncm_valido = (
            df_encontrados['Código NCM'].notna() & 
            (df_encontrados['Código NCM'] != '') & 
            (df_encontrados['Código NCM'].str.strip() != '-')
        )
        
        df_sucesso = df_encontrados[mask_ncm_valido].copy()
        
        df_erros_ncm = df_encontrados[~mask_ncm_valido].copy()
        df_erros_ncm['Motivo_Erro'] = 'NCM inválido ou ausente na referência'
    else:
        # Caso raro onde a coluna sumiu
        df_sucesso = pd.DataFrame()
        df_erros_ncm = df_encontrados.copy()
        df_erros_ncm['Motivo_Erro'] = 'Coluna Código NCM inexistente'

    # Consolidar Erros
    df_erros_total = pd.concat([df_erros_catmat, df_erros_ncm])
    
    # Selecionar colunas para o relatório de erros
    colunas_erro = ['ITEM', 'CATMAT', 'Motivo_Erro']
    # Adiciona Descrição se existir, para ajudar o usuário
    if 'Descrição do Item' in df_merged.columns:
        colunas_erro.insert(2, 'Descrição do Item')
    elif 'ESPECIFICAÇÃO' in df_merged.columns: # Caso use outro nome
        colunas_erro.insert(2, 'ESPECIFICAÇÃO')

    # Garante que só pega colunas que existem
    cols_finais_erro = [c for c in colunas_erro if c in df_erros_total.columns]
    df_erros_final = df_erros_total[cols_finais_erro]

    # Selecionar colunas para o sucesso
    colunas_sucesso = ['ITEM', 'Descrição do Item', 'CATMAT', 'Código NCM']
    cols_existentes_sucesso = [c for c in colunas_sucesso if c in df_sucesso.columns]
    
    st.write(f"Itens processados com sucesso: {len(df_sucesso)}")
    st.write(f"Itens com erro/não encontrados: {len(df_erros_final)}")
    
    return df_sucesso[cols_existentes_sucesso], df_erros_final

def etapa2_unir_por_ncm(df_etapa1, df3):
    st.info("--- Iniciando Etapa 2: Junção Final por NCM ---")
    
    df_etapa1['chave_juncao'] = df_etapa1['Código NCM'].astype(str).str.replace('.', '', regex=False).str.strip()
    df3['chave_juncao'] = df3['NCM'].astype(str).str.replace('.', '', regex=False).str.strip()

    resultado = pd.merge(df_etapa1, df3, on='chave_juncao', how='inner')
    resultado = resultado.drop(columns=['chave_juncao'])
    
    if 'ITEM' in resultado.columns:
        resultado['ITEM'] = pd.to_numeric(resultado['ITEM'], errors='coerce')
        resultado = resultado.sort_values(by='ITEM')
    
    st.success(f"Processamento concluído! Linhas finais válidas: {len(resultado)}")
    return resultado

# --- INTERFACE LATERAL (ARQUIVOS FIXOS) ---

st.sidebar.header("Arquivos de Referência")
df_ref_catmat = carregar_arquivo_referencia("02-planilhaCatmat", "Carregar Tabela CATMAT (csv/zip)")
df_ref_anexo = carregar_arquivo_referencia("03-anexo01", "Carregar Anexo 01 (csv/zip)")

if df_ref_catmat is not None:
    st.sidebar.success(f"✅ CATMAT carregado ({len(df_ref_catmat)} linhas)")
else:
    st.sidebar.warning("⚠️ Tabela CATMAT pendente")

if df_ref_anexo is not None:
    st.sidebar.success(f"✅ Anexo carregado ({len(df_ref_anexo)} linhas)")
else:
    st.sidebar.warning("⚠️ Tabela Anexo pendente")

# --- INTERFACE PRINCIPAL ---

st.header("Entrada de Dados")

modo_entrada = st.radio("Como você deseja inserir os dados?", 
                        ["📁 Upload de Arquivo CSV/ZIP", "✍️ Digitar CATMATs Manualmente"])

df_user = None 

if modo_entrada == "📁 Upload de Arquivo CSV/ZIP":
    st.markdown("O arquivo deve conter colunas separadas por ponto e vírgula (;).")
    user_file = st.file_uploader("Selecione seu arquivo", type=["csv", "zip"])
    
    if user_file:
        try:
            if user_file.name.endswith('.zip'):
                df_user = pd.read_csv(user_file, sep=';', dtype=str, encoding='utf-8', compression='zip')
            else:
                df_user = pd.read_csv(user_file, sep=';', dtype=str, encoding='utf