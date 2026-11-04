import csv
from html import escape
import json
import logging
import os
import re
import secrets
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime
from io import BytesIO, StringIO
from urllib.parse import quote_plus, urljoin

import requests
from apscheduler.schedulers.background import BackgroundScheduler
from bs4 import BeautifulSoup
from flask import (
    Flask,
    flash,
    redirect,
    render_template_string,
    request,
    send_file,
    send_from_directory,
    session,
    url_for,
)


app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "scaan-auto-offline-session-key")

ADMIN_USER = "admin"
ADMIN_PASSWORD = "1234"
AGUARDANDO = "AGUARDANDO SUA AUTORIZAÇÃO"
DATA_DIR = os.environ.get("SCAAN_DATA_DIR", os.path.dirname(os.path.abspath(__file__)))
EXPORT_DIR = os.path.join(DATA_DIR, "exports")
LATEST_PRODUCTS_FILE = os.path.join(EXPORT_DIR, "produtos_atuais.json")
ALIEXPRESS_SEARCH_URL = "https://www.aliexpress.com/w/wholesale.html"
ALIEXPRESS_CATEGORIAS = [
    "pneu",
    "pastilha freio",
    "vela ignicao",
    "filtro oleo",
    "kit embreagem",
    "amortecedor",
    "correia dentada",
    "disco freio",
    "rolamento",
    "capa cinto",
    "aromatizador",
    "pelicula farol",
    "suporte celular",
    "aspirador portatil",
]
logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))
logger = logging.getLogger("scaan_auto")
PRECO_SELECTORS = (
    ".product-price-value",
    ".product-price-current",
    ".uniform-banner-box-price",
    'span[class*="price"]',
)
IMAGEM_SELECTORS = (
    ".magnifier-image",
    ".images-view-item img",
    ".image-view img",
    'img[class*="product-image"]',
)
CAMBIO_USD_BRL = 5.2
PRECO_RESERVA_BRL = 29.90

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


def calcular_preco(product):
    try:
        preco_custo = float(product.get("custo"))
    except (TypeError, ValueError):
        preco_custo = PRECO_RESERVA_BRL
        product["custo_estimado"] = True
    if preco_custo <= 0:
        preco_custo = PRECO_RESERVA_BRL
        product["custo_estimado"] = True
    preco_venda = round(preco_custo * 1.5, 2)
    product["custo"] = preco_custo
    product["venda"] = preco_venda
    product["preco"] = preco_venda
    product["lucro"] = round(preco_venda - preco_custo, 2)
    return preco_venda


def normalizar_url_imagem(image_url):
    if not image_url:
        return ""
    image_url = str(image_url).strip()
    if image_url.startswith("//"):
        image_url = "https:" + image_url
    elif image_url.startswith("http://"):
        image_url = "https://" + image_url[len("http://"):]
    if not image_url.startswith("https://"):
        return ""
    return image_url


def normalizar_imagens(image_urls):
    if isinstance(image_urls, str):
        values = image_urls.split("|")
    elif isinstance(image_urls, (tuple, list, set)):
        values = list(image_urls)
    else:
        values = [image_urls]

    normalized = []
    for value in values:
        if isinstance(value, dict):
            value = value.get("url") or value.get("src") or value.get("imageUrl")
        url = normalizar_url_imagem(value)
        if url and url not in normalized:
            normalized.append(url)
    return "|".join(normalized)


def imagens_do_produto(product):
    images = normalizar_imagens(product.get("imagens") or product.get("imagem") or product.get("imagem_url"))
    return [url for url in images.split("|") if url]


def traduzir_titulo(title):
    title = " ".join(str(title or "").split())
    translations = (
        (r"\btire\s+cover\b", "Capa de Pneu Estepe"),
        (r"\bcar\s+light\b", "Lâmpada LED Automotiva"),
    )
    for pattern, replacement in translations:
        title = re.sub(pattern, replacement, title, flags=re.IGNORECASE)
    return title


def peso_kg_para_titulo(title):
    lowered = str(title or "").casefold()
    if "pneu" in lowered or "capa" in lowered:
        return 3.5
    if "lampada" in lowered or "lâmpada" in lowered:
        return 0.2
    return 0.5


def novo_sku(usados=None):
    usados = usados if usados is not None else set()
    for _ in range(100):
        sku = f"SCAAN-{secrets.randbelow(9000) + 1000}"
        if sku not in usados:
            usados.add(sku)
            return sku
    raise RuntimeError("Não foi possível gerar um SKU único.")


