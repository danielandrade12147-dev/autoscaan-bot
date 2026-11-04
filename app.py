import hmac
import os
import secrets
from functools import wraps
from io import BytesIO
from pathlib import Path
from urllib.parse import quote, quote_plus

import pandas as pd
import requests
from dotenv import load_dotenv, set_key
from flask import (
    Flask,
    abort,
    flash,
    redirect,
    render_template_string,
    request,
    send_file,
    session,
    url_for,
)


BASE_DIR = Path(__file__).resolve().parent
ENV_FILE = BASE_DIR / ".env"
load_dotenv(ENV_FILE)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=bool(os.environ.get("RENDER")),
)

ADMIN_USER = os.environ.get("ADMIN_USER", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "1234")
NUVEMSHOP_API_VERSION = os.environ.get("NUVEMSHOP_API_VERSION", "v1").strip("/") or "v1"
STORE_DOMAIN = "https://autoscaanlogavirtualnuvem.com.br"

AGUARDANDO = "AGUARDANDO SUA AUTORIZAÇÃO"
APROVADO = "APROVADO - PRONTO PARA NUVEMSHOP"

PRODUCTS = [
    {"id": 1, "nome": "Mini Aspirador Portátil 12V", "categoria": "Acessórios automotivos", "custo": 42.00, "venda": 139.00, "emoji": "🧹"},
    {"id": 2, "nome": "HUD Display Projetor Velocidade", "categoria": "Eletrônicos automotivos", "custo": 65.00, "venda": 179.00, "emoji": "🚘"},
    {"id": 3, "nome": "Organizador Porta-Malas Dobrável", "categoria": "Organização automotiva", "custo": 38.00, "venda": 119.00, "emoji": "🧰"},
    {"id": 4, "nome": "Luz LED Interna RGB", "categoria": "Iluminação automotiva", "custo": 28.00, "venda": 97.00, "emoji": "💡"},
    {"id": 5, "nome": "Suporte Celular Retrovisor", "categoria": "Acessórios automotivos", "custo": 30.00, "venda": 99.00, "emoji": "📱"},
    {"id": 6, "nome": "Kit Restauração Farol", "categoria": "Cuidados automotivos", "custo": 35.00, "venda": 129.00, "emoji": "✨"},
    {"id": 7, "nome": "Capa Banco Couro Universal", "categoria": "Interior automotivo", "custo": 65.00, "venda": 179.00, "emoji": "🪑"},
    {"id": 8, "nome": "Shampoo com Cera Automotiva", "categoria": "Cuidados automotivos", "custo": 28.00, "venda": 97.00, "emoji": "🫧"},
    {"id": 9, "nome": "Tela Protetora Painel Carbono", "categoria": "Interior automotivo", "custo": 45.00, "venda": 129.00, "emoji": "🏎️"},
    {"id": 10, "nome": "Limpador Parabrisa com Reservatório", "categoria": "Acessórios automotivos", "custo": 35.00, "venda": 139.00, "emoji": "🚿"},
]

for product in PRODUCTS:
    product["lucro"] = round(product["venda"] - product["custo"], 2)
    product["lucro_pct"] = round(product["lucro"] / product["venda"] * 100, 1)
    product["demanda"] = "ALTA"
    product["status"] = AGUARDANDO
    product["subido_nuvem"] = False
    product["nuvemshop_id"] = ""
    product["erro_envio"] = ""


TAILWIND_HEAD = """
<script src="https://cdn.tailwindcss.com"></script>
<script>tailwind.config={theme:{extend:{colors:{auto:{950:'#07110f',900:'#0b1714',800:'#10231e',700:'#1a352d',500:'#17c964'}}}}}</script>
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="theme-color" content="#07110f">
"""

