import os
import sqlite3
import json
from google import genai
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash

load_dotenv()
app = Flask(__name__)

# atualizacao do google genai
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# lista de modelos disponiveis:
# for m in client.models.list(): print(f"Modelo disponível: {m.name}")   

app.secret_key = os.getenv("FLASK_SECRET_KEY", "DEFAULT_KEY")


def get_db_connection():
    # Conecta ao arquivo do banco
    conn = sqlite3.connect('nutroide.db')
    # Faz com que os resultados venham como dicionários (igual a lib do CS50)
    conn.row_factory = sqlite3.Row
    # Ativa as chaves estrangeiras para efeito de 'deletar em cascata' funcionar
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
    # Pega o texto do usuário enviado via JSON
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
        
        texto_resposta = response.text
        
        # Tenta converter o texto da IA em um dicionário Python real
        dados_refeicao = json.loads(texto_resposta)
        
        # salvando no banco
        with get_db_connection() as conn:
            # inserindo refeicao teste
            cursor = conn.execute(
                "INSERT INTO refeicoes (humano_id, titulo) VALUES (?, ?)",
                (1, dados_refeicao.get("titulo", "Refeição"))
            )
            # Pega o ID que o banco acabou de criar
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
            
            # Salva todos os registros
            conn.commit() 

        return jsonify({
            "status": "sucesso", 
            "mensagem": "Refeição registrada no banco de dados!",
            "dados": dados_refeicao
        })

    except Exception as e:
        print(f"Erro detalhado: {e}") # Aparece no seu terminal
        return jsonify({"erro": "Não consegui processar a refeição", "detalhe": str(e)}), 400

if __name__ == "__main__":
    app.run(debug=True)