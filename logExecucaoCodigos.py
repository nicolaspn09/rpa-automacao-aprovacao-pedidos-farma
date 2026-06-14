from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import mysql.connector
import smtplib
import locale

#Envia e-mail para os usuários
def envia_email(mensagemEmail, destinatarios_email, assunto_email):    
    # Configurações do servidor SMTP
    smtp_server = 'mail.EMPRESA.com.br'
    smtp_port = 25  # Porta para comunicação segura com TLS

    # Credenciais do remetente
    remetente_email = "rpa@EMPRESA.com.br"
    remetente_senha = 'DADO_HIGIENIZADO'

    destinatarios = destinatarios_email
    #destinatarios = [destinatarios_enviar]

    # Crie uma mensagem MIMEMultipart
    mensagem = MIMEMultipart()
    mensagem['From'] = remetente_email
    mensagem['To'] = ",".join(destinatarios)
    mensagem['Subject'] = assunto_email

    # Adicione o corpo do e-mail
    corpo_email = mensagemEmail
    mensagem.attach(MIMEText(corpo_email, 'html'))  # 'plain' para texto simples ou 'html' para HTML

    try:
        servidor_smtp = smtplib.SMTP(smtp_server, smtp_port)
        servidor_smtp.starttls()  # Ative a criptografia TLS

        # Faça login com suas credenciais
        servidor_smtp.login(remetente_email, remetente_senha)

        # Envie o e-mail
        texto_email = mensagem.as_string()
        servidor_smtp.sendmail(remetente_email, destinatarios, texto_email)


    except Exception as e:
        #Bloco de logs
        locale.setlocale(locale.LC_ALL, 'pt_BR') #Seta o local
        data_hora_atual = datetime.now() #Busca a data atual
        mensagem = f"Erro ao enviar e-mail na API do código de clientes antecipados (liberaPedidoClienteAntecipadoAPI): {str(e)}" #Informa a mensagem do Log

    finally:
        servidor_smtp.quit()  # Encerre a conexão com o servidor SMTP

#Roda query para executar o MySQL
def conecta_my_sql(sql):
    host = '10.1.1.199'  # Endereço do servidor MySQL
    database = 'fiscal'  # Nome do banco de dados
    user = 'root'  # Nome de usuário para acessar o banco de dados
    password = 'DADO_HIGIENIZADO'  # Senha do usuário para acessar o banco de dados

    try:
        # Estabelece a conexão com o banco de dados
        connection = mysql.connector.connect(
            host=host,
            database=database,
            user=user,
            password=password
        )
   
        if connection.is_connected():
            cursor = connection.cursor()
            cursor.execute(sql)
            tabela_sql = cursor.fetchall()
            cursor.close()
            connection.close()

            #Retorna o resultado da consulta do SQL para o usuário
            return tabela_sql
        
    except mysql.connector.Error as error:
        #Bloco de logs
        locale.setlocale(locale.LC_ALL, 'pt_BR') #Seta o local
        data_hora_atual = datetime.now() #Busca a data atual
        mensagem = f"Erro ao conectar-se ao banco de dados do MySQL (update ou insert) no código de log: {data_hora_atual} - {error}" #Informa a mensagem do Log

        #Envio dos e-mails de erro
        destinatarios_email = []
        destinatarios_email.append('Nicolas.nasario@EMPRESA.com.br')
        destinatarios_email.append('Lucas.remor@EMPRESA.com.br')

        assunto_email = "Erro no código de Log"

        envia_email(mensagemEmail=mensagem, destinatarios_email=destinatarios_email, assunto_email=assunto_email)

#Roda query para executar o MySQL
def conecta_my_sql_insert(sql):
    host = '10.1.1.199'  # Endereço do servidor MySQL
    database = 'fiscal'  # Nome do banco de dados
    user = 'root'  # Nome de usuário para acessar o banco de dados
    password = 'DADO_HIGIENIZADO'  # Senha do usuário para acessar o banco de dados

    try:
        # Estabelece a conexão com o banco de dados
        connection = mysql.connector.connect(
            host=host,
            database=database,
            user=user,
            password=password
        )
   
        if connection.is_connected():
            cursor = connection.cursor()
            cursor.execute(sql)
            connection.commit()
            cursor.close()
            connection.close()
        
    except mysql.connector.Error as error:
        #Bloco de logs
        locale.setlocale(locale.LC_ALL, 'pt_BR') #Seta o local
        data_hora_atual = datetime.now() #Busca a data atual
        mensagem = f"Erro ao conectar-se ao banco de dados do MySQL (update ou insert) no código de log: {data_hora_atual} - {error}" #Informa a mensagem do Log

        #Envio dos e-mails de erro
        destinatarios_email = []
        destinatarios_email.append('Nicolas.nasario@EMPRESA.com.br')
        destinatarios_email.append('Lucas.remor@EMPRESA.com.br')

        assunto_email = "Erro no código de Log"

        envia_email(mensagemEmail=mensagem, destinatarios_email=destinatarios_email, assunto_email=assunto_email)

def grava_log_execucao_sql(codigo, status):
    locale.setlocale(locale.LC_ALL, 'pt_BR') #Seta o local
    data_hora_atual = datetime.now() #Busca a data atual

    sql_select = f"select * from fiscal.log_execucao_python where nome_codigo = '{codigo}'"

    retorno_select = conecta_my_sql(sql=sql_select)

    if len(retorno_select) == 0:
        sql = f"INSERT INTO fiscal.log_execucao_python (horario_execucao, nome_codigo, status_execucao) VALUES('{data_hora_atual}', '{codigo}', '{status}')"

        conecta_my_sql_insert(sql=sql)
    
    else:
        sql = f"UPDATE fiscal.log_execucao_python SET horario_execucao = '{data_hora_atual}', status_execucao = '{status}' where nome_codigo = '{codigo}'"

        conecta_my_sql_insert(sql=sql)

if __name__ == "__main__":
    grava_log_execucao_sql()