LOGIN_HTML = """
<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">{{ head|safe }}<title>Login | AUTOSCAAN AUTO</title></head>
<body class="min-h-screen bg-auto-950 text-slate-100 flex items-center justify-center p-5">
<main class="w-full max-w-md rounded-3xl border border-emerald-400/20 bg-auto-900 p-8 shadow-2xl shadow-black/40">
  <div class="mb-7 flex items-center gap-3"><div class="grid h-12 w-12 place-items-center rounded-2xl bg-emerald-400 text-2xl">🚘</div><div><p class="text-xs font-bold uppercase tracking-[.25em] text-emerald-300">AUTOSCAAN AUTO</p><h1 class="text-2xl font-black">Acesso do administrador</h1></div></div>
  {% if erro %}<p class="mb-4 rounded-xl border border-red-500/30 bg-red-950/50 px-4 py-3 font-bold text-red-300">{{ erro }}</p>{% endif %}
  <form method="post" action="{{ url_for('login') }}" class="space-y-4">
    <input type="hidden" name="_csrf_token" value="{{ csrf_token() }}">
    <label class="block text-sm text-slate-300">Usuário<input name="usuario" autocomplete="username" required class="mt-2 w-full rounded-xl border border-auto-700 bg-auto-950 px-4 py-3 text-white outline-none focus:border-emerald-400"></label>
    <label class="block text-sm text-slate-300">Senha<input name="senha" type="password" autocomplete="current-password" required class="mt-2 w-full rounded-xl border border-auto-700 bg-auto-950 px-4 py-3 text-white outline-none focus:border-emerald-400"></label>
    <button class="w-full rounded-xl bg-emerald-400 px-5 py-3 font-extrabold text-auto-950 transition hover:bg-emerald-300">Entrar no painel</button>
  </form>
  <a href="/" class="mt-6 inline-block text-sm text-emerald-300 hover:text-emerald-200">← Voltar ao site</a>
</main></body></html>
"""

