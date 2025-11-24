import streamlit as st
import pandas as pd
import os

# Configuração da Página
st.set_page_config(page_title="Processador NCM", layout="wide")

st.title("Processador de Arquivos NCM/CATMAT")
st.markdown("""
Este sistema realiza a junção de arquivos CSV para processamento de NCM e CATMAT.
""")

# --- FUNÇÕES DE PROCESSAMENTO ---

def carregar_arquivo_referencia(nome_base, uploader_label):
    """
    Procura por arquivos locais (ZIP ou CSV).
    Prioriza ZIP por ser mais leve para o GitHub.
    """
    # 1. Tenta carregar versão ZIP (ex: 02-planilhaCatmat.zip)
    if os.path.exists(f"{nome_base}.zip"):
        return pd.read_csv(f"{nome_base}.zip", sep=';', dtype=str, encoding='utf-8', compression='zip')
    
    # 2. Tenta carregar versão CSV normal
    elif os.path.exists(f"{nome_base}.csv"):
        return pd.read_csv(f"{nome_base}.csv", sep=';', dtype=str, encoding='utf-8')
    
    # 3. Se não achar, pede upload manual
    else:
        uploaded = st.sidebar.file_uploader(uploader_label, type=["csv", "zip"])
        if uploaded:
            # Detecta se o usuário subiu zip ou csv
            if uploaded.name.endswith('.zip'):
                return pd.read_csv(uploaded, sep=';', dtype=str, encoding='utf-8', compression='zip')
            else:
                return pd.read_csv(uploaded, sep=';', dtype=str, encoding='utf-8')
        return None

def etapa1_unir_por_catmat(df1, df2):
    st.info("--- Iniciando Etapa 1: Junção por CATMAT ---")
    
    # Verifica colunas essenciais
    if 'CATMAT' not in df1.columns or 'Código do Item' not in df2.columns:
        st.error("Erro na Etapa 1: Colunas 'CATMAT' ou 'Código do Item' não encontradas.")
        return None

    df1['CATMAT'] = df1['CATMAT'].astype(str)
    df2['Código do Item'] = df2['Código do Item'].astype(str)

    df_merged = pd.merge(df1, df2, left_on='CATMAT', right_on='Código do Item', how='inner')
    st.write(f"Correspondências encontradas: {len(df_merged)}")

    if 'Código NCM' not in df_merged.columns:
         st.error("Erro: Coluna 'Código NCM' perdida após junção.")
         return None

    df_filtrado = df_merged[
        df_merged['Código NCM'].notna() &
        (df_merged['Código NCM'] != '') &
        (df_merged['Código NCM'].str.strip() != '-')
    ].copy()
    
    colunas_desejadas = ['ITEM', 'Descrição do Item', 'CATMAT', 'Código NCM']
    cols_existentes = [c for c in colunas_desejadas if c in df_filtrado.columns]
    
    return df_filtrado[cols_existentes]

def etapa2_unir_por_ncm(df_etapa1, df3):
    st.info("--- Iniciando Etapa 2: Junção Final por NCM ---")
    
    df_etapa1['chave_juncao'] = df_etapa1['Código NCM'].astype(str).str.replace('.', '', regex=False).str.strip()
    df3['chave_juncao'] = df3['NCM'].astype(str).str.replace('.', '', regex=False).str.strip()

    resultado = pd.merge(df_etapa1, df3, on='chave_juncao', how='inner')
    resultado = resultado.drop(columns=['chave_juncao'])
    
    if 'ITEM' in resultado.columns:
        resultado['ITEM'] = pd.to_numeric(resultado['ITEM'], errors='coerce')
        resultado = resultado.sort_values(by='ITEM')
    
    st.success(f"Processamento concluído! Linhas finais: {len(resultado)}")
    return resultado

# --- INTERFACE DO USUÁRIO ---

st.sidebar.header("Arquivos de Referência")

# O código agora procura por "02-planilhaCatmat" (seja .zip ou .csv)
df_ref_catmat = carregar_arquivo_referencia("02-planilhaCatmat", "Carregar Tabela CATMAT (csv/zip)")
df_ref_anexo = carregar_arquivo_referencia("03-anexo01", "Carregar Anexo 01 (csv/zip)")

# Status visual
if df_ref_catmat is not None:
    st.sidebar.success(f"✅ CATMAT carregado ({len(df_ref_catmat)} linhas)")
else:
    st.sidebar.warning("⚠️ Tabela CATMAT pendente")

if df_ref_anexo is not None:
    st.sidebar.success(f"✅ Anexo carregado ({len(df_ref_anexo)} linhas)")
else:
    st.sidebar.warning("⚠️ Tabela Anexo pendente")

st.header("Seu Arquivo de Dados")
user_file = st.file_uploader("Upload Arquivo de Dados", type=["csv", "zip"])

if st.button("Processar Arquivos"):
    if user_file and df_ref_catmat is not None and df_ref_anexo is not None:
        try:
            # Lê o arquivo do usuário (também aceita zip se ele quiser subir zipado)
            if user_file.name.endswith('.zip'):
                df_user = pd.read_csv(user_file, sep=';', dtype=str, encoding='utf-8', compression='zip')
            else:
                df_user = pd.read_csv(user_file, sep=';', dtype=str, encoding='utf-8')
            
            df_intermed = etapa1_unir_por_catmat(df_user, df_ref_catmat)
            
            if df_intermed is not None and not df_intermed.empty:
                df_final = etapa2_unir_por_ncm(df_intermed, df_ref_anexo)
                
                if df_final is not None:
                    st.dataframe(df_final.head())
                    csv = df_final.to_csv(sep=';', index=False, encoding='utf-8-sig').encode('utf-8-sig')
                    st.download_button(
                        label="📥 Baixar Resultado Final",
                        data=csv,
                        file_name="resultado_final_consolidado.csv",
                        mime="text/csv"
                    )
            else:
                st.warning("A Etapa 1 não gerou resultados. Verifique se os códigos CATMAT conferem.")
                
        except Exception as e:
            st.error(f"Erro ao processar: {e}")
    else:
        st.error("Faltam arquivos. Verifique a barra lateral.")