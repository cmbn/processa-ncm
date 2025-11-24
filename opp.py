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
    st.info("--- Iniciando Etapa 1: Junção por CATMAT ---")
    
    if 'CATMAT' not in df1.columns or 'Código do Item' not in df2.columns:
        st.error(f"Erro na Etapa 1: Colunas não encontradas. Seu arquivo tem: {list(df1.columns)}")
        return None

    df1['CATMAT'] = df1['CATMAT'].astype(str).str.strip()
    df2['Código do Item'] = df2['Código do Item'].astype(str).str.strip()

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
                df_user = pd.read_csv(user_file, sep=';', dtype=str, encoding='utf-8')
        except Exception as e:
            st.error(f"Erro ao ler arquivo: {e}")

else: # Modo Digitação Manual
    st.markdown("Digite os códigos CATMAT separados por **ponto e vírgula (;)**.")
    texto_input = st.text_area("Exemplo: 12345; 67890; 455321", height=100)
    
    if texto_input:
        lista_catmats = texto_input.split(';')
        dados_virtuais = []
        
        contador_item = 1
        for codigo in lista_catmats:
            codigo_limpo = codigo.strip()
            if codigo_limpo: 
                dados_virtuais.append({
                    'ITEM': contador_item,
                    'CATMAT': codigo_limpo,
                    'Descrição do Item': 'Item Inserido Manualmente' 
                })
                contador_item += 1
        
        if dados_virtuais:
            df_user = pd.DataFrame(dados_virtuais)
            st.info(f"Reconhecidos {len(df_user)} códigos para processamento.")
            
            # --- MUDANÇA AQUI: set_index('ITEM') esconde a coluna 0, 1, 2 ---
            st.dataframe(df_user.set_index('ITEM')) 
        else:
            st.warning("Nenhum código válido identificado.")

# --- BOTÃO DE PROCESSAMENTO ---

st.divider()

if st.button("🚀 Processar Dados"):
    if df_user is not None and not df_user.empty:
        if df_ref_catmat is not None and df_ref_anexo is not None:
            try:
                df_intermed = etapa1_unir_por_catmat(df_user, df_ref_catmat)
                
                if df_intermed is not None and not df_intermed.empty:
                    df_final = etapa2_unir_por_ncm(df_intermed, df_ref_anexo)
                    
                    if df_final is not None:
                        # Também apliquei o filtro visual no resultado final para ficar limpo
                        st.dataframe(df_final.set_index('ITEM') if 'ITEM' in df_final.columns else df_final)
                        
                        csv = df_final.to_csv(sep=';', index=False, encoding='utf-8-sig').encode('utf-8-sig')
                        st.download_button(
                            label="📥 Baixar Resultado Final (.csv)",
                            data=csv,
                            file_name="resultado_processado.csv",
                            mime="text/csv"
                        )
                else:
                    st.warning("⚠️ Nenhum dos CATMATs informados foi encontrado na base de dados de referência.")
            except Exception as e:
                st.error(f"Erro durante o processamento: {e}")
        else:
            st.error("❌ Faltam os arquivos de referência (CATMAT ou Anexo). Verifique a barra lateral.")
    else:
        st.warning("⚠️ Por favor, faça o upload de um arquivo ou digite os códigos antes de processar.")