ADMIN_HTML = """
<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">{{ head|safe }}<title>AUTOSCAAN AUTO - Bot Automotivo</title></head>
<body class="min-h-screen bg-auto-950 text-slate-100">
<header class="border-b border-white/10 bg-auto-900/90"><div class="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-4 px-5 py-5">
  <a href="/admin" class="flex items-center gap-3"><span class="grid h-11 w-11 place-items-center rounded-2xl bg-emerald-400 text-xl">🚘</span><span><strong class="block text-lg font-black tracking-wide">AUTOSCAAN AUTO</strong><span class="text-xs uppercase tracking-[.2em] text-emerald-300">BOT AUTOMOTIVO</span></span></a>
  <nav class="flex flex-wrap items-center gap-4 text-sm text-slate-300"><a class="hover:text-emerald-300" href="{{ url_for('admin') }}">Painel</a><a class="hover:text-emerald-300" href="{{ url_for('planilha') }}">Planilha</a><a class="hover:text-emerald-300" href="{{ url_for('configuracao') }}">Configuração</a><form method="post" action="{{ url_for('logout') }}"><input type="hidden" name="_csrf_token" value="{{ csrf_token() }}"><button class="rounded-lg border border-white/10 px-3 py-2 hover:border-red-400/50 hover:text-red-300">Sair</button></form></nav>
</div></header>
<main class="mx-auto max-w-7xl space-y-7 px-5 py-8">
  {% with messages = get_flashed_messages(with_categories=true) %}{% for category, message in messages %}<div class="rounded-xl border px-4 py-3 {{ 'border-emerald-400/30 bg-emerald-950/50 text-emerald-200' if category == 'success' else 'border-amber-400/30 bg-amber-950/40 text-amber-200' }}">{{ message }}</div>{% endfor %}{% endwith %}
  <section class="flex flex-col justify-between gap-5 md:flex-row md:items-end"><div><p class="mb-2 text-xs font-bold uppercase tracking-[.25em] text-emerald-300">Central de oportunidades</p><h1 class="text-3xl font-black sm:text-4xl">AUTOSCAAN AUTO - BOT AUTOMOTIVO</h1><p class="mt-2 max-w-2xl text-slate-400">Analise produtos, compare fornecedores e escolha o que deseja autorizar.</p></div><a href="{{ url_for('configuracao') }}" class="rounded-xl border border-white/10 px-4 py-3 text-sm hover:border-emerald-400/50">Nuvemshop: {{ 'Conectada' if conectado else 'Desconectada' }}</a></section>
  <section class="grid gap-4 sm:grid-cols-3">
    <article class="rounded-2xl border border-white/10 bg-auto-900 p-5"><p class="text-sm text-slate-400">Produtos em Análise</p><p class="mt-2 text-3xl font-black">{{ produtos|length }}</p><p class="mt-1 text-xs text-emerald-300">Catálogo automotivo</p></article>
    <article class="rounded-2xl border border-white/10 bg-auto-900 p-5"><p class="text-sm text-slate-400">Lucro Médio</p><p class="mt-2 text-3xl font-black">{{ lucro_medio|brl }}</p><p class="mt-1 text-xs text-emerald-300">Estimativa antes do frete</p></article>
    <article class="rounded-2xl border border-white/10 bg-auto-900 p-5"><p class="text-sm text-slate-400">Fornecedores Mapeados</p><p class="mt-2 text-3xl font-black">{{ fornecedores_total }}</p><p class="mt-1 text-xs text-emerald-300">3 opções por produto</p></article>
  </section>
  <section class="flex flex-col items-start justify-between gap-4 rounded-2xl border border-emerald-400/20 bg-gradient-to-r from-emerald-950/70 to-auto-900 p-5 md:flex-row md:items-center">
    <div><h2 class="text-lg font-extrabold">Encontre sua próxima oportunidade</h2><p class="mt-1 text-sm text-slate-400">A lista e os preços abaixo são dados de demonstração; a busca viral real precisa de uma fonte de dados conectada.</p></div>
    <form method="post" action="{{ url_for('buscar') }}"><input type="hidden" name="_csrf_token" value="{{ csrf_token() }}"><button class="rounded-xl bg-emerald-400 px-6 py-4 font-black text-auto-950 shadow-lg shadow-emerald-950/50 transition hover:bg-emerald-300">🔍 BUSCAR TOP 10 PRODUTOS AUTO MAIS VENDIDOS HOJE</button></form>
  </section>
  <section class="overflow-hidden rounded-2xl border border-white/10 bg-auto-900">
    <div class="flex flex-wrap items-center justify-between gap-3 border-b border-white/10 px-5 py-4"><div><h2 class="font-bold">Produtos automotivos</h2><p class="text-xs text-slate-400">Custos e fornecedores são estimativas simuladas.</p></div><a href="{{ url_for('planilha') }}" class="text-sm font-semibold text-emerald-300 hover:text-emerald-200">Ver planilha →</a></div>
    <div class="overflow-x-auto"><table class="min-w-[1050px] w-full text-left text-sm"><thead class="bg-white/[.03] text-xs uppercase tracking-wider text-slate-400"><tr><th class="px-4 py-3">Produto</th><th class="px-4 py-3">Custo</th><th class="px-4 py-3">Venda</th><th class="px-4 py-3">Lucro</th><th class="px-4 py-3">Lucro %</th><th class="px-4 py-3">Demanda</th><th class="px-4 py-3">Status</th><th class="px-4 py-3">Ações</th></tr></thead><tbody class="divide-y divide-white/5">
    {% for p in produtos %}<tr class="hover:bg-white/[.025]"><td class="px-4 py-4"><div class="flex items-center gap-3"><div class="grid h-14 w-14 shrink-0 place-items-center rounded-xl border border-white/10 bg-auto-800 text-2xl">{{ p.emoji }}</div><div><div class="font-bold text-white">{{ p.nome }}</div><div class="mt-1 text-xs text-slate-500">{{ p.categoria }} · imagem ilustrativa</div></div></div></td><td class="px-4 py-4">{{ p.custo|brl }}</td><td class="px-4 py-4 font-semibold">{{ p.venda|brl }}</td><td class="px-4 py-4 font-semibold text-emerald-300">{{ p.lucro|brl }}</td><td class="px-4 py-4">{{ '%.1f'|format(p.lucro_pct) }}%</td><td class="px-4 py-4"><span class="rounded-full bg-emerald-400/10 px-2.5 py-1 text-xs font-bold text-emerald-300">ALTA</span></td><td class="px-4 py-4"><span class="max-w-52 inline-block rounded-lg bg-white/5 px-2.5 py-1.5 text-xs text-slate-300">{{ p.status }}</span>{% if p.subido_nuvem %}<div class="mt-1 text-xs text-emerald-300">Criado na Nuvemshop · ID {{ p.nuvemshop_id }}</div>{% elif p.erro_envio %}<div class="mt-1 max-w-48 text-xs text-amber-300">{{ p.erro_envio }}</div>{% endif %}</td><td class="px-4 py-4"><div class="flex flex-col gap-2"><a href="{{ url_for('fornecedores', produto_id=p.id) }}" class="whitespace-nowrap rounded-lg border border-white/10 px-3 py-2 text-center text-xs font-semibold hover:border-emerald-400/50">Ver 3 Fornecedores</a>{% if p.subido_nuvem %}<button disabled class="rounded-lg bg-slate-700 px-3 py-2 text-xs font-bold text-slate-400">Enviado</button>{% else %}<form method="post" action="{{ url_for('aprovar', produto_id=p.id) }}" onsubmit="return confirm('Confirma a autorização para enviar este produto à Nuvemshop como produto oculto?')"><input type="hidden" name="_csrf_token" value="{{ csrf_token() }}"><button class="w-full whitespace-nowrap rounded-lg bg-emerald-400 px-3 py-2 text-xs font-black text-auto-950 hover:bg-emerald-300">{{ 'Aprovar' if p.status == aguardando else 'Enviar à Nuvemshop' }}</button></form>{% endif %}</div></td></tr>{% endfor %}
    </tbody></table></div>
  </section>
  <p class="text-xs leading-5 text-slate-500">Nenhum produto é enviado automaticamente. A aprovação é individual e gera um rascunho oculto na Nuvemshop. Configure as credenciais e revise os dados antes de publicá-lo na loja.</p>
</main></body></html>
"""