for product_id, product in enumerate(PRODUCTS, start=1):
    product["id"] = product_id
    product["fornecedor_vencedor"], product["custo"] = min(
        product["fornecedores"].items(), key=lambda item: item[1]
    )
    product["sku"] = novo_sku({item["sku"] for item in PRODUCTS[:product_id - 1]})
    product["imagem"] = product["imagem_url"]
    product["imagens"] = product["imagem"]
    product["estoque"] = 50
    product["peso"] = peso_kg_para_titulo(product["nome"])
    product["descricao"] = product["nome"]
    calcular_preco(product)
    product["status"] = AGUARDANDO


def _price_value(value, currency_hint=None, page_has_brl=False):
    if isinstance(value, dict):
        currency_hint = value.get("currencyCode") or value.get("currency") or currency_hint
        for key in ("formattedPrice", "formatted", "value", "amount", "min"):
            if value.get(key) is not None:
                value = value[key]
                break
    currency_hint = str(currency_hint or "").upper()
    if isinstance(value, (int, float)):
        if currency_hint in ("USD", "US$", "$"):
            return round(float(value) * CAMBIO_USD_BRL, 2) if float(value) > 0 else None
        if currency_hint not in ("BRL", "R$", "REAL", "REAIS") and not page_has_brl:
            return None
        return round(float(value), 2) if float(value) > 0 else None

    text = str(value or "").strip()
    lowered = text.casefold()
    is_brl = "r$" in lowered or "brl" in lowered or currency_hint in ("BRL", "R$", "REAL", "REAIS")
    is_usd = not is_brl and (
        ("$" in text and "r$" not in lowered) or "usd" in lowered or currency_hint in ("USD", "US$")
    )
    if not is_brl and not is_usd and not page_has_brl:
        return None
    match = re.search(r"([0-9][0-9.,]*[0-9]|[0-9])", text)
    if not match:
        return None
    number = match.group(1)
    if "," in number and "." in number and number.rfind(",") > number.rfind("."):
        number = number.replace(".", "").replace(",", ".")
    elif "," in number and "." not in number:
        number = number.replace(",", ".")
    else:
        number = number.replace(",", "")
    try:
        parsed = float(number)
    except ValueError:
        return None
    if is_usd:
        parsed *= CAMBIO_USD_BRL
    return round(parsed, 2) if parsed > 0 else None


def _first_value(item, keys):
    for key in keys:
        value = item.get(key)
        if value not in (None, ""):
            return value
    return None


def _image_value(value):
    if isinstance(value, list):
        return next((url for url in (_image_value(item) for item in value) if url), "")
    if isinstance(value, dict):
        value = _first_value(value, ("url", "src", "imageUrl"))
    return normalizar_url_imagem(value)


def _images_in_element(element):
    images = []
    for selector in IMAGEM_SELECTORS:
        for image_tag in element.select(selector):
            for attribute in ("src", "data-src", "data-lazy-src", "data-original"):
                candidate = image_tag.get(attribute)
                if candidate:
                    normalized = normalizar_url_imagem(candidate)
                    if normalized and normalized not in images:
                        images.append(normalized)
            srcset = image_tag.get("srcset", "")
            if srcset:
                for candidate in srcset.split(","):
                    normalized = normalizar_url_imagem(candidate.strip().split(" ")[0])
                    if normalized and normalized not in images:
                        images.append(normalized)
    if not images:
        for image_tag in element.select("img"):
            candidate = next(
                (
                    image_tag.get(attribute)
                    for attribute in ("src", "data-src", "data-lazy-src", "data-original")
                    if image_tag.get(attribute)
                ),
                "",
            )
            normalized = normalizar_url_imagem(candidate)
            if normalized and normalized not in images:
                images.append(normalized)
    return images


def _price_from_element(element, page_has_brl):
    for selector in PRECO_SELECTORS:
        price_node = element.select_one(selector)
        if not price_node:
            continue
        value = price_node.get("content") or price_node.get("data-price") or price_node.get_text(" ", strip=True)
        price = _price_value(value, page_has_brl=page_has_brl)
        if price:
            return price
    return None


