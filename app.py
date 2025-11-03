import os  # importa o módulo do sistema para ler variáveis de ambiente e manipular caminhos
from flask import Flask, render_template, request, redirect, url_for, session, flash  # importa classes/funções do Flask usadas no app
import psycopg2  # driver PostgreSQL para conectar e executar queries
from psycopg2.extras import RealDictCursor  # cursor que retorna linhas como dicionários (acesso por nome de coluna)
from dotenv import load_dotenv  # carrega variáveis de ambiente de um arquivo .env

load_dotenv()  # carrega variáveis definidas no arquivo .env para o ambiente (útil localmente)

app = Flask(__name__)  # cria a instância da aplicação Flask
app.secret_key = os.environ.get("SECRET_KEY", "segredo-local")  # define a chave secreta para sessões; busca em env ou usa valor padrão

# Conexão com Neon
def get_conn():
    return psycopg2.connect(os.getenv("DATABASE_URL"), sslmode="require")  # cria e retorna uma conexão ao banco usando DATABASE_URL; força SSL

@app.route("/")  # rota para a raiz do site
def index():
    if "user_id" in session:  # se o usuário já estiver logado (tem user_id na sessão)
        return redirect(url_for("list_items"))  # redireciona para a lista de itens
    return redirect(url_for("login"))  # caso contrário, redireciona para a página de login

@app.route("/register", methods=["GET", "POST"])  # rota de registro que aceita GET (form) e POST (envio)
def register():
    if request.method == "POST":  # se o formulário foi enviado
        username = request.form.get("username", "").strip()  # pega o campo username do formulário, remove espaços
        password = request.form.get("password", "").strip()  # pega o campo password do formulário, remove espaços

        if not username or not password:  # validação simples: campos obrigatórios
            flash("Preencha todos os campos.", "warning")  # armazena uma mensagem para exibir ao usuário
            return render_template("register.html")  # reexibe o formulário de registro

        try:
            with get_conn() as conn, conn.cursor() as cur:  # abre conexão e cursor; contexto fecha automaticamente
                cur.execute("INSERT INTO usuarios (username, senha) VALUES (%s, %s)", (username, password))  # insere novo usuário
                conn.commit()  # confirma a transação no banco
            flash("✅ Cadastro realizado com sucesso! Faça login.", "success")  # mensagem de sucesso
            return redirect(url_for("login"))  # redireciona para a tela de login
        except psycopg2.errors.UniqueViolation:  # exceção específica quando username já existe (constraint UNIQUE)
            flash("⚠️ Usuário já existe.", "danger")  # mensagem de aviso
        except Exception as e:  # captura qualquer outra exceção
            flash(f"Erro ao cadastrar: {e}", "danger")  # exibe erro genérico com a mensagem retornada

    return render_template("register.html")  # para GET, apenas renderiza o template de registro

@app.route("/login", methods=["GET", "POST"])  # rota de login que aceita GET e POST
def login():
    if request.method == "POST":  # se o formulário de login foi submetido
        username = request.form.get("username", "").strip()  # pega username enviado
        password = request.form.get("password", "").strip()  # pega password enviado

        if not username or not password:  # valida campos obrigatórios
            flash("Preencha todos os campos.", "warning")  # informa usuário
            return render_template("login.html")  # reexibe formulário

        with get_conn() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:  # abre conexão com cursor que retorna dicts
            cur.execute("SELECT id_user, senha FROM usuarios WHERE username = %s", (username,))  # busca usuário pelo username
            user = cur.fetchone()  # pega a primeira linha (ou None)

        if user and user["senha"] == password:  # verifica se usuário existe e senha bate (comparação direta, sem hash)
            session["user_id"] = user["id_user"]  # guarda id do usuário na sessão
            session["username"] = username  # guarda username na sessão (útil pra exibir)
            flash(f"Bem-vindo, {username}!", "success")  # mensagem de boas-vindas
            return redirect(url_for("list_items"))  # redireciona para página de itens

        flash("Usuário ou senha inválidos.", "danger")  # mensagem caso login falhe

    return render_template("login.html")  # para GET, renderiza o template de login

@app.route("/logout")  # rota para logout
def logout():
    session.clear()  # limpa todos os dados da sessão (desloga o usuário)
    flash("Você saiu da conta.", "info")  # mensagem informativa
    return redirect(url_for("login"))  # redireciona para o login

@app.route("/items", methods=["GET","POST"])  # rota que serve o formulário de adicionar item (GET) e processa envio (POST)
def add_item():
    if "user_id" not in session:  # se usuário não estiver logado
        return redirect(url_for("login"))  # redireciona para login
    if request.method == "POST":  # se o formulário foi enviado
        nome = request.form["nome"]  # lê o campo nome do formulário
        descricao = request.form["descricao"]  # lê o campo descricao do formulário
        preco = request.form["preco"].replace(",", ".")  # normaliza vírgula para ponto no preço (ex: "10,50" -> "10.50")
        with get_conn() as conn, conn.cursor() as cur:  # abre conexão e cursor
            cur.execute("INSERT INTO itens (nome, descricao, preco) VALUES (%s,%s,%s)",(nome, descricao, preco),)  # insere novo item
            conn.commit()  # confirma a transação
            flash("✅ Item adicionado com sucesso!", "success")  # mensagem de sucesso
            return redirect(url_for("list_items"))  # redireciona para a lista de itens
    return render_template("add_item.html")  # para GET, renderiza o formulário de adicionar item

@app.route("/list_items", methods=["GET"])  # rota que lista os itens (apenas GET)
def list_items():
    if "user_id" not in session:  # exige autenticação
        return redirect(url_for("login"))  # redireciona se não autenticado
    with get_conn() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:  # abre conexão e cursor em formato dicionário
        cur.execute("SELECT * FROM itens ORDER BY id_itens DESC")  # busca todos os itens ordenando pelo id (mais recentes primeiro)
        rows = cur.fetchall()  # obtém todas as linhas retornadas pela query
    return render_template("list_items.html", items=rows)  # renderiza o template passando os itens como variável

if __name__ == "__main__":  # executa somente se o script for rodado diretamente (não quando importado)
    app.run(debug=True)  # inicia o servidor Flask em modo debug (mostra erros detalhados) 
