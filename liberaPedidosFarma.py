import os
import re
import sys
import time
import psutil
import shutil
import locale
import smtplib
import datetime
import psycopg2
import requests
import cx_Oracle
import zipfile
import subprocess
from datetime import datetime
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from webdriver_manager.firefox import GeckoDriverManager
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import Select
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from logExecucaoCodigos import grava_log_execucao_sql


def get_firefox_version(directory, executable_name):
    """
    Obtém a versão do Firefox a partir do arquivo `firefox.exe` no diretório especificado.
    """
    try:
        firefox_executable = os.path.join(directory, executable_name)
        if not os.path.exists(firefox_executable):
            return None
        result = subprocess.run(
            [firefox_executable, "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        version_match = re.search(r"Mozilla Firefox (\d+\.\d+)", result.stdout)
        if version_match:
            return version_match.group(1)
    except Exception as e:
        print(f"Erro ao obter versão do Firefox no diretório '{directory}': {e}")
    return None


def rename_firefox_executable():
    try:
        # Caminho original e caminho do diretório de cópia
        firefox_install_dir = r"C:\Program Files\Mozilla Firefox"
        selenium_firefox_dir = r"C:\Firefox_Selenium"
        selenium_firefox_path = os.path.join(selenium_firefox_dir, "firefox_selenium.exe")
        
        # Verifica se o diretório de instalação original existe
        if not os.path.exists(firefox_install_dir):
            print(f"Diretório de instalação do Firefox não encontrado: {firefox_install_dir}")
            return
        
        # Obtém as versões do Firefox nos dois diretórios
        original_version = get_firefox_version(firefox_install_dir, "firefox.exe")
        selenium_version = get_firefox_version(selenium_firefox_dir, "firefox_selenium.exe")

        # Verifica se precisa atualizar a pasta Selenium
        if original_version != selenium_version:
            print(f"Atualizando Firefox para Selenium (versão original: {original_version}, versão Selenium: {selenium_version}).")

            # Remove o diretório `C:\Firefox_Selenium` se ele já existir
            if os.path.exists(selenium_firefox_dir):
                print("Diretório C:\\Firefox_Selenium já existe. Limpando diretório para atualização...")
                shutil.rmtree(selenium_firefox_dir)
            
            # Copia toda a instalação do Firefox para `C:\Firefox_Selenium`
            print("Iniciando cópia da instalação do Firefox...")
            shutil.copytree(firefox_install_dir, selenium_firefox_dir)
            print("Instalação do Firefox copiada para uso exclusivo do Selenium.")
            
            # Renomeia o executável para `firefox_selenium.exe`
            original_executable = os.path.join(selenium_firefox_dir, "firefox.exe")
            if os.path.exists(original_executable):
                os.rename(original_executable, selenium_firefox_path)
                print("Firefox renomeado para uso exclusivo do Selenium.")
        else:
            print("A instalação do Firefox para Selenium já está atualizada.")
    
    except Exception as e:
        print(f"Erro ao configurar Firefox para Selenium: {e}")
        pass


def get_latest_geckodriver_url():
    """
    Obtém a URL de download da última versão do GeckoDriver para Windows 64-bit.
    """
    api_url = "https://api.github.com/repos/mozilla/geckodriver/releases/latest"
    response = requests.get(api_url)
    
    if response.status_code == 200:
        release_data = response.json()
        for asset in release_data["assets"]:
            if "win64.zip" in asset["browser_download_url"]:
                return asset["browser_download_url"]
    else:
        raise Exception("Falha ao obter a última versão do GeckoDriver.")


# Faz o download do Geckodriver
def download_geckodriver():
    """
    Faz o download do GeckoDriver mais recente e extrai para C:\Firefox_Selenium se ainda não existir.
    """
    selenium_firefox_dir = r"C:\Firefox_Selenium"
    geckodriver_path = os.path.join(selenium_firefox_dir, "geckodriver.exe")
    
    # Verifica se o GeckoDriver já existe
    if os.path.exists(geckodriver_path):
        print("GeckoDriver já está presente.")
        return geckodriver_path

    # Obtém a URL do GeckoDriver mais recente
    geckodriver_url = get_latest_geckodriver_url()
    
    # Baixa o GeckoDriver
    print("Baixando GeckoDriver mais recente...")
    response = requests.get(geckodriver_url)
    
    # Verifica se o download foi bem-sucedido
    if response.status_code == 200:
        zip_path = os.path.join(selenium_firefox_dir, "geckodriver.zip")
        with open(zip_path, "wb") as file:
            file.write(response.content)
    else:
        raise Exception("Falha ao baixar o GeckoDriver. Verifique o URL e a conexão com a internet.")

    # Verifica se o arquivo baixado é um ZIP válido antes de extrair
    try:
        print("Extraindo GeckoDriver...")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(selenium_firefox_dir)
        print("GeckoDriver baixado e extraído com sucesso.")
    except zipfile.BadZipFile:
        print("Erro: o arquivo baixado não é um arquivo ZIP válido.")
        os.remove(zip_path)  # Remove o arquivo inválido
        raise

    # Remove o arquivo zip após extração
    os.remove(zip_path)
    return geckodriver_path


# Caminho do arquivo JSON
def diretorio_json():
    """
    Obtém o diretório do JSON para conexão no Google Sheet

    Returns:
    Diretorio: string
    """

    diretorio = r"C:\rpa\Python\Liberacao pedido farma\token.json"

    return diretorio


# Tratamento de erros
def handle_exception(bloco_codigo, e):
    """
    Lida com exceções e envia e-mails de erro

    Parameters:
    bloco_codigo: string
    e: string
    """
    locale.setlocale(locale.LC_ALL, 'pt_BR')
    data_hora_atual = datetime.now()
    mensagem = f"Erro no retorno da liberação de pedidos farma. Função: {bloco_codigo}. Erro: {e}"
    grava_log(mensagem_log=f"{data_hora_atual} - {mensagem}")
    grava_log_execucao_sql(codigo="liberacaoPedidoFarma", status="Erro")

    destinatarios_email = ['Nicolas.nasario@EMPRESA.com.br', 'Lucas.remor@EMPRESA.com.br']
    assunto_email = "Erro no RPA de Liberação de Pedidos Farma"
    envia_email(mensagem, destinatarios_email, assunto_email)


# Função que obtém a margem informada pelo usuário
def solicita_tabela_base():
    """
    Solicita as informações do Google Sheet, guia de margens

    Returns:
    Valores: collection
    """

    # Grava no log que o código está executando
    grava_log_execucao_sql(codigo="liberacaoPedidoFarma", status="Executando")

    # If modifying these scopes, delete the file token.json.
    SCOPES = ["https://www.googleapis.com/auth/spreadsheets"] #Acessa o google sheets

    # The ID and range of a sample spreadsheet.
    SAMPLE_SPREADSHEET_ID = "1823UdTl448meqbJQfzeQBo18_G5-TYhjiX4AMPaGc0w"
    SAMPLE_RANGE_NAME = "Base!A2:I"

    creds = None

    # Faz o login da API do Google
    if os.path.exists(diretorio_json()):
        creds = Credentials.from_authorized_user_file(diretorio_json(), SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(diretorio_json(), SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open(diretorio_json(), 'w') as token:
            token.write(creds.to_json())

    # Faz a leitura e edição da planilha
    #try:
    service = build('sheets', 'v4', credentials=creds)

    # Ler informacoes do Google Sheets
    sheet = service.spreadsheets()
    # Lê a planilha através do .get, o .update altera informações
    result = sheet.values().get(spreadsheetId=SAMPLE_SPREADSHEET_ID,
                                range=SAMPLE_RANGE_NAME).execute()
    valores = result['values']

    # Retorna uma lista
    return valores

    #except HttpError as err:
        #print(err)
        #handle_exception(bloco_codigo="Solicita_margem_minima", e=err)


# Envia e-mails
def envia_email(mensagemEmail, destinatarios_email, assunto_email):
    """
    Envia e-mails personalizados

    Parameters:
    MensagemEmail = string
    Destinatarios_email = collection
    Assunto_email = string
    """

    smtp_server = 'mail.EMPRESA.com.br'
    smtp_port = 25
    remetente_email = "rpa@EMPRESA.com.br"
    remetente_senha = 'DADO_HIGIENIZADO'

    mensagem = MIMEMultipart()
    mensagem['From'] = remetente_email
    mensagem['To'] = ",".join(destinatarios_email)
    mensagem['Subject'] = assunto_email

    mensagem.attach(MIMEText(mensagemEmail, 'html'))

    #try:
    servidor_smtp = smtplib.SMTP(smtp_server, smtp_port)
    servidor_smtp.starttls()
    servidor_smtp.login(remetente_email, remetente_senha)
    texto_email = mensagem.as_string()
    servidor_smtp.sendmail(remetente_email, destinatarios_email, texto_email)

    #except Exception as e:
        #print(e)
        #handle_exception(bloco_codigo="Envia_email", e=e)

    #finally:
    servidor_smtp.quit()


# Grava o log
def grava_log(mensagem_log):
    """Grava a informação no log."""

    caminho_arquivo_log = r"C:\rpa\Python\Liberacao pedido farma\Log\Log.txt"
    with open(caminho_arquivo_log, "a") as arquivo:
        arquivo.write(f"\n{mensagem_log}")


# Conecta no Oracle e executa o SQL
def conecta_oracle(sql):
    """
    Conecta no Oracle e retorna a tabela do SQL pesquisada

    Parameters:
    Query = string

    Returns:
    Tabela SQL = collection
    """

    #Grava no log que o código está executando
    grava_log_execucao_sql(codigo="liberacaoPedidoFarma", status="Executando")

    dsn = cx_Oracle.makedsn("10.1.1.20", "1521", service_name="pdb1")
    user = "nicolas"
    password = 'DADO_HIGIENIZADO'

    connection = cx_Oracle.connect(user, password, dsn)
    cursor = connection.cursor()
    cursor.execute(sql)
    select_sql = cursor.fetchall()

    return select_sql


# Roda query para executar o MySQL
def conecta_pg(sql):
    """
    Roda query para executar o MySQL

    Parameters:
    Sql = string

    Returns:
    Quantidade_linhas = int
    """

    host = 'pgdw.EMPRESA.com.br'  # Endereço do servidor MySQL
    database = "rpa"  # Nome do banco de dados
    user = 'rpa'  # Nome de usuário para acessar o banco de dados
    password = 'DADO_HIGIENIZADO'  # Senha do usuário para acessar o banco de dados
    port = 5432

    # Estabelece a conexão com o banco de dados
    connection = psycopg2.connect(
        host=host,
        database=database,
        user=user,
        password=password,
        port=port
    )

    cursor = connection.cursor()
    cursor.execute(sql)
    tabela_sql = cursor.fetchall()
    quantidade_linhas = len(tabela_sql)
    cursor.close()
    connection.close()

    grava_log_execucao_sql(codigo="liberacaoPedidoFarma", status="Executando")

    # Retorna o resultado da consulta do SQL para o usuário
    return quantidade_linhas


# Roda query para executar o MySQL
def conecta_pg_insert(sql):
    """
    Roda query para executar o MySQL

    Parameters: 
    sql = string
    """

    host = 'pgdw.EMPRESA.com.br'  # Endereço do servidor MySQL
    database = "rpa"  # Nome do banco de dados
    user = 'rpa'  # Nome de usuário para acessar o banco de dados
    password = 'DADO_HIGIENIZADO'  # Senha do usuário para acessar o banco de dados
    port = 5432

    # Estabelece a conexão com o banco de dados
    connection = psycopg2.connect(
        host=host,
        database=database,
        user=user,
        password=password,
        port=port
    )

    cursor = connection.cursor()
    cursor.execute(sql)
    connection.commit()
    cursor.close()
    connection.close()

    grava_log_execucao_sql(codigo="liberacaoPedidoFarma", status="Executando")


# Função para encontrar subprocessos do ChromeDriver
def find_chrome_processes(ppid):
    """
    Função para encontrar subprocessos do ChromeDriver

    Parameters:
    ppid: string

    Returns:
    chrome_pids: list
    """

    chrome_pids = []
    for proc in psutil.process_iter(['pid', 'ppid', 'name']):
        try:
            # Ajusta o nome do processo conforme necessário
            if proc.info['ppid'] == ppid and proc.info['name'].lower() in ['firefox_selenium', 'firefox_selenium.exe']:
                chrome_pids.append(proc.info['pid'])
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return chrome_pids


# Função para matar o Firefox
def kill_firefox():
    try:
        subprocess.run(["taskkill", "/F", "/IM", "firefox_selenium.exe"], check=True)

    except Exception as e:
        print(e)


# Função para matar processos pelo PID
def kill_process(pid):
    """
    Função para matar processos pelo PID

    Parameters:
    pid = string
    """

    try:
        if os.name == 'nt':  # Windows
            subprocess.run(["taskkill", "/F", "/PID", str(pid)], check=True)
        else:  # Unix-based systems (Linux, Mac)
            os.kill(pid, 9)
        print(f"Processo {pid} foi finalizado.")
    except Exception as e:
        print(f"Erro ao tentar finalizar o processo {pid}: {e}")


# Trata o alerta
def trata_alerta(navegador):
    """
    Trata o alerta

    Parameters:
    navegador = navigator
    """

    # Espera o elemento de OK
    try:
        WebDriverWait(navegador, 5).until(EC.alert_is_present())
        alert = navegador.switch_to.alert

        # Aceita a caixa de diálogo (clica em OK)
        alert.accept()
    
    except:
        time.sleep(1)


# Libera o pedido
def libera_pedido(navegador):
    """
    Libera o pedido

    Parameters:
    navegador = navigator
    """


    # Verifica se o elemento está carregado na página
    elemento_pagina = navegador.find_element(By.XPATH, f"/html/body/form/div/input[1]")

    # Clica no elemento de voltar
    navegador.execute_script("arguments[0].click();", elemento_pagina)


# Acessa o navegador
def acessa_navegador():
    """
    Acessa o navegador
    """

    try:
        # Grava no log que o código está executando
        grava_log_execucao_sql(codigo="liberacaoPedidoFarma", status="Executando")

        # Mata o firefox
        # kill_firefox()

        # Renomeia o firefox
        rename_firefox_executable()

        # Obtém o local do geckodriver
        geckodriver_path = download_geckodriver()

        # Configurações para o Firefox
        options = FirefoxOptions()
        options.binary_location = r"C:\Firefox_Selenium\firefox_selenium.exe"  # Especifica o executável renomeado do Firefox

        sys.stdout = open(r"C:\rpa\Python\Liberacao pedido farma\Log.txt", 'w') #AJUSTAR
        user_agent = ("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.182 Safari/537.36")
        options.add_argument('--headless')  # Executa o Firefox em modo headless (sem interface gráfica)
        options.add_argument("--width=1920")  # Define a largura da janela
        options.add_argument("--height=1080")  # Define a altura da janela
        options.add_argument("--disable-gpu")
        options.add_argument(user_agent)  # Define o user-agent para o Firefox
        options.add_argument('--ignore-certificate-errors')  # Desabilita a verificação de certificado SSL

        # Define o serviço do FirefoxDriver
        #servico = FirefoxService()
        servico = FirefoxService(executable_path=geckodriver_path)

        # Inicia o navegador Firefox com as opções definidas
        navegador = webdriver.Firefox(options=options, service=servico)

        # Maximiza o navegador
        navegador.maximize_window() #Maximiza a tela

        # Obtém o PID do processo do ChromeDriver
        chromedriver_pid = servico.process.pid

        # Encontra subprocessos do ChromeDriver
        chrome_pids = find_chrome_processes(chromedriver_pid)

        return navegador, chrome_pids

    except Exception as e:
        #print(e)
        handle_exception(bloco_codigo="Acessa_navegador", e=e)

        navegador.quit()

        for pid in chrome_pids:
            kill_process(pid)


# Acessa o sistema Intranet
def loga_sistema_intranet():
    """
    Acessa o sistema Intranet

    Returns:
    navegador: navigator
    chrome_pids: string
    """

    try:
        # Grava no log que o código está executando
        grava_log_execucao_sql(codigo="liberacaoPedidoFarma", status="Executando")

        # Chama a função que instancia o navegador
        navegador, chrome_pids = acessa_navegador()

        # Define a url de navegação
        url = "'http://api.empresa.com.br'/login.xhtml"

        # Define o usuário e senha
        usuario = "robo.geral"
        senha = 'DADO_HIGIENIZADO'

        navegador.get(url)

        # Usuário
        WebDriverWait(navegador, 120).until(EC.presence_of_element_located((By.XPATH, "/html/body/form/div/div/div[1]/div/input")))
        navegador.find_element("xpath", "/html/body/form/div/div/div[1]/div/input").send_keys(usuario)

        # Senha
        WebDriverWait(navegador, 120).until(EC.presence_of_element_located((By.XPATH, "/html/body/form/div/div/div[2]/div/span/input")))
        navegador.find_element("xpath", "/html/body/form/div/div/div[2]/div/span/input").send_keys(senha)

        # Botão de login
        WebDriverWait(navegador, 120).until(EC.presence_of_element_located((By.XPATH, "/html/body/form/div/div/div[4]/button")))

        # Verifica se o elemento está carregado na página
        elemento_cliente = navegador.find_element(By.XPATH, "/html/body/form/div/div/div[4]/button")

        # Clica nos dados cadastrais por Javascript
        navegador.execute_script("arguments[0].click();", elemento_cliente)

        # Botão de aplicativos
        WebDriverWait(navegador, 120).until(EC.presence_of_element_located((By.XPATH, "/html/body/div[1]/div[2]/div[1]/div/form/ul[1]/li/a")))

        # Verifica se o elemento está carregado na página
        elemento_cliente = navegador.find_element(By.XPATH, "/html/body/div[1]/div[2]/div[1]/div/form/ul[1]/li/a")

        # Clica nos botão de aplicativos por Javascript
        navegador.execute_script("arguments[0].click();", elemento_cliente)

        # Aplicativos
        WebDriverWait(navegador, 120).until(EC.presence_of_element_located((By.ID, "pesquisar:pesquisarTexto")))
        time.sleep(1)
        navegador.find_element("id", "pesquisar:pesquisarTexto").send_keys("LIBERAÇÃO DE PEDIDOS")

        # Espera um segundo até aparecer o elemento
        time.sleep(1)

        # Botão de liberação
        WebDriverWait(navegador, 120).until(EC.presence_of_element_located((By.XPATH, "/html/body/div[1]/div[2]/div[3]/div[2]/div/div[2]/form/table/tbody/tr/td[2]/a")))

        # Verifica se o elemento está carregado na página
        elemento_cliente = navegador.find_element(By.XPATH, "/html/body/div[1]/div[2]/div[3]/div[2]/div/div[2]/form/table/tbody/tr/td[2]/a")

        # Clica nos botão dos pedidos por Javascript
        navegador.execute_script("arguments[0].click();", elemento_cliente)

        # Espera a página carregar
        time.sleep(1)

        # Obtenha todas as guias abertas
        handles = navegador.window_handles
        
        # Foca na segunda guia
        navegador.switch_to.window(handles[1])

        return navegador, chrome_pids

    except Exception as e:
        handle_exception(bloco_codigo="Loga_sistema_intranet", e=e)

        navegador.quit()

        for pid in chrome_pids:
            kill_process(pid)

    # finally:
    #     if navegador is not None:
    #         navegador.quit()


# Busca a tela de liberação de pedidos
def consulta_liberacao_pedidos_farma():
    """
    Busca a tela de liberação de pedidos
    """

    # try:
    # Grava no log que o código está executando
    grava_log_execucao_sql(codigo="liberacaoPedidoFarma", status="Executando")

    navegador, chrome_pids = loga_sistema_intranet()

    # Espera a tela carregar
    time.sleep(1)
    
    # Carrega a segunda guia
    navegador.switch_to.window(navegador.window_handles[1])

    # Espera o elemento de pedidos farma
    WebDriverWait(navegador, 120).until(EC.presence_of_element_located((By.ID, "check-farma")))

    # Verifica se o elemento está carregado na página
    elemento_pagina = navegador.find_element(By.ID, "check-farma")

    # Clica nos dados cadastrais por Javascript
    navegador.execute_script("arguments[0].click();", elemento_pagina)

    # Espera a tabela carregar
    time.sleep(2)

    # Espera o elemento de pedidos farma
    WebDriverWait(navegador, 120).until(EC.presence_of_element_located((By.ID, "tbPedidos")))

    return navegador, chrome_pids

    # except Exception as e:
    #     print(e)
    #     #handle_exception(bloco_codigo="Consulta_liberacao_pedidos_farma", e=e)

    # finally:
    #     navegador.close()


def deslogar_sistema_intranet(navegador):
    # Carrega a segunda guia
    navegador.switch_to.window(navegador.window_handles[0])

    # Espera a tela carregar
    time.sleep(1)

    # Espera o botão do boneco para deslogar
    WebDriverWait(navegador, 120).until(EC.presence_of_element_located((By.XPATH, "/html/body/div[1]/div[1]/div/div[2]/a/img")))

    # Verifica se o elemento está carregado na página
    elemento_pagina = navegador.find_element(By.XPATH, "/html/body/div[1]/div[1]/div/div[2]/a/img")

    # Clica nos dados cadastrais por Javascript
    navegador.execute_script("arguments[0].click();", elemento_pagina)

    # Espera a tela carregar
    time.sleep(1)

    # Espera o elemento de sair
    WebDriverWait(navegador, 120).until(EC.presence_of_element_located((By.XPATH, "/html/body/div[1]/div[1]/div/div[2]/form/ul/li[3]/a")))

    # Verifica se o elemento está carregado na página
    elemento_pagina = navegador.find_element(By.XPATH, "/html/body/div[1]/div[1]/div/div[2]/form/ul/li[3]/a")

    # Clica nos dados cadastrais por Javascript
    navegador.execute_script("arguments[0].click();", elemento_pagina)

    # Espera a tela carregar
    time.sleep(2)



# Navega entre os pedidos
def navega_tabela_pedidos_gerais():
    """
    Navega entre os pedidos
    """

    #try:
    # Grava no log que o código está executando
    grava_log_execucao_sql(codigo="liberacaoPedidoFarma", status="Executando")

    locale.setlocale(locale.LC_ALL, "pt_BR")
    data_hora_atual = datetime.now()
    data_convertida = data_hora_atual.strftime('%Y-%m-%d')

    # Acessa o navegador
    navegador, chrome_pids = consulta_liberacao_pedidos_farma()

    # Verifica se o elemento está carregado na página
    elemento_pagina = navegador.find_element(By.XPATH, f"/html/body/form/table/thead/tr/td[12]/a/img")

    # Clica no elemento do pedido por Javascript
    navegador.execute_script("arguments[0].click();", elemento_pagina)

    time.sleep(2)

    # Espera carregar a tabela de pedidos
    tabela_pedidos = WebDriverWait(navegador, 120).until(EC.presence_of_element_located((By.XPATH, "/html/body/form/table")))
    linhas_tabela = tabela_pedidos.find_elements(By.TAG_NAME, 'tr')
    quantidade_linhas = len(linhas_tabela)

    time.sleep(1)

    if quantidade_linhas > 1:
        for i in range(1, (quantidade_linhas)):
            time.sleep(1)
            
            # Obtém as informações do pedido
            elemento = navegador.find_element("xpath", f"/html/body/form/table/tbody/tr[{i}]/td[1]/input") 
            numero_pedido = elemento.get_attribute("value") 
            elemento_pedido_cadeado = navegador.find_element("xpath", f"/html/body/form/table/tbody/tr[{i}]/td[2]/a")  
            pedido_cadeado = elemento_pedido_cadeado.get_attribute("title")

            sql = f"select * from comercial.liberacao_pedidos_farma where nr_pedido = '{numero_pedido}' and dt_pedido = '{data_convertida}'"

            qtd_linhas = conecta_pg(sql=sql)
            # qtd_linhas = 0

            if "CADEADO POR USUARIO" not in str(pedido_cadeado).upper() and qtd_linhas == 0:
                # Verifica se o elemento está carregado na página
                elemento_pagina = navegador.find_element(By.XPATH, f"/html/body/form/table/tbody/tr[{i}]/td[1]/input")

                # Verifica se o elemento está carregado na página
                razao_social = navegador.find_element(By.XPATH, f"/html/body/form/table/tbody/tr[{i}]/td[4]").text

                # Clica no elemento do pedido por Javascript
                navegador.execute_script("arguments[0].click();", elemento_pagina)

                # Espera carregar a tabela de pedidos e obtém os dados do pedido
                WebDriverWait(navegador, 60).until(EC.presence_of_element_located((By.ID, "margemPB")))

                time.sleep(1)

                # Atualiza o navegador
                navegador.refresh()

                # Trata o alerta da página
                trata_alerta(navegador=navegador)

                time.sleep(1)

                print(f"Número do pedido: {str(numero_pedido)}")

                # Analisa a quantidade de indústrias diferentes
                retorno_quantidade = analisa_quantidades_industrias(navegador=navegador)

                if retorno_quantidade == True:
                    # Analisa a margem
                    retorno_liberacao = analisa_margem_bloqueio(navegador=navegador)

                    if retorno_liberacao == True:
                        # Busca o código do cliente
                        codigo_cliente = navegador.find_element("xpath", f"/html/body/div[4]/table[1]/tbody/tr[2]/td[2]").text

                        # Busca o setor do cliente
                        setor_cliente = navegador.find_element("id", f"setor").text
                        
                        # Busca os dados do pedido
                        numero_pedido = navegador.find_element("id", f"nroPedido").text

                        # Busca o horário de fechamento do pedido
                        horario_fechamento = navegador.find_element("xpath", f"/html/body/div[4]/table[1]/tbody/tr[2]/td[5]").text

                        # Busca a margem mínima de bloqueio
                        margem_bloqueio = navegador.find_element("id", f"pc_margem_ponderada_bloqueio").text

                        # Busca a margem do pedido
                        margem_pedido = navegador.find_element("id", f"margemPB").text

                        ####### Libera o pedido #######
                        libera_pedido(navegador=navegador)

                        # Trata o alerta da página
                        trata_alerta(navegador=navegador)

                        # Envia e-mail quando liberar o pedido
                        # Informa os destinatários
                        destinatarios_email = []
                        destinatarios_email.append("nicolas.nasario@EMPRESA.com.br")
                        destinatarios_email.append("lucas.remor@EMPRESA.com.br")
                        destinatarios_email.append("elton@EMPRESA.com.br")
                        destinatarios_email.append("tais.cascaes@EMPRESA.com.br")
                        destinatarios_email.append("amanda.santana@EMPRESA.com.br")
                        destinatarios_email.append("heloisa.henrique@EMPRESA.com.br")

                        # Informa o assunto
                        assunto_email = f"RPA Liberação de Pedidos Farma - Pedido Liberado Automaticamente"

                        # Grava a mensagem
                        mensagem_email = f"""
                        Olá!<br><br> 
                        Abaixo segue a informação do pedido que foi liberado automaticamente pelo RPA:<br>
                        <strong>Cliente: </strong>{str(codigo_cliente).strip()} - {str(razao_social).strip()}<br>
                        <strong>Setor: </strong>{str(setor_cliente).strip()}<br>
                        <strong>Número do pedido: </strong>{str(numero_pedido).strip()}<br>
                        <strong>Horário de fechamento do pedido: </strong>{str(horario_fechamento).strip()}<br>
                        <strong>Margem do pedido: </strong>{str(margem_pedido).strip()}<br>
                        <strong>Mínima bloqueio: </strong>{str(margem_bloqueio).strip()}<br>
                        """

                        # Dispara e-mail de liberação automática
                        envia_email(mensagemEmail=mensagem_email, destinatarios_email=destinatarios_email, assunto_email=assunto_email)

                        # Obtém informação da data
                        data_hora_atual_gravar = datetime.now()
                        
                        # Grava a informação de situação no Google sheet do DP
                        url = f"https://script.google.com/macros/s/AKfycbw-doRcDu9ppE0nieD2mzYzKYUR0ofsiqN55QvJLgoTJPcdNJQa7DWoEEK08sRW6UFB/exec?numero_pedido={numero_pedido}&cliente={codigo_cliente}&setor_cliente={setor_cliente}&data_pedido={data_hora_atual_gravar}&situacao_pedido=Liberado"

                        # Fazendo a requisição para a API
                        response = requests.get(url)

                        # Faz o insert na tabela de controle (para evitar que seja analisado mais de uma vez)
                        insert = f"INSERT INTO comercial.liberacao_pedidos_farma (nr_pedido, dt_pedido) VALUES('{numero_pedido}', '{data_convertida}')"
                        conecta_pg_insert(sql=insert)

                        ####### Volta para a tela inicial #######
                        try:
                            # Verifica se o elemento está carregado na página
                            elemento_pagina = navegador.find_element(By.XPATH, f"/html/body/table/tbody/tr/td/span/a/img")
                        
                        except:
                            # Verifica se o elemento está carregado na página
                            elemento_pagina = navegador.find_element(By.XPATH, f"/html/body/div[4]/p/a")

                        # Clica no elemento de voltar
                        navegador.execute_script("arguments[0].click();", elemento_pagina)

                    else:
                        # Busca a margem do pedido
                        margem_pedido = navegador.find_element("id", f"margemPB").text

                        # Busca a margem mínima de bloqueio
                        margem_bloqueio = navegador.find_element("id", f"pc_margem_ponderada_bloqueio").text

                        if "nan" not in str(margem_pedido).strip() and float(margem_bloqueio) > 0.00:
                            # Busca o código do cliente
                            codigo_cliente_completo = navegador.find_element("xpath", f"/html/body/div[4]/table[1]/tbody/tr[2]/td[2]").text

                            # Busca o setor do cliente
                            setor_cliente = navegador.find_element("id", f"setor").text
                            
                            # Busca os dados do pedido
                            numero_pedido = navegador.find_element("id", f"nroPedido").text

                            # Obtém o código do cliente
                            lista_codigo = codigo_cliente_completo.split("/")
                            codigo_cliente = lista_codigo[0]

                            # Verifica a UF do cliente
                            sql = f"SELECT UFEP_P FROM PRDDM.DCCLI CLI, PRDDM.DCPES PES WHERE CLI.CGCP_C = PES.CGCP_P AND NROC_C = '{codigo_cliente}'"

                            tabela_uf_cliente = conecta_oracle(sql=sql)
                            uf_cliente = tabela_uf_cliente[0]

                            analisa_margem_itens(navegador=navegador, uf_cliente=uf_cliente)

                            ####### Volta para a tela inicial #######
                            #Atualiza a página
                            #navegador.refresh()

                            # Trata o alerta da página
                            #trata_alerta(navegador=navegador)

                            #time.sleep(1)

                            # Obtém informação da data
                            data_hora_atual_gravar = datetime.now()
                            
                            # Grava a informação de situação no Google sheet do DP
                            url = f"https://script.google.com/macros/s/AKfycbw-doRcDu9ppE0nieD2mzYzKYUR0ofsiqN55QvJLgoTJPcdNJQa7DWoEEK08sRW6UFB/exec?numero_pedido={numero_pedido}&cliente={codigo_cliente_completo}&setor_cliente={setor_cliente}&data_pedido={data_hora_atual_gravar}&situacao_pedido=Analisado"

                            # Fazendo a requisição para a API
                            response = requests.get(url)

                            # Faz o insert na tabela de controle (para evitar que seja analisado mais de uma vez)
                            insert = f"INSERT INTO comercial.liberacao_pedidos_farma (nr_pedido, dt_pedido) VALUES('{numero_pedido}', '{data_convertida}')"
                            conecta_pg_insert(sql=insert)

                        else:
                            # Busca o código do cliente
                            codigo_cliente_completo = navegador.find_element("xpath", f"/html/body/div[4]/table[1]/tbody/tr[2]/td[2]").text

                            # Busca o setor do cliente
                            setor_cliente = navegador.find_element("id", f"setor").text
                            
                            # Busca os dados do pedido
                            numero_pedido = navegador.find_element("id", f"nroPedido").text

                            # Obtém o código do cliente
                            lista_codigo = codigo_cliente_completo.split("/")
                            codigo_cliente = lista_codigo[0]

                            # Verifica a UF do cliente
                            sql = f"SELECT UFEP_P FROM PRDDM.DCCLI CLI, PRDDM.DCPES PES WHERE CLI.CGCP_C = PES.CGCP_P AND NROC_C = '{codigo_cliente}'"

                            tabela_uf_cliente = conecta_oracle(sql=sql)
                            uf_cliente = tabela_uf_cliente[0]

                            # Obtém informação da data
                            data_hora_atual_gravar = datetime.now()
                            
                            # Grava a informação de situação no Google sheet do DP
                            url = f"https://script.google.com/macros/s/AKfycbw-doRcDu9ppE0nieD2mzYzKYUR0ofsiqN55QvJLgoTJPcdNJQa7DWoEEK08sRW6UFB/exec?numero_pedido={numero_pedido}&cliente={codigo_cliente_completo}&setor_cliente={setor_cliente}&data_pedido={data_hora_atual_gravar}&situacao_pedido=Não analisado"

                            # Fazendo a requisição para a API
                            response = requests.get(url)

                            # Faz o insert na tabela de controle (para evitar que seja analisado mais de uma vez)
                            insert = f"INSERT INTO comercial.liberacao_pedidos_farma (nr_pedido, dt_pedido) VALUES('{numero_pedido}', '{data_convertida}')"
                            conecta_pg_insert(sql=insert)


                        # Aguarda a página carregar
                        time.sleep(2)
                        
                        # Verifica se o elemento está carregado na página
                        elemento_pagina = navegador.find_element(By.XPATH, f"/html/body/div[4]/p/a")

                        # Clica no elemento de voltar
                        navegador.execute_script("arguments[0].click();", elemento_pagina)

                else:
                    # Busca a margem do pedido
                    margem_pedido = navegador.find_element("id", f"margemPB").text

                    # Busca a margem mínima de bloqueio
                    margem_bloqueio = navegador.find_element("id", f"pc_margem_ponderada_bloqueio").text

                    if "nan" not in str(margem_pedido).strip() and float(margem_bloqueio) > 0.00:
                        # Busca o código do cliente
                        codigo_cliente_completo = navegador.find_element("xpath", f"/html/body/div[4]/table[1]/tbody/tr[2]/td[2]").text

                        # Busca o setor do cliente
                        setor_cliente = navegador.find_element("id", f"setor").text
                        
                        # Busca os dados do pedido
                        numero_pedido = navegador.find_element("id", f"nroPedido").text


                        # Obtém o código do cliente
                        lista_codigo = codigo_cliente_completo.split("/")
                        codigo_cliente = lista_codigo[0]

                        # Verifica a UF do cliente
                        sql = f"SELECT UFEP_P FROM PRDDM.DCCLI CLI, PRDDM.DCPES PES WHERE CLI.CGCP_C = PES.CGCP_P AND NROC_C = '{codigo_cliente}'"

                        tabela_uf_cliente = conecta_oracle(sql=sql)
                        uf_cliente = tabela_uf_cliente[0]

                        analisa_margem_itens(navegador=navegador, uf_cliente=uf_cliente)

                        ####### Volta para a tela inicial #######
                        #Atualiza a página
                        #navegador.refresh()

                        # Trata o alerta da página
                        #trata_alerta(navegador=navegador)

                        #time.sleep(1)

                        # Obtém informação da data
                        data_hora_atual_gravar = datetime.now()
                        
                        # Grava a informação de situação no Google sheet do DP
                        url = f"https://script.google.com/macros/s/AKfycbw-doRcDu9ppE0nieD2mzYzKYUR0ofsiqN55QvJLgoTJPcdNJQa7DWoEEK08sRW6UFB/exec?numero_pedido={numero_pedido}&cliente={codigo_cliente_completo}&setor_cliente={setor_cliente}&data_pedido={data_hora_atual_gravar}&situacao_pedido=Analisado"

                        # Fazendo a requisição para a API
                        response = requests.get(url)

                        # Faz o insert na tabela de controle (para evitar que seja analisado mais de uma vez)
                        insert = f"INSERT INTO comercial.liberacao_pedidos_farma (nr_pedido, dt_pedido) VALUES('{numero_pedido}', '{data_convertida}')"
                        conecta_pg_insert(sql=insert)

                    else:
                            # Busca o código do cliente
                            codigo_cliente_completo = navegador.find_element("xpath", f"/html/body/div[4]/table[1]/tbody/tr[2]/td[2]").text

                            # Busca o setor do cliente
                            setor_cliente = navegador.find_element("id", f"setor").text
                            
                            # Busca os dados do pedido
                            numero_pedido = navegador.find_element("id", f"nroPedido").text

                            # Obtém o código do cliente
                            lista_codigo = codigo_cliente_completo.split("/")
                            codigo_cliente = lista_codigo[0]

                            # Verifica a UF do cliente
                            sql = f"SELECT UFEP_P FROM PRDDM.DCCLI CLI, PRDDM.DCPES PES WHERE CLI.CGCP_C = PES.CGCP_P AND NROC_C = '{codigo_cliente}'"

                            tabela_uf_cliente = conecta_oracle(sql=sql)
                            uf_cliente = tabela_uf_cliente[0]

                            # Obtém informação da data
                            data_hora_atual_gravar = datetime.now()
                            
                            # Grava a informação de situação no Google sheet do DP
                            url = f"https://script.google.com/macros/s/AKfycbw-doRcDu9ppE0nieD2mzYzKYUR0ofsiqN55QvJLgoTJPcdNJQa7DWoEEK08sRW6UFB/exec?numero_pedido={numero_pedido}&cliente={codigo_cliente_completo}&setor_cliente={setor_cliente}&data_pedido={data_hora_atual_gravar}&situacao_pedido=Não analisado"

                            # Fazendo a requisição para a API
                            response = requests.get(url)

                            # Faz o insert na tabela de controle (para evitar que seja analisado mais de uma vez)
                            insert = f"INSERT INTO comercial.liberacao_pedidos_farma (nr_pedido, dt_pedido) VALUES('{numero_pedido}', '{data_convertida}')"
                            conecta_pg_insert(sql=insert)

                    # Aguarda a página carregar
                    time.sleep(2)
                    
                    # Verifica se o elemento está carregado na página
                    elemento_pagina = navegador.find_element(By.XPATH, f"/html/body/div[4]/p/a")

                    # Clica no elemento de voltar
                    navegador.execute_script("arguments[0].click();", elemento_pagina)

                # Aguarda a tabela carregar
                time.sleep(1)
                
                # Espera carregar novamente a tabela
                tabela_pedidos = WebDriverWait(navegador, 120).until(EC.presence_of_element_located((By.XPATH, "/html/body/form/table")))

                # Obtém as informações novas da tabela
                linhas_tabela_novo = tabela_pedidos.find_elements(By.TAG_NAME, 'tr')
                quantidade_linhas_novo = len(linhas_tabela_novo)

                # Valida se houveram alterações nas linhas da tabela principal
                if quantidade_linhas_novo != quantidade_linhas:
                    # Retorna a quantidade de linhas
                    quantidade_linhas = quantidade_linhas_novo

                    # Retorna o index para 0
                    i = 0

                # Aguarda a tabela carregar
                time.sleep(2)

    deslogar_sistema_intranet(navegador=navegador)

    navegador.quit()


    # except Exception as e:
    #     print(e)
    #     handle_exception(bloco_codigo="Navega_tabela_pedidos_gerais", e=e)

    #     for pid in chrome_pids:
    #         kill_process(pid)


# Analisa a quantidade de itens por indústria
def analisa_quantidades_industrias(navegador):
    """
    Analisa os itens caso a margem ainda esteja abaixo

    Parameters:
    navegador = navigator
    uf_cliente = string
    """

    # Ordena os itens por verba
    # Verifica se o elemento está carregado na página
    elemento_pagina = navegador.find_element(By.ID, f"th-verba-necessaria")

    # Clica no elemento de voltar
    navegador.execute_script("arguments[0].click();", elemento_pagina)

    time.sleep(0.2)

    # Ordena os itens por verba
    # Verifica se o elemento está carregado na página
    elemento_pagina = navegador.find_element(By.ID, f"th-verba-necessaria")

    # Clica no elemento de voltar
    navegador.execute_script("arguments[0].click();", elemento_pagina)

    time.sleep(0.2)
    
    # Ordena os itens por laboratório
    # Verifica se o elemento está carregado na página
    elemento_pagina = navegador.find_element(By.ID, f"th-nome-fornecedor")

    # Clica no elemento de voltar
    navegador.execute_script("arguments[0].click();", elemento_pagina)

    time.sleep(0.5)

    # Obtém a tabela dos itens
    tabela_itens = WebDriverWait(navegador, 120).until(EC.presence_of_element_located((By.ID, "tabelaItens")))
    linhas_tabela = tabela_itens.find_elements(By.TAG_NAME, 'tr')
    quantidade_linhas = len(linhas_tabela)

    # Instancia as variáveis
    retorno_analise_desconto_tela_tabela = False
    colecao_industria_verba = {}
    colecao_media_lab = {}

    # Itera sobre cada linha de produto
    for linha in range(1, quantidade_linhas):
        # Obtém os dados da linha do item
        verba_necessaria = navegador.find_element("xpath", f"/html/body/form/table/tbody/tr[{linha}]/td[15]/span").text
        verba_necessaria_float = float(verba_necessaria)
        codigo_laboratorio = navegador.find_element("xpath", f"/html/body/form/table/tbody/tr[{linha}]/td[20]").text

        # Faz a soma dos valores das verbas por laboratório
        if codigo_laboratorio in colecao_industria_verba:
            valor_total_verba, quantidade = colecao_industria_verba[codigo_laboratorio]

            verba_necessaria_float += float(valor_total_verba)
            quantidade += 1

        else:
            quantidade = 1
        
        # Insere as verbas por indústria
        colecao_industria_verba[codigo_laboratorio] = (verba_necessaria_float, quantidade)

    if len(colecao_industria_verba) > 1:
        return False
    
    else:
        # Busca o código do cliente
        codigo_cliente = navegador.find_element("xpath", f"/html/body/div[4]/table[1]/tbody/tr[2]/td[2]").text

        # Obtém o código do cliente
        lista_codigo = codigo_cliente.split("/")
        codigo_cliente = lista_codigo[0]

        # Verifica a UF do cliente
        sql = f"SELECT UFEP_P FROM PRDDM.DCCLI CLI, PRDDM.DCPES PES WHERE CLI.CGCP_C = PES.CGCP_P AND NROC_C = '{codigo_cliente}'"

        tabela_uf_cliente = conecta_oracle(sql=sql)
        uf_cliente = tabela_uf_cliente[0]

        tabela = solicita_tabela_base()

        for linha in range(1, quantidade_linhas):
            codigo_laboratorio = navegador.find_element("xpath", f"/html/body/form/table/tbody/tr[{linha}]/td[20]").text

            # Itera sobre os dados da tabela do Google Sheet
            for comprador, divisao, fornecedor, uf, desconto, desconto_negociacoes, margem_atingir, verba, verba_auxiliar in tabela:
                # Valida a UF do cliente e a informação de margem para que seja comparado com os dados em tela
                if str(codigo_laboratorio) == str(divisao) and (uf_cliente[0] in uf or "Todos" in uf) and ("Usar verba até" in margem_atingir):
                    return True
                
                 # Valida a UF do cliente e a informação de margem, para que seja comparada com as informações do Google Sheet
                elif str(codigo_laboratorio) == str(divisao) and (uf_cliente[0] in uf or "Todos" in uf) and ("Usar verba até" not in margem_atingir):
                    return False


# Analisa os itens caso a margem ainda esteja abaixo
def analisa_margem_itens(navegador, uf_cliente):
    """
    Analisa os itens caso a margem ainda esteja abaixo

    Parameters:
    navegador = navigator
    uf_cliente = string
    """

    # Ordena os itens por verba
    # Verifica se o elemento está carregado na página
    elemento_pagina = navegador.find_element(By.ID, f"th-verba-necessaria")

    # Clica no elemento de voltar
    navegador.execute_script("arguments[0].click();", elemento_pagina)

    time.sleep(0.2)

    # Ordena os itens por verba
    # Verifica se o elemento está carregado na página
    elemento_pagina = navegador.find_element(By.ID, f"th-verba-necessaria")

    # Clica no elemento de voltar
    navegador.execute_script("arguments[0].click();", elemento_pagina)

    time.sleep(0.2)
    
    # Ordena os itens por laboratório
    # Verifica se o elemento está carregado na página
    elemento_pagina = navegador.find_element(By.ID, f"th-nome-fornecedor")

    # Clica no elemento de voltar
    navegador.execute_script("arguments[0].click();", elemento_pagina)

    time.sleep(0.2)

    # Obtém a tabela dos itens
    tabela_itens = WebDriverWait(navegador, 120).until(EC.presence_of_element_located((By.ID, "tabelaItens")))
    linhas_tabela = tabela_itens.find_elements(By.TAG_NAME, 'tr')
    quantidade_linhas = len(linhas_tabela)

    # Instancia as variáveis
    retorno_analise_desconto_tela_tabela = False
    colecao_industria_verba = {}
    colecao_media_lab = {}

    # Itera sobre cada linha de produto
    for linha in range(1, quantidade_linhas):
        # Obtém os dados da linha do item
        verba_necessaria = navegador.find_element("xpath", f"/html/body/form/table/tbody/tr[{linha}]/td[15]/span").text
        verba_necessaria_float = float(verba_necessaria)
        codigo_laboratorio = navegador.find_element("xpath", f"/html/body/form/table/tbody/tr[{linha}]/td[20]").text

        # Faz a soma dos valores das verbas por laboratório
        if codigo_laboratorio in colecao_industria_verba:
            valor_total_verba, quantidade = colecao_industria_verba[codigo_laboratorio]

            verba_necessaria_float += float(valor_total_verba)
            quantidade += 1

        else:
            quantidade = 1
        
        # Insere as verbas por indústria
        colecao_industria_verba[codigo_laboratorio] = (verba_necessaria_float, quantidade)

    # Itera para gerar as médias
    for laboratorio in colecao_industria_verba:
        verba_necessaria_total_lab, quantidade = colecao_industria_verba[laboratorio]
        verba_media = verba_necessaria_total_lab / quantidade

        colecao_media_lab[laboratorio] = verba_media

    # Solicita a tabela de base
    tabela_base_sheet = solicita_tabela_base()

    for linha in range(1, quantidade_linhas):
        #Obtenção dos dados da tabela de itens
        percentual_desconto = navegador.find_element("xpath", f"/html/body/form/table/tbody/tr[{linha}]/td[10]").text
        percentual_desconto_promocional = navegador.find_element("xpath", f"/html/body/form/table/tbody/tr[{linha}]/td[11]").text
        percentual_margem_bruta = navegador.find_element("xpath", f"/html/body/form/table/tbody/tr[{linha}]/td[12]/span").text
        verba_necessaria = navegador.find_element("xpath", f"/html/body/form/table/tbody/tr[{linha}]/td[15]/span").text

        elemento_verba_utilizada = navegador.find_element("xpath", f"/html/body/form/table/tbody/tr[{linha}]/td[16]/input")
        verba_utilizada = elemento_verba_utilizada.get_attribute("value")
        elemento_verba_reais = navegador.find_element("xpath", f"/html/body/form/table/tbody/tr[{linha}]/td[17]/input")
        valor_verba_utilizada = elemento_verba_reais.get_attribute("value")

        codigo_laboratorio = navegador.find_element("xpath", f"/html/body/form/table/tbody/tr[{linha}]/td[20]").text
        nome_laboratorio = navegador.find_element("xpath", f"/html/body/form/table/tbody/tr[{linha}]/td[21]").text

        # Obtém a verba média do laboratório analisado para informar nos itens
        verba_media_laboratorio = colecao_media_lab[codigo_laboratorio]

        # Somente fará se o percentual do desconto promocional for zero (condição especial)
        if str(percentual_desconto_promocional).strip() == "0.00":
            # if len(colecao_media_lab) > 1:
            analisa_desconto_tela_tabela(navegador=navegador, tabela=tabela_base_sheet, codigo_fornecedor=codigo_laboratorio, uf_cliente=uf_cliente[0], percentual_desconto_tela=percentual_desconto, verba_necessaria_tela=verba_necessaria, verba_media_laboratorio_tela=verba_media_laboratorio, verba_utilizada=verba_utilizada, linha_atual=linha)
    
    retorno_liberacao = False
    
    # Valida se há mais de um laboratório
    if len(colecao_media_lab) > 1:
        retorno_analise_margem = analisa_margem_bloqueio_final(navegador=navegador)

        # Caso o campo (Do pedido em % p/ Bloqueio) ainda fique menor do que (Mínima Bloqueio), irá preencher as verbas máximas item a item até que fique maior
        if retorno_analise_margem == True:
            retorno_liberacao = True

            # for linha in range(1, quantidade_linhas):
            #     # Obtém as informações do item
            #     elemento_verba_utilizada = navegador.find_element("xpath", f"/html/body/form/table/tbody/tr[{linha}]/td[16]/input")
            #     verba_utilizada = elemento_verba_utilizada.get_attribute("value")

            #     verba_necessaria = navegador.find_element("xpath", f"/html/body/form/table/tbody/tr[{linha}]/td[15]/span").text

            #     porcentagem_desconto_promocional = navegador.find_element("xpath", f"/html/body/form/table/tbody/tr[{linha}]/td[11]/span").text
                
            #     # Preencherá somente se a verba for diferente de zero, ou seja, quando houver verba "linkada"
            #     if str(verba_utilizada) != "0" and str(porcentagem_desconto_promocional) == "0.00":
            #         # Obtém o percentual de desconto do item
            #         percentual_desconto = navegador.find_element("xpath", f"/html/body/form/table/tbody/tr[{linha}]/td[10]").text
                    
            #         # Ajusta a margem máxima daquele item para verificarmos se o pedido poderá ser liberado
            #         ajusta_margem_item(navegador=navegador, verba_necessaria_tela=verba_necessaria, linha_atual=linha)

            #         # Analisa os campos (Do pedido em % p/ Bloqueio) x (Mínima Bloqueio), caso o primeiro seja maior que o segundo, liberaremos o pedido
            #         retorno_analise_margem = analisa_margem_bloqueio_final(navegador=navegador)

            #         if retorno_analise_margem == True:
            #             break

    # Apenas um laboratório
    else:
        laboratorio = list(colecao_media_lab.keys())[0]

        # Itera sobre a tabela do Google Sheet
        for comprador, divisao, fornecedor, uf, desconto, desconto_negociacoes, margem_atingir, verba, verba_auxiliar in tabela_base_sheet:
            # Valida se os fornecedores são iguais
            if str(laboratorio).strip() == str(divisao).strip():
                # Valida os dados da verba
                if ("verba" not in str(margem_atingir).lower().strip() and "0,00" not in str(margem_atingir).strip()):
                    if (float(str(margem_atingir).replace(",", ".").strip()) > 0):
                        # Valida se a margem do pedido está aceitável para liberação
                        retorno_analise_margem = analisa_margem_bloqueio_final_industria(navegador=navegador, margem_industria=margem_atingir)

                        if retorno_analise_margem == True:
                            break

    if retorno_liberacao == False:
        # Chama a função que analisa e ajusta a margem x verba
        ajusta_verba_margem_geral(navegador=navegador, quantidade_linhas=quantidade_linhas, colecao_media_lab=colecao_media_lab, tabela_base_sheet=tabela_base_sheet)


# Função que ajusta a margem dos itens até chegar na margem mínima do pedido
def ajusta_verba_margem_geral(navegador, quantidade_linhas, colecao_media_lab, tabela_base_sheet):
    """
    Função que ajusta a margem dos itens até chegar na margem mínima do pedido

    Parameters:
    navegador: navigator
    quantidade_linhas: int
    colecao_media_lab: collection
    tabela_base_sheet: collection
    """

    # Cria a coleção
    colecao_linhas = {}
    
    # Itera sobre os itens
    for linha in range(1, quantidade_linhas):
        # Obtém os dados do item
        valor_verba_utilizada, verba_utilizada, verba_necessaria, porcentagem_desconto_promocional, margem_produto, codigo_laboratorio = obtem_dados_item(navegador=navegador, linha=linha)

        # Informa o valor de verba na linha
        colecao_linhas[linha] = valor_verba_utilizada

    # Valida se há mais de um laboratório
    if len(colecao_media_lab) > 1:
        #Obtém os dados da mínima e porcentagem do pedido
        percentual_porcentagem_bloqueio = navegador.find_element("id", f"margemPB").text
        percentual_minima_bloqueio = navegador.find_element("id", f"pc_margem_ponderada_bloqueio").text

        # Se o percentual de bloqueio ficou igual à mínima, já nem entra pra validação
        if float(percentual_porcentagem_bloqueio) == float(percentual_minima_bloqueio):
            pass

        # Caso o percentual de bloqueio seja maior, entra pra validar
        if float(percentual_porcentagem_bloqueio) > float(percentual_minima_bloqueio):
            # Define o booleano de bloqueio
            encontrou_fornecedor = False

            # Define o booleano de bloqueio
            boolean_percentual_bloqueio = False

            # Define o valor de verba do primeiro item
            valor_verba_primeiro_item = 0.00
            
            # Enquanto a margem do pedido for acima do bloqueio, vai ajustando os itens para otimizar o uso de verba
            #while (float(str(percentual_porcentagem_bloqueio).replace(",", ".").strip()) > float(str(percentual_minima_bloqueio).replace(",", ".").strip())) or boolean_percentual_bloqueio == False:

            while boolean_percentual_bloqueio == False:
                # Itera sobre os itens
                for linha in range(1, quantidade_linhas):
                    # Aguarda um tempo para digitar os textos
                    time.sleep(0.35)
                    
                    # Obtém os dados do item
                    valor_verba_utilizada, verba_utilizada, verba_necessaria, porcentagem_desconto_promocional, margem_produto, codigo_laboratorio = obtem_dados_item(navegador=navegador, linha=linha)

                    # Obtém o valor de verba da coleção
                    valor_verba_utilizada = colecao_linhas[linha]

                    # Verificar se o código está em qualquer uma das sublistas
                    if any(codigo_laboratorio in sublista for sublista in tabela_base_sheet):
                        encontrou_fornecedor = True

                        # Itera sobre a tabela do Google Sheet
                        for comprador, divisao, fornecedor, uf, desconto, desconto_negociacoes, margem_atingir, verba, verba_auxiliar in tabela_base_sheet:
                            # Valida se os fornecedores são iguais
                            if str(codigo_laboratorio).strip() == str(divisao).strip():
                                if str(verba_utilizada) == "0":
                                    # Aplica o número da verba para caso esteja vazia
                                    aplica_numero_verba(navegador=navegador, numero_verba=verba, numero_verba_auxiliar=verba_auxiliar, linha_atual=linha)                    

                                # Valida os dados do item
                                if float(str(valor_verba_utilizada).replace(",", ".").replace("M", "")) > 0.01 and str(porcentagem_desconto_promocional) == "0.00" and float(margem_produto) > 1:
                                    valor_verba_utilizada = ajuste_verba(valor_verba_utilizada=valor_verba_utilizada, margem_item=margem_produto)

                                    # Altera o valor da verba na coleção
                                    colecao_linhas[linha] = valor_verba_utilizada

                                    # Equaliza o valor de verba
                                    equaliza_margem(navegador=navegador, verba_utilizar=valor_verba_utilizada, linha_atual=linha)

                                    # Obtém o valor da margem do produto
                                    margem_produto = navegador.find_element("xpath", f"/html/body/form/table/tbody/tr[{linha}]/td[12]/span").text

                                    # Enquanto a margem ficar negativa, vai adicionando pontos percentuais até ficar positivo
                                    while float(margem_produto) < 1:
                                        # Aguarda um tempo para digitar os textos
                                        time.sleep(0.35)
                                        
                                        # Obtém os percentuais do pedido
                                        elemento_verba = navegador.find_element("xpath", f"/html/body/form/table/tbody/tr[{linha}]/td[16]/input")
                                        verba_utilizada = elemento_verba.get_attribute("value")

                                        valor_verba_utilizada = float(str(valor_verba_utilizada).replace("M", "")) + 0.01

                                        if valor_verba_utilizada <= float(verba_necessaria):
                                            # Altera o valor da verba na coleção
                                            colecao_linhas[linha] = valor_verba_utilizada

                                            # Ajusta a verba do item
                                            equaliza_margem(navegador=navegador, verba_utilizar=valor_verba_utilizada, linha_atual=linha)                                           

                                            margem_produto = navegador.find_element("xpath", f"/html/body/form/table/tbody/tr[{linha}]/td[12]/span").text

                                        else:
                                            break

                                    # Aguarda o ajuste da verba dos itens
                                    time.sleep(0.35)
                                    
                                    # Obtém os percentuais do pedido
                                    percentual_porcentagem_bloqueio = navegador.find_element("id", f"margemPB").text
                                    percentual_minima_bloqueio = navegador.find_element("id", f"pc_margem_ponderada_bloqueio").text

                                    if percentual_minima_bloqueio == "":
                                        # Caso o percentual de bloqueio esteja vazio, atualiza o valor
                                        percentual_minima_bloqueio, percentual_porcentagem_bloqueio = atualiza_percentual_bloqueio(navegador=navegador, percentual_minima_bloqueio=percentual_minima_bloqueio)

                                    # Calcula a diferença de valores
                                    diferenca_valores = float(str(percentual_minima_bloqueio).replace(",", ".")) - float(percentual_porcentagem_bloqueio)
                                    
                                    # Valida se a diferença de valores está aceitável
                                    if -0.05 <= diferenca_valores <= 0.01:
                                        boolean_percentual_bloqueio = True

                                        break
                                    
                                    # Caso a margem do pedido esteja equalizado com a mínima para bloqueio, libera o pedido
                                    # if float(str(percentual_porcentagem_bloqueio).replace(",", ".").strip()) == float(str(percentual_minima_bloqueio).replace(",", ".").strip()):
                                    #     boolean_percentual_bloqueio = True

                                    #     break

                                    # Caso a margem do pedido fique abaixo da mínima, ajusta o valor da verba do item até ficar positivo
                                    elif float(str(percentual_porcentagem_bloqueio).replace(",", ".").strip()) < float(str(percentual_minima_bloqueio).replace(",", ".").strip()):
                                        while float(str(percentual_porcentagem_bloqueio).replace(",", ".").strip()) < float(str(percentual_minima_bloqueio).replace(",", ".").strip()) and (float(verba_necessaria) >= float(valor_verba_utilizada)):
                                            # Aguarda um tempo para digitar os textos
                                            time.sleep(0.35)
                                            
                                            valor_verba_utilizada = float(str(valor_verba_utilizada).replace("M", "")) + 0.01

                                            if valor_verba_utilizada <= float(verba_necessaria):
                                                # Altera o valor da verba na coleção
                                                colecao_linhas[linha] = valor_verba_utilizada

                                                # Ajusta a verba do item
                                                equaliza_margem(navegador=navegador, verba_utilizar=valor_verba_utilizada, linha_atual=linha)
                                                
                                                # Aguarda um tempo depois de alterar a verba
                                                time.sleep(0.20)

                                                percentual_porcentagem_bloqueio = navegador.find_element("id", f"margemPB").text
                                                percentual_minima_bloqueio = navegador.find_element("id", f"pc_margem_ponderada_bloqueio").text

                                                # Calcula a diferença de valores
                                                diferenca_valores = float(percentual_minima_bloqueio) - float(percentual_porcentagem_bloqueio)

                                                # Valida se a diferença de valores está aceitável
                                                if -0.05 <= diferenca_valores <= 0.01:
                                                    boolean_percentual_bloqueio = True

                                                    break

                                            else:
                                                break

                                        break

                                    elif linha == 1 and float(str(valor_verba_utilizada).replace(",", ".").replace("M", "")) == 0.01:
                                        valor_verba_primeiro_item = 0.01

                                    # Seo primeiro e o último item forem iguais a 0.01, então sai do laço
                                    if linha == quantidade_linhas - 1 and (round(float(str(valor_verba_utilizada).replace(",", ".").replace("M", "")), 2) == 0.01 or round(float(str(valor_verba_utilizada).replace(",", ".").replace("M", "")), 2) == 0.00) and (round(valor_verba_primeiro_item, 2) == 0.01 or round(valor_verba_primeiro_item, 2) == 0.00):
                                        boolean_percentual_bloqueio = True

                    # Quando não encontrar a indústria
                    else:
                        if linha == quantidade_linhas - 1 and encontrou_fornecedor == False:
                            boolean_percentual_bloqueio = True

    # Valida se há apenas um laboratório
    else:
        laboratorio = list(colecao_media_lab.keys())[0]

        # Itera sobre a tabela do Google Sheet
        for comprador, divisao, fornecedor, uf, desconto, desconto_negociacoes, margem_atingir, verba, verba_auxiliar in tabela_base_sheet:
            # Valida se os fornecedores são iguais
            if str(laboratorio).strip() == str(divisao).strip():
                # Valida os dados da verba
                if ("verba" not in str(margem_atingir).lower().strip() and str(margem_atingir).strip() != "0,00"):
                    if (float(str(margem_atingir).replace(",", ".").strip()) > 0):
                        #Obtém os dados da mínima e porcentagem do pedido
                        percentual_porcentagem_bloqueio = navegador.find_element("id", f"margemPB").text

                        if percentual_porcentagem_bloqueio == "":
                            # Caso o percentual de bloqueio esteja vazio, atualiza o valor
                            percentual_minima_bloqueio, percentual_porcentagem_bloqueio = atualiza_percentual_bloqueio(navegador=navegador, percentual_minima_bloqueio=percentual_porcentagem_bloqueio)

                            # Ordena os itens por verba
                            # Verifica se o elemento está carregado na página
                            elemento_pagina = navegador.find_element(By.ID, f"th-verba-necessaria")

                            # Clica no elemento de voltar
                            navegador.execute_script("arguments[0].click();", elemento_pagina)

                            time.sleep(0.2)

                            # Ordena os itens por verba
                            # Verifica se o elemento está carregado na página
                            elemento_pagina = navegador.find_element(By.ID, f"th-verba-necessaria")

                            # Clica no elemento de voltar
                            navegador.execute_script("arguments[0].click();", elemento_pagina)

                            time.sleep(0.2)

                            # Ordena os itens por laboratório
                            # Verifica se o elemento está carregado na página
                            elemento_pagina = navegador.find_element(By.ID, f"th-nome-fornecedor")

                            # Clica no elemento de voltar
                            navegador.execute_script("arguments[0].click();", elemento_pagina)

                            time.sleep(0.2)

                            # Obtém a tabela dos itens
                            tabela_itens = WebDriverWait(navegador, 120).until(EC.presence_of_element_located((By.ID, "tabelaItens")))

                        if float(percentual_porcentagem_bloqueio) > float(str(margem_atingir).replace(",", ".").strip()):
                            # Define o booleano de bloqueio
                            boolean_percentual_bloqueio = False

                            # Define o valor de verba do primeiro item
                            valor_verba_primeiro_item = 0.00

                            # Enquanto a margem do pedido for acima do bloqueio, vai ajustando os itens para otimizar o uso de verba
                            #while (float(str(percentual_porcentagem_bloqueio).replace(",", ".").strip()) > float(str(margem_atingir).replace(",", ".").strip())) or boolean_percentual_bloqueio == False:

                            while boolean_percentual_bloqueio == False:
                                # Itera sobre os itens
                                for linha in range(1, quantidade_linhas):
                                    # Aguarda um tempo para digitar os textos
                                    time.sleep(0.35)

                                    # Obtém os dados do item
                                    valor_verba_utilizada, verba_utilizada, verba_necessaria, porcentagem_desconto_promocional, margem_produto, codigo_laboratorio = obtem_dados_item(navegador=navegador, linha=linha)

                                    # Obtém o valor de verba da coleção
                                    valor_verba_utilizada = colecao_linhas[linha]

                                    if str(verba_utilizada) == "0":
                                        # Aplica o número da verba para caso esteja vazia
                                        aplica_numero_verba(navegador=navegador, numero_verba=verba, numero_verba_auxiliar=verba_auxiliar, linha_atual=linha)

                                    # Valida os dados do item
                                    if float(str(valor_verba_utilizada).replace(",", ".").replace("M", "")) > 0.01 and str(porcentagem_desconto_promocional) == "0.00" and float(margem_produto) > 1:
                                        valor_verba_utilizada = ajuste_verba(valor_verba_utilizada=valor_verba_utilizada, margem_item=margem_produto)

                                        # Altera o valor da verba na coleção
                                        colecao_linhas[linha] = valor_verba_utilizada

                                        # Ajusta a verba do item
                                        equaliza_margem(navegador=navegador, verba_utilizar=valor_verba_utilizada, linha_atual=linha)

                                        margem_produto = navegador.find_element("xpath", f"/html/body/form/table/tbody/tr[{linha}]/td[12]/span").text

                                        # Enquanto a margem ficar negativa, vai adicionando pontos percentuais até ficar positivo
                                        while float(margem_produto) < 1:
                                            # Aguarda um tempo para digitar os textos
                                            time.sleep(0.35)

                                            elemento_verba = navegador.find_element("xpath", f"/html/body/form/table/tbody/tr[{linha}]/td[16]/input")
                                            verba_utilizada = elemento_verba.get_attribute("value")

                                            valor_verba_utilizada = float(str(valor_verba_utilizada).replace("M", "")) + 0.01

                                            if valor_verba_utilizada <= float(verba_necessaria):
                                                # Altera o valor da verba na coleção
                                                colecao_linhas[linha] = valor_verba_utilizada

                                                # Ajusta a verba do item
                                                equaliza_margem(navegador=navegador, verba_utilizar=valor_verba_utilizada, linha_atual=linha)

                                                margem_produto = navegador.find_element("xpath", f"/html/body/form/table/tbody/tr[{linha}]/td[12]/span").text

                                            else:
                                                break

                                        # Espera carregar
                                        time.sleep(0.35)
                                        
                                        percentual_porcentagem_bloqueio = navegador.find_element("id", f"margemPB").text

                                        # Calcula a diferença de valores
                                        diferenca_valores = float(str(margem_atingir).replace(",", ".")) - float(percentual_porcentagem_bloqueio)
                                        
                                        # Valida se a diferença de valores está aceitável
                                        if -0.05 <= diferenca_valores <= 0.01:
                                            boolean_percentual_bloqueio = True

                                            break

                                        # Caso a margem do pedido esteja equalizado com a mínima para bloqueio, libera o pedido
                                        # if float(str(percentual_porcentagem_bloqueio).replace(",", ".").strip()) == float(str(margem_atingir).replace(",", ".").strip()):
                                            # boolean_percentual_bloqueio = True

                                            # break

                                        # Caso a margem do pedido fique abaixo da mínima, ajusta o valor da verba do item até ficar positivo
                                        elif float(str(percentual_porcentagem_bloqueio).replace(",", ".").strip()) < float(str(margem_atingir).replace(",", ".").strip()):
                                            while float(str(percentual_porcentagem_bloqueio).replace(",", ".").strip()) < float(str(margem_atingir).replace(",", ".").strip()) and (float(verba_necessaria) >= float(valor_verba_utilizada)):
                                                # Aguarda um tempo para digitar os textos
                                                time.sleep(0.35)

                                                valor_verba_utilizada = float(str(valor_verba_utilizada).replace("M", "")) + 0.01

                                                if valor_verba_utilizada <= float(verba_necessaria):
                                                    # Altera o valor da verba na coleção
                                                    colecao_linhas[linha] = valor_verba_utilizada

                                                    # Ajusta a verba do item
                                                    equaliza_margem(navegador=navegador, verba_utilizar=valor_verba_utilizada, linha_atual=linha)

                                                    # Aguarda um tempo depois de alterar a verba
                                                    #time.sleep(0.35)

                                                    percentual_porcentagem_bloqueio = navegador.find_element("id", f"margemPB").text
                                                    percentual_minima_bloqueio = navegador.find_element("id", f"pc_margem_ponderada_bloqueio").text

                                                    # Calcula a diferença de valores
                                                    diferenca_valores = float(str(margem_atingir).replace(",", ".")) - float(percentual_porcentagem_bloqueio)

                                                    # Valida se a diferença de valores está aceitável
                                                    if -0.05 <= diferenca_valores <= 0.01:
                                                        boolean_percentual_bloqueio = True

                                                        break

                                                else:
                                                    break

                                            break

                                    elif linha == 1 and float(str(valor_verba_utilizada).replace(",", ".").replace("M", "")) == 0.01:
                                        valor_verba_primeiro_item = 0.01

                                    # Seo primeiro e o último item forem iguais a 0.01, então sai do laço
                                    if linha == quantidade_linhas - 1 and (round(float(str(valor_verba_utilizada).replace(",", ".").replace("M", "")), 2) == 0.01 or round(float(str(valor_verba_utilizada).replace(",", ".").replace("M", "")), 2) == 0.00) and (round(valor_verba_primeiro_item, 2) == 0.01 or round(valor_verba_primeiro_item, 2) == 0.00):
                                        boolean_percentual_bloqueio = True

                # Se não há a palavra "verba" na coluna de margem, ou a margem não é 0,00 e a margem para atingir é maior que zero
                else:
                    #Obtém os dados da mínima e porcentagem do pedido
                    percentual_porcentagem_bloqueio = navegador.find_element("id", f"margemPB").text
                    percentual_minima_bloqueio = navegador.find_element("id", f"pc_margem_ponderada_bloqueio").text

                    if percentual_minima_bloqueio == "":
                        # Caso o percentual de bloqueio esteja vazio, atualiza o valor
                        percentual_minima_bloqueio, percentual_porcentagem_bloqueio = atualiza_percentual_bloqueio(navegador=navegador, percentual_minima_bloqueio=percentual_minima_bloqueio)

                        # Ordena os itens por verba
                        # Verifica se o elemento está carregado na página
                        elemento_pagina = navegador.find_element(By.ID, f"th-verba-necessaria")

                        # Clica no elemento de voltar
                        navegador.execute_script("arguments[0].click();", elemento_pagina)

                        time.sleep(0.2)

                        # Ordena os itens por verba
                        # Verifica se o elemento está carregado na página
                        elemento_pagina = navegador.find_element(By.ID, f"th-verba-necessaria")

                        # Clica no elemento de voltar
                        navegador.execute_script("arguments[0].click();", elemento_pagina)

                        time.sleep(0.2)

                        # Ordena os itens por laboratório
                        # Verifica se o elemento está carregado na página
                        elemento_pagina = navegador.find_element(By.ID, f"th-nome-fornecedor")

                        # Clica no elemento de voltar
                        navegador.execute_script("arguments[0].click();", elemento_pagina)

                        time.sleep(0.2)

                        # Obtém a tabela dos itens
                        tabela_itens = WebDriverWait(navegador, 120).until(EC.presence_of_element_located((By.ID, "tabelaItens")))

                    if float(percentual_porcentagem_bloqueio) > float(percentual_minima_bloqueio):
                        # Define o booleano de bloqueio
                        boolean_percentual_bloqueio = False

                        # Define o valor de verba do primeiro item
                        valor_verba_primeiro_item = 0.00

                        #while (float(str(percentual_porcentagem_bloqueio).replace(",", ".").strip()) > float(str(percentual_minima_bloqueio).replace(",", ".").strip())) or boolean_percentual_bloqueio == False:

                        while boolean_percentual_bloqueio == False:
                            for linha in range(1, quantidade_linhas):
                                # Aguarda um tempo para digitar os textos
                                time.sleep(0.35)

                                valor_verba_utilizada, verba_utilizada, verba_necessaria, porcentagem_desconto_promocional, margem_produto, codigo_laboratorio = obtem_dados_item(navegador=navegador, linha=linha)

                                # Obtém o valor de verba da coleção
                                valor_verba_utilizada = colecao_linhas[linha]

                                if str(verba_utilizada) == "0":
                                    # Aplica o número da verba para caso esteja vazia
                                    aplica_numero_verba(navegador=navegador, numero_verba=verba, numero_verba_auxiliar=verba_auxiliar, linha_atual=linha)

                                if float(str(valor_verba_utilizada).replace(",", ".").replace("M", "")) > 0.01 and str(porcentagem_desconto_promocional) == "0.00" and float(margem_produto) > 1:
                                    valor_verba_utilizada = ajuste_verba(valor_verba_utilizada=valor_verba_utilizada, margem_item=margem_produto)

                                    # Altera o valor da verba na coleção
                                    colecao_linhas[linha] = valor_verba_utilizada

                                    equaliza_margem(navegador=navegador, verba_utilizar=valor_verba_utilizada, linha_atual=linha)

                                    margem_produto = navegador.find_element("xpath", f"/html/body/form/table/tbody/tr[{linha}]/td[12]/span").text

                                    while float(margem_produto) < 1:
                                        # Aguarda um tempo para digitar os textos
                                        time.sleep(0.35)

                                        elemento_verba = navegador.find_element("xpath", f"/html/body/form/table/tbody/tr[{linha}]/td[16]/input")
                                        verba_utilizada = elemento_verba.get_attribute("value")

                                        valor_verba_utilizada = float(str(valor_verba_utilizada).replace("M", "")) + 0.01
                                        
                                        if valor_verba_utilizada <= float(verba_necessaria):
                                            # Altera o valor da verba na coleção
                                            colecao_linhas[linha] = valor_verba_utilizada

                                            equaliza_margem(navegador=navegador, verba_utilizar=valor_verba_utilizada, linha_atual=linha)

                                            # Aguarda um tempo para digitar os textos
                                            time.sleep(0.35)

                                            margem_produto = navegador.find_element("xpath", f"/html/body/form/table/tbody/tr[{linha}]/td[12]/span").text

                                        else:
                                            break

                                    # Aguarda um tempo
                                    time.sleep(0.35)

                                    percentual_porcentagem_bloqueio = navegador.find_element("id", f"margemPB").text
                                    percentual_minima_bloqueio = navegador.find_element("id", f"pc_margem_ponderada_bloqueio").text

                                    if percentual_minima_bloqueio == "":
                                        # Caso o percentual de bloqueio esteja vazio, atualiza o valor
                                        percentual_minima_bloqueio, percentual_porcentagem_bloqueio = atualiza_percentual_bloqueio(navegador=navegador, percentual_minima_bloqueio=percentual_minima_bloqueio)

                                    # Aguarda um tempo
                                    time.sleep(0.35)

                                    percentual_porcentagem_bloqueio = navegador.find_element("id", f"margemPB").text
                                    percentual_minima_bloqueio = navegador.find_element("id", f"pc_margem_ponderada_bloqueio").text
                                    
                                    # Calcula a diferença de valores
                                    diferenca_valores = float(str(percentual_minima_bloqueio).replace(",", ".")) - float(percentual_porcentagem_bloqueio)
                                        
                                    # Valida se a diferença de valores está aceitável
                                    if -0.05 <= diferenca_valores <= 0.01:
                                        boolean_percentual_bloqueio = True

                                        break
                                    
                                    # if float(str(percentual_porcentagem_bloqueio).replace(",", ".").strip()) == float(str(margem_atingir).replace(",", ".").strip()):
                                    #     boolean_percentual_bloqueio = True

                                    #     break

                                    elif float(str(percentual_porcentagem_bloqueio).replace(",", ".").strip()) < float(str(percentual_minima_bloqueio).replace(",", ".").strip()):
                                        while float(str(percentual_porcentagem_bloqueio).replace(",", ".").strip()) < float(str(percentual_minima_bloqueio).replace(",", ".").strip()) and (float(verba_necessaria) >= float(valor_verba_utilizada)):
                                            # Aguarda um tempo para digitar os textos
                                            time.sleep(0.35)

                                            valor_verba_utilizada = float(str(valor_verba_utilizada).replace("M", "")) + 0.01

                                            if valor_verba_utilizada <= float(verba_necessaria):
                                                # Altera o valor da verba na coleção
                                                colecao_linhas[linha] = valor_verba_utilizada

                                                equaliza_margem(navegador=navegador, verba_utilizar=valor_verba_utilizada, linha_atual=linha)

                                                # Aguarda um tempo depois de alterar a verba
                                                time.sleep(0.35)

                                                percentual_porcentagem_bloqueio = navegador.find_element("id", f"margemPB").text
                                                percentual_minima_bloqueio = navegador.find_element("id", f"pc_margem_ponderada_bloqueio").text

                                                # Calcula a diferença de valores
                                                diferenca_valores = float(str(percentual_minima_bloqueio).replace(",", ".")) - float(percentual_porcentagem_bloqueio)

                                                # Valida se a diferença de valores está aceitável
                                                if -0.05 <= diferenca_valores <= 0.01:
                                                    boolean_percentual_bloqueio = True

                                                    break

                                            else:
                                                break

                                        break

                                elif linha == 1 and float(str(valor_verba_utilizada).replace(",", ".").replace("M", "")) == 0.01:
                                    valor_verba_primeiro_item = 0.01

                                # Seo primeiro e o último item forem iguais a 0.01, então sai do laço
                                if linha == quantidade_linhas - 1 and (round(float(str(valor_verba_utilizada).replace(",", ".").replace("M", "")), 2) == 0.01 or round(float(str(valor_verba_utilizada).replace(",", ".").replace("M", "")), 2) == 0.00) and (round(valor_verba_primeiro_item, 2) == 0.01 or round(valor_verba_primeiro_item, 2) == 0.00):
                                    boolean_percentual_bloqueio = True


# Obtém os dados do item
def obtem_dados_item(navegador, linha):
    """
    Obtém os dados do item

    Parameters:
    navegador = navigator
    linha = int

    Returns:
    valor_verba_utilizada = float
    verba_utilizada = float
    verba_necessaria = float
    porcentagem_desconto_promocional = float
    margem_produto = float
    """

    #Obtém os valores do item
    elemento_valor_verba = navegador.find_element("xpath", f"/html/body/form/table/tbody/tr[{linha}]/td[17]/input")
    valor_verba_utilizada = elemento_valor_verba.get_attribute("value")

    elemento_verba = navegador.find_element("xpath", f"/html/body/form/table/tbody/tr[{linha}]/td[16]/input")
    verba_utilizada = elemento_verba.get_attribute("value")

    verba_necessaria = navegador.find_element("xpath", f"/html/body/form/table/tbody/tr[{linha}]/td[15]/span").text

    porcentagem_desconto_promocional = navegador.find_element("xpath", f"/html/body/form/table/tbody/tr[{linha}]/td[11]/span").text

    margem_produto = navegador.find_element("xpath", f"/html/body/form/table/tbody/tr[{linha}]/td[12]/span").text

    codigo_fornecedor = navegador.find_element("xpath", f"/html/body/form/table/tbody/tr[{linha}]/td[20]").text

    return valor_verba_utilizada, verba_utilizada, verba_necessaria, porcentagem_desconto_promocional, margem_produto, codigo_fornecedor


# Atualiza o percentual de bloqueio
def atualiza_percentual_bloqueio(navegador, percentual_minima_bloqueio):
    """
    Atualiza o percentual de bloqueio

    Parameters:
    navegador = navigator
    percentual_minima_bloqueio = string
    
    Returns:
    percentual_minima_bloqueio = string
    """

    navegador.refresh()

    trata_alerta(navegador=navegador)

    time.sleep(3)

    #Obtém os dados da mínima e porcentagem do pedido
    WebDriverWait(navegador, 60).until(EC.presence_of_element_located((By.ID, "margemPB")))

    percentual_porcentagem_bloqueio = navegador.find_element("id", f"margemPB").text
    percentual_minima_bloqueio = navegador.find_element("id", f"pc_margem_ponderada_bloqueio").text
    percentual_porcentagem_bloqueio = navegador.find_element("id", f"margemPB").text

    return percentual_minima_bloqueio, percentual_porcentagem_bloqueio


#Ajusta a verba a ser utilizada
def ajuste_verba(valor_verba_utilizada, margem_item):
    """
    Equaliza a margem para otimizar o uso de verba

    Parameters:
    valor_verba_utilizada = float
    margem_item = float
    
    Returns:
    valor_verba_utilizada = float
    """

    # Valida se a verba utilizada é maior do que 5.00 e a margem do item é maior do que 7.00
    if float(str(valor_verba_utilizada).replace("M", "")) > 3 and float(str(margem_item).replace(",", ".")) > 3:
        # Reduz 1,00 da verba utilizada no item no momento para otimizar o uso de verba x margem
        valor_verba_utilizada = float(str(valor_verba_utilizada).replace("M", "")) - 1.00

    # Valida se a verba utilizada é menor do que 5.00 e maior que 2.00 e a margem do item é maior do que 7.00
    elif (float(str(valor_verba_utilizada).replace("M", "")) < 3 and float(str(valor_verba_utilizada).replace("M", "")) > 1) and float(str(margem_item).replace(",", ".")) > 3:
        # Reduz 0,50 da verba utilizada no item no momento para otimizar o uso de verba x margem
        valor_verba_utilizada = float(str(valor_verba_utilizada).replace("M", "")) - 0.50
    
    # Caso não entre em nenhuma das duas validações acima, retira apenas 0.01 do valor da verba
    else:
        # Reduz 0,01 da verba utilizada no item no momento para otimizar o uso de verba x margem
        valor_verba_utilizada = float(str(valor_verba_utilizada).replace("M", "")) - 0.01

    # Caso a verba fique negativa ou zero, ajusta para 0.01
    if float(valor_verba_utilizada) < 0.00 or float(valor_verba_utilizada) == 0.00:
        valor_verba_utilizada = 0.01

    return valor_verba_utilizada


#Equaliza a margem para otimizar o uso de verba
def equaliza_margem(navegador, verba_utilizar, linha_atual):
    """
    Equaliza a margem para otimizar o uso de verba

    Parameters:
    navegador = navigator
    verba_necessaria_tela = float
    linha_atual = int
    """

    # Deleta a informação que pode estar no campo
    # Verifica se o elemento está carregado na página
    elemento_pagina = navegador.find_element(By.XPATH, f"/html/body/form/table/tbody/tr[{linha_atual}]/td[17]/input")

    # Força o foco no campo com um clique
    elemento_pagina.click()

    # Ajuste no timer
    time.sleep(0.35)

    # Simula a tecla "Home" para mover o cursor para o início
    elemento_pagina.send_keys(Keys.HOME)

    # Pequena pausa para garantir que o Home foi pressionado
    time.sleep(0.35)

    # Simula pressionar a tecla "Delete" quatro vezes
    for _ in range(5):
        elemento_pagina.send_keys(Keys.DELETE)
        # Pequena pausa entre as teclas para simular o comportamento humano
        #time.sleep(0.1)

    # Verifica se o elemento está carregado na página
    elemento_pagina = navegador.find_element(By.XPATH, f"/html/body/form/table/tbody/tr[{linha_atual}]/td[17]/input")

    #time.sleep(1)
    
    # Clica no elemento
    elemento_pagina.click()

    #time.sleep(1)

    # Formata o valor com duas casas decimais
    valor_formatado = f"{float(verba_utilizar):.2f}M"

    # Digita o valor caractere por caractere da verba necessária
    for char in valor_formatado:
        elemento_pagina.send_keys(char)
        # Pequena pausa entre as teclas para simular a digitação humana
        #time.sleep(0.1)

    #time.sleep(1)
    
    # Dá tab após configurar o valor
    elemento_pagina.send_keys(Keys.TAB)

    # Espera o sistema confirmar a alteração
    elemento = navegador.find_element("xpath", f"/html/body/form/table/tbody/tr[{linha_atual}]/td[17]/span")
    # Pegue o valor do atributo "class"
    valor_classe = elemento.get_attribute('class')

    contador = 0

    while "ok" not in valor_classe:
        # Espera o sistema confirmar a alteração
        elemento = navegador.find_element("xpath", f"/html/body/form/table/tbody/tr[{linha_atual}]/td[17]/span")
        # Pegue o valor do atributo "class"
        valor_classe = elemento.get_attribute('class')

        contador += 1

        if contador == 10:
            break
    
    # Aguarda um tempo depois de alterar a verba
    time.sleep(0.20)

    #time.sleep(0.01)


################# INUTILIZADO #################
#Analisa o desconto da tabela x desconto tela de pedidos
def analisa_desconto_tela_tabela_uma_industria(navegador, tabela, codigo_fornecedor, uf_cliente, percentual_desconto_tela, verba_necessaria_tela, verba_media_laboratorio_tela, verba_utilizada, linha_atual):
    """
    Analisa o desconto da tabela x desconto tela de pedidos

    Parameters:
    navegador = navigator
    tabela = collection
    codigo_fornecedor = string
    uf_cliente = string
    percentual_desconto_tela = float
    verba_necessaria_tela = float
    verba_media_laboratorio_tela = float
    verba_utilizada = float
    linha_atual = int
    """

    # Itera sobre os itens da tabela do Google Sheet
    for comprador, divisao, fornecedor, uf, desconto, desconto_negociacoes, margem_atingir, verba, verba_auxiliar in tabela:
        # Valida os fornecedores e dados
        if str(codigo_fornecedor) == str(divisao) and (uf_cliente in uf or "Todos" in uf) and ("Usar verba até" not in margem_atingir):
            retorno_porcentagem_minima_uma_industria = valida_porcentagem_pedido_minima_uma_industria(navegador=navegador, margem_atingir=margem_atingir)

            if retorno_porcentagem_minima_uma_industria == True:
                break


#Analisa se a porcentagem mínima está acima da margem do sheet
def valida_porcentagem_pedido_minima_uma_industria(navegador, margem_atingir):
    """
    Analisa se a porcentagem mínima está acima da margem do sheet

    Parameters:
    navegador = navigator
    margem_atingir = float
    """

    # Espera carregar a tabela de pedidos
    WebDriverWait(navegador, 60).until(EC.presence_of_element_located((By.ID, "margemPB")))
    porcentagem_pedido_bloqueio = navegador.find_element("id", f"margemPB").text
    float_porcentagem_pedido_bloqueio = float(porcentagem_pedido_bloqueio)

    if float_porcentagem_pedido_bloqueio >= float(str(margem_atingir).replace(",", ".").strip()) and (float(str(margem_atingir).replace(",", ".").strip()) > 0):
        return True


#Analisa o desconto da tabela x desconto tela de pedidos
def analisa_desconto_tela_tabela(navegador, tabela, codigo_fornecedor, uf_cliente, percentual_desconto_tela, verba_necessaria_tela, verba_media_laboratorio_tela, verba_utilizada, linha_atual):
    """
    Analisa o desconto da tabela x desconto tela de pedidos

    Parameters:
    navegador = navigator
    tabela = collection
    codigo_fornecedor = string
    uf_cliente = string
    percentual_desconto_tela = float
    verba_necessaria_tela = float
    verba_media_laboratorio_tela = float
    verba_utilizada = float
    linha_atual = int
    """

    # Itera sobre os dados da tabela do Google Sheet
    for comprador, divisao, fornecedor, uf, desconto, desconto_negociacoes, margem_atingir, verba, verba_auxiliar in tabela:
        # Valida a UF do cliente e a informação de margem para que seja comparado com os dados em tela
        if str(codigo_fornecedor) == str(divisao) and (uf_cliente in uf or "Todos" in uf) and ("Usar verba até" in margem_atingir):
            # Obtém os percentuais de desconto
            float_percentual_desconto_tela = float(str(percentual_desconto_tela).replace(",", ".").strip())
            float_percentual_desconto_negociacoes_tabela_base = float(str(desconto_negociacoes).replace(",", ".").strip())

            # Caso o desconto da tela seja menor ou igual ao da tabela de base, prossegue com as informações
            if float_percentual_desconto_tela <= float_percentual_desconto_negociacoes_tabela_base:
                # Valida se a verba foi "linkada"
                if str(verba_utilizada) == "0":
                    # Aplica o número da verba para caso esteja vazia
                    aplica_numero_verba(navegador=navegador, numero_verba=verba, numero_verba_auxiliar=verba_auxiliar, linha_atual=linha_atual)

                # Espera um segundo para que a verba seja "linkada"
                #time.sleep(1)
                
                # Obtém o número da verba depois de fazer a aplicação
                elemento_verba_utilizada = navegador.find_element("xpath", f"/html/body/form/table/tbody/tr[{linha_atual}]/td[16]/input")
                verba_utilizada = elemento_verba_utilizada.get_attribute("value")

                # Caso a verba tenha sido corretamente informada, segue o processo
                if str(verba_utilizada) != "0":
                    # Verifica o valor de R$ Verba para ser aplicado por item
                    #valida_margem_verba(navegador=navegador, verba_necessaria_tela=verba_necessaria_tela, verba_media_laboratorio_tela=verba_media_laboratorio_tela, linha_atual=linha_atual)

                    # TESTE COM A VERBA MÁXIMA POR ITEM
                    valida_margem_verba(navegador=navegador, verba_necessaria_tela=verba_necessaria_tela, verba_media_laboratorio_tela=verba_necessaria_tela, linha_atual=linha_atual)

                    # Após aplicar o R$ Verba, valida se a margem bruta do item ficou acima de 0,00
                    valida_margem_bruta_item(navegador=navegador, linha_atual=linha_atual, verba_necessaria_tela=verba_necessaria_tela)

            break

        # Valida a UF do cliente e a informação de margem, para que seja comparada com as informações do Google Sheet
        elif str(codigo_fornecedor) == str(divisao) and (uf_cliente in uf or "Todos" in uf) and ("Usar verba até" not in margem_atingir):
            # # Se houver valor de margem para atingir e for a primeira indústria, verifica se a margem já foi atingida
            # if linha_atual == 1:
            #     retorno_validacao = valida_porcentagem_pedido_minima_uma_industria(navegador=navegador, margem_atingir=margem_atingir)
            
            # # Caso a porcentagem do pedido não tenha sido atendida, irá retornar falso para entrar no processo de validação item a item
            # else:
            #     retorno_validacao = False

            # # Valida se o pedido já foi liberado
            # if retorno_validacao == True:
            #     return True

            # else:
            # Caso não possua verba, "linka" no sistema
            if str(verba_utilizada) == "0":
                # Aplica o número da verba para caso esteja vazia
                aplica_numero_verba(navegador=navegador, numero_verba=verba, numero_verba_auxiliar=verba_auxiliar, linha_atual=linha_atual)

            # Espera um segundo até a verba estar vinculada
            #time.sleep(1)
            
            # Obtém o valor da verba utilizada
            elemento_verba_utilizada = navegador.find_element("xpath", f"/html/body/form/table/tbody/tr[{linha_atual}]/td[16]/input")
            verba_utilizada = elemento_verba_utilizada.get_attribute("value")

            if verba_utilizada != "0":
                # Verifica o valor de R$ Verba para ser aplicado por item
                #valida_margem_verba(navegador=navegador, verba_necessaria_tela=verba_necessaria_tela, verba_media_laboratorio_tela=verba_media_laboratorio_tela, linha_atual=linha_atual)

                # TESTE COM A VERBA MÁXIMA DO ITEM
                valida_margem_verba(navegador=navegador, verba_necessaria_tela=verba_necessaria_tela, verba_media_laboratorio_tela=verba_necessaria_tela, linha_atual=linha_atual)

                # Após aplicar o R$ Verba, valida se a margem bruta do item ficou acima de 0,00
                valida_margem_bruta_item(navegador=navegador, linha_atual=linha_atual, verba_necessaria_tela=verba_necessaria_tela)

            break


#Aplica número verba
def aplica_numero_verba(navegador, numero_verba, linha_atual, numero_verba_auxiliar):
    """
    Aplica número verba

    Parameters:
    navegador = navigator
    numero_verba = int
    linha_atual = int
    numero_verba_auxiliar = int
    """

    # Valida a informação do Google Sheet, caso tenha informação "Sistema" na coluna I
    if "sistema" in str(numero_verba).lower():
        # Valida a verba auxiliar do Google Sheet, caso tenha informação "Sistema" na coluna J
        if "sistema" in str(numero_verba_auxiliar).lower():
            # Verifica se o elemento está carregado na página
            elemento_pagina = navegador.find_element(By.XPATH, f"/html/body/form/table/tbody/tr[{linha_atual}]/td[16]/input")

            # Clica no elemento da verba
            navegador.execute_script("""var evt = new MouseEvent('dblclick', {
                bubbles: true,
                cancelable: true,
                view: window
            });
            arguments[0].dispatchEvent(evt);""", elemento_pagina)

            # Esperar até que o combobox esteja presente
            combobox = WebDriverWait(navegador, 10).until(
                EC.presence_of_element_located((By.XPATH, f"/html/body/form/table/tbody/tr[{linha_atual}]/td[16]/span[1]/table/tbody/tr[3]/td[1]/select"))
            )

            # Validador de verba
            verba_selecionada = False

            # Criar um objeto Select
            select = Select(combobox)

            # Obter todas as opções do select
            opcoes = select.options

            #Iterar sobre as opções do select (SELECIONAR O QUE ESTÁ COM MELHOR VALOR?)
            for i, opcao in enumerate(opcoes):
                # Exibe o texto de cada opção
                print(f"Índice: {i}. Texto: {opcao.text}")

                if "Selecione" not in opcao.text:
                    lista_texto = (opcao.text).split("|")
                    valor_verba_tela = lista_texto[1]
                    valor_verba_tela = valor_verba_tela.strip()

                    if float(valor_verba_tela) > 0:
                        # Seleciona a verba que tem valor maior que zero
                        select.select_by_index(i) 

                        # Informa que a verba foi selecionada
                        verba_selecionada = True

                        break

            if verba_selecionada == False:
                # Selecionar a segunda opção pelo índice (o índice começa em 0, então 1 é a segunda opção)
                select.select_by_index(1)

            # Espera aparecer a verba
            WebDriverWait(navegador, 120).until(EC.presence_of_element_located((By.ID, f"img-fechar")))

            # Verifica se o elemento está carregado na página
            elemento_pagina = navegador.find_element(By.ID, f"img-fechar")

            # Clica para fechar a janela
            navegador.execute_script("arguments[0].click();", elemento_pagina)

            #time.sleep(1)

            return True
        
        # Valida a verba auxiliar do Google Sheet, caso não tenha informação "Sistema" na coluna J, ou seja, há verba para vincular
        else:
            # Verifica se o elemento está carregado na página
            elemento_pagina = navegador.find_element(By.XPATH, f"/html/body/form/table/tbody/tr[{linha_atual}]/td[16]/input")

            # Clica no elemento da verba
            navegador.execute_script("""var evt = new MouseEvent('dblclick', {
                bubbles: true,
                cancelable: true,
                view: window
            });
            arguments[0].dispatchEvent(evt);""", elemento_pagina)

            # Esperar até que o combobox esteja presente
            combobox = WebDriverWait(navegador, 10).until(
                EC.presence_of_element_located((By.XPATH, f"/html/body/form/table/tbody/tr[{linha_atual}]/td[16]/span[1]/table/tbody/tr[3]/td[1]/select"))
            )

            # Criar um objeto Select
            select = Select(combobox)

            # Selecionar a segunda opção pelo índice (o índice começa em 0, então 1 é a segunda opção)
            select.select_by_value(numero_verba_auxiliar)

            # Espera aparecer a verba
            WebDriverWait(navegador, 120).until(EC.presence_of_element_located((By.ID, f"img-fechar")))

            # Verifica se o elemento está carregado na página
            elemento_pagina = navegador.find_element(By.ID, f"img-fechar")

            # Clica para fechar a janela
            navegador.execute_script("arguments[0].click();", elemento_pagina)

            #time.sleep(1)

            return True
    
    # Valida a informação do Google Sheet, caso não tenha informação "Sem verba" na coluna I, ou seja, há verba para vincular
    elif "sem" not in str(numero_verba).lower():
        # Verifica se o elemento está carregado na página
        elemento_pagina = navegador.find_element(By.XPATH, f"/html/body/form/table/tbody/tr[{linha_atual}]/td[16]/input")

        # Clica no elemento da verba
        navegador.execute_script("""var evt = new MouseEvent('dblclick', {
            bubbles: true,
            cancelable: true,
            view: window
        });
        arguments[0].dispatchEvent(evt);""", elemento_pagina)

        # Esperar até que o combobox esteja presente
        combobox = WebDriverWait(navegador, 10).until(
            EC.presence_of_element_located((By.XPATH, f"/html/body/form/table/tbody/tr[{linha_atual}]/td[16]/span[1]/table/tbody/tr[3]/td[1]/select"))
        )

        # Criar um objeto Select
        select = Select(combobox)

        try:
            # Selecionar a segunda opção pelo índice (o índice começa em 0, então 1 é a segunda opção)
            select.select_by_value(numero_verba)
        except:
            try:
                # Selecionar a segunda opção pelo índice (o índice começa em 0, então 1 é a segunda opção)
                select.select_by_value(numero_verba_auxiliar)
            
            except:
                # Busca os dados do pedido
                numero_pedido = navegador.find_element("id", f"nroPedido").text

                sql = f"select * from comercial.envio_email_liberacao_farma where numero_pedido = '{numero_pedido}'"
                qtd_linhas = conecta_pg(sql=sql)

                if len(str(qtd_linhas)) == 0:
                    # Envia e-mail quando liberar o pedido
                    # Informa os destinatários
                    destinatarios_email = []
                    destinatarios_email.append("nicolas.nasario@EMPRESA.com.br")
                    destinatarios_email.append("lucas.remor@EMPRESA.com.br")
                    destinatarios_email.append("elton@EMPRESA.com.br")
                    destinatarios_email.append("tais.cascaes@EMPRESA.com.br")
                    destinatarios_email.append("amanda.santana@EMPRESA.com.br")
                    destinatarios_email.append("heloisa.henrique@EMPRESA.com.br")

                    # Informa o assunto
                    assunto_email = f"RPA Liberação de Pedidos Farma - Verba não encontrada"

                    # Grava a mensagem
                    mensagem_email = f"""
                    Olá!<br><br> 
                    Favor verificar a planilha de verbas, não há vinculação para os dados abaixo:<br>
                    <strong>Número do pedido: </strong>{str(numero_pedido)}<br>
                    <strong>Verba principal: </strong>{str(numero_verba)}<br>
                    <strong>Verba auxiliar: </strong>{str(numero_verba_auxiliar)}<br><br>

                    O RPA deixará esse pedido pendente e seguirá para o próximo!
                    """

                    # Dispara e-mail de liberação automática
                    envia_email(mensagemEmail=mensagem_email, destinatarios_email=destinatarios_email, assunto_email=assunto_email)

                    sql = f"insert into comercial.envio_email_liberacao_farma (numero_pedido) values ('{numero_pedido}')"
                    conecta_pg_insert(sql=sql)

                    return False
                

        # Espera aparecer a verba
        WebDriverWait(navegador, 120).until(EC.presence_of_element_located((By.ID, f"img-fechar")))

        # Verifica se o elemento está carregado na página
        elemento_pagina = navegador.find_element(By.ID, f"img-fechar")

        # Clica para fechar a janela
        navegador.execute_script("arguments[0].click();", elemento_pagina)

        #time.sleep(1)

        return True
    
    # Valida se há "Sem verba" na coluna I e "Sistema" ou "Sem verba" nas colunas I e J, respectivamente
    elif "sem" in str(numero_verba).lower() and ("sistema" in str(numero_verba_auxiliar).lower() or "sem" in str(numero_verba_auxiliar).lower()):
        # Verifica se o elemento está carregado na página
        elemento_pagina = navegador.find_element(By.XPATH, f"/html/body/form/table/tbody/tr[{linha_atual}]/td[16]/input")

        # Clica no elemento da verba
        navegador.execute_script("""var evt = new MouseEvent('dblclick', {
            bubbles: true,
            cancelable: true,
            view: window
        });
        arguments[0].dispatchEvent(evt);""", elemento_pagina)

        # Esperar até que o combobox esteja presente
        combobox = WebDriverWait(navegador, 10).until(
            EC.presence_of_element_located((By.XPATH, f"/html/body/form/table/tbody/tr[{linha_atual}]/td[16]/span[1]/table/tbody/tr[3]/td[1]/select"))
        )

        # Validador de verba
        verba_selecionada = False

        # Criar um objeto Select
        select = Select(combobox)

        # Obter todas as opções do select
        opcoes = select.options

        # Iterar sobre as opções do select (SELECIONAR O QUE ESTÁ COM MELHOR VALOR?)
        for i, opcao in enumerate(opcoes):
            # Exibe o texto de cada opção
            print(f"Índice: {i}. Texto: {opcao.text}")

            if "Selecione" not in opcao.text:
                lista_texto = (opcao.text).split("|")
                valor_verba_tela = lista_texto[1]
                valor_verba_tela = valor_verba_tela.strip()

                if float(valor_verba_tela) > 0:
                    # Seleciona a verba que tem valor maior que zero
                    select.select_by_index(i)

                    # Informa que a verba foi selecionada
                    verba_selecionada = True

                    break

        if verba_selecionada == False:
            # Selecionar a segunda opção pelo índice (o índice começa em 0, então 1 é a segunda opção)
            select.select_by_index(1)

        # Espera aparecer a verba
        WebDriverWait(navegador, 120).until(EC.presence_of_element_located((By.ID, f"img-fechar")))

        # Verifica se o elemento está carregado na página
        elemento_pagina = navegador.find_element(By.ID, f"img-fechar")

        # Clica para fechar a janela
        navegador.execute_script("arguments[0].click();", elemento_pagina)

        #time.sleep(1)

        return True


#Ajusta a margem do item, somente quando o pedido não passar
def ajusta_margem_item(navegador, verba_necessaria_tela, linha_atual):
    """
    Ajusta a margem do item, somente quando o pedido não passar

    Parameters:
    navegador = navigator
    verba_necessaria_tela = float
    linha_atual = int
    """

    # Deleta a informação que pode estar no campo
    # Verifica se o elemento está carregado na página
    elemento_pagina = navegador.find_element(By.XPATH, f"/html/body/form/table/tbody/tr[{linha_atual}]/td[17]/input")

    # Oculta o elemento que está bloqueando
    navegador.execute_script("document.getElementById('conteudo-fixo').style.display = 'none';")

    # Faz scroll até o elemento
    navegador.execute_script("arguments[0].scrollIntoView(true);", elemento_pagina)

    # Força o foco no campo com um clique
    elemento_pagina.click()

    # Ajuste no timer
    time.sleep(0.35)

    # Simula a tecla "Home" para mover o cursor para o início
    elemento_pagina.send_keys(Keys.HOME)

    # Pequena pausa para garantir que o Home foi pressionado
    time.sleep(0.35)

    # Simula pressionar a tecla "Delete" quatro vezes
    for _ in range(5):
        elemento_pagina.send_keys(Keys.DELETE)
        # Pequena pausa entre as teclas para simular o comportamento humano
        #time.sleep(0.1)

    # Verifica se o elemento está carregado na página
    elemento_pagina = navegador.find_element(By.XPATH, f"/html/body/form/table/tbody/tr[{linha_atual}]/td[17]/input")

    #time.sleep(1)
    
    # Clica no elemento
    elemento_pagina.click()

    #time.sleep(1)

    # Formata o valor com duas casas decimais
    valor_formatado = f"{float(verba_necessaria_tela):.2f}M"

    # Digita o valor caractere por caractere da verba necessária
    for char in valor_formatado:
        elemento_pagina.send_keys(char)
        # Pequena pausa entre as teclas para simular a digitação humana
        #time.sleep(0.1)

    #time.sleep(1)
    
    # Dá tab após configurar o valor
    elemento_pagina.send_keys(Keys.TAB)

    # Espera o sistema confirmar a alteração
    elemento = navegador.find_element("xpath", f"/html/body/form/table/tbody/tr[{linha_atual}]/td[17]/span")
    # Pegue o valor do atributo "class"
    valor_classe = elemento.get_attribute('class')

    contador = 0

    while "ok" not in valor_classe:
        # Espera o sistema confirmar a alteração
        elemento = navegador.find_element("xpath", f"/html/body/form/table/tbody/tr[{linha_atual}]/td[17]/span")
        # Pegue o valor do atributo "class"
        valor_classe = elemento.get_attribute('class')

        contador += 1

        if contador == 10:
            break

    #time.sleep(0.01)


#Verifica margem bruta x verba por item
def valida_margem_verba(navegador, verba_necessaria_tela, verba_media_laboratorio_tela, linha_atual):
    """
    Verifica margem bruta x verba por item

    Parameters:
    navegador = navigator
    verba_necessaria_tela = float
    verba_media_laboratorio_tela = float
    linha_atual = int
    """

    # Deleta a informação que pode estar no campo
    # Verifica se o elemento está carregado na página
    elemento_pagina = navegador.find_element(By.XPATH, f"/html/body/form/table/tbody/tr[{linha_atual}]/td[17]/input")

    # Oculta o elemento que está bloqueando
    navegador.execute_script("document.getElementById('conteudo-fixo').style.display = 'none';")

    # Faz scroll até o elemento
    navegador.execute_script("arguments[0].scrollIntoView(true);", elemento_pagina)

    # Força o foco no campo com um clique
    elemento_pagina.click()

    # Ajuste no timer
    time.sleep(0.35)

    # Simula a tecla "Home" para mover o cursor para o início
    elemento_pagina.send_keys(Keys.HOME)

    # Pequena pausa para garantir que o Home foi pressionado
    time.sleep(0.35)

    # Simula pressionar a tecla "Delete" quatro vezes
    for _ in range(5):
        elemento_pagina.send_keys(Keys.DELETE)
        # Pequena pausa entre as teclas para simular o comportamento humano
        #time.sleep(0.1)

    if float(verba_media_laboratorio_tela) < float(verba_necessaria_tela):
        # Verifica se o elemento está carregado na página
        elemento_pagina = navegador.find_element(By.XPATH, f"/html/body/form/table/tbody/tr[{linha_atual}]/td[17]/input")

        #time.sleep(1)

        #Clica no elemento
        elemento_pagina.click()

        #time.sleep(1)

        # Formata o valor com duas casas decimais
        valor_formatado = f"{float(verba_media_laboratorio_tela):.2f}M"

        # Digita o valor caractere por caractere da verba necessária
        for char in valor_formatado:
            elemento_pagina.send_keys(char)
            # Pequena pausa entre as teclas para simular a digitação humana
            #time.sleep(0.1)

        #time.sleep(1)    
        
        # Dá tab após configurar o valor
        elemento_pagina.send_keys(Keys.TAB)

        #time.sleep(0.01)

    else:
        # Verifica se o elemento está carregado na página
        elemento_pagina = navegador.find_element(By.XPATH, f"/html/body/form/table/tbody/tr[{linha_atual}]/td[17]/input")

        # Oculta o elemento que está bloqueando
        navegador.execute_script("document.getElementById('conteudo-fixo').style.display = 'none';")

        #time.sleep(1)
        
        # Faz scroll até o elemento
        navegador.execute_script("arguments[0].scrollIntoView(true);", elemento_pagina)

        # Clica no elemento
        elemento_pagina.click()

        #time.sleep(1)

        # Formata o valor com duas casas decimais
        valor_formatado = f"{float(verba_necessaria_tela):.2f}M"

        # Digita o valor caractere por caractere
        for char in valor_formatado:
            elemento_pagina.send_keys(char)
            #time.sleep(0.1)

        # Configura o valor da média
        #navegador.execute_script(f"arguments[0].value = '{float(verba_necessaria_tela):.2f}M';", elemento_pagina)

        #time.sleep(1)
        
        # Dá tab após configurar o valor
        elemento_pagina.send_keys(Keys.TAB)

        #time.sleep(0.01)


#Valida a margem bruta por item
def valida_margem_bruta_item(navegador, linha_atual, verba_necessaria_tela):
    """
    Valida a margem bruta por item

    Parameters:
    navegador = navigator
    linha_atual = int
    verba_necessaria_tela = float
    """

    # Verifica se o elemento está carregado na página
    elemento_pagina = navegador.find_element(By.XPATH, f"/html/body/form/table/tbody/tr[{linha_atual}]/td[12]/span")

    time.sleep(0.02)
    
    # Obtém o valor da margem bruta do item
    margem_bruta_item = navegador.find_element("xpath", f"/html/body/form/table/tbody/tr[{linha_atual}]/td[12]/span").text

    # Verifica se a margem bruta do item ficou acima de zero
    if float(margem_bruta_item) < 1:
        # Deleta a informação que pode estar no campo
        # Verifica se o elemento está carregado na página
        elemento_pagina = navegador.find_element(By.XPATH, f"/html/body/form/table/tbody/tr[{linha_atual}]/td[17]/input")

        # Oculta o elemento que está bloqueando
        navegador.execute_script("document.getElementById('conteudo-fixo').style.display = 'none';")

        # Faz scroll até o elemento
        navegador.execute_script("arguments[0].scrollIntoView(true);", elemento_pagina)

        # Força o foco no campo com um clique
        elemento_pagina.click()

        # Ajuste no timer
        time.sleep(0.35)

        # Simula a tecla "Home" para mover o cursor para o início
        elemento_pagina.send_keys(Keys.HOME)

        # Pequena pausa para garantir que o Home foi pressionado
        time.sleep(0.35)

        # Simula pressionar a tecla "Delete" quatro vezes
        for _ in range(5):
            elemento_pagina.send_keys(Keys.DELETE)
            # Pequena pausa entre as teclas para simular o comportamento humano
            #time.sleep(0.1)

        # Verifica se o elemento está carregado na página
        elemento_pagina = navegador.find_element(By.XPATH, f"/html/body/form/table/tbody/tr[{linha_atual}]/td[17]/input")

        #time.sleep(1)

        #Clica no elemento
        elemento_pagina.click()

        #time.sleep(1)

        # Formata o valor com duas casas decimais
        valor_formatado = f"{float(verba_necessaria_tela):.2f}M"

        # Digita o valor caractere por caractere da verba necessária
        for char in valor_formatado:
            elemento_pagina.send_keys(char)
            # Pequena pausa entre as teclas para simular a digitação humana
            #time.sleep(0.1)

        #time.sleep(1)    
        
        # Dá tab após configurar o valor
        elemento_pagina.send_keys(Keys.TAB)


#Analisa margem
def analisa_margem_bloqueio(navegador):
    """
    Analisa margem

    Parameters:
    navegador = navigator
    """

    #Atualiza a página
    navegador.refresh()

    # Trata o alerta da página
    trata_alerta(navegador=navegador)

    time.sleep(1)

    # Espera carregar a tabela de pedidos e obtém os dados do pedido
    WebDriverWait(navegador, 60).until(EC.presence_of_element_located((By.ID, "margemPB")))
    porcentagem_pedido_bloqueio = navegador.find_element("id", f"margemPB").text
    float_porcentagem_pedido_bloqueio = float(porcentagem_pedido_bloqueio)

    porcentagem_minima_bloqueio = navegador.find_element("id", f"pc_margem_ponderada_bloqueio").text
    porcentagem_minima_bloqueio = str(porcentagem_minima_bloqueio).replace("%", "").strip()
    float_porcentagem_minima_bloqueio = float(porcentagem_minima_bloqueio)

    verba_utilizada = navegador.find_element("id", f"verbaTotalPPedido").text

    # Verifica se o campo (Do pedido em % p/ Bloqueio) ficou maior ou igual ao (Do pedido em %) e a verba utilizada for 0
    if (float_porcentagem_pedido_bloqueio >= float_porcentagem_minima_bloqueio) and verba_utilizada == "0.00" and float_porcentagem_pedido_bloqueio > 0:
        return True
    
    else:
        return False
    

#Analisa margem
def analisa_margem_bloqueio_final(navegador):
    """
    Analisa margem

    Parameters:
    navegador = navigator
    """

    try:
        # Espera carregar a tabela de pedidos
        WebDriverWait(navegador, 10).until(EC.presence_of_element_located((By.ID, "margemPB")))
        porcentagem_pedido_bloqueio = navegador.find_element("id", f"margemPB").text
        float_porcentagem_pedido_bloqueio = float(porcentagem_pedido_bloqueio)
    
    except:
        #Atualiza a página
        navegador.refresh()

        # Trata o alerta da página
        trata_alerta(navegador=navegador)

        time.sleep(4)

        # Espera carregar a tabela de pedidos
        WebDriverWait(navegador, 60).until(EC.presence_of_element_located((By.ID, "margemPB")))

        # Ordena os itens por verba
        # Verifica se o elemento está carregado na página
        elemento_pagina = navegador.find_element(By.ID, f"th-verba-necessaria")

        # Clica no elemento de voltar
        navegador.execute_script("arguments[0].click();", elemento_pagina)

        time.sleep(0.2)

        # Ordena os itens por verba
        # Verifica se o elemento está carregado na página
        elemento_pagina = navegador.find_element(By.ID, f"th-verba-necessaria")

        # Clica no elemento de voltar
        navegador.execute_script("arguments[0].click();", elemento_pagina)

        time.sleep(0.2)

        # Ordena os itens por laboratório
        # Verifica se o elemento está carregado na página
        elemento_pagina = navegador.find_element(By.ID, f"th-nome-fornecedor")

        # Clica no elemento de voltar
        navegador.execute_script("arguments[0].click();", elemento_pagina)

        time.sleep(0.2)
    
    # Espera carregar a tabela de pedidos
    WebDriverWait(navegador, 60).until(EC.presence_of_element_located((By.ID, "margemPB")))
    porcentagem_pedido_bloqueio = navegador.find_element("id", f"margemPB").text
    float_porcentagem_pedido_bloqueio = float(porcentagem_pedido_bloqueio)

    porcentagem_minima_bloqueio = navegador.find_element("id", f"pc_margem_ponderada_bloqueio").text
    porcentagem_minima_bloqueio = str(porcentagem_minima_bloqueio).replace("%", "").strip()
    float_porcentagem_minima_bloqueio = float(porcentagem_minima_bloqueio)

    # Calcula a diferença de valores
    diferenca_valores = float(str(float_porcentagem_minima_bloqueio).replace(",", ".")) - float(float_porcentagem_pedido_bloqueio)
    
    # Valida se a diferença de valores está aceitável
    if -0.05 <= diferenca_valores <= 0.01:
        return True
    
    else:
        return False
    

#Analisa margem
def analisa_margem_bloqueio_final_industria(navegador, margem_industria):
    """
    Analisa margem

    Parameters:
    navegador = navigator
    """

    try:
        # Espera carregar a tabela de pedidos
        WebDriverWait(navegador, 10).until(EC.presence_of_element_located((By.ID, "margemPB")))
        porcentagem_pedido_bloqueio = navegador.find_element("id", f"margemPB").text
        float_porcentagem_pedido_bloqueio = float(porcentagem_pedido_bloqueio)

    except:
        #Atualiza a página
        navegador.refresh()

        # Trata o alerta da página
        trata_alerta(navegador=navegador)

        time.sleep(4)

        # Espera carregar a tabela de pedidos
        WebDriverWait(navegador, 60).until(EC.presence_of_element_located((By.ID, "margemPB")))

        # Ordena os itens por verba
        # Verifica se o elemento está carregado na página
        elemento_pagina = navegador.find_element(By.ID, f"th-verba-necessaria")

        # Clica no elemento de voltar
        navegador.execute_script("arguments[0].click();", elemento_pagina)

        time.sleep(0.2)

        # Ordena os itens por verba
        # Verifica se o elemento está carregado na página
        elemento_pagina = navegador.find_element(By.ID, f"th-verba-necessaria")

        # Clica no elemento de voltar
        navegador.execute_script("arguments[0].click();", elemento_pagina)

        time.sleep(0.2)

        # Ordena os itens por laboratório
        # Verifica se o elemento está carregado na página
        elemento_pagina = navegador.find_element(By.ID, f"th-nome-fornecedor")

        # Clica no elemento de voltar
        navegador.execute_script("arguments[0].click();", elemento_pagina)

        time.sleep(0.2)

    # Espera carregar a tabela de pedidos
    WebDriverWait(navegador, 60).until(EC.presence_of_element_located((By.ID, "margemPB")))
    porcentagem_pedido_bloqueio = navegador.find_element("id", f"margemPB").text
    float_porcentagem_pedido_bloqueio = float(porcentagem_pedido_bloqueio)

    # Verifica se o campo (Do pedido em % p/ Bloqueio) ficou maior ou igual ao (Do pedido em %)
    if (float_porcentagem_pedido_bloqueio >= float(str(margem_industria).replace(",", ".").strip())):
        return True
    
    else:
        return False


#Chama o código principal
def executa_codigo_principal():
    """
    Chama o código principal
    """

    # try:
    navega_tabela_pedidos_gerais()

    # except Exception as e:
    #     print(e)


###################################### CHAMA O SCRIPT PRINCIPAL ######################################
if __name__ == "__main__":
    navega_tabela_pedidos_gerais()