SUPPLIERS_HTML = """
<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">{{ head|safe }}<title>Fornecedores | AUTOSCAAN</title></head><body class="min-h-screen bg-auto-950 text-slate-100">
<header class="border-b border-white/10 bg-auto-900"><div class="mx-auto flex max-w-6xl items-center justify-between px-5 py-5"><a class="font-black tracking-wide" href="/admin">AUTOSCAAN AUTO</a><a class="text-sm text-emerald-300" href="/admin">← Voltar ao painel</a></div></header>
<main class="mx-auto max-w-6xl space-y-6 px-5 py-8"><div><p class="text-xs font-bold uppercase tracking-[.25em] text-emerald-300">Comparativo demonstrativo</p><h1 class="mt-2 text-3xl font-black">{{ produto.nome }}</h1><p class="mt-2 text-slate-400">Preços estimados para comparação; confirme valores, estoque e frete com o fornecedor.</p></div>
<div class="overflow-x-auto rounded-2xl border border-white/10 bg-auto-900"><table class="min-w-[850px] w-full text-left text-sm"><thead class="bg-white/[.03] text-xs uppercase text-slate-400"><tr><th class="px-4 py-3">Fornecedor</th><th class="px-4 py-3">Produto</th><th class="px-4 py-3">Frete</th><th class="px-4 py-3">Prazo</th><th class="px-4 py-3">Avaliação</th><th class="px-4 py-3">Lucro final</th><th class="px-4 py-3">Acesso</th></tr></thead><tbody class="divide-y divide-white/5">{% for f in fornecedores %}<tr class="{{ 'bg-emerald-500/10' if f.vencedor else '' }}"><td class="px-4 py-5 font-bold">{{ f.nome }}{% if f.vencedor %}<div class="mt-2 inline-block rounded-full bg-emerald-400 px-2.5 py-1 text-[10px] font-black tracking-wide text-auto-950">MELHOR OPÇÃO DROP</div>{% endif %}</td><td class="px-4 py-5">{{ f.preco|brl }}</td><td class="px-4 py-5">{{ 'Grátis' if f.frete == 0 else f.frete|brl }}</td><td class="px-4 py-5">{{ f.prazo }} dias</td><td class="px-4 py-5">⭐ {{ f.avaliacao }}</td><td class="px-4 py-5 font-bold text-emerald-300">{{ f.lucro_final|brl }} <span class="block text-xs font-normal text-slate-400">{{ '%.1f'|format(f.lucro_pct) }}% da venda</span></td><td class="px-4 py-5"><a class="rounded-lg border border-white/10 px-3 py-2 text-xs hover:border-emerald-400/50" href="{{ f.link }}" target="_blank" rel="noopener">Pesquisar produto</a></td></tr>{% endfor %}</tbody></table></div>
<section class="rounded-2xl border border-white/10 bg-auto-900 p-5"><h2 class="text-lg font-bold">Mensagem para o fornecedor</h2><p class="mb-3 mt-1 text-sm text-slate-400">Confira e ajuste a mensagem antes de enviar.</p><textarea id="mensagem-fornecedor" readonly class="min-h-28 w-full rounded-xl border border-auto-700 bg-auto-950 p-4 text-sm leading-6 text-slate-200">{{ mensagem }}</textarea><button onclick="navigator.clipboard.writeText(document.getElementById('mensagem-fornecedor').value)" class="mt-3 rounded-lg bg-emerald-400 px-4 py-2 text-sm font-bold text-auto-950">Copiar mensagem</button></section></main></body></html>
"""

