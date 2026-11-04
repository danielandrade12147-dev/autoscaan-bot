import csv
import os
from io import BytesIO, StringIO

from flask import Flask, redirect, render_template_string, request, send_file, session, url_for


app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "autoscaan-offline-session-key")

ADMIN_USER = "admin"
ADMIN_PASSWORD = "1234"
AGUARDANDO = "AGUARDANDO SUA AUTORIZAÇÃO"

PRODUCTS = [
    {
        "nome": "Capa volante couro",
        "categoria": "Acessórios automotivos",
        "peso": 450,
        "imagem_url": "https://ae01.alicdn.com/kf/Sc5477bafe3cf4784b336506192cd4adbe.jpg",
        "fornecedores": {"AliExpress Choice": 28.90, "CJ Dropshipping BR": 31.90, "Shopee Nacional": 35.00},
    },
    {
        "nome": "Organizador banco",
        "categoria": "Acessórios automotivos",
        "peso": 700,
        "imagem_url": "https://ae01.alicdn.com/kf/Sc1c337498d464700b69c839eab018df3O.jpg",
        "fornecedores": {"AliExpress Choice": 22.50, "CJ Dropshipping BR": 25.00, "Shopee Nacional": 27.90},
    },
    {
        "nome": "Aspirador portátil",
        "categoria": "Acessórios automotivos",
        "peso": 1200,
        "imagem_url": "https://ae01.alicdn.com/kf/Sa5fc9e63faa743b49857e6cd1caf36dfC.jpg",
        "fornecedores": {"AliExpress Choice": 48.00, "CJ Dropshipping BR": 54.90, "Shopee Nacional": 59.90},
    },
    {
        "nome": "Suporte celular",
        "categoria": "Acessórios automotivos",
        "peso": 250,
        "imagem_url": "https://ae01.alicdn.com/kf/HTB1EfOwac_vK1Rjy0Foq6xIxVXao.jpg",
        "fornecedores": {"AliExpress Choice": 15.90, "CJ Dropshipping BR": 18.50, "Shopee Nacional": 21.00},
    },
    {
        "nome": "Película farol",
        "categoria": "Acessórios automotivos",
        "peso": 200,
        "imagem_url": "https://ae01.alicdn.com/kf/S32d8f62d603e406eb169c69e421a758fR/Gloss-Transparent-Light-Black-Smoke-PVC-Film-Tint-30-X60cm-Auto-Car-Light-Headlight-Taillight-Tint.jpg",
        "fornecedores": {"AliExpress Choice": 17.50, "CJ Dropshipping BR": 19.90, "Shopee Nacional": 23.50},
    },
    {
        "nome": "Aromatizador",
        "categoria": "Aromatizadores",
        "peso": 180,
        "imagem_url": "https://ae01.alicdn.com/kf/S3e9908a40e6a4630b997bb5f43829245y.jpg",
        "fornecedores": {"AliExpress Choice": 12.90, "CJ Dropshipping BR": 15.00, "Shopee Nacional": 16.90},
    },
    {
        "nome": "Capa cinto",
        "categoria": "Acessórios automotivos",
        "peso": 100,
        "imagem_url": "https://ae01.alicdn.com/kf/S441f589525854abd9317a6981c7ee846V/Car-Accessories-Seat-Belt-For-Suzuki-Kizashi-Swift-Vitara-SX4-Pu-Leather-Safety-Belt-Shoulder-Cover.jpg",
        "fornecedores": {"AliExpress Choice": 9.90, "CJ Dropshipping BR": 12.50, "Shopee Nacional": 14.00},
    },
    {
        "nome": "Tapete porta-malas",
        "categoria": "Tapetes automotivos",
        "peso": 1500,
        "imagem_url": "https://ae01.alicdn.com/kf/Sc78a8241c48748ba9ddd40e21525a294Z.jpg",
        "fornecedores": {"AliExpress Choice": 38.00, "CJ Dropshipping BR": 43.00, "Shopee Nacional": 49.90},
    },
    {
        "nome": "Limpador vidro",
        "categoria": "Limpeza automotiva",
        "peso": 350,
        "imagem_url": "https://ae01.alicdn.com/kf/Se0d06305fafa4e3c88e312f61351f9bbS.jpg",
        "fornecedores": {"AliExpress Choice": 13.50, "CJ Dropshipping BR": 16.00, "Shopee Nacional": 17.90},
    },
    {
        "nome": "Luz led interna",
        "categoria": "Iluminação automotiva",
        "peso": 220,
        "imagem_url": "https://ae01.alicdn.com/kf/S85829c26ec7b4a9ca8a7400bf7867870G.jpg",
        "fornecedores": {"AliExpress Choice": 19.90, "CJ Dropshipping BR": 22.00, "Shopee Nacional": 25.00},
    },
]

