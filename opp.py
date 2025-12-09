import streamlit as st
import pandas as pd
import os

# Configuração da Página
st.set_page_config(page_title="Processador NCM", layout="wide")

st.title("Processador de Arquivos NCM/CATMAT")
st.markdown("""
Este sistema processa arquivos CSV para vincular NCMs baseados no CATMAT.
**Aceita arquivos separados por vírgula (,) ou ponto-e-vírgula (;).**
""")

# --- FUNÇÃO AUXILIAR DE LEITURA ---
def ler_csv_dinamico(arquivo_ou_path, is_zip=False):
    """
    Tenta ler o CSV detectando automaticamente o separador (; ou ,).
    Usa engine='python' com sep=None para auto-detecção (Sniffer).
    """
    try:
        compression_type = 'zip' if is_zip else None
        
        # sep=None com engine='python' permite que o pandas descubra o separador sozinho
        return pd.read_csv(
            arquivo_ou_path, 
            sep=None, 
            engine='python', 
            dtype=str, 
            encoding='utf-8', 
            compression=compression_type
        )
    except Exception as e:
        # Se falhar a detecção, tenta fallback para os padrões comuns
        return None

# --- FUNÇÕES DE PROCESSAMENTO ---

def carregar_arquivo_referencia(nome_base, uploader_label):
    """
    Procura por arquivos locais ou pede upload.
    Agora usa leitura dinâmica para aceitar ; ou ,
    """
    df = None
    
    # 1. Tenta carregar localmente (Prioridade ZIP, depois CSV)
    if os.path.exists(f"{nome_base}.zip"):
        df = ler_csv_dinamico(f"{nome_base}.zip", is_zip=True)
    elif os.path.exists(f"{nome_base}.csv"):
        df = ler_csv_dinamico(f"{nome_base}.csv", is_zip=False)
    
    # 2. Se não achou local, pede upload na sidebar
    if df is None:
        uploaded = st.sidebar.file_uploader(uploader_label, type=["csv", "zip"])
        if uploaded:
            is_zip_upload = uploaded.name.endswith('.zip')
            # Resetar ponteiro do arquivo caso tenha havido tentativa anterior
            uploaded.seek(0)
            df = ler_csv_dinamico(uploaded, is_zip=is_zip_upload)
            
    return df

def etapa1_unir_por_catmat(df1, df2):
    """
    Realiza a junção e separa sucessos de exceções.
    Retorna: (df_sucesso, df_excecoes)
    """
    st.info("--- Iniciando Etapa 1: Junção por CATMAT ---")
    
    if 'CATMAT' not in df1.columns or 'Código do Item' not in df2.columns:
        cols_df1 = list(df1.columns)
        st.error(f"Erro na Etapa 1: Colunas não encontradas. O arquivo carregado possui as colunas: {cols_df1}")
        return None, None

    df1['CATMAT'] = df1['CATMAT'].astype(str).str.strip()
    df2['Código do Item'] = df2['Código do Item'].astype(str).str.strip()

    df_merged = pd.merge(df1, df2, left_on='CATMAT', right_on='Código do Item', how='left', indicator=True)
    
    # 1. Identificar CATMATs não encontrados
    mask_nao_encontrado = df_merged['_merge'] == 'left_only'
    df_excecoes_catmat = df_merged[mask_nao_encontrado].copy()
    df_excecoes_catmat['Motivo_Excecao'] = 'CATMAT não encontrado na base de referência'

    # 2. Filtrar os encontrados para verificar NCM
    df_encontrados = df_merged[df_merged['_merge'] == 'both'].copy()
    
    # Verifica validade do NCM
    if 'Código NCM' in df_encontrados.columns:
        mask_ncm_valido = (
            df_encontrados['Código NCM'].notna() & 
            (df_encontrados['Código NCM'] != '') & 
            (df_encontrados['Código NCM'].str.strip() != '-')
        )
        
        df_sucesso = df_encontrados[mask_ncm_valido].copy()
        
        df_excecoes_ncm = df_encontrados[~mask_ncm_valido].copy()
        df_excecoes_ncm['Motivo_Excecao'] = 'NCM inválido ou ausente na referência'
    else:
        df_sucesso = pd.DataFrame()
        df_excecoes_ncm = df_encontrados.copy()
        df_excecoes_ncm['Motivo_Excecao'] = 'Coluna Código NCM inexistente'

    # Consolidar Exceções
    df_excecoes_total = pd.concat([df_excecoes_catmat, df_excecoes_ncm])
    
    # Selecionar colunas para o relatório de exceções
    colunas_excecao = ['ITEM', 'CATMAT', 'Motivo_Excecao']
    if 'Descrição do Item' in df_merged.columns:
        colunas_excecao.insert(2, 'Descrição do Item')
    elif 'ESPECIFICAÇÃO' in df_merged.columns:
        colunas_excecao.insert(2, 'ESPECIFICAÇÃO')

    cols_finais_excecao = [c for c in colunas_excecao if c in df_excecoes_total.columns]
    df_excecoes_final = df_excecoes_total[cols_finais_excecao]

    # Selecionar colunas para o sucesso
    colunas_sucesso = ['ITEM', 'Descrição do Item', 'CATMAT', 'Código NCM']
    cols_existentes_sucesso = [c for c in colunas_sucesso if c in df_sucesso.columns]
    
    st.write(f"Processamento inicial: {len(df_sucesso)} itens válidos identificados.")
    
    return df_sucesso[cols_existentes_sucesso], df_excecoes_final

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
    st.markdown("O arquivo pode usar **vírgula (,)** ou **ponto-e-vírgula (;)** como separador.")
    user_file = st.file_uploader("Selecione seu arquivo", type=["csv", "zip"])
    
    if user_file:
        try:
            is_zip_user = user_file.name.endswith('.zip')
            df_user = ler_csv_dinamico(user_file, is_zip=is_zip_user)
            
            if df_user is None:
                st.error("Não foi possível ler o arquivo. Verifique se é um CSV válido.")
            else:
                st.info(f"Arquivo lido com sucesso! {len(df_user)} linhas encontradas.")
                
        except Exception as e:
            st.error(f"Erro ao ler arquivo: {e}")