PLANILHA_HTML = """
<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">{{ head|safe }}<title>Planilha | AUTOSCAAN AUTO</title></head><body class="min-h-screen bg-auto-950 text-slate-100">
<header class="border-b border-white/10 bg-auto-900"><div class="mx-auto flex max-w-7xl items-center justify-between px-5 py-5"><a class="font-black tracking-wide" href="/admin">AUTOSCAAN AUTO</a><nav class="flex gap-4 text-sm"><a class="text-emerald-300" href="/admin">Painel</a><a class="text-emerald-300" href="/configuracao">Configuração</a></nav></div></header>
<main class="mx-auto max-w-7xl space-y-6 px-5 py-8"><section class="rounded-2xl border border-amber-400/30 bg-amber-950/30 p-5"><h1 class="text-xl font-black text-amber-200">ESSE BOT SÓ SOBE PRODUTO COM SUA AUTORIZAÇÃO. CLIQUE EM APROVAR NOS PRODUTOS QUE QUER VENDER.</h1><p class="mt-2 text-sm text-amber-100/70">A planilha registra a situação atual do catálogo demonstrativo.</p></section><div class="flex flex-wrap items-center justify-between gap-4"><div><h2 class="text-2xl font-black">Planilha de produtos</h2><p class="mt-1 text-sm text-slate-400">10 produtos · 3 fornecedores comparados por produto</p></div><a href="{{ url_for('baixar_planilha') }}" class="rounded-xl bg-emerald-400 px-5 py-3 font-black text-auto-950 hover:bg-emerald-300">📥 BAIXAR PLANILHA COMPLETA .XLSX</a></div><div class="overflow-x-auto rounded-2xl border border-white/10 bg-auto-900"><table class="min-w-[1000px] w-full text-left text-xs"><thead class="bg-white/[.03] uppercase text-slate-400"><tr><th class="p-3">Produto</th><th class="p-3">Custo</th><th class="p-3">Frete</th><th class="p-3">Venda</th><th class="p-3">Lucro</th><th class="p-3">Fornecedor</th><th class="p-3">Prazo</th><th class="p-3">Status</th><th class="p-3">Nuvem?</th></tr></thead><tbody class="divide-y divide-white/5">{% for row in rows %}<tr><td class="p-3 font-semibold">{{ row.produto }}</td><td class="p-3">{{ row.custo|brl }}</td><td class="p-3">{{ row.frete|brl }}</td><td class="p-3">{{ row.venda|brl }}</td><td class="p-3 text-emerald-300">{{ row.lucro|brl }} ({{ '%.1f'|format(row.lucro_pct) }}%)</td><td class="p-3">{{ row.fornecedor }}</td><td class="p-3">{{ row.prazo }} dias</td><td class="p-3">{{ row.status }}</td><td class="p-3">{{ 'Sim' if row.subido else 'Não' }}</td></tr>{% endfor %}</tbody></table></div><a href="/admin" class="text-sm text-emerald-300">← Voltar ao painel</a></main></body></html>
"""

CONFIG_HTML = """
<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">{{ head|safe }}<title>Configuração | AUTOSCAAN AUTO</title></head><body class="min-h-screen bg-auto-950 text-slate-100">
<header class="border-b border-white/10 bg-auto-900"><div class="mx-auto flex max-w-5xl items-center justify-between px-5 py-5"><a class="font-black tracking-wide" href="/admin">AUTOSCAAN AUTO</a><a class="text-sm text-emerald-300" href="/admin">← Painel</a></div></header>
<main class="mx-auto max-w-3xl space-y-6 px-5 py-8"><div><p class="text-xs font-bold uppercase tracking-[.25em] text-emerald-300">Integração da loja</p><h1 class="mt-2 text-3xl font-black">Configuração Nuvemshop</h1><p class="mt-2 text-slate-400">As credenciais são gravadas em <code>.env</code> no servidor e não são exibidas novamente.</p></div>
{% with messages = get_flashed_messages(with_categories=true) %}{% for category, message in messages %}<div class="rounded-xl border px-4 py-3 {{ 'border-emerald-400/30 bg-emerald-950/50 text-emerald-200' if category == 'success' else 'border-amber-400/30 bg-amber-950/40 text-amber-200' }}">{{ message }}</div>{% endfor %}{% endwith %}
<section class="rounded-2xl border border-white/10 bg-auto-900 p-6"><p class="mb-5 rounded-xl {{ 'bg-emerald-950/50 text-emerald-200' if conectado else 'bg-amber-950/40 text-amber-200' }} px-4 py-3 text-sm font-semibold">{{ 'Conectado - credenciais configuradas; o envio exige aprovação individual.' if conectado else 'Desconectado - Coloque seu token para subir automaticamente' }}</p><form method="post" action="{{ url_for('configuracao') }}" class="space-y-5"><input type="hidden" name="_csrf_token" value="{{ csrf_token() }}"><label class="block text-sm text-slate-300">NUVEMSHOP_STORE_ID<input name="store_id" value="{{ store_id }}" required class="mt-2 w-full rounded-xl border border-auto-700 bg-auto-950 px-4 py-3 text-white outline-none focus:border-emerald-400"></label><label class="block text-sm text-slate-300">NUVEMSHOP_ACCESS_TOKEN<input name="access_token" type="password" autocomplete="new-password" placeholder="{{ 'Token salvo; deixe em branco para manter' if token_configurado else 'Cole aqui o token de acesso' }}" class="mt-2 w-full rounded-xl border border-auto-700 bg-auto-950 px-4 py-3 text-white outline-none focus:border-emerald-400"><span class="mt-1 block text-xs text-slate-500">O token salvo nunca é mostrado nesta página.</span></label><button class="rounded-xl bg-emerald-400 px-5 py-3 font-black text-auto-950 hover:bg-emerald-300">Salvar</button></form></section>
<section class="rounded-2xl border border-white/10 bg-auto-900 p-6"><h2 class="font-bold">Como obter o token</h2><p class="mt-2 text-sm leading-6 text-slate-300">Para pegar o token acesse: sua loja <code class="rounded bg-auto-950 px-2 py-1">/admin/apps/my-apps/</code>, crie um app com permissão de produtos (<code>write_products</code>).</p><p class="mt-3 text-xs leading-5 text-amber-200">No Render, configure STORE_ID, ACCESS_TOKEN, ADMIN_USER, ADMIN_PASSWORD e SECRET_KEY também nas variáveis Environment do serviço. O sistema de arquivos do serviço pode ser recriado em novos deploys; não dependa do <code>.env</code> gravado pela página para manter o token após um reinício.</p></section></main></body></html>
"""

