import streamlit as st
import pandas as pd
import os
import re
import zipfile

# Configuração da Página
st.set_page_config(page_title="Processador NCM", layout="wide")

st.title("Processador de Arquivos NCM/CATMAT")
st.markdown("""
Este sistema processa arquivos CSV para vincular NCMs baseados no CATMAT.
**Agora compatível com CSVs separados por vírgula, ponto e vírgula ou tabulação, e diversas codificações.**
""")

# --- FUNÇÕES UTILITÁRIAS ---

def ler_csv_flexivel(arquivo, compression=None):
    """
    Tenta ler um arquivo CSV/ZIP testando diferentes encodings e separadores.
    Agora com suporte avançado a ZIPs contendo pastas e múltiplos formatos.
    """
    encodings = ['utf-8', 'latin-1', 'cp1252', 'utf-8-sig', 'iso-8859-1']
    separadores = [';', ',', '\t'] # Adicionado TAB como possível separador
    
    def tentar_ler(arquivo_aberto):
        """Função interna para testar combinações de encoding e separador"""
        # Se for um buffer de arquivo (como upload do streamlit), volta o ponteiro para o início
        if hasattr(arquivo_aberto, 'seek'):
            arquivo_aberto.seek(0)
            
        for enc in encodings:
            for sep in separadores:
                try:
                    # Reseta o ponteiro a cada tentativa se for arquivo aberto
                    if hasattr(arquivo_aberto, 'seek'):
                        arquivo_aberto.seek(0)
                    
                    df = pd.read_csv(
                        arquivo_aberto, 
                        sep=sep, 
                        dtype=str, 
                        encoding=enc, 
                        on_bad_lines='skip'
                    )
                    
                    # Se tiver mais de 1 coluna, consideramos sucesso
                    if df.shape[1] > 1:
                        return df
                except Exception:
                    continue # Tenta a próxima combinação
        return None

    # LÓGICA PARA ARQUIVOS ZIP
    # Verifica se foi marcado como zip ou se o nome termina com .zip
    is_zip = compression == 'zip' or (isinstance(arquivo, str) and arquivo.lower().endswith('.zip'))
    
    if is_zip:
        try:
            # Se for string (caminho local), usa direto. Se for UploadedFile, usa ele mesmo.
            zf_source = arquivo
            
            with zipfile.ZipFile(zf_source) as z:
                # Procura arquivos válidos (.csv ou .txt) e ignora pastas de sistema do Mac (__MACOSX)
                lista_arquivos = [f for f in z.namelist() if f.lower().endswith(('.csv', '.txt')) and not '__MACOSX' in f]
                
                if not lista_arquivos:
                    raise ValueError("O arquivo ZIP não contém arquivos .csv ou .txt válidos na raiz ou subpastas.")
                
                # Pega o primeiro arquivo válido encontrado
                nome_arquivo_dentro = lista_arquivos[0]
                
                with z.open(nome_arquivo_dentro) as f:
                    df = tentar_ler(f)
                    if df is not None:
                        return df
                    else:
                        raise ValueError(f"Não foi possível ler o arquivo '{nome_arquivo_dentro}' dentro do ZIP com nenhuma codificação padrão.")
                        
        except zipfile.BadZipFile:
            raise ValueError("O arquivo fornecido não é um ZIP válido ou está corrompido.")
            
    # LÓGICA PARA ARQUIVOS CSV NORMAIS (Upload ou Local sem ser zip)
    else:
        df = tentar_ler(arquivo)
        if df is not None:
            return df

    # Se chegou aqui, falhou tudo
    raise ValueError("Falha na leitura: Não foi possível detectar o separador ou encoding correto (Tentei: UTF-8, Latin-1, CP1252 com ; , e Tab).")

# --- FUNÇÕES DE PROCESSAMENTO ---

def carregar_arquivo_referencia(nome_base, uploader_label):
    """
    Procura por arquivos locais (ZIP ou CSV) ou aceita upload, usando a leitura flexível.
    """
    df = None
    
    # 1. Tenta carregar localmente
    if os.path.exists(f"{nome_base}.zip"):
        try:
            df = ler_csv_flexivel(f"{nome_base}.zip", compression='zip')
        except Exception as e:
            st.warning(f"Erro ao tentar ler arquivo local {nome_base}.zip: {e}")
            
    elif os.path.exists(f"{nome_base}.csv"):
        try:
            df = ler_csv_flexivel(f"{nome_base}.csv")
        except Exception as e:
            st.warning(f"Erro ao tentar ler arquivo local {nome_base}.csv: {e}")
    
    # 2. Se não achou local ou falhou, pede upload
    if df is None:
        uploaded = st.sidebar.file_uploader(uploader_label, type=["csv", "zip"])
        if uploaded:
            compression_type = 'zip' if uploaded.name.endswith('.zip') else None
            try:
                df = ler_csv_flexivel(uploaded, compression=compression_type)
            except Exception as e:
                st.sidebar.error(f"Erro ao ler arquivo enviado: {e}")
                
    return df

