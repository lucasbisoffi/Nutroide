import os
import json
import psycopg
from psycopg.rows import dict_row
from google import genai
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash

load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "DEFAULT_KEY")

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
DATABASE_URL = os.getenv("DATABASE_URL")

def get_db_connection():
    conn = psycopg.connect(DATABASE_URL, row_factory=dict_row)
    return conn

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        nome = request.form.get("nome")
        email = request.form.get("email")
        senha = request.form.get("senha")
        
        hash_senha = generate_password_hash(senha)
        
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "INSERT INTO humanos (nome, email, senha_hash) VALUES (%s, %s, %s) RETURNING id",
                        (nome, email, hash_senha)
                    )
                    user_id = cursor.fetchone()["id"]
                    conn.commit()
                    
                    session["user_id"] = user_id
                    session["user_name"] = nome
            return redirect(url_for("index"))
        except Exception as e:
            print(f"Erro no registro: {e}")
            return "Email já cadastrado ou erro no servidor", 400
            
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        senha = request.form.get("senha")
        
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM humanos WHERE email = %s", (email,))
                user = cursor.fetchone()
            
            if user and check_password_hash(user["senha_hash"], senha):
                session["user_id"] = user["id"]
                session["user_name"] = user["nome"]
                return redirect(url_for("index"))
            else:
                return "Login inválido", 401
                
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/chat", methods=["POST"])
def chat():
    if "user_id" not in session:
        return jsonify({"erro": "Faça login primeiro"}), 401

    user_id = session["user_id"]
    dados_entrada = request.get_json()
    mensagem_usuario = dados_entrada.get("texto")
    
    prompt = f"""
    You are Nutroide, a multilingual nutrition assistant.
    Your task is to extract food items and quantities from the user's input, regardless of the language used.
    
    RESPOND ONLY with a raw JSON object (no markdown, no backticks), using this exact structure:
    {{
        "titulo": "A short name for the meal",
        "itens": [
            {{
                "alimento": "food name",
                "quantidade": "measure",
                "proteina": 0.0,
                "carboidrato": 0.0,
                "gordura": 0.0,
                "calorias": 0.0
            }}
        ]
    }}
    
    User input: "{mensagem_usuario}"
    """

    try:
        response = client.models.generate_content(
            model='gemini-flash-lite-latest',
            contents=prompt
        )
        
        texto_resposta = response.text.strip()
        if texto_resposta.startswith("```json"):
            texto_resposta = texto_resposta[7:]
        if texto_resposta.endswith("```"):
            texto_resposta = texto_resposta[:-3]
            
        dados_refeicao = json.loads(texto_resposta.strip())
        
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                # Inserir Refeição
                cursor.execute(
                    "INSERT INTO refeicoes (humano_id, titulo) VALUES (%s, %s) RETURNING id",
                    (user_id, dados_refeicao.get("titulo", "Refeição"))
                )
                refeicao_id = cursor.fetchone()["id"]

                # Inserir Itens
                for item in dados_refeicao["itens"]:
                    cursor.execute(
                        """INSERT INTO itens_refeicao 
                        (refeicao_id, alimento, quantidade, calorias, proteina, carboidrato, gordura) 
                        VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                        (
                            refeicao_id, 
                            item["alimento"], 
                            item["quantidade"], 
                            item["calorias"], 
                            item["proteina"], 
                            item["carboidrato"], 
                            item["gordura"]
                        )
                    )
                conn.commit() 

                # Buscar novos totais do dia (usando CURRENT_DATE do Postgres)
                cursor.execute("""
                    SELECT SUM(i.calorias) as kcal, SUM(i.proteina) as prot, 
                        SUM(i.carboidrato) as carb, SUM(i.gordura) as gord
                    FROM itens_refeicao i
                    JOIN refeicoes r ON i.refeicao_id = r.id
                    WHERE r.humano_id = %s AND DATE(r.data_hora) = CURRENT_DATE
                """, (user_id,))
                novos_totais = cursor.fetchone()

                # Calorias da refeição atual
                cursor.execute(
                    "SELECT SUM(calorias) as total FROM itens_refeicao WHERE refeicao_id = %s", 
                    (refeicao_id,)
                )
                res_kcal = cursor.fetchone()
                kcal_refeicao_atual = res_kcal["total"] if res_kcal and res_kcal["total"] else 0

        return jsonify({
            "status": "sucesso",
            "novos_totais": {
                "kcal": round(novos_totais['kcal'] or 0, 1),
                "prot": round(novos_totais['prot'] or 0, 1),
                "carb": round(novos_totais['carb'] or 0, 1),
                "gord": round(novos_totais['gord'] or 0, 1)
            },
            "refeicao_titulo": dados_refeicao.get("titulo"),
            "refeicao_kcal": round(kcal_refeicao_atual, 1)
        })
    except Exception as e:
        print(f"Erro detalhado: {e}") 
        return jsonify({"erro": "Não consegui processar a refeição", "detalhe": str(e)}), 400

@app.route("/")
def index():
    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]
    
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            # Totais do dia
            cursor.execute("""
                SELECT 
                    SUM(i.calorias) as kcal, 
                    SUM(i.proteina) as prot, 
                    SUM(i.carboidrato) as carb, 
                    SUM(i.gordura) as gord
                FROM itens_refeicao i
                JOIN refeicoes r ON i.refeicao_id = r.id
                WHERE r.humano_id = %s AND DATE(r.data_hora) = CURRENT_DATE
            """, (user_id,))
            totais = cursor.fetchone()

            # Histórico do dia
            cursor.execute("""
                SELECT r.titulo, SUM(i.calorias) as kcal, r.data_hora
                FROM refeicoes r
                JOIN itens_refeicao i ON r.id = i.refeicao_id
                WHERE r.humano_id = %s AND DATE(r.data_hora) = CURRENT_DATE
                GROUP BY r.id, r.titulo, r.data_hora
                ORDER BY r.data_hora DESC
            """, (user_id,))
            historico = cursor.fetchall()

    return render_template("index.html", totais=totais, historico=historico)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)