HOME_HTML = """
<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">{{ head|safe }}<title>AUTOSCAAN AUTO</title></head><body class="min-h-screen bg-auto-950 text-white grid place-items-center p-6"><main class="max-w-2xl rounded-3xl border border-emerald-400/20 bg-auto-900 p-10 text-center shadow-2xl"><div class="text-5xl">🚘</div><h1 class="mt-5 text-4xl font-black">AUTOSCAAN AUTO</h1><p class="mt-3 text-slate-400">Bot automotivo para analisar produtos e fornecedores.</p><a class="mt-7 inline-block rounded-xl bg-emerald-400 px-6 py-3 font-black text-auto-950" href="{{ url_for('login') }}">Entrar no painel</a></main></body></html>
"""


def format_brl(value):
    formatted = f"{float(value):,.2f}"
    return "R$ " + formatted.replace(",", "X").replace(".", ",").replace("X", ".")


app.jinja_env.filters["brl"] = format_brl


def csrf_token():
    token = session.get("_csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        session["_csrf_token"] = token
    return token


app.jinja_env.globals["csrf_token"] = csrf_token


@app.before_request
def validate_csrf():
    if request.method == "POST":
        expected = session.get("_csrf_token", "")
        supplied = request.form.get("_csrf_token", "")
        if not expected or not supplied or not hmac.compare_digest(expected, supplied):
            abort(400, description="Token de segurança inválido. Atualize a página e tente novamente.")


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


def get_product(product_id):
    return next((product for product in PRODUCTS if product["id"] == product_id), None)


def get_supplier_offers(product):
    search = quote_plus(product["nome"])
    cost = product["custo"]
    sale = product["venda"]
    offers = [
        {
            "nome": "AliExpress Choice",
            "preco": round(cost * 0.72, 2),
            "frete": 12.00,
            "prazo": 12,
            "avaliacao": 4.8,
            "link": f"https://www.aliexpress.com/wholesale?SearchText={search}",
        },
        {
            "nome": "CJ Dropshipping BR",
            "preco": round(cost * 0.84, 2),
            "frete": 0.00,
            "prazo": 7,
            "avaliacao": 4.9,
            "link": f"https://cjdropshipping.com/search.html?key={search}",
        },
        {
            "nome": "Fornecedor Nacional Shopee",
            "preco": round(cost * 1.12, 2),
            "frete": 0.00,
            "prazo": 4,
            "avaliacao": 4.7,
            "link": f"https://shopee.com.br/search?keyword={search}",
        },
    ]
    for offer in offers:
        offer["lucro_final"] = round(sale - offer["preco"] - offer["frete"], 2)
        offer["lucro_pct"] = round(offer["lucro_final"] / sale * 100, 1)
    winner = max(offers, key=lambda offer: (offer["lucro_final"], offer["avaliacao"], -offer["prazo"]))
    for offer in offers:
        offer["vencedor"] = offer is winner
    return offers


def autorizar_e_subir(product):
    """Marca a autorização e, com credenciais, cria um produto oculto na Nuvemshop."""
    if product["subido_nuvem"]:
        return "Este produto já foi enviado à Nuvemshop."

    product["status"] = APROVADO
    product["erro_envio"] = ""

    store_id = os.environ.get("NUVEMSHOP_STORE_ID", "").strip()
    access_token = os.environ.get("NUVEMSHOP_ACCESS_TOKEN", "").strip()
    if not store_id or not access_token:
        return "Produto aprovado. Configure o ID da loja e o token para enviá-lo à Nuvemshop."

    description = (
        f"{product['nome']} — acessório automotivo. "
        f"Preço sugerido: R$ {product['venda']:.2f}. "
        "Confira compatibilidade, especificações e prazo de entrega antes da compra."
    )
    payload = {
        "name": {"pt": product["nome"]},
        "description": {"pt": description},
        "published": False,
        "variants": [{"price": f"{product['venda']:.2f}", "sku": f"AUTOSCAAN-{product['id']:03d}"}],
        "tags": "AUTOSCAAN, automotivo, produto em revisão",
    }
    store_path = quote(store_id, safe="")
    api_url = f"https://api.nuvemshop.com.br/{NUVEMSHOP_API_VERSION}/{store_path}/products"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json; charset=utf-8",
        "User-Agent": f"AUTOSCAAN AUTO BOT ({STORE_DOMAIN})",
    }

    try:
        response = requests.post(api_url, headers=headers, json=payload, timeout=20, allow_redirects=False)
        if response.status_code not in (200, 201):
            product["erro_envio"] = (
                f"Nuvemshop respondeu HTTP {response.status_code}. "
                "Verifique o token e a permissão write_products."
            )
            return product["erro_envio"]
        try:
            body = response.json()
        except ValueError:
            body = {}
        product["nuvemshop_id"] = str(body.get("id", ""))
        product["subido_nuvem"] = True
        return "Produto autorizado e criado como oculto na Nuvemshop. Revise-o antes de publicá-lo."
    except requests.RequestException:
        product["erro_envio"] = "Não foi possível conectar à Nuvemshop. A autorização foi salva; tente enviar novamente."
        return product["erro_envio"]


