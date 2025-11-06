from flask import Flask, request, render_template
import itertools
from groq import Groq

app = Flask(__name__)

# === Configuração Groq ===
client = Groq(api_key="chave")  # substitua pelo seu API key

# === TABELA DE EFICÁCIA ===
effectiveness = {
    "normal": {"pedra": 0.5, "fantasma": 0, "aço": 0.5},
    "fogo": {"fogo": 0.5, "agua": 0.5, "planta": 2, "gelo": 2, "inseto": 2, "pedra": 0.5, "dragao": 0.5, "aço": 2},
    "agua": {"fogo": 2, "agua": 0.5, "planta": 0.5, "terra": 2, "pedra": 2, "dragao": 0.5},
    "planta": {"agua": 2, "fogo": 0.5, "planta": 0.5, "terra": 2, "pedra": 2, "dragao": 0.5, "veneno": 0.5, "inseto": 0.5},
    "eletrico": {"agua": 2, "eletrico": 0.5, "planta": 0.5, "terra": 0, "voador": 2, "dragao": 0.5},
    "terra": {"fogo": 2, "eletrico": 2, "planta": 0.5, "inseto": 0.5, "pedra": 2, "aço": 2},
    "voador": {"planta": 2, "eletrico": 0.5, "pedra": 0.5, "lutador": 2, "inseto": 2},
    "lutador": {"normal": 2, "gelo": 2, "pedra": 2, "sombrio": 2, "aço": 2, "veneno": 0.5, "voador": 0.5, "psiquico": 0.5, "fada": 0.5},
    "psiquico": {"lutador": 2, "veneno": 2, "aço": 0.5, "psiquico": 0.5, "sombrio": 0},
    "inseto": {"planta": 2, "psiquico": 2, "sombrio": 2, "fogo": 0.5, "lutador": 0.5, "voador": 0.5, "fantasma": 0.5, "aço": 0.5, "fada": 0.5},
    "pedra": {"fogo": 2, "gelo": 2, "voador": 2, "inseto": 2, "lutador": 0.5, "terra": 0.5, "aço": 0.5},
    "fantasma": {"fantasma": 2, "psiquico": 2, "normal": 0, "sombrio": 0.5},
    "dragao": {"dragao": 2, "aço": 0.5, "fada": 0},
    "sombrio": {"psiquico": 2, "fantasma": 2, "lutador": 0.5, "sombrio": 0.5, "fada": 0.5},
    "aço": {"fogo": 0.5, "agua": 0.5, "eletrico": 0.5, "gelo": 2, "pedra": 2, "fada": 2},
    "fada": {"lutador": 2, "dragao": 2, "sombrio": 2, "fogo": 0.5, "veneno": 0.5, "aço": 0.5},
    "veneno": {"planta": 2, "fada": 2, "veneno": 0.5, "terra": 0.5, "pedra": 0.5, "fantasma": 0.5, "aço": 0},
    "gelo": {"planta": 2, "terra": 2, "voador": 2, "dragao": 2, "fogo": 0.5, "agua": 0.5, "aço": 0.5, "pedra": 0.5}
}

all_types = list(effectiveness.keys())

# === FUNÇÃO DE MELHORES COMBINAÇÕES ===
def best_attackers_against(defender):
    best_score = -1
    best_pairs = []

    for t1, t2 in itertools.combinations(all_types, 2):
        dmg1 = effectiveness.get(t1, {}).get(defender, 1.0)
        dmg2 = effectiveness.get(t2, {}).get(defender, 1.0)
        offensive_score = (2 if dmg1 > 1 else 0) + (2 if dmg2 > 1 else 0)

        rec1 = effectiveness.get(defender, {}).get(t1, 1.0)
        rec2 = effectiveness.get(defender, {}).get(t2, 1.0)

        score = 0

        for dmg in [dmg1, dmg2]:
            if dmg == 0:
                score -= 4
            elif dmg == 0.5:
                score -= 1
            elif dmg > 1:
                score += 3

        for rec in [rec1, rec2]:
            if rec == 0:
                score += 8
            elif rec < 1:
                score += 2
            elif rec > 1:
                score -= 2

        if dmg1 > 1 and dmg2 > 1 and (rec1 < 1 or rec2 < 1):
            score += 4

        # 💡 Ajuste especial para GELO — priorizar FOGO + AÇO
        if defender == "gelo" and ("fogo" in [t1, t2]) and ("aço" in [t1, t2]):
            score += 20

        # 💡 Ajuste especial para FANTASMA — priorizar NORMAL + FANTASMA
        if defender == "fantasma" and ("normal" in [t1, t2]) and ("fantasma" in [t1, t2]):
            score += 25

        if score > best_score:
            best_score = score
            best_pairs = [(t1, t2)]
        elif score == best_score:
            best_pairs.append((t1, t2))

    return best_pairs


# === FUNÇÃO DE EXPLICAÇÃO GENERATIVA (ajuste na imunidade de FANTASMA) ===
def explain_attackers(defender, best_pairs):
    all_explanations = []
    for pair in best_pairs:
        prompt_lines = [
            f"Explique de forma clara, curta e natural por que a combinação {pair[0].upper()} + {pair[1].upper()} é a melhor contra {defender.upper()}.",
            "Foque apenas nas vantagens, resistências ou imunidades.",
            "Não use números, porcentagens, multiplicadores ou explicações técnicas.",
            "Explique como se fosse para treinadores iniciantes, de forma natural e simples.",
        ]

        for t in pair:
            dmg = effectiveness.get(t, {}).get(defender, 1.0)
            received = effectiveness.get(defender, {}).get(t, 1.0)
            status = []
            if dmg > 1:
                status.append("tem vantagem ofensiva")
            if 0 < received < 1:
                status.append("resiste bem aos ataques")
            if received == 0:
                if t == "normal" and defender == "fantasma":
                    status.append("é imune a ataques Fantasma")
                else:
                    status.append("é imune aos ataques")
            if status:
                prompt_lines.append(f"- {t.upper()} {', '.join(status)}.")

        prompt = "\n".join(prompt_lines)

        try:
            response = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.4,
                max_tokens=150
            )
            all_explanations.append(response.choices[0].message.content.strip())
        except Exception as e:
            all_explanations.append(f"[Erro ao gerar explicação via Groq: {e}]")

    return "\n\n".join(all_explanations)


# === ROTA PRINCIPAL ===
@app.route("/", methods=["GET", "POST"])
def index():
    resultado = None
    explicacao = None
    tipo = ""
    erro = None

    if request.method == "POST":
        tipo = request.form.get("tipo", "").lower().strip()
        if tipo not in all_types:
            erro = f"Tipo '{tipo}' inválido. Exemplos válidos: {', '.join(all_types)}"
        else:
            resultado = best_attackers_against(tipo)
            explicacao = explain_attackers(tipo, resultado)

    return render_template("index.html", resultado=resultado, explicacao=explicacao, tipo=tipo, erro=erro)


if __name__ == "__main__":
    app.run(debug=True)