def _walk_product_data(node, page_has_brl, category):
    if isinstance(node, dict):
        title = _first_value(node, ("title", "productTitle", "name", "subject"))
        images = normalizar_imagens(
            _first_value(node, ("imageUrl", "image", "productImage", "productImageUrl", "imgUrl", "imageMain"))
        )
        if title and not images:
            logger.warning("Produto sem foto nos dados AliExpress: %s", title)
        price = _first_value(node, ("formattedPrice", "salePrice", "price", "priceValue", "actPrice", "minPrice"))
        currency = node.get("currencyCode") or node.get("currency")
        cost = _price_value(price, currency, page_has_brl) if price is not None else None
        if title and images:
            estimated = cost is None or cost <= 0
            cost = cost if not estimated else PRECO_RESERVA_BRL
            yield {
                "nome": traduzir_titulo(title),
                "custo": cost,
                "imagens": images,
                "imagem": images,
                "categoria": category,
                "url_produto": _first_value(node, ("productDetailUrl", "productUrl", "detailUrl", "url")) or "",
                "custo_estimado": estimated,
            }
        for child in node.values():
            yield from _walk_product_data(child, page_has_brl, category)
    elif isinstance(node, list):
        for child in node:
            yield from _walk_product_data(child, page_has_brl, category)


def _json_roots_from_html(soup):
    decoder = json.JSONDecoder()
    markers = re.compile(r"(?:runParams|__NEXT_DATA__|pageData|productList|initialData)\s*[:=]\s*", re.I)
    for script in soup.find_all("script"):
        script_text = script.string or script.get_text() or ""
        script_text = script_text.strip()
        if not script_text:
            continue
        if "json" in str(script.get("type", "")).lower():
            try:
                yield json.loads(script_text)
            except (json.JSONDecodeError, TypeError):
                pass
        for marker in markers.finditer(script_text):
            start = marker.end()
            while start < len(script_text) and script_text[start].isspace():
                start += 1
            if start < len(script_text) and script_text[start] in "[{":
                try:
                    root, _ = decoder.raw_decode(script_text[start:])
                    yield root
                except json.JSONDecodeError:
                    continue


def _products_from_cards(soup, page_has_brl, category):
    results = []
    for anchor in soup.select("a[href*='/item/']"):
        title = traduzir_titulo(anchor.get("title") or anchor.get_text(" ", strip=True))
        if not title or len(title) < 4:
            continue
        card = anchor
        for _ in range(4):
            if card.parent is None:
                break
            card = card.parent
            if card.find("img"):
                break
        images = _images_in_element(card) if card else []
        if not images:
            logger.warning("Produto sem foto no resultado AliExpress: %s", title)
            continue
        card_text = card.get_text(" ", strip=True)
        cost = _price_from_element(card, page_has_brl)
        if cost is None:
            currency_match = re.search(r"(?:R\$|BRL)\s*[0-9][0-9.,]*", card_text, re.I)
            cost = _price_value(currency_match.group(0), "BRL", page_has_brl) if currency_match else None
        if cost is None:
            currency_match = re.search(r"(?:US\s*)?\$\s*[0-9][0-9.,]*", card_text, re.I)
            cost = _price_value(currency_match.group(0), "USD") if currency_match else None
        estimated = cost is None
        if estimated:
            cost = PRECO_RESERVA_BRL
        results.append(
            {
                "nome": title,
                "custo": cost,
                "imagens": images,
                "imagem": images,
                "categoria": category,
                "url_produto": urljoin(ALIEXPRESS_SEARCH_URL, anchor.get("href", "")),
                "custo_estimado": estimated,
            }
        )
    return results


def _buscar_categoria_aliexpress(category):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0 Safari/537.36",
        "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.7",
    }
    response = requests.get(
        ALIEXPRESS_SEARCH_URL,
        params={"SearchText": category, "currency": "BRL", "shipTo": "BR", "lang": "pt_BR"},
        headers=headers,
        timeout=(5, 12),
    )
    response.raise_for_status()
    page_has_brl = "R$" in response.text or "BRL" in response.text.upper()
    if not page_has_brl:
        logger.info("AliExpress não apresentou preços em reais para a busca '%s'.", category)
    soup = BeautifulSoup(response.text, "lxml")
    products = []
    for root in _json_roots_from_html(soup):
        products.extend(_walk_product_data(root, page_has_brl, category))
    products.extend(_products_from_cards(soup, page_has_brl, category))
    if not products:
        logger.warning("Busca AliExpress sem produtos com foto para a categoria '%s'.", category)
    return products