def etapa1_unir_por_catmat(df1, df2):
    """
    Realiza a junção e separa sucessos de exceções.
    """
    st.info("--- Iniciando Etapa 1: Junção por CATMAT ---")
    
    # Padronização dos nomes das colunas para evitar erros de Case Sensitive ou espaços extras
    df1.columns = df1.columns.str.strip()
    df2.columns = df2.columns.str.strip()
    
    if 'CATMAT' not in df1.columns or 'Código do Item' not in df2.columns:
        st.error(f"Erro na Etapa 1: Colunas obrigatórias não encontradas.")
        st.write(f"Colunas do seu arquivo: {list(df1.columns)}")
        st.write(f"Colunas esperadas no arquivo de referência: 'Código do Item'. Encontradas: {list(df2.columns)}")
        return None, None

    df1['CATMAT'] = df1['CATMAT'].astype(str).str.strip()
    df2['Código do Item'] = df2['Código do Item'].astype(str).str.strip()

    # 'left' join
    df_merged = pd.merge(df1, df2, left_on='CATMAT', right_on='Código do Item', how='left', indicator=True)
    
    # 1. Identificar CATMATs não encontrados
    mask_nao_encontrado = df_merged['_merge'] == 'left_only'
    df_excecoes_catmat = df_merged[mask_nao_encontrado].copy()
    df_excecoes_catmat['Motivo_Excecao'] = 'CATMAT não encontrado na base de referência'

    # 2. Filtrar os encontrados para verificar NCM
    df_encontrados = df_merged[df_merged['_merge'] == 'both'].copy()
    
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
        df_excecoes_ncm['Motivo_Excecao'] = 'Coluna Código NCM inexistente na referência'

    df_excecoes_total = pd.concat([df_excecoes_catmat, df_excecoes_ncm])
    
    # Seleção inteligente de colunas para o relatório
    cols_possiveis = ['ITEM', 'Descrição do Item', 'ESPECIFICAÇÃO', 'CATMAT', 'Motivo_Excecao']
    cols_finais_excecao = [c for c in cols_possiveis if c in df_excecoes_total.columns]
    df_excecoes_final = df_excecoes_total[cols_finais_excecao]

    colunas_sucesso = ['ITEM', 'Descrição do Item', 'CATMAT', 'Código NCM']
    cols_existentes_sucesso = [c for c in colunas_sucesso if c in df_sucesso.columns]
    
    st.write(f"Processamento inicial: {len(df_sucesso)} itens válidos identificados.")
    
    return df_sucesso[cols_existentes_sucesso], df_excecoes_final

def etapa2_unir_por_ncm(df_etapa1, df3):
    st.info("--- Iniciando Etapa 2: Junção Final por NCM ---")
    
    # Limpeza preventiva
    df_etapa1['Código NCM'] = df_etapa1['Código NCM'].astype(str)
    df3['NCM'] = df3['NCM'].astype(str)

    df_etapa1['chave_juncao'] = df_etapa1['Código NCM'].str.replace('.', '', regex=False).str.strip()
    df3['chave_juncao'] = df3['NCM'].str.replace('.', '', regex=False).str.strip()

    resultado = pd.merge(df_etapa1, df3, on='chave_juncao', how='inner')
    resultado = resultado.drop(columns=['chave_juncao'])
    
    if 'ITEM' in resultado.columns:
        resultado['ITEM'] = pd.to_numeric(resultado['ITEM'], errors='coerce')
        resultado = resultado.sort_values(by='ITEM')
    
    st.success(f"Processamento concluído! Linhas finais válidas: {len(resultado)}")
    return resultado

# --- INTERFACE LATERAL (ARQUIVOS DE REFERÊNCIA) ---

st.sidebar.header("Arquivos de Referência")
df_ref_catmat = carregar_arquivo_referencia("02-planilhaCatmat", "Carregar Tabela CATMAT")
df_ref_anexo = carregar_arquivo_referencia("03-anexo01", "Carregar Anexo 01")

if df_ref_catmat is not None:
    st.sidebar.success(f"✅ CATMAT OK ({len(df_ref_catmat)} linhas)")
    # --- ADIÇÃO DA MENSAGEM COM LINK SOLICITADA ---
    st.sidebar.markdown(
        "[Planilha CATMAT: última modificação 21/11/2025 17h30](https://www.gov.br/compras/pt-br/acesso-a-informacao/consulta-detalhada/planilha-catmat-catser)"
    )
else:
    st.sidebar.warning("⚠️ Tabela CATMAT pendente")

