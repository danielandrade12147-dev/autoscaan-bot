from flask import Flask
app = Flask(__name__)

@app.route("/")
def home():
    return "<h1>BOT AUTOSCAAN TA NO AR!</h1><p>Funcionou!</p><br><a href='/admin'>ADMIN</a>"

@app.route("/admin")
def admin():
    return "<h2>ADMIN AUTOSCAAN</h2><p>Bot funcionando</p>"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
