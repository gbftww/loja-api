const express = require("express");
const app = express();
app.use(express.json());

// CORS simples (permite o front no GitHub Pages chamar a API)
app.use((req, res, next) => {
  res.header("Access-Control-Allow-Origin", "*");
  res.header("Access-Control-Allow-Headers", "Content-Type");
  res.header("Access-Control-Allow-Methods", "GET,POST,OPTIONS");
  if (req.method === "OPTIONS") return res.sendStatus(204);
  next();
});

const INICIAL = [
  { id: 1, nome: "Camiseta Preta", preco: 59.9, estoque: 10, emoji: "👕", descricao: "Camiseta de algodão, corte reto." },
  { id: 2, nome: "Caneca de Cerâmica", preco: 34.5, estoque: 5, emoji: "☕", descricao: "Caneca branca de 300 ml." },
  { id: 3, nome: "Fone de Ouvido", preco: 129.0, estoque: 3, emoji: "🎧", descricao: "Fone com fio e microfone." },
  { id: 4, nome: "Mochila", preco: 199.9, estoque: 0, emoji: "🎒", descricao: "Mochila resistente de 20 litros." },
  { id: 5, nome: "Boné", preco: 49.0, estoque: 8, emoji: "🧢", descricao: "Boné ajustável." },
];

let produtos = JSON.parse(JSON.stringify(INICIAL));
let proximoPedido = 1001;

app.get("/", (req, res) => res.json({ status: "API da loja no ar" }));

// Listar produtos
app.get("/produtos", (req, res) => res.json(produtos));

// Detalhe de um produto
app.get("/produtos/:id", (req, res) => {
  const p = produtos.find((x) => x.id === Number(req.params.id));
  if (!p) return res.status(404).json({ erro: "Produto não encontrado" });
  res.json(p);
});

// Finalizar compra: body { itens: [{ id, quantidade }] }
app.post("/comprar", (req, res) => {
  const itens = req.body.itens;
  if (!Array.isArray(itens) || itens.length === 0)
    return res.status(400).json({ erro: "Sacola vazia" });

  // 1) valida tudo antes de baixar o estoque
  for (const item of itens) {
    const p = produtos.find((x) => x.id === Number(item.id));
    const qtd = Number(item.quantidade);
    if (!p) return res.status(404).json({ erro: "Produto não encontrado" });
    if (!(qtd > 0)) return res.status(400).json({ erro: "Quantidade inválida" });
    if (p.estoque === 0) return res.status(400).json({ erro: `${p.nome} está sem estoque` });
    if (qtd > p.estoque)
      return res.status(400).json({ erro: `${p.nome}: só temos ${p.estoque} em estoque` });
  }

  // 2) baixa o estoque e calcula o total
  let total = 0;
  for (const item of itens) {
    const p = produtos.find((x) => x.id === Number(item.id));
    p.estoque -= Number(item.quantidade);
    total += p.preco * Number(item.quantidade);
  }

  res.json({ pedido: proximoPedido++, total: Math.round(total * 100) / 100 });
});

// Resetar estoques (para demonstrações)
app.post("/resetar", (req, res) => {
  produtos = JSON.parse(JSON.stringify(INICIAL));
  res.json({ ok: true });
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => console.log("API rodando na porta " + PORT));
