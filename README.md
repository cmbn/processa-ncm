
Guia para Execução do Script processar_ncm.py no Windows
Este guia detalha todos os passos necessários para preparar seu computador e executar o script de processamento de arquivos CSV.
Parte 1: Preparação do Ambiente
Antes de executar o script, você precisa garantir que o Python e a biblioteca necessária (pandas) estejam instalados.
1. Instalação do Python no Windows
Se você ainda não tem o Python instalado, siga estes passos:
    • Acesse o site oficial: Abra seu navegador e vá para python.org.
    • Baixe o instalador: O site geralmente detecta seu sistema operacional (Windows) e sugere a versão mais recente. Clique no botão de download.
    • Execute o instalador:
        ◦ Abra o arquivo que você baixou.
        ◦ MUITO IMPORTANTE: Na primeira tela da instalação, marque a caixa que diz "Add Python to PATH" ou "Adicionar Python ao PATH". Isso é crucial para que você possa executar o Python a partir de qualquer pasta no sistema.
        ◦ Clique em "Install Now" e siga as instruções até a conclusão.
    • Verifique a instalação:
        ◦ Abra o menu Iniciar, digite cmd e pressione Enter para abrir o Prompt de Comando.
        ◦ Digite o comando python --version e pressione Enter. Se a instalação foi bem-sucedida, você verá a versão do Python instalada (ex: Python 3.11.5).
2. Instalação da Biblioteca pandas
O script utiliza uma biblioteca chamada pandas para manipular os dados dos arquivos CSV. Para instalá-la:
    • Abra um novo Prompt de Comando (cmd).
    • Digite o seguinte comando e pressione Enter:
    • pip install pandas
    • Aguarde a conclusão do download e da instalação. pip é o gerenciador de pacotes do Python, que cuida da instalação de bibliotecas para você.
Parte 2: Organização dos Arquivos
Para que o script funcione corretamente, todos os arquivos necessários devem estar na mesma pasta.
    • Crie uma pasta: Crie uma nova pasta em um local de fácil acesso (por exemplo, na sua Área de Trabalho ou em C:\) e dê a ela um nome simples, como Processamento_NCM.
    • Mova os arquivos para a pasta: Coloque os seguintes arquivos dentro desta pasta recém-criada:
        1. O script Python: processar_ncm.py
        2. O primeiro arquivo de dados que você deseja processar (ex: meusdados01.csv).
        3. O arquivo de CATMAT e NCM: 02-planilhaCatmat.csv
        4. O arquivo anexo para a junção final: 03-anexo01.csv
Ao final, sua pasta deve ter uma estrutura parecida com esta:
Processamento_NCM/
|
|--- processar_ncm.py
|--- meusdados01.csv        <-- (ou o nome do seu arquivo de dados principal)
|--- 02-planilhaCatmat.csv
|--- 03-anexo01.csv

Parte 3: Execução do Script
Agora que tudo está preparado, você pode executar o script.
1. Abra o Prompt de Comando na Pasta Correta
    • Abra a pasta Processamento_NCM que você criou.
    • Clique na barra de endereço na parte superior da janela (onde aparece o caminho da pasta, ex: C:\Users\SeuUsuario\Desktop\Processamento_NCM).
    • Delete o texto que está lá, digite cmd e pressione Enter.
    • Isso abrirá o Prompt de Comando diretamente no diretório correto, o que é fundamental para o script encontrar os arquivos.
2. Rode o Script
    • Na janela do Prompt de Comando que se abriu, digite o seguinte comando e pressione Enter:
    • python processar_ncm.py
    • O script começará a ser executado e solicitará o nome do arquivo .CSV (separador ‘;’) com seus dados. Responda e pressione Enter.
        ◦ Se o arquivo a ser processado for do tipo “NÃO TIC”, você deve baixar a aba “Tabela para exportar para TR” como .CSV separado por ponto-e-vírgula (;) e apagar as colunas ocultas ‘Grupo’ e ‘Forma de Apresentação’. Então o sistema será capaz de processar o seu arquivo de dados. O diretório do código-fonte possui o arquivo “01-dados-exemplo-NAO-TIC.csv”;
        ◦ Se o arquivo a ser processado for TIC, você terá que criar um arquivo .CSV separado por ponto-e-vírgula, com as colunas ‘ITEM’ e ‘CATMAT’. A coluna ‘ITEM‘ é usada somente para a ordenação do resultado final. O diretório do código-fonte possui o arquivo “01-dados-exemplo- TIC.csv”.
    • Após informar todas as informações, o script processará os dados e, se tudo correr bem, exibirá a mensagem: Processamento concluído com sucesso!.
    • O arquivo de saída gerado ‘resultado_final_consolidado.csv’ aparecerá na mesma pasta Processamento_NCM.
    • Exemplo de uso do código no Windows e processamento.
