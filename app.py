import os
import json
import psycopg
from psycopg.rows import dict_row
from groq import Groq
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash

load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "DEFAULT_KEY")

client = Groq(api_key=os.getenv("GROQ_API_KEY"))
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
    
    You MUST respond strictly with a valid JSON object using this exact structure:
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
        # Chamada otimizada para o modelo OpenAI OSS na infraestrutura da Groq
        completion = client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[
                {
                    "role": "system", 
                    "content": "You are a precise nutrition assistant. You must output ONLY valid raw JSON, with no markdown formatting, no backticks, matching this structure: {\"titulo\": \"...\", \"itens\": [{\"alimento\": \"...\", \"quantidade\": \"...\", \"proteina\": 0.0, \"carboidrato\": 0.0, \"gordura\": 0.0, \"calorias\": 0.0}]}"
                },
                {"role": "user", "content": mensagem_usuario}
            ]
        )

        resposta_texto = completion.choices[0].message.content.strip()
        
        # Limpeza robusta caso venha com markdown por insistência do modelo
        if "```json" in resposta_texto:
            resposta_texto = resposta_texto.split("```json")[1].split("```")[0].strip()
        elif "```" in resposta_texto:
            resposta_texto = resposta_texto.split("```")[1].split("```")[0].strip()

        dados_refeicao = json.loads(resposta_texto)
        
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                # Inserir Refeição
                cursor.execute(
                    "INSERT INTO refeicoes (humano_id, titulo) VALUES (%s, %s) RETURNING id",
                    (user_id, dados_refeicao.get("titulo", "Refeição"))
                )
                refeicao_id = cursor.fetchone()["id"]

                # Inserir Itens
                itens_salvos = []
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
                    itens_salvos.append(item)
                conn.commit() 

                # Buscar novos totais do dia
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
            "refeicao_id": refeicao_id,
            "novos_totais": {
                "kcal": round(novos_totais['kcal'] or 0, 1),
                "prot": round(novos_totais['prot'] or 0, 1),
                "carb": round(novos_totais['carb'] or 0, 1),
                "gord": round(novos_totais['gord'] or 0, 1)
            },
            "refeicao_titulo": dados_refeicao.get("titulo"),
            "refeicao_kcal": round(kcal_refeicao_atual, 1),
            "itens": itens_salvos
        })
    except Exception as e:
        print(f"Erro detalhado na Groq: {e}") 
        return jsonify({"erro": "Não consegui processar a refeição", "detalhe": str(e)}), 400

@app.route("/refeicao/<int:refeicao_id>/deletar", methods=["POST"])
def deletar_refeicao(refeicao_id):
    if "user_id" not in session:
        return jsonify({"erro": "Não autorizado"}), 401
    
    user_id = session["user_id"]
    
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            # Verifica se a refeição pertence ao usuário logado por segurança
            cursor.execute("SELECT id FROM refeicoes WHERE id = %s AND humano_id = %s", (refeicao_id, user_id))
            ref = cursor.fetchone()
            if not ref:
                return jsonify({"erro": "Refeição não encontrada"}), 404
            
            # Deleta (os itens caem em cascata pelo ON DELETE CASCADE)
            cursor.execute("DELETE FROM refeicoes WHERE id = %s", (refeicao_id,))
            conn.commit()
            
            # Recalcula totais do dia
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
            novos_totais = cursor.fetchone()

    return jsonify({
        "status": "sucesso",
        "novos_totais": {
            "kcal": round(novos_totais['kcal'] or 0, 1),
            "prot": round(novos_totais['prot'] or 0, 1),
            "carb": round(novos_totais['carb'] or 0, 1),
            "gord": round(novos_totais['gord'] or 0, 1)
        }
    })

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

            # Histórico de refeições do dia com itens e macros detalhados
            cursor.execute("""
                SELECT id, titulo, data_hora 
                FROM refeicoes 
                WHERE humano_id = %s AND DATE(data_hora) = CURRENT_DATE 
                ORDER BY data_hora DESC
            """, (user_id,))
            refeicoes_raw = cursor.fetchall()

            historico = []
            for ref in refeicoes_raw:
                cursor.execute("""
                    SELECT alimento, quantidade, calorias, proteina, carboidrato, gordura 
                    FROM itens_refeicao 
                    WHERE refeicao_id = %s
                """, (ref["id"],))
                itens = cursor.fetchall()
                
                # Soma calorias e macros da refeição
                total_kcal_ref = sum(item["calorias"] or 0 for item in itens)
                total_prot_ref = sum(item["proteina"] or 0 for item in itens)
                total_carb_ref = sum(item["carboidrato"] or 0 for item in itens)
                total_gord_ref = sum(item["gordura"] or 0 for item in itens)
                
                historico.append({
                    "id": ref["id"],
                    "titulo": ref["titulo"],
                    "data_hora": ref["data_hora"],
                    "kcal": round(total_kcal_ref, 1),
                    "prot": round(total_prot_ref, 1),
                    "carb": round(total_carb_ref, 1),
                    "gord": round(total_gord_ref, 1),
                    "itens": itens
                })

    return render_template("index.html", totais=totais, historico=historico)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)