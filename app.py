from flask import Flask, render_template_string, request, redirect, session
import os

app = Flask(__name__)
app.secret_key = "autoscaan123"

# LOGIN SIMPLES
USUARIO = "admin"
SENHA = "123"

HTML_LOGIN = """
<h2 style="text-align:center; margin-top:100px;">ADMIN AUTOSCAAN</h2>
<form method="post" style="text-align:center;">
<input name="usuario" placeholder="Usuário" style="padding:10px;"><br><br>
<input name="senha" type="password" placeholder="Senha" style="padding:10px;"><br><br>
<button style="padding:10px 30px; background:green; color:white; border:none;">ENTRAR</button>
</form>
"""

HTML_PAINEL = """
<h1>BOT AUTOSCAAN TA NO AR! ✅</h1>
<p>Logado como: admin | <a href='/logout'>Sair</a></p>
<hr>
<h2>Painel de Controle</h2>
<ul>
<li>✅ Bot Online</li>
<li>✅ Flask Funcionando</li>
<li>✅ Pronto para Deploy no Render</li>
</ul>
<p>Link do Bot: <a href='/'>Home</a> | <a href='/admin'>Admin</a></p>
"""

@app.route("/")
def home():
    return "<h1>BOT AUTOSCAAN TA NO AR!</h1><p>Site funcionando!</p><a href='/admin'>Ir para ADMIN</a>"

@app.route("/admin", methods=["GET", "POST"])
def admin():
    if request.method == "POST":
        if request.form.get("usuario") == USUARIO and request.form.get("senha") == SENHA:
            session["logado"] = True
            return redirect("/painel")
        else:
            return HTML_LOGIN + "<p style='color:red; text-align:center;'>Senha errada!</p>"
    
    if session.get("logado"):
        return redirect("/painel")
    
    return HTML_LOGIN

@app.route("/painel")
def painel():
    if not session.get("logado"):
        return redirect("/admin")
    return render_template_string(HTML_PAINEL)

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/admin")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
