"""API da loja — Flask.

Rotas:
    GET  /                 -> status da API
    GET  /produtos         -> lista de produtos (aceita ?q=termo)
    GET  /produtos/<id>    -> detalhe de um produto
    POST /pedidos          -> finaliza a compra (baixa estoque, gera nº do pedido)
    POST /resetar          -> volta os estoques ao valor inicial (demonstração)
"""

import copy
import os
import threading
from datetime import datetime, timezone

from flask import Flask, jsonify, request

app = Flask(__name__)

# Produtos vindos do projeto mcp-encontrabilidade (+ descrição e categoria).
PRODUTOS_INICIAIS = [
    {"id": "fone-a", "nome": "Fone Pulse Air", "preco": 199.90, "estoque": 12,
     "descricao": "Fone bluetooth sem fio com estojo de carga e até 24h de bateria.",
     "emoji": "🎧"},
    {"id": "fone-b", "nome": "Fone Run Pro", "preco": 249.90, "estoque": 0,
     "descricao": "Fone esportivo resistente a suor, com encaixe firme para corrida.",
     "emoji": "🏃"},
    {"id": "fone-c", "nome": "Fone Lit Basic", "preco": 129.90, "estoque": 30,
     "descricao": "Fone de entrada com ótimo custo-benefício e microfone embutido.",
     "emoji": "🎵"},
]

produtos = {p["id"]: copy.deepcopy(p) for p in PRODUTOS_INICIAIS}
proximo_pedido = 1001
trava = threading.Lock()  # evita duas compras mexendo no estoque ao mesmo tempo


@app.after_request
def liberar_cors(resp):
    """Permite que a loja (GitHub Pages) chame esta API de outro domínio."""
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
    resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return resp


@app.route("/pedidos", methods=["OPTIONS"])
@app.route("/resetar", methods=["OPTIONS"])
def preflight():
    return "", 204


@app.get("/")
def status():
    return jsonify({"status": "ok", "api": "loja", "produtos": len(produtos)})


@app.get("/produtos")
def listar_produtos():
    termo = (request.args.get("q") or "").strip().lower()
    lista = [p for p in produtos.values() if termo in p["nome"].lower()]
    return jsonify(lista)


@app.get("/produtos/<produto_id>")
def detalhe_produto(produto_id):
    produto = produtos.get(produto_id)
    if produto is None:
        return jsonify({"erro": "Produto não encontrado."}), 404
    return jsonify(produto)


@app.post("/pedidos")
def finalizar_compra():
    """Body: {"cliente": {"nome": "...", "email": "..."}, "itens": [{"id": "fone-a", "quantidade": 2}]}"""
    global proximo_pedido
    dados = request.get_json(silent=True) or {}
    itens = dados.get("itens")

    if not isinstance(itens, list) or not itens:
        return jsonify({"erro": "A sacola está vazia."}), 400

    # Junta itens repetidos e valida o formato.
    quantidades = {}
    for item in itens:
        try:
            pid = item["id"]
            qtd = int(item["quantidade"])
        except (KeyError, TypeError, ValueError):
            return jsonify({"erro": "Item inválido no pedido."}), 400
        if qtd < 1:
            return jsonify({"erro": "Quantidade deve ser ao menos 1."}), 400
        quantidades[pid] = quantidades.get(pid, 0) + qtd

    with trava:
        # 1) Valida TUDO antes de baixar qualquer estoque (compra "tudo ou nada").
        for pid, qtd in quantidades.items():
            produto = produtos.get(pid)
            if produto is None:
                return jsonify({"erro": f"Produto '{pid}' não existe."}), 404
            if produto["estoque"] == 0:
                return jsonify({
                    "erro": f"{produto['nome']} está esgotado e não pode ser comprado.",
                    "produto_id": pid,
                }), 409
            if qtd > produto["estoque"]:
                return jsonify({
                    "erro": f"Só temos {produto['estoque']} unidade(s) de {produto['nome']}.",
                    "produto_id": pid,
                }), 409

        # 2) Baixa o estoque e monta o pedido.
        linhas, total = [], 0.0
        for pid, qtd in quantidades.items():
            produto = produtos[pid]
            produto["estoque"] -= qtd
            subtotal = round(produto["preco"] * qtd, 2)
            total += subtotal
            linhas.append({"id": pid, "nome": produto["nome"], "quantidade": qtd,
                           "preco": produto["preco"], "subtotal": subtotal})

        numero = f"PED-{proximo_pedido}"
        proximo_pedido += 1

    print(f"[pedido] {numero} total={total:.2f}", flush=True)
    return jsonify({
        "numero_pedido": numero,
        "cliente": dados.get("cliente") or {},
        "itens": linhas,
        "total": round(total, 2),
        "criado_em": datetime.now(timezone.utc).isoformat(),
    }), 201


@app.post("/resetar")
def resetar_estoques():
    """Volta os estoques ao valor inicial e reinicia a numeração dos pedidos."""
    global produtos, proximo_pedido
    with trava:
        produtos = {p["id"]: copy.deepcopy(p) for p in PRODUTOS_INICIAIS}
        proximo_pedido = 1001
    return jsonify({"mensagem": "Estoques resetados.", "produtos": list(produtos.values())})


if __name__ == "__main__":
    porta = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=porta)