def make_spreadsheet_rows():
    rows = []
    for product in PRODUCTS:
        offers = get_supplier_offers(product)
        winner = next(offer for offer in offers if offer["vencedor"])
        message = (
            f"Olá fornecedor, sou da loja AUTOSCAAN em Nova Iguaçu-RJ, faço drop para todo Brasil "
            f"do produto {product['nome']}. Qual melhor preço para envio sem logo e com rastreio completo?"
        )
        rows.append(
            {
                "ID": product["id"],
                "Produto": product["nome"],
                "Categoria": product["categoria"],
                "Custo": winner["preco"],
                "Frete": winner["frete"],
                "Preço Venda Sugerido": product["venda"],
                "Lucro R$": winner["lucro_final"],
                "Lucro %": winner["lucro_pct"],
                "Melhor Fornecedor": winner["nome"],
                "Link Fornecedor": winner["link"],
                "Prazo Entrega": f"{winner['prazo']} dias",
                "Link Vídeo Anúncio": "A buscar",
                "Mensagem Fornecedor": message,
                "Status": product["status"],
                "Subido Nuvem?": "Sim" if product["subido_nuvem"] else "Não",
            }
        )
    return rows


@app.route("/")
def home():
    return render_template_string(HOME_HTML, head=TAILWIND_HEAD)


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("logged_in"):
        return redirect(url_for("admin"))
    erro = None
    if request.method == "POST":
        usuario = request.form.get("usuario", "")
        senha = request.form.get("senha", "")
        if hmac.compare_digest(usuario.encode("utf-8"), ADMIN_USER.encode("utf-8")) and hmac.compare_digest(
            senha.encode("utf-8"), ADMIN_PASSWORD.encode("utf-8")
        ):
            session.clear()
            session["logged_in"] = True
            session["username"] = usuario
            return redirect(url_for("admin"))
        erro = "Usuário ou senha incorretos."
    return render_template_string(LOGIN_HTML, head=TAILWIND_HEAD, erro=erro)


@app.route("/admin")
@login_required
def admin():
    average_profit = round(sum(product["lucro"] for product in PRODUCTS) / len(PRODUCTS), 2)
    return render_template_string(
        ADMIN_HTML,
        head=TAILWIND_HEAD,
        produtos=PRODUCTS,
        lucro_medio=average_profit,
        fornecedores_total=len(PRODUCTS) * 3,
        conectado=bool(os.environ.get("NUVEMSHOP_STORE_ID") and os.environ.get("NUVEMSHOP_ACCESS_TOKEN")),
        aguardando=AGUARDANDO,
    )


