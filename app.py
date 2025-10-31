import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "segredo-local")

# Conexão com Neon
def get_conn():
    return psycopg2.connect(os.getenv("DATABASE_URL"), sslmode="require")

# Criar tabelas
def criar_tabelas():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id SERIAL PRIMARY KEY,
        username VARCHAR(100) UNIQUE NOT NULL,
        senha VARCHAR(100) NOT NULL
    );

    CREATE TABLE IF NOT EXISTS itens (
        id SERIAL PRIMARY KEY,
        user_id INTEGER REFERENCES usuarios(id) ON DELETE CASCADE,
        name VARCHAR(100),
        description TEXT,
        price DECIMAL(10,2),
        created_at TIMESTAMP DEFAULT NOW()
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

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        if not username or not password:
            flash("Preencha todos os campos.", "warning")
            return render_template("register.html")

        try:
            with get_conn() as conn, conn.cursor() as cur:
                cur.execute("INSERT INTO usuarios (username, senha) VALUES (%s, %s)", (username, password))
                conn.commit()
            flash("✅ Cadastro realizado com sucesso! Faça login.", "success")
            return redirect(url_for("login"))
        except psycopg2.errors.UniqueViolation:
            flash("⚠️ Usuário já existe.", "danger")
        except Exception as e:
            flash(f"Erro ao cadastrar: {e}", "danger")

    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        if not username or not password:
            flash("Preencha todos os campos.", "warning")
            return render_template("login.html")

        with get_conn() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT id, senha FROM usuarios WHERE username = %s", (username,))
            user = cur.fetchone()

        if user and user["senha"] == password:
            session["user_id"] = user["id"]
            session["username"] = username
            flash(f"Bem-vindo, {username}!", "success")
            return redirect(url_for("list_items"))

        flash("Usuário ou senha inválidos.", "danger")

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("Você saiu da conta.", "info")
    return redirect(url_for("login"))

@app.route("/items/new", methods=["GET","POST"])
def add_item():
    if "user_id" not in session:
        return redirect(url_for("login"))
    if request.method == "POST":
        name = request.form["name"]
        desc = request.form["description"]
        price = request.form["price"]
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute(
                "INSERT INTO itens (user_id, name, description, price) VALUES (%s,%s,%s,%s)",
                (session["user_id"], name, desc, price),
            )
            conn.commit()
            flash("✅ Item adicionado com sucesso!", "success")
            return redirect(url_for("list_items"))
    return render_template("add_item.html")

@app.route("/items")
def list_items():
    if "user_id" not in session:
        return redirect(url_for("login"))
    with get_conn() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT * FROM itens ORDER BY id DESC")
        rows = cur.fetchall()
    return render_template("list_items.html", items=rows)

if __name__ == "__main__":
    criar_tabelas()
    app.run(debug=True)