def buscar_produtos(qtd=100):
    """Busca resultados públicos do AliExpress e mantém fallback local com imagens."""
    qtd = max(0, int(qtd))
    if qtd == 0:
        return []

    por_categoria = {}
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(_buscar_categoria_aliexpress, category): category for category in ALIEXPRESS_CATEGORIAS}
        for future in futures:
            category = futures[future]
            try:
                category_products = future.result()
            except Exception as error:
                logger.warning("Falha na busca AliExpress '%s': %s", category, error)
                continue
            por_categoria[category] = []
            vistos_categoria = set()
            for product in category_products:
                image_list = normalizar_imagens(product.get("imagens") or product.get("imagem"))
                image = image_list.split("|", 1)[0] if image_list else ""
                title = traduzir_titulo(" ".join(product.get("nome", "").split()))
                try:
                    cost = float(product.get("custo"))
                except (TypeError, ValueError):
                    continue
                key = (title.casefold(), image)
                if not title or not image_list or cost <= 0 or key in vistos_categoria:
                    continue
                vistos_categoria.add(key)
                product.update(
                    {
                        "nome": title,
                        "custo": cost,
                        "imagens": image_list,
                        "imagem": image,
                        "imagem_url": image,
                        "peso": peso_kg_para_titulo(title),
                        "categoria": "Automotivo",
                    }
                )
                product["estoque"] = 50
                product["descricao"] = title
                product["origem"] = "AliExpress"
                calcular_preco(product)
                por_categoria[category].append(product)

    encontrados = []
    vistos = set()
    usados_sku = set()
    max_por_categoria = max((len(items) for items in por_categoria.values()), default=0)
    for position in range(max_por_categoria):
        for category in ALIEXPRESS_CATEGORIAS:
            items = por_categoria.get(category, [])
            if position >= len(items):
                continue
            product = items[position]
            key = (product["nome"].casefold(), product["imagem"])
            if key in vistos:
                continue
            vistos.add(key)
            product["sku"] = novo_sku(usados_sku)
            encontrados.append(product)
            if len(encontrados) >= qtd:
                return encontrados

    if encontrados:
        return encontrados[:qtd]

    logger.warning("Nenhum produto AliExpress foi lido; usando o catálogo local existente.")
    fallback = []
    skus = set()
    for original in PRODUCTS[:qtd]:
        product = dict(original)
        product["fornecedores"] = dict(original.get("fornecedores", {}))
        product["imagem"] = normalizar_url_imagem(original.get("imagem_url"))
        product["imagens"] = product["imagem"]
        product["imagem_url"] = product["imagem"]
        product["sku"] = novo_sku(skus)
        product["estoque"] = 50
        product["peso"] = peso_kg_para_titulo(product["nome"])
        product["descricao"] = product["nome"]
        product["categoria"] = "Automotivo"
        product["origem"] = "Catálogo local existente"
        calcular_preco(product)
        fallback.append(product)
    return fallback


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
  <title>Login | SCAAN AUTO PEÇAS</title>
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
    <div class="eyebrow">SCAAN AUTO PEÇAS</div>
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
  <title>SCAAN AUTO PEÇAS - Bot Garimpo Nova Iguaçu - Nuvemshop + Shopee</title>
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
    .toolbar { display: flex; flex-wrap: wrap; align-items: center; gap: 10px; margin: 20px 0; }
    .toolbar form { margin: 0; }
    .action { display: inline-block; padding: 12px 16px; border: 0; border-radius: 10px;
      color: #062112; background: #4ade80; font-weight: bold; cursor: pointer; }
    .action:hover { color: #062112; background: #86efac; }
    .secondary { padding: 11px 14px; border: 1px solid #315347; border-radius: 10px;
      color: #d1fae5; background: #10231e; font-weight: bold; cursor: pointer; }
    .flash { margin: 12px 0; padding: 12px 14px; border: 1px solid #345342;
      border-radius: 10px; color: #a7f3d0; background: #0c2119; }
    .history { margin: 20px 0; padding: 18px; border: 1px solid #1e3a32;
      border-radius: 14px; background: #0b1714; }
    .history h2 { margin: 0 0 12px; font-size: 18px; }
    .history ul { margin: 0; padding-left: 20px; }
    .history li { margin: 8px 0; color: #9ca3af; }
    .history-empty { color: #9ca3af; }
    .table-box { overflow-x: auto; border: 1px solid #1e3a32; border-radius: 14px; background: #0b1714; }
    table { width: 100%; min-width: 860px; border-collapse: collapse; }
    th, td { padding: 14px 13px; border-bottom: 1px solid #1a2b25; text-align: left; vertical-align: top; }
    th { color: #9ca3af; background: #10231e; font-size: 11px; letter-spacing: .08em; text-transform: uppercase; }
    tr:last-child td { border-bottom: 0; }
    .supplier { display: block; margin: 0 0 5px; color: #aebcb6; white-space: nowrap; }
    .winner { color: #4ade80; font-weight: bold; }
    .profit { color: #86efac; font-weight: bold; }
    .product-photo { display: block; width: 50px; height: 50px; object-fit: contain;
      border: 1px solid #315347; border-radius: 9px; background: #fff; }
    .select-count { color: #a7f3d0; font-weight: bold; }
    .status { display: inline-block; max-width: 220px; padding: 7px 9px; border: 1px solid #6b5428;
      border-radius: 8px; color: #fcd34d; background: #2b2110; font-size: 11px; line-height: 1.4; }
    .foot { margin-top: 14px; color: #788780; font-size: 12px; }
    @media (max-width: 680px) { .summary { grid-template-columns: 1fr; } .top { align-items: flex-start; } }
  </style>
</head>
<body>
<header><div class="wrap top">
  <div><div class="brand">Scaan Auto Peças</div><h1>SCAAN AUTO PEÇAS - Bot Garimpo Nova Iguaçu - Nuvemshop + Shopee</h1></div>
  <a class="logout" href="{{ url_for('logout') }}">Sair</a>
</div></header>
<main class="wrap">
  <div class="notice">Origem do catálogo: {{ origem_garimpo }}. Preços não lidos do AliExpress usam o valor de reserva R$ 29,90; confirme custo e frete antes de publicar.</div>
  {% with messages = get_flashed_messages() %}{% for message in messages %}<div class="flash">{{ message }}</div>{% endfor %}{% endwith %}
  <section class="summary">
    <div class="metric"><span>Produtos em análise</span><strong>{{ produtos|length }}</strong></div>
    <div class="metric"><span>Lucro médio sobre o custo</span><strong>{{ lucro_medio|brl }}</strong></div>
    <div class="metric"><span>Categorias pesquisadas</span><strong>{{ categorias_buscadas }}</strong></div>
  </section>
  <div class="toolbar">
    <form method="post" action="{{ url_for('rodar_agora') }}"><button class="action" type="submit">Rodar Garimpo de Hoje Agora</button></form>
    <button class="secondary" id="top10" type="button">Selecionar Top 10 Maior Lucro</button>
    <span class="select-count"><span id="selected-count">0</span> produtos prontos pra vender hoje</span>
  </div>
  <section class="history">
    <h2>HISTORICO DIARIO</h2>
    {% if arquivos_csv %}<ul>{% for arquivo in arquivos_csv %}<li>{{ arquivo.data }} — <a href="{{ url_for('baixar_csv_arquivo', filename=arquivo.nome) }}">{{ arquivo.nome }}</a></li>{% endfor %}</ul>
    {% else %}<p class="history-empty">Nenhum CSV foi gerado ainda.</p>{% endif %}
  </section>
  <form method="post" action="{{ url_for('exportar_plataforma', plataforma='nuvemshop') }}" id="form-selecionados">
  <div class="table-box"><table>
    <thead><tr><th>Selecionar</th><th>Foto</th><th>Nome Scaan</th><th>Custo R$</th><th>Venda R$</th><th>Peso kg</th><th>SKU SCAAN-</th><th>Link Ali</th></tr></thead>
    <tbody>
    {% for produto in produtos %}
      <tr data-profit="{{ produto.lucro }}">
        <td><input type="checkbox" class="product-check" name="skus" value="{{ produto.sku }}" aria-label="Selecionar {{ produto.nome }}"></td>
        <td>{% if produto.imagem %}<img class="product-photo" src="{{ produto.imagem }}" alt="{{ produto.nome }}" loading="lazy">{% endif %}</td>
        <td><strong>{{ produto.titulo_venda }}</strong></td>
        <td>{{ produto.custo|brl }}{% if produto.custo_estimado %}<br><small>Estimado</small>{% endif %}</td>
        <td class="profit">{{ produto.venda|brl }}</td>
        <td>{{ "%.2f"|format(produto.peso) }}</td>
        <td>{{ produto.sku }}</td>
        <td><a href="{{ produto.link_aliexpress }}" target="_blank" rel="noopener">Abrir AliExpress</a></td>
      </tr>
    {% endfor %}
    </tbody>
  </table></div>
  <div class="toolbar">
    <button class="action" type="submit">BAIXAR CSV NUVEMSHOP - SCAAN</button>
    <button class="action" type="submit" formaction="{{ url_for('exportar_plataforma', plataforma='shopee') }}">BAIXAR CSV SHOPEE - SCAAN</button>
  </div>
  </form>
  <section class="history">
    <h2>CHECKLIST GRÁTIS LOJA CONFIÁVEL</h2>
    <label><input type="checkbox"> 1. Nuvemshop &gt; Configurações &gt; Endereço Nova Iguaçu</label><br><br>
    <label><input type="checkbox"> 2. Layout &gt; Rodapé &gt; WhatsApp oficial</label><br><br>
    <label><input type="checkbox"> 3. Config &gt; Frete &gt; Frete Grátis Nova Iguaçu acima de R$ 50 (se configurado)</label><br><br>
    <label><input type="checkbox"> 4. Produtos &gt; Avaliações &gt; Publique somente avaliações reais</label>
  </section>
  <p class="foot">Preço de venda = custo × 1,5. Nuvemshop: ponto e vírgula; Shopee: vírgula. Fotos separadas por |. Confirme preços, frete, estoque e informações da loja antes de publicar.</p>
</main>
<script>
  const checkboxes = Array.from(document.querySelectorAll('.product-check'));
  const counter = document.getElementById('selected-count');
  function updateCounter() { counter.textContent = checkboxes.filter((item) => item.checked).length; }
  checkboxes.forEach((item) => item.addEventListener('change', updateCounter));
  document.getElementById('top10').addEventListener('click', () => {
    const rows = Array.from(document.querySelectorAll('tbody tr'));
    rows.sort((a, b) => Number(b.dataset.profit) - Number(a.dataset.profit));
    checkboxes.forEach((item) => { item.checked = false; });
    rows.slice(0, 10).forEach((row) => { row.querySelector('.product-check').checked = true; });
    updateCounter();
  });
</script>
</body>
</html>
"""


def require_login():
    return bool(session.get("logged_in"))


def _descricao_html(product):
    title = escape(product["titulo_venda"])
    product_name = escape(product["nome"])
    sku = escape(product["sku"])
    weight = f'{product["peso"]:.2f}'
    return (
        f"<h2>{title}</h2>"
        "<p>📍 <b>SCAAN AUTO PEÇAS - NOVA IGUAÇU - RJ</b> | Atendimento pelo chat da plataforma</p>"
        "<p>🚚 Consulte o custo e o prazo de entrega informando seu CEP no checkout.</p>"
        "<hr><h3>Informações do produto</h3>"
        f"<p><b>PRODUTO:</b> {product_name}. Confira compatibilidade, medidas e aplicação antes da compra.</p>"
        f"<p><b>CONTEÚDO:</b> 1x {product_name} | PESO: {weight} kg | SKU: {sku}</p>"
        "<p>Garantia, nota fiscal e rastreamento seguem as condições informadas pela loja e pela plataforma.</p>"
    )


def _descricao_texto(product):
    return (
        f'🛠️ {product["titulo_venda"]}\n'
        "📍 SCAAN AUTO PEÇAS - NOVA IGUAÇU - RJ\n"
        "💬 Atendimento pelo chat da plataforma\n"
        "🚚 Consulte custo e prazo pelo CEP no checkout\n\n"
        "✅ Confira compatibilidade, medidas e aplicação antes da compra.\n"
        f'📦 CONTEÚDO: 1x {product["nome"]}\n'
        f'⚖️ PESO: {product["peso"]:.2f} kg\n'
        f'🏷️ SKU: {product["sku"]}\n'
        "ℹ️ Garantia, nota fiscal e rastreamento conforme as condições da loja e da plataforma."
    )


def _normalizar_produto(product):
    item = dict(product)
    item["nome"] = traduzir_titulo(item.get("nome") or "Produto automotivo")
    item["imagens"] = normalizar_imagens(item.get("imagens") or item.get("imagem") or item.get("imagem_url"))
    image_list = imagens_do_produto(item)
    if not image_list:
        logger.warning("Produto sem URL de imagem: %s", item["nome"])
    item["imagem"] = image_list[0] if image_list else ""
    item["imagem_url"] = item["imagem"]
    item["categoria"] = "Automotivo"
    if not re.fullmatch(r"SCAAN-\d{4}", str(item.get("sku", ""))):
        item["sku"] = novo_sku()
    item["peso"] = peso_kg_para_titulo(item["nome"])
    item.setdefault("estoque", 50)
    try:
        item["custo"] = float(item.get("custo"))
    except (TypeError, ValueError):
        item["custo"] = PRECO_RESERVA_BRL
        item["custo_estimado"] = True
    calcular_preco(item)
    item["lucro"] = round(item["venda"] - item["custo"], 2)
    item["titulo_venda"] = f'{item["nome"]} Premium - Scaan Auto Peças Nova Iguaçu'
    product_url = str(item.get("url_produto") or "").strip()
    product_url = urljoin(ALIEXPRESS_SEARCH_URL, product_url) if product_url else ""
    if product_url.startswith("http://"):
        product_url = "https://" + product_url[len("http://"):]
    if not product_url.startswith("https://"):
        product_url = f"{ALIEXPRESS_SEARCH_URL}?SearchText={quote_plus(item['nome'])}"
    item["link_aliexpress"] = product_url
    return item


def _salvar_produtos_atuais(produtos):
    os.makedirs(EXPORT_DIR, exist_ok=True)
    temporary_path = LATEST_PRODUCTS_FILE + ".tmp"
    with open(temporary_path, "w", encoding="utf-8") as current_file:
        json.dump(produtos, current_file, ensure_ascii=False)
    os.replace(temporary_path, LATEST_PRODUCTS_FILE)


def _carregar_produtos_atuais():
    try:
        with open(LATEST_PRODUCTS_FILE, "r", encoding="utf-8") as current_file:
            products = json.load(current_file)
        if isinstance(products, list):
            normalized = [_normalizar_produto(product) for product in products]
            source = "Catálogo local de reserva" if any(
                product.get("origem") == "Catálogo local existente" for product in normalized
            ) else "AliExpress"
            return normalized, source
    except (OSError, json.JSONDecodeError, TypeError):
        pass
    products = []
    used_skus = set()
    for product in PRODUCTS:
        item = dict(product)
        item["sku"] = novo_sku(used_skus)
        item = _normalizar_produto(item)
        item["origem"] = "Catálogo local existente"
        products.append(item)
    _salvar_produtos_atuais(products)
    return products, "Catálogo local de reserva"


def gerar_csv_completo(produtos, plataforma):
    plataforma = str(plataforma).strip().lower()
    if plataforma == "nuvemshop":
        delimiter = ";"
        headers = [
            "Nome",
            "Preço",
            "SKU",
            "Estoque",
            "Peso (kg)",
            "Altura (cm)",
            "Largura (cm)",
            "Profundidade (cm)",
            "Imagens",
            "Descrição",
            "Categoria",
            "Marca",
        ]
    elif plataforma == "shopee":
        delimiter = ","
        headers = ["Nome", "Preço", "Estoque", "SKU", "Peso(g)", "Descrição", "Imagens", "Categoria"]
    else:
        raise ValueError("Plataforma inválida. Use 'nuvemshop' ou 'shopee'.")

    output = StringIO(newline="")
    writer = csv.writer(output, delimiter=delimiter, lineterminator="\r\n")
    writer.writerow(headers)
    for original in produtos:
        product = _normalizar_produto(original)
        nome = product["titulo_venda"]
        preco = f'{round(float(product["custo"]) * 1.5, 2):.2f}'
        images = normalizar_imagens(product.get("imagens"))
        if plataforma == "nuvemshop":
            writer.writerow(
                [
                    nome,
                    preco,
                    product["sku"],
                    100,
                    f'{product["peso"]:.2f}',
                    30,
                    30,
                    15,
                    images,
                    _descricao_html(product),
                    "Automotivo",
                    "Scaan Auto Peças",
                ]
            )
        else:
            writer.writerow(
                [
                    nome,
                    preco,
                    100,
                    product["sku"],
                    round(product["peso"] * 1000),
                    _descricao_texto(product),
                    images,
                    "Automotivo",
                ]
            )
    return output.getvalue()


def salvar_csv(filename, produtos=None, atualizar_catalogo=True):
    os.makedirs(EXPORT_DIR, exist_ok=True)
    safe_filename = os.path.basename(filename)
    if not safe_filename.lower().endswith(".csv"):
        safe_filename += ".csv"
    if produtos is None:
        produtos, _ = _carregar_produtos_atuais()
    normalized = [_normalizar_produto(product) for product in produtos]
    content = gerar_csv_completo(normalized, "nuvemshop")
    path = os.path.join(EXPORT_DIR, safe_filename)
    with open(path, "w", encoding="utf-8-sig", newline="") as csv_file:
        csv_file.write(content)
    if atualizar_catalogo:
        _salvar_produtos_atuais(normalized)
    return path


def job_diario():
    produtos = buscar_produtos(100)
    for product in produtos:
        calcular_preco(product)
    day = date.today()
    nuvemshop_path = salvar_csv(f"scaan_nuvemshop_{day}.csv", produtos)
    salvar_csv(f"scaan_shopee_{day}.csv", produtos, atualizar_catalogo=False)
    return nuvemshop_path


def _historico_csv():
    if not os.path.isdir(EXPORT_DIR):
        return []
    entries = []
    for filename in os.listdir(EXPORT_DIR):
        if not filename.startswith("scaan_") or not filename.lower().endswith(".csv"):
            continue
        match = re.search(r"(\d{4}-\d{2}-\d{2})", filename)
        entries.append(
            {
                "nome": filename,
                "data": datetime.strptime(match.group(1), "%Y-%m-%d").strftime("%d/%m/%Y") if match else filename,
                "ordem": match.group(1) if match else "",
            }
        )
    return sorted(entries, key=lambda item: (item["ordem"], item["nome"]), reverse=True)


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

    products, source = _carregar_produtos_atuais()
    average_profit = sum(product["lucro"] for product in products) / len(products) if products else 0
    return render_template_string(
        ADMIN_HTML,
        produtos=products,
        lucro_medio=average_profit,
        arquivos_csv=_historico_csv(),
        origem_garimpo=source,
        categorias_buscadas=len(ALIEXPRESS_CATEGORIAS),
    )


@app.route("/rodar-agora", methods=["POST"])
def rodar_agora():
    if not require_login():
        return redirect(url_for("admin"))
    try:
        path = job_diario()
        products, source = _carregar_produtos_atuais()
        flash(f"Garimpo concluído: {len(products)} produtos ({source}). CSV salvo como {os.path.basename(path)}.")
    except Exception as error:
        logger.exception("Falha ao rodar garimpo manual.")
        flash(f"Não foi possível concluir o garimpo: {error}")
    return redirect(url_for("admin"))


@app.route("/exportar/<plataforma>", methods=["POST"])
@app.route("/gerar-csv-selecionados", methods=["POST"])
def exportar_plataforma(plataforma="nuvemshop"):
    if not require_login():
        return redirect(url_for("admin"))
    if plataforma not in ("nuvemshop", "shopee"):
        return "Plataforma inválida.", 404
    selected_skus = set(request.form.getlist("skus"))
    products, _ = _carregar_produtos_atuais()
    selected = [product for product in products if product.get("sku") in selected_skus]
    if not selected:
        flash("Marque pelo menos um produto para gerar o CSV.")
        return redirect(url_for("admin"))
    filename = f"scaan_{plataforma}_selecionados_{date.today()}_{datetime.now().strftime('%H%M%S')}.csv"
    csv_bytes = gerar_csv_completo(selected, plataforma).encode("utf-8-sig")
    os.makedirs(EXPORT_DIR, exist_ok=True)
    with open(os.path.join(EXPORT_DIR, filename), "wb") as csv_file:
        csv_file.write(csv_bytes)
    return send_file(
        BytesIO(csv_bytes),
        as_attachment=True,
        download_name=filename,
        mimetype="text/csv; charset=utf-8-sig",
    )


@app.route("/csvs/<path:filename>")
def baixar_csv_arquivo(filename):
    if not require_login():
        return redirect(url_for("admin"))
    return send_from_directory(EXPORT_DIR, filename, as_attachment=True, mimetype="text/csv; charset=utf-8")


@app.route("/download")
@app.route("/export-csv")
def download():
    if not require_login():
        return redirect(url_for("admin"))

    products, _ = _carregar_produtos_atuais()
    csv_bytes = gerar_csv_completo(products, "nuvemshop").encode("utf-8-sig")
    return send_file(
        BytesIO(csv_bytes),
        as_attachment=True,
        download_name="SCAAN_AUTO_PECAS_NUVEMSHOP.csv",
        mimetype="text/csv; charset=utf-8-sig",
    )


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("admin"))


scheduler = BackgroundScheduler(timezone="America/Sao_Paulo")
scheduler.add_job(job_diario, "cron", hour=9, minute=0, id="garimpo_diario", replace_existing=True)
scheduler.start()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "10000")))
