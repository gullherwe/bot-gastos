from flask import Flask, request, Response
from twilio.twiml.messaging_response import MessagingResponse
from datetime import datetime
import os

app = Flask(__name__)

def detectar_categoria(descricao):
    descricao = descricao.lower()
    categorias = {
        'Alimentação': ['ifood', 'mcdonalds', 'pizza', 'lanche', 'mercado', 'supermercado', 'padaria', 'café', 'restaurante'],
        'Transporte': ['uber', '99', 'ônibus', 'metro', 'combustível', 'gasolina'],
        'Lazer': ['cinema', 'spotify', 'netflix', 'show', 'jogo'],
        'Moradia': ['aluguel', 'condomínio', 'luz', 'água', 'internet'],
        'Saúde': ['farmácia', 'remédio', 'consulta', 'dentista'],
        'Educação': ['curso', 'faculdade', 'livro'],
        'Outros': []
    }

    for categoria, palavras in categorias.items():
        if any(palavra in descricao for palavra in palavras):
            return categoria
    return 'Outros'

def ler_gastos():
    gastos = []
    try:
        with open('gastos.csv', 'r') as f:
            next(f)  # pula o cabeçalho
            for linha in f:
                data_str, descricao, valor_str, categoria = linha.strip().split(',')
                gastos.append((data_str, descricao, float(valor_str), categoria))
    except FileNotFoundError:
        pass
    return gastos

@app.route('/webhook', methods=['POST'])
def webhook():
    msg = request.values.get('Body', '').strip()
    msg_lower = msg.lower()
    resposta = ""

    if msg_lower == 'listar':
        gastos = ler_gastos()
        if not gastos:
            resposta = "Nenhum gasto registrado ainda."
        else:
            ultimos = gastos[-5:]
            lista = "\n".join([
                f"{d[0]}: {d[1]} - R${d[2]:.2f} ({d[3]})" for d in ultimos
            ])
            resposta = f"Últimos gastos:\n{lista}"

    elif msg_lower == 'total hoje':
        gastos = ler_gastos()
        hoje = datetime.now().strftime('%Y-%m-%d')
        total = sum(g[2] for g in gastos if g[0].startswith(hoje))
        resposta = f"Total gasto hoje: R${total:.2f}"

    elif msg_lower == 'total mês':
        gastos = ler_gastos()
        mes_atual = datetime.now().strftime('%Y-%m')
        total = sum(g[2] for g in gastos if g[0].startswith(mes_atual))
        resposta = f"Total gasto no mês: R${total:.2f}"

    elif msg_lower == 'total categorias':
        gastos = ler_gastos()
        mes_atual = datetime.now().strftime('%Y-%m')
        categorias = {}
        for g in gastos:
            if g[0].startswith(mes_atual):
                categorias[g[3]] = categorias.get(g[3], 0) + g[2]
        if not categorias:
            resposta = "Nenhum gasto neste mês."
        else:
            linhas = [f"- {cat}: R${total:.2f}" for cat, total in categorias.items()]
            resposta = f"Gastos por categoria em {datetime.now().strftime('%B')}:\n" + "\n".join(linhas)

    elif msg_lower in ['ajuda', 'help']:
        resposta = (
            "Comandos disponíveis:\n"
            "- registrar gasto: descrição - valor (ex: Café - 10.50)\n"
            "- listar: mostra últimos 5 gastos\n"
            "- total hoje: soma dos gastos de hoje\n"
            "- total mês: soma dos gastos do mês\n"
            "- total categorias: mostra total por categoria do mês\n"
            "- ajuda / help: mostra esta mensagem"
        )

    else:
        # Tentar registrar gasto novo no formato "descrição - valor"
        try:
            descricao, valor = [x.strip() for x in msg.split('-', 1)]
            valor = float(valor.replace(',', '.'))
            data = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            categoria = detectar_categoria(descricao)
            nova_linha = f"{data},{descricao},{valor:.2f},{categoria}"

            # Checar se gasto já foi registrado (última linha)
            try:
                with open('gastos.csv', 'r') as f:
                    linhas = f.readlines()
                    ultima_linha = linhas[-1].strip() if linhas else ""
            except FileNotFoundError:
                linhas = []
                ultima_linha = ""

            if ultima_linha.endswith(f"{descricao},{valor:.2f},{categoria}"):
                resposta = "Esse gasto já foi registrado."
            else:
                with open('gastos.csv', 'a') as f:
                    if not linhas:
                        f.write("data,descricao,valor,categoria\n")
                    f.write(f"{nova_linha}\n")
                resposta = f"Gasto registrado: {descricao} - R${valor:.2f} ({categoria})"

        except Exception:
            resposta = "Formato inválido. Use: descrição - valor (ex: Café - 10.50)"

    resp = MessagingResponse()
    resp.message(resposta)
    return Response(str(resp), mimetype='application/xml')


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"Rodando na porta: {port}")
    app.run(host="0.0.0.0", port=port, debug=True)
