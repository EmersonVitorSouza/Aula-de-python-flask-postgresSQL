import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
import psycopg2
from psycopg2.extras import RealDictCursor
from werkzeug.security import generate_password_hash, check_password_hash
from urllib.parse import urlparse
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY")

DATABASE_URL = os.environ.get("DATABASE_URL")

# conectar ao banco Neon
def get_conn():
    return psycopg2.connect(os.getenv("DATABASE_URL"))

# criar tabelas (executar 1x no início)
def criar_tabelas():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id SERIAL PRIMARY KEY,
        username VARCHAR(50) UNIQUE NOT NULL,
        senha VARCHAR(50) NOT NULL
    );
    
    CREATE TABLE IF NOT EXISTS itens (
        id SERIAL PRIMARY KEY,
        nome VARCHAR(100),
        descricao TEXT,
        preco DECIMAL(10,2)
    );
    """)
    conn.commit()
    cur.close()
    conn.close()

@app.route("/")
def index():
    if "user_id" in session:
        return redirect(url_for("list_items"))
    return redirect(url_for("login"))

@app.route("/register", methods=["GET","POST"])
def register():
    if request.method=="POST":
        username = request.form["username"]
        password = request.form["password"]
        pw_hash = generate_password_hash(password)
        with get_conn() as conn:
            with conn.cursor() as cur:
                try:
                    cur.execute("INSERT INTO usuarios (username,senha) VALUES (%s,%s) RETURNING id", (username,pw_hash))
                    conn.commit()
                    flash("Cadastro realizado. Faça login.")
                    return redirect(url_for("login"))
                except Exception as e:
                    conn.rollback()
                    flash("Erro: usuário já existe ou dados inválidos.")
    return render_template("register.html")

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method=="POST":
        username = request.form["username"]
        password = request.form["password"]
        with get_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT id, senha FROM usuarios WHERE username=%s", (username,))
                user = cur.fetchone()
                if user and check_password_hash(user["senha"], password):
                    session["user_id"] = user["id"]
                    session["username"] = username
                    return redirect(url_for("list_items"))
                flash("Usuário ou senha inválidos.")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/items/new", methods=["GET","POST"])
def add_item():
    if "user_id" not in session:
        return redirect(url_for("login"))
    if request.method=="POST":
        name = request.form["name"]
        desc = request.form["description"]
        price = request.form["price"]
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("INSERT INTO items (user_id,name,description,price) VALUES (%s,%s,%s,%s)",
                            (session["user_id"], name, desc, price))
                conn.commit()
                return redirect(url_for("list_items"))
    return render_template("add_item.html")

@app.route("/items")
def list_items():
    if "user_id" not in session:
        return redirect(url_for("login"))
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT id, name, description, price, created_at FROM items ORDER BY created_at DESC")
            rows = cur.fetchall()
    return render_template("list_items.html", items=rows)

if __name__ == "__main__":
    criar_tabelas()
    app.run(debug=True,)
    
