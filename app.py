import os
import sqlite3
import json
from google import genai
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "DEFAULT_KEY")

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# lista de modelos disponiveis:
# for m in client.models.list(): print(f"Modelo disponível: {m.name}")   

def get_db_connection():
    conn = sqlite3.connect('nutroide.db')
    # resultados como dicionários
    conn.row_factory = sqlite3.Row
    # ativa as chaves estrangeiras para efeito de 'deletar em cascata' funcionar
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

@app.route("/register_test")
def register_test():
    nome = "Lucas Bisoffi"
    email = "lucas@teste.com"
    hash_senha = generate_password_hash("123456")
    
    # 'with' para garantir que a conexão feche sozinha se der erro
    try:
        with get_db_connection() as conn:
            conn.execute(
                "INSERT INTO humanos (nome, email, senha_hash) VALUES (?, ?, ?)",
                (nome, email, hash_senha)
            )
            # é preciso confirmar a gravação
            conn.commit() 
        return "Registrado via SQL!"
    except sqlite3.IntegrityError:
        return "Erro: Email já existe."

@app.route("/chat", methods=["POST"])
def chat():
    # pega o texto do usuário via JSON
    dados_entrada = request.get_json()
    mensagem_usuario = dados_entrada.get("texto")
    
    prompt = f"""
    Você é o Nutroide, um assistente especializado em nutrição.
    Sua tarefa é extrair alimentos e quantidades da frase do usuário.
    Responda APENAS com um objeto JSON puro, sem as crases de markdown (sem ```json), seguindo este modelo:
    {{
        "titulo": "Nome da refeição",
        "itens": [
            {{
                "alimento": "nome do alimento",
                "quantidade": "medida",
                "proteina": 0.0,
                "carboidrato": 0.0,
                "gordura": 0.0,
                "calorias": 0.0
            }}
        ]
    }}
    Frase do usuário: "{mensagem_usuario}"
    """

    try:
        response = client.models.generate_content(
            model='gemini-flash-latest',
            contents=prompt
        )
        
        # tenta converter o texto do gemini em um dicionário Python real
        dados_refeicao = json.loads(response.text)
        
        with get_db_connection() as conn:
            # inserindo refeicao teste
            cursor = conn.execute(
                "INSERT INTO refeicoes (humano_id, titulo) VALUES (?, ?)",
                (1, dados_refeicao.get("titulo", "Refeição"))
            )
            # pega o ID que o banco acabou de criar
            refeicao_id = cursor.lastrowid 

            # inserindo cada item da lista que a IA gerou
            for item in dados_refeicao["itens"]:
                conn.execute(
                    """INSERT INTO itens_refeicao 
                    (refeicao_id, alimento, quantidade, calorias, proteina, carboidrato, gordura) 
                    VALUES (?, ?, ?, ?, ?, ?, ?)""",
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
            
            # salva todos os registros (essencial)
            conn.commit() 

        # busca os macros atualizados do dia
        novos_totais = conn.execute("""
            SELECT SUM(calorias) as kcal, SUM(proteina) as prot, 
                SUM(carboidrato) as carb, SUM(gordura) as gord
            FROM itens_refeicao i
            JOIN refeicoes r ON i.refeicao_id = r.id
            WHERE r.humano_id = 1 AND date(r.data_hora, 'localtime') = date('now', 'localtime')
        """).fetchone()

        # calcula o total APENAS da refeição atual
        kcal_refeicao_atual = conn.execute(
            "SELECT SUM(calorias) FROM itens_refeicao WHERE refeicao_id = ?", 
            (refeicao_id,)
        ).fetchone()[0]

        return jsonify({
            "status": "sucesso",
            "novos_totais": {
                "kcal": round(novos_totais['kcal'] or 0, 1),
                "prot": round(novos_totais['prot'] or 0, 1),
                "carb": round(novos_totais['carb'] or 0, 1),
                "gord": round(novos_totais['gord'] or 0, 1)
            },
            "refeicao_titulo": dados_refeicao.get("titulo"),
            "refeicao_kcal": round(kcal_refeicao_atual or 0, 1)
        })
    except Exception as e:
        # log de erro no terminal
        print(f"Erro detalhado: {e}") 
        return jsonify({"erro": "Não consegui processar a refeição", "detalhe": str(e)}), 400

@app.route("/")
def index():
    # testando com user de id = 1
    user_id = 1
    
    with get_db_connection() as conn:
        # busca a soma de macros do dia atual
        totais = conn.execute("""
            SELECT 
                SUM(i.calorias) as kcal, 
                SUM(i.proteina) as prot, 
                SUM(i.carboidrato) as carb, 
                SUM(i.gordura) as gord
            FROM itens_refeicao i
            JOIN refeicoes r ON i.refeicao_id = r.id
            WHERE r.humano_id = ? AND date(r.data_hora, 'localtime') = date('now', 'localtime')
        """, (user_id,)).fetchone()

        # busca a lista de refeições de hoje para exibir
        historico = conn.execute("""
            SELECT r.titulo, SUM(i.calorias) as kcal, r.data_hora
            FROM refeicoes r
            JOIN itens_refeicao i ON r.id = i.refeicao_id
            WHERE r.humano_id = ? AND date(r.data_hora, 'localtime') = date('now', 'localtime')
            GROUP BY r.id
            ORDER BY r.data_hora DESC
        """, (user_id,)).fetchall()

    return render_template("index.html", totais=totais, historico=historico)

if __name__ == "__main__":
    app.run(debug=True)