for product_id, product in enumerate(PRODUCTS, start=1):
    product["id"] = product_id
    product["fornecedor_vencedor"], product["custo"] = min(
        product["fornecedores"].items(), key=lambda item: item[1]
    )
    product["sku"] = f"AUTOSCAAN-{product_id:03d}"
    product["preco"] = round(product["custo"] * 1.5, 2)
    product["lucro"] = round(product["preco"] - product["custo"], 2)
    product["status"] = AGUARDANDO


def format_brl(value):
    formatted = f"{value:,.2f}"
    return "R$ " + formatted.replace(",", "X").replace(".", ",").replace("X", ".")


app.jinja_env.filters["brl"] = format_brl

LOGIN_HTML = """
<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Login | AUTOSCAAN AUTO</title>
  <style>
    * { box-sizing: border-box; }
    body { min-height: 100vh; margin: 0; display: grid; place-items: center; padding: 24px;
      color: #e5e7eb; background: radial-gradient(circle at top, #153b30, #07110f 60%);
      font: 16px Arial, sans-serif; }
    .card { width: min(100%, 410px); padding: 34px; border: 1px solid #28483d;
      border-radius: 22px; background: #0b1714; box-shadow: 0 24px 80px #0008; }
    .eyebrow { color: #5ee29a; font-size: 12px; font-weight: bold; letter-spacing: .2em; }
    h1 { margin: 8px 0 24px; }
    label { display: block; margin: 16px 0 7px; color: #bac8c2; }
    input { width: 100%; padding: 13px; border: 1px solid #315347; border-radius: 10px;
      color: white; background: #07110f; font-size: 16px; }
    button { width: 100%; margin-top: 22px; padding: 14px; border: 0; border-radius: 10px;
      color: #062112; background: #4ade80; font-weight: 800; cursor: pointer; }
    button:hover { background: #86efac; }
    .error { margin-top: 18px; color: #f87171; font-weight: bold; }
  </style>
</head>
<body>
  <main class="card">
    <div class="eyebrow">AUTOSCAAN AUTO</div>
    <h1>Acesso do administrador</h1>
    <form method="post">
      <label for="usuario">Usuário</label>
      <input id="usuario" name="usuario" autocomplete="username" required>
      <label for="senha">Senha</label>
      <input id="senha" name="senha" type="password" autocomplete="current-password" required>
      <button type="submit">Entrar no painel</button>
    </form>
    {% if erro %}<p class="error">{{ erro }}</p>{% endif %}
  </main>
</body>
</html>
"""

