import os
from io import BytesIO

import pandas as pd
from flask import Flask, redirect, render_template_string, request, send_file, session, url_for


app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "autoscaan-offline-session-key")

ADMIN_USER = "admin"
ADMIN_PASSWORD = "1234"
AGUARDANDO = "AGUARDANDO SUA AUTORIZAÇÃO"

PRODUCTS = [
    {
        "nome": "Capa volante couro",
        "fornecedores": {"AliExpress Choice": 28.90, "CJ Dropshipping BR": 31.90, "Shopee Nacional": 35.00},
    },
    {
        "nome": "Organizador banco",
        "fornecedores": {"AliExpress Choice": 22.50, "CJ Dropshipping BR": 25.00, "Shopee Nacional": 27.90},
    },
    {
        "nome": "Aspirador portátil",
        "fornecedores": {"AliExpress Choice": 48.00, "CJ Dropshipping BR": 54.90, "Shopee Nacional": 59.90},
    },
    {
        "nome": "Suporte celular",
        "fornecedores": {"AliExpress Choice": 15.90, "CJ Dropshipping BR": 18.50, "Shopee Nacional": 21.00},
    },
    {
        "nome": "Película farol",
        "fornecedores": {"AliExpress Choice": 17.50, "CJ Dropshipping BR": 19.90, "Shopee Nacional": 23.50},
    },
    {
        "nome": "Aromatizador",
        "fornecedores": {"AliExpress Choice": 12.90, "CJ Dropshipping BR": 15.00, "Shopee Nacional": 16.90},
    },
    {
        "nome": "Capa cinto",
        "fornecedores": {"AliExpress Choice": 9.90, "CJ Dropshipping BR": 12.50, "Shopee Nacional": 14.00},
    },
    {
        "nome": "Tapete porta-malas",
        "fornecedores": {"AliExpress Choice": 38.00, "CJ Dropshipping BR": 43.00, "Shopee Nacional": 49.90},
    },
    {
        "nome": "Limpador vidro",
        "fornecedores": {"AliExpress Choice": 13.50, "CJ Dropshipping BR": 16.00, "Shopee Nacional": 17.90},
    },
    {
        "nome": "Luz led interna",
        "fornecedores": {"AliExpress Choice": 19.90, "CJ Dropshipping BR": 22.00, "Shopee Nacional": 25.00},
    },
]

for product in PRODUCTS:
    product["fornecedor_vencedor"], product["custo"] = min(
        product["fornecedores"].items(), key=lambda item: item[1]
    )
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
  <a class="download" href="{{ url_for('download') }}">📥 Baixar AUTOSCAAN_AUTO_DROP.xlsx</a>
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
def download():
    if not require_login():
        return redirect(url_for("admin"))

    rows = [
        {
            "Nome": product["nome"],
            "Preço": product["preco"],
            "Estoque (50)": 50,
            "Descrição": (
                f"{product['nome']} automotivo. Menor custo estimado: "
                f"{format_brl(product['custo'])}; preço sugerido com acréscimo de 50%: "
                f"{format_brl(product['preco'])}."
            ),
        }
        for product in PRODUCTS
    ]
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        pd.DataFrame(rows, columns=["Nome", "Preço", "Estoque (50)", "Descrição"]).to_excel(
            writer, index=False, sheet_name="Produtos"
        )
        worksheet = writer.sheets["Produtos"]
        worksheet.freeze_panes = "A2"
        worksheet.auto_filter.ref = worksheet.dimensions
        worksheet.column_dimensions["A"].width = 34
        worksheet.column_dimensions["B"].width = 16
        worksheet.column_dimensions["C"].width = 16
        worksheet.column_dimensions["D"].width = 72
    output.seek(0)
    return send_file(
        output,
        as_attachment=True,
        download_name="AUTOSCAAN_AUTO_DROP.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("admin"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "10000")))