else: # Modo Digitação Manual
    st.markdown("Digite os códigos CATMAT separados por **vírgula (,)** ou **ponto-e-vírgula (;)**.")
    texto_input = st.text_area("Exemplo: 12345, 67890; 455321", height=100)
    
    if texto_input:
        # Normaliza: Troca tudo que for ; por , e depois divide por ,
        texto_normalizado = texto_input.replace(';', ',')
        lista_catmats = texto_normalizado.split(',')
        
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
            st.dataframe(df_user.set_index('ITEM')) 
        else:
            st.warning("Nenhum código válido identificado.")

# --- BOTÃO DE PROCESSAMENTO ---

st.divider()

if st.button("🚀 Processar Dados"):
    if df_user is not None and not df_user.empty:
        if df_ref_catmat is not None and df_ref_anexo is not None:
            try:
                # --- Executa Processamento ---
                df_intermed, df_excecoes = etapa1_unir_por_catmat(df_user, df_ref_catmat)
                
                sucesso_gerado = False
                
                if df_intermed is not None and not df_intermed.empty:
                    df_final = etapa2_unir_por_ncm(df_intermed, df_ref_anexo)
                    
                    if df_final is not None:
                        sucesso_gerado = True
                        st.markdown("### ✅ Resultado Final Processado")
                        st.markdown("Estes são os itens encontrados e prontos para uso.")
                        st.dataframe(df_final.set_index('ITEM') if 'ITEM' in df_final.columns else df_final)
                        
                        # Gera CSV de saída (Padrão: Vírgula)
                        csv = df_final.to_csv(sep=',', index=False, encoding='utf-8-sig').encode('utf-8-sig')
                        st.download_button(
                            label="📥 Baixar Resultado (.csv)",
                            data=csv,
                            file_name="resultado_processado.csv",
                            mime="text/csv"
                        )
                
                if not sucesso_gerado and (df_excecoes is None or df_excecoes.empty):
                    st.warning("O processamento não retornou dados válidos, mas também não listou exceções específicas.")

                # --- EXIBIÇÃO EXCEÇÕES ---
                if df_excecoes is not None and not df_excecoes.empty:
                    st.divider() 
                    st.warning(f"⚠️ Relatório de Exceções: {len(df_excecoes)} itens não puderam ser processados.")
                    
                    with st.expander("Clique para visualizar a lista de exceções"):
                        st.dataframe(df_excecoes.set_index('ITEM') if 'ITEM' in df_excecoes.columns else df_excecoes)
                    
                    csv_excecoes = df_excecoes.to_csv(sep=',', index=False, encoding='utf-8-sig').encode('utf-8-sig')
                    st.download_button(
                        label="📥 Baixar Exceções (.csv)",
                        data=csv_excecoes,
                        file_name="relatorio_excecoes.csv",
                        mime="text/csv"
                    )

            except Exception as e:
                st.error(f"Erro crítico durante o processamento: {e}")
        else:
            st.error("❌ Faltam os arquivos de referência (CATMAT ou Anexo). Verifique a barra lateral.")
    else:
        st.warning("⚠️ Por favor, faça o upload de um arquivo ou digite os códigos antes de processar.")