if df_ref_anexo is not None:
    st.sidebar.success(f"✅ Anexo OK ({len(df_ref_anexo)} linhas)")
else:
    st.sidebar.warning("⚠️ Tabela Anexo pendente")

# --- INTERFACE PRINCIPAL ---

st.header("Entrada de Dados")

modo_entrada = st.radio("Como você deseja inserir os dados?", 
                        ["📁 Upload de Arquivo CSV/ZIP", "✍️ Digitar CATMATs Manualmente"])

df_user = None 

if modo_entrada == "📁 Upload de Arquivo CSV/ZIP":
    st.markdown("Aceita arquivos separados por **ponto e vírgula (;)**, **vírgula (,)** ou **tabulação**.")
    user_file = st.file_uploader("Selecione seu arquivo", type=["csv", "zip"])
    
    if user_file:
        try:
            compression_type = 'zip' if user_file.name.endswith('.zip') else None
            df_user = ler_csv_flexivel(user_file, compression=compression_type)
            st.success(f"Arquivo lido com sucesso! {len(df_user)} linhas identificadas.")
            with st.expander("Ver primeiras linhas do seu arquivo"):
                st.dataframe(df_user.head())
        except Exception as e:
            st.error(f"Erro ao ler arquivo. Verifique se é um CSV válido. Detalhe: {e}")

else: # Modo Digitação Manual Flexível
    st.markdown("Digite os códigos CATMAT. Você pode separar por **Enter**, **ponto e vírgula** ou **vírgula**.")
    texto_input = st.text_area("Exemplo:\n12345\n67890; 455321, 998877", height=150)
    
    if texto_input:
        # Regex poderosa: separa por ponto e vírgula, vírgula ou quebra de linha/espaço
        lista_catmats = re.split(r'[;,\n\s]+', texto_input)
        
        dados_virtuais = []
        contador_item = 1
        
        for codigo in lista_catmats:
            codigo_limpo = codigo.strip()
            # Garante que é numérico ou alfanumérico válido e ignora strings vazias
            if codigo_limpo: 
                dados_virtuais.append({
                    'ITEM': contador_item,
                    'CATMAT': codigo_limpo,
                    'Descrição do Item': 'Item Manual' 
                })
                contador_item += 1
        
        if dados_virtuais:
            df_user = pd.DataFrame(dados_virtuais)
            st.info(f"Reconhecidos {len(df_user)} códigos para processamento.")
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
                
                # --- EXIBIÇÃO: SUCESSO ---
                if df_intermed is not None and not df_intermed.empty:
                    df_final = etapa2_unir_por_ncm(df_intermed, df_ref_anexo)
                    
                    if df_final is not None and not df_final.empty:
                        sucesso_gerado = True
                        st.markdown("### ✅ Resultado Final Processado")
                        # hide_index=True oculta a coluna de índices 0, 1, 2...
                        st.dataframe(df_final, hide_index=True)
                        
                        csv = df_final.to_csv(sep=';', index=False, encoding='utf-8-sig').encode('utf-8-sig')
                        st.download_button(
                            label="📥 Baixar Resultado (.csv)",
                            data=csv,
                            file_name="resultado_processado.csv",
                            mime="text/csv"
                        )
                    else:
                        st.warning("A junção NCM (Etapa 2) não retornou resultados (nenhum NCM da Etapa 1 bateu com o Anexo).")
                
                # --- EXIBIÇÃO: EXCEÇÕES ---
                if df_excecoes is not None and not df_excecoes.empty:
                    st.divider()
                    st.warning(f"⚠️ Relatório de Exceções: {len(df_excecoes)} itens não processados.")
                    
                    with st.expander("Clique para visualizar a lista de exceções"):
                        # hide_index=True remove a coluna visual do índice (0, 1, 2...)
                        st.dataframe(df_excecoes, hide_index=True)
                    
                    csv_excecoes = df_excecoes.to_csv(sep=';', index=False, encoding='utf-8-sig').encode('utf-8-sig')
                    st.download_button(
                        label="📥 Baixar Exceções (.csv)",
                        data=csv_excecoes,
                        file_name="relatorio_excecoes.csv",
                        mime="text/csv"
                    )
                
                if not sucesso_gerado and (df_excecoes is None or df_excecoes.empty):
                     st.error("Ocorreu um erro lógico: Nenhum dado de sucesso e nenhuma exceção foram gerados. Verifique as colunas dos arquivos.")

            except Exception as e:
                st.error(f"Erro crítico durante o processamento: {e}")
                st.exception(e) # Mostra o traceback completo para debug
        else:
            st.error("❌ Faltam os arquivos de referência (CATMAT ou Anexo).")
    else:
        st.warning("⚠️ Forneça dados de entrada antes de processar.")