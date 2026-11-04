from flask import Flask, render_template_string, request, redirect, session
import os

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY") or os.urandom(32)

USUARIO = os.environ.get("ADMIN_USER", "admin")
SENHA = os.environ.get("ADMIN_PASSWORD", "1234")
SITE_URL = "https://autoscaan-bot-1.onrender.com"

ESTILO = """
<style>
    * { box-sizing: border-box; }
    body {
        margin: 0;
        min-height: 100vh;
        font-family: Arial, sans-serif;
        color: #e8f5ee;
        background: radial-gradient(circle at top, #194d38, #071711 65%);
        display: grid;
        place-items: center;
        padding: 24px;
    }
    .card {
        width: min(100%, 480px);
        padding: 36px;
        border: 1px solid rgba(134, 239, 172, .2);
        border-radius: 20px;
        background: rgba(9, 27, 19, .92);
        box-shadow: 0 24px 80px rgba(0, 0, 0, .38);
    }
    h1, h2 { margin-top: 0; }
    h1 { font-size: clamp(1.8rem, 6vw, 2.5rem); }
    p { color: #bdd4c6; line-height: 1.6; }
    label { display: block; text-align: left; margin: 18px 0 7px; color: #c5d9cc; }
    input {
        width: 100%; padding: 13px 14px; border-radius: 10px;
        border: 1px solid #315744; background: #0d2118; color: white;
        font-size: 1rem;
    }
    input:focus { outline: 2px solid #4ade80; border-color: transparent; }
    button, .button {
        display: inline-block; border: 0; border-radius: 10px;
        background: #22c55e; color: #06210f; font-weight: 700;
        padding: 13px 18px; text-decoration: none; cursor: pointer;
        font-size: 1rem; margin-top: 18px;
    }
    button:hover, .button:hover { background: #4ade80; }
    .muted-link { color: #86efac; }
    .error { color: #ff8585; font-weight: 700; margin: 16px 0 0; }
    .status { display: flex; align-items: center; gap: 10px; color: #86efac; font-weight: 700; }
    .dot { width: 10px; height: 10px; border-radius: 50%; background: #4ade80; box-shadow: 0 0 14px #4ade80; }
    .actions { display: flex; flex-wrap: wrap; align-items: center; gap: 12px; margin-top: 16px; }
    .actions .button { margin-top: 0; }
    hr { border: 0; border-top: 1px solid #294536; margin: 24px 0; }
    .home-card { text-align: center; }
</style>
"""

HTML_HOME = """
<!doctype html>
<html lang="pt-BR">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">{{ estilo|safe }}<title>AUTOSCAAN</title></head>
<body><main class="card home-card">
    <p class="status"><span class="dot"></span> SISTEMA ONLINE</p>
    <h1>BOT AUTOSCAAN TA NO AR!</h1>
    <p>O site está funcionando.</p>
    <a class="button" href="/admin">Abrir painel ADMIN</a>
</main></body>
</html>
"""

HTML_LOGIN = """
<!doctype html>
<html lang="pt-BR">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">{{ estilo|safe }}<title>ADMIN AUTOSCAAN</title></head>
<body><main class="card">
    <p class="status"><span class="dot"></span> ACESSO RESTRITO</p>
    <h1>ADMIN AUTOSCAAN</h1>
    <p>Entre para abrir o painel de controle.</p>
    {% if erro %}<p class="error">{{ erro }}</p>{% endif %}
    <form method="post" action="/admin">
        <label for="usuario">Usuário</label>
        <input id="usuario" name="usuario" autocomplete="username" required>
        <label for="senha">Senha</label>
        <input id="senha" name="senha" type="password" autocomplete="current-password" required>
        <button type="submit">Entrar no painel</button>
    </form>
    <p><a class="muted-link" href="/">Voltar ao site</a></p>
</main></body>
</html>
"""

HTML_PAINEL = """
<!doctype html>
<html lang="pt-BR">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">{{ estilo|safe }}<title>Painel AUTOSCAAN</title></head>
<body><main class="card">
    <p class="status"><span class="dot"></span> PAINEL ADMINISTRATIVO</p>
    <h1>BOT FUNCIONANDO 100%!</h1>
    <p>Você entrou como <strong>{{ usuario }}</strong>. O painel está pronto.</p>
    <hr>
    <h2>Status do bot</h2>
    <p>Consulte o status atual do serviço ou abra o site publicado.</p>
    <div class="actions">
        <a class="button" href="/status">Ver status</a>
        <a class="muted-link" href="{{ site_url }}" target="_blank" rel="noopener">Abrir site</a>
    </div>
    <p><a class="muted-link" href="/logout">Sair do painel</a></p>
</main></body>
</html>
"""

HTML_STATUS = """
<!doctype html>
<html lang="pt-BR">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">{{ estilo|safe }}<title>Status AUTOSCAAN</title></head>
<body><main class="card">
    <p class="status"><span class="dot"></span> STATUS ONLINE</p>
    <h1>BOT FUNCIONANDO 100%!</h1>
    <p>O servidor Flask respondeu normalmente.</p>
    <a class="button" href="/admin">Voltar ao painel</a>
</main></body>
</html>
"""


@app.route("/")
def home():
    return render_template_string(HTML_HOME, estilo=ESTILO)


@app.route("/admin", methods=["GET", "POST"])
def admin():
    if request.method == "POST":
        usuario = request.form.get("usuario", "")
        senha = request.form.get("senha", "")
        if usuario == USUARIO and senha == SENHA:
            session["logado"] = True
            session["usuario"] = usuario
            return redirect("/admin")
        return render_template_string(HTML_LOGIN, estilo=ESTILO, erro="Senha errada!")

    if session.get("logado"):
        return render_template_string(
            HTML_PAINEL,
            estilo=ESTILO,
            usuario=session.get("usuario", USUARIO),
            site_url=SITE_URL,
        )
    return render_template_string(HTML_LOGIN, estilo=ESTILO, erro=None)


@app.route("/status")
def status():
    if not session.get("logado"):
        return redirect("/admin")
    return render_template_string(HTML_STATUS, estilo=ESTILO)


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/admin")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "10000")))