ADMIN_HTML = """
<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>AUTOSCAAN AUTO - Catálogo</title>
  <style>
    * { box-sizing: border-box; }
    body { margin: 0; color: #e5e7eb; background: #07110f; font: 14px Arial, sans-serif; }
    header { border-bottom: 1px solid #1e3a32; background: #0b1714; }
    .wrap { width: min(1240px, calc(100% - 36px)); margin: auto; }
    .top { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 16px; padding: 22px 0; }
    .brand { color: #5ee29a; font-size: 12px; font-weight: bold; letter-spacing: .18em; }
    h1 { margin: 7px 0 0; font-size: clamp(22px, 4vw, 32px); }
    a { color: #86efac; text-decoration: none; }
    a:hover { color: white; }
    .logout { padding: 10px 14px; border: 1px solid #315347; border-radius: 9px; background: transparent; cursor: pointer; }
    main { padding: 28px 0 50px; }
    .notice { margin-bottom: 20px; padding: 14px 16px; border: 1px solid #345342; border-radius: 12px; color: #a7f3d0; background: #0c2119; }
    .summary { display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; margin-bottom: 20px; }
    .metric { padding: 18px; border: 1px solid #1e3a32; border-radius: 14px; background: #0b1714; }
    .metric span { color: #9ca3af; }
    .metric strong { display: block; margin-top: 8px; color: white; font-size: 24px; }
    .download { display: inline-block; margin: 0 0 18px; padding: 13px 18px; border-radius: 10px;
      color: #062112; background: #4ade80; font-weight: bold; }
    .download:hover { color: #062112; background: #86efac; }
    .table-box { overflow-x: auto; border: 1px solid #1e3a32; border-radius: 14px; background: #0b1714; }
    table { width: 100%; min-width: 980px; border-collapse: collapse; }
    th, td { padding: 14px 13px; border-bottom: 1px solid #1a2b25; text-align: left; vertical-align: top; }
    th { color: #9ca3af; background: #10231e; font-size: 11px; letter-spacing: .08em; text-transform: uppercase; }
    tr:last-child td { border-bottom: 0; }
    .supplier { display: block; margin: 0 0 5px; color: #aebcb6; white-space: nowrap; }
    .winner { color: #4ade80; font-weight: bold; }
    .profit { color: #86efac; font-weight: bold; }
    .status { display: inline-block; max-width: 220px; padding: 7px 9px; border: 1px solid #6b5428;
      border-radius: 8px; color: #fcd34d; background: #2b2110; font-size: 11px; line-height: 1.4; }
    .foot { margin-top: 14px; color: #788780; font-size: 12px; }
    @media (max-width: 680px) { .summary { grid-template-columns: 1fr; } .top { align-items: flex-start; } }
  </style>
</head>
<body>
<header><div class="wrap top">
  <div><div class="brand">AUTOSCAAN AUTO</div><h1>Catálogo automotivo</h1></div>
  <a class="logout" href="{{ url_for('logout') }}">Sair</a>
</div></header>
<main class="wrap">
  <div class="notice">Produtos e preços de fornecedores são estimativas offline. Todos aguardam sua autorização.</div>
  <section class="summary">
    <div class="metric"><span>Produtos em análise</span><strong>{{ produtos|length }}</strong></div>
    <div class="metric"><span>Lucro médio sobre o custo</span><strong>{{ lucro_medio|brl }}</strong></div>
    <div class="metric"><span>Fornecedores comparados</span><strong>{{ produtos|length * 3 }}</strong></div>
  </section>
  <a class="download" href="{{ url_for('download') }}">📥 Baixar CSV Nuvemshop (.csv)</a>
  <div class="table-box"><table>
    <thead><tr><th>Produto</th><th>3 fornecedores / custo</th><th>Menor custo</th><th>Preço de venda</th><th>Lucro</th><th>Status</th></tr></thead>
    <tbody>
    {% for produto in produtos %}
      <tr>
        <td><strong>{{ produto.nome }}</strong></td>
        <td>{% for nome, custo in produto.fornecedores.items() %}<span class="supplier {{ 'winner' if nome == produto.fornecedor_vencedor else '' }}">{{ nome }}: {{ custo|brl }}{% if nome == produto.fornecedor_vencedor %} · MENOR{% endif %}</span>{% endfor %}</td>
        <td class="winner">{{ produto.custo|brl }}<br><small>{{ produto.fornecedor_vencedor }}</small></td>
        <td>{{ produto.preco|brl }}</td>
        <td class="profit">{{ produto.lucro|brl }}</td>
        <td><span class="status">{{ produto.status }}</span></td>
      </tr>
    {% endfor %}
    </tbody>
  </table></div>
  <p class="foot">Preço sugerido = menor custo × 1,5. Lucro estimado antes de frete, taxas e impostos.</p>
</main>
</body>
</html>
"""


def require_login():
    return bool(session.get("logged_in"))


@app.route("/")
def home():
    return redirect(url_for("admin"))


@app.route("/admin", methods=["GET", "POST"])
def admin():
    if request.method == "POST":
        username = request.form.get("usuario", "")
        password = request.form.get("senha", "")
        if username == ADMIN_USER and password == ADMIN_PASSWORD:
            session["logged_in"] = True
            return redirect(url_for("admin"))
        return render_template_string(LOGIN_HTML, erro="Usuário ou senha incorretos.")

    if not require_login():
        return render_template_string(LOGIN_HTML, erro=None)

    average_profit = sum(product["lucro"] for product in PRODUCTS) / len(PRODUCTS)
    return render_template_string(
        ADMIN_HTML,
        produtos=PRODUCTS,
        lucro_medio=average_profit,
    )


@app.route("/download")
@app.route("/export-csv")
def download():
    if not require_login():
        return redirect(url_for("admin"))

    output = StringIO(newline="")
    writer = csv.writer(output, delimiter=";", lineterminator="\r\n")
    writer.writerow(["Nome", "Preco", "SKU", "Categorias", "Estoque", "Peso", "Descricao", "Imagens"])
    for product in PRODUCTS:
        description = (
            f"{product['nome']} automotivo. Menor custo estimado: "
            f"{product['custo']:.2f}. Preço sugerido com acréscimo de 50% sobre o custo."
        )
        writer.writerow(
            [
                product["nome"],
                f"{product['preco']:.2f}",
                product["sku"],
                product["categoria"],
                50,
                product["peso"],
                description,
                product["imagem_url"],
            ]
        )
    output.seek(0)
    return send_file(
        BytesIO(output.getvalue().encode("utf-8")),
        as_attachment=True,
        download_name="AUTOSCAAN_AUTO_DROP.csv",
        mimetype="text/csv; charset=utf-8",
    )


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("admin"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "10000")))