@app.route("/buscar", methods=["POST"])
@login_required
def buscar():
    flash(
        "10 produtos demonstrativos carregados. A descoberta de tendências em tempo real exige uma API de produtos ou tendências.",
        "info",
    )
    return redirect(url_for("admin"))


@app.route("/fornecedores/<int:produto_id>")
@login_required
def fornecedores(produto_id):
    product = get_product(produto_id)
    if not product:
        abort(404)
    message = (
        f"Olá fornecedor, sou da loja AUTOSCAAN em Nova Iguaçu-RJ, faço drop para todo Brasil "
        f"do produto {product['nome']}. Qual melhor preço para envio sem logo e com rastreio completo?"
    )
    return render_template_string(
        SUPPLIERS_HTML,
        head=TAILWIND_HEAD,
        produto=product,
        fornecedores=get_supplier_offers(product),
        mensagem=message,
    )


@app.route("/aprovar/<int:produto_id>", methods=["POST"])
@login_required
def aprovar(produto_id):
    product = get_product(produto_id)
    if not product:
        abort(404)
    message = autorizar_e_subir(product)
    flash(message, "success" if not product["erro_envio"] else "info")
    return redirect(url_for("admin"))


@app.route("/planilha")
@login_required
def planilha():
    return render_template_string(PLANILHA_HTML, head=TAILWIND_HEAD, rows=make_spreadsheet_rows())


@app.route("/planilha/baixar")
@login_required
def baixar_planilha():
    columns = [
        "ID",
        "Produto",
        "Categoria",
        "Custo",
        "Frete",
        "Preço Venda Sugerido",
        "Lucro R$",
        "Lucro %",
        "Melhor Fornecedor",
        "Link Fornecedor",
        "Prazo Entrega",
        "Link Vídeo Anúncio",
        "Mensagem Fornecedor",
        "Status",
        "Subido Nuvem?",
    ]
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        pd.DataFrame(make_spreadsheet_rows(), columns=columns).to_excel(
            writer, index=False, sheet_name="Produtos"
        )
        sheet = writer.sheets["Produtos"]
        sheet.freeze_panes = "A2"
        sheet.auto_filter.ref = sheet.dimensions
        for column_cells in sheet.columns:
            width = min(max(max(len(str(cell.value or "")) for cell in column_cells) + 2, 12), 48)
            sheet.column_dimensions[column_cells[0].column_letter].width = width
    output.seek(0)
    return send_file(
        output,
        as_attachment=True,
        download_name="AUTOSCAAN_AUTO_DROP.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@app.route("/configuracao", methods=["GET", "POST"])
@login_required
def configuracao():
    if request.method == "POST":
        store_id = request.form.get("store_id", "").strip()
        submitted_token = request.form.get("access_token", "").strip()
        access_token = submitted_token or os.environ.get("NUVEMSHOP_ACCESS_TOKEN", "").strip()
        if not store_id or not access_token:
            flash("Informe o ID da loja e o token de acesso antes de salvar.", "info")
        else:
            try:
                store_saved = set_key(str(ENV_FILE), "NUVEMSHOP_STORE_ID", store_id, quote_mode="always")[0]
                token_saved = set_key(
                    str(ENV_FILE), "NUVEMSHOP_ACCESS_TOKEN", access_token, quote_mode="always"
                )[0]
                if not store_saved or not token_saved:
                    raise OSError("Não foi possível gravar as credenciais.")
                os.environ["NUVEMSHOP_STORE_ID"] = store_id
                os.environ["NUVEMSHOP_ACCESS_TOKEN"] = access_token
                flash(
                    "Credenciais salvas. O token foi ocultado; os envios continuam exigindo sua aprovação.",
                    "success",
                )
            except OSError:
                flash("Não foi possível gravar o .env neste servidor. Configure as variáveis no Render.", "info")
        return redirect(url_for("configuracao"))

    current_store_id = os.environ.get("NUVEMSHOP_STORE_ID", "").strip()
    token_configurado = bool(os.environ.get("NUVEMSHOP_ACCESS_TOKEN", "").strip())
    return render_template_string(
        CONFIG_HTML,
        head=TAILWIND_HEAD,
        store_id=current_store_id,
        token_configurado=token_configurado,
        conectado=bool(current_store_id and token_configurado),
    )


@app.route("/logout", methods=["POST"])
@login_required
def logout():
    session.clear()
    return redirect(url_for("login"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "10000")))
