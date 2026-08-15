#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Gera o site estático do cardápio em dist/.

Lê os quatro JSONs de data/ e escreve HTML com os 645 itens já renderizados.
A navegação (drill-down, busca, filtros) é melhoria progressiva: sem
JavaScript a página continua sendo o cardápio inteiro, rolável.

    python3 scripts/build_site.py
"""
import json, re, shutil, unicodedata, pathlib, html, collections

RAIZ = pathlib.Path(__file__).resolve().parent.parent
DADOS = RAIZ / "data"
DIST = RAIZ / "dist"

SITE = "https://marcelojrfarias.github.io/festa-italiana/"
UTM = "?utm_source=whatsapp&utm_medium=share&utm_campaign=cardapio-33a"
LINKEDIN = "https://www.linkedin.com/in/marcelojrfarias/"

ICONES = {
    "massas": "🍝", "pizzas-e-fogazza": "🍕", "doces": "🍰", "lanches": "🥪",
    "petiscos-e-porcoes": "🧀", "carnes-e-polenta": "🍖", "outros-pratos": "🍽️",
    "bebidas-sem-alcool": "🥤", "bebidas-com-alcool": "🍺",
}
# Ordem de navegação: comida primeiro, bebida por último. A ordem do arquivo de
# categorias é por volume, o que jogaria bebida para o topo do índice.
ORDEM = ["massas", "pizzas-e-fogazza", "lanches", "carnes-e-polenta",
         "petiscos-e-porcoes", "doces", "bebidas-sem-alcool", "bebidas-com-alcool",
         "outros-pratos"]


def sem_acento(s):
    return "".join(c for c in unicodedata.normalize("NFD", s or "")
                   if unicodedata.category(c) != "Mn").lower()


def moeda(v):
    return f"R$ {v:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")


def e(s):
    return html.escape(str(s), quote=True)


def carregar():
    ler = lambda n: json.loads((DADOS / n).read_text(encoding="utf-8"))
    return ler("cardapio.json"), ler("categorias-site.json"), ler("evento.json")


def agrupar_pratos(cardapio, categorias):
    """Um prato = um título. 645 itens viram ~365 pratos com faixa de preço.

    O mesmo prato aparece em até 10 barracas com preços diferentes; agrupar
    responde "onde tem tiramisù e por quanto" sem obrigar a varrer a lista.
    """
    atrib = categorias["atribuicoes"]
    grupos = {}
    for barraca in cardapio["barracas"]:
        for item in barraca["itens"]:
            chave = sem_acento(item["titulo"])
            g = grupos.setdefault(chave, {
                "titulo": item["titulo"], "cats": collections.Counter(),
                "ofertas": [], "descricoes": [],
            })
            g["cats"][atrib[item["id"]]] += 1
            g["ofertas"].append({
                "num": barraca["numero"], "nome": barraca["nome"],
                "preco": item["preco"], "descricao": item["descricao"],
            })
            g["descricoes"].append(item["descricao"])

    pratos = []
    for g in grupos.values():
        precos = [o["preco"] for o in g["ofertas"]]
        g["ofertas"].sort(key=lambda o: o["preco"])
        pratos.append({
            "titulo": g["titulo"],
            "categoria": g["cats"].most_common(1)[0][0],
            "ofertas": g["ofertas"],
            "min": min(precos), "max": max(precos),
            "descricao": collections.Counter(g["descricoes"]).most_common(1)[0][0],
            # sorted(): a ordem de iteração de um set de strings muda entre
            # processos (PYTHONHASHSEED), e sem isso o build não é reprodutível
            "busca": sem_acento(g["titulo"] + " " + " ".join(sorted(set(g["descricoes"])))),
        })
    pratos.sort(key=lambda p: sem_acento(p["titulo"]))
    return pratos


def faixa_preco(p):
    return moeda(p["min"]) if p["min"] == p["max"] else f"{moeda(p['min'])} a {moeda(p['max'])}"


def bucket_preco(v):
    return "ate10" if v <= 10 else "11a20" if v <= 20 else "21a30" if v <= 30 else "31mais"


def render_prato(p):
    nums = " ".join(sem_acento(o["num"]).replace("/", " ") for o in p["ofertas"])
    buckets = " ".join(sorted({bucket_preco(o["preco"]) for o in p["ofertas"]}))
    ofertas = "".join(
        f'<li class="oferta" data-barraca="{e(sem_acento(o["num"]))}">'
        f'<span class="oferta__num">{e(o["num"])}</span>'
        f'<span class="oferta__nome">{e(o["nome"])}</span>'
        f'<span class="oferta__preco">{e(moeda(o["preco"]))}</span></li>'
        for o in p["ofertas"])
    n = len(p["ofertas"])
    toggle = (f'<button class="prato__toggle" type="button" aria-expanded="false">'
              f'em {n} barracas</button>') if n > 1 else ""
    return (
        f'<article class="prato" data-cat="{e(p["categoria"])}" '
        f'data-barracas=" {e(nums)} " data-precos=" {e(buckets)} " '
        f'data-busca="{e(p["busca"])}">'
        f'<div class="prato__topo"><h3 class="prato__titulo">{e(p["titulo"])}</h3>'
        f'<span class="prato__faixa">{e(faixa_preco(p))}</span></div>'
        f'<p class="prato__desc">{e(p["descricao"])}</p>'
        f'{toggle}<ul class="ofertas">{ofertas}</ul></article>')


def render_indices(cardapio, categorias, pratos):
    por_cat = collections.Counter(p["categoria"] for p in pratos)
    nomes = {c["id"]: c["nome"] for c in categorias["categorias"]}
    cards_cat = "".join(
        f'<a class="card" href="?cat={e(cid)}" data-cat="{e(cid)}">'
        f'<span class="card__icone" aria-hidden="true">{ICONES[cid]}</span>'
        f'<span class="card__nome">{e(nomes[cid])}</span>'
        f'<span class="card__contagem">{por_cat[cid]}</span>'
        f'<span class="card__chevron" aria-hidden="true">›</span></a>'
        for cid in ORDEM if por_cat[cid])

    cards_bar = "".join(
        f'<a class="card" href="?barraca={e(sem_acento(b["numero"]))}" '
        f'data-barraca="{e(sem_acento(b["numero"]))}">'
        f'<span class="card__numero">{e(b["numero"])}</span>'
        f'<span class="card__nome">{e(b["nome"])}</span>'
        f'<span class="card__contagem">{b["total_itens"]}</span>'
        f'<span class="card__chevron" aria-hidden="true">›</span></a>'
        for b in sorted(cardapio["barracas"], key=lambda x: x["numeros"][0]))
    return cards_cat, cards_bar


def render_html(cardapio, categorias, evento, pratos):
    cards_cat, cards_bar = render_indices(cardapio, categorias, pratos)
    lista = "".join(render_prato(p) for p in pratos)
    ev = evento["local"]
    endereco = f'{ev["endereco"]} — {ev["bairro"]}, {ev["cidade"]}/{ev["uf"]}'
    mapa = "https://www.google.com/maps/search/?api=1&query=" + \
           re.sub(r"\s+", "+", f'{ev["endereco"]} {ev["bairro"]} {ev["cidade"]}')

    msg = ("Achei um cardápio digital da Festa Italiana de SCS — dá pra procurar "
           "prato e ver preço de todas as barracas. Tá me ajudando a decidir o que "
           "comer: " + SITE + UTM)
    from urllib.parse import quote
    wa = "https://wa.me/?text=" + quote(msg, safe="")

    dados_js = json.dumps({"dias": evento["dias"], "horarios": evento["horarios"]},
                          ensure_ascii=False)
    total = sum(len(p["ofertas"]) for p in pratos)

    return f"""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Cardápio da 33ª Festa Italiana — São Caetano do Sul</title>
<meta name="description" content="Cardápio completo da 33ª Festa Italiana de São Caetano do Sul: {total} itens de {len(cardapio['barracas'])} barracas, com preço e busca por prato.">
<meta name="theme-color" content="#196B24">
<meta property="og:title" content="Cardápio da 33ª Festa Italiana">
<meta property="og:description" content="{total} pratos e bebidas de {len(cardapio['barracas'])} barracas, com preço. Procure o que quer comer.">
<meta property="og:type" content="website">
<meta property="og:url" content="{e(SITE)}">
<link rel="stylesheet" href="style.css">
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'><text y='26' font-size='26'>🍝</text></svg>">
</head>
<body data-modo="categoria">

<header class="marca">
  <div class="marca__linha">
    <img class="marca__logo" src="assets/logo.webp" width="742" height="386"
         alt="33ª Festa Italiana de São Caetano do Sul">
    <a class="botao-share botao-share--icone" href="{e(wa)}" target="_blank" rel="noopener"
       aria-label="Compartilhar no WhatsApp">
      <svg viewBox="0 0 24 24" width="22" height="22" aria-hidden="true"><path fill="currentColor"
        d="M18 16.1c-.8 0-1.6-.2-2.3-.5l-.4-.2-3.1.8.8-3-.2-.4A6 6 0 1 1 18 16.1M12 2a10 10 0 0 0-8.6 15L2 22l5.1-1.3A10 10 0 1 0 12 2"/></svg>
    </a>
  </div>
  <p class="status" id="status" data-evento='{dados_js}'>33ª Festa Italiana · São Caetano do Sul</p>
</header>

<div class="ferramentas">
  <form class="busca" role="search" onsubmit="return false">
    <label class="sr" for="q">Buscar prato</label>
    <input id="q" type="search" placeholder="buscar prato, ex: tiramisù" autocomplete="off">
  </form>
  <nav class="modos" aria-label="Modo de visualização">
    <button type="button" data-modo="categoria" aria-pressed="true">Categorias</button>
    <button type="button" data-modo="barraca" aria-pressed="false">Barracas</button>
    <button type="button" data-modo="tudo" aria-pressed="false">Tudo</button>
  </nav>
</div>

<main>
  <div class="trilha" id="trilha" hidden>
    <button class="voltar" type="button">‹ voltar</button>
    <h2 class="trilha__titulo" id="trilha-titulo"></h2>
  </div>

  <section class="indice" id="idx-categoria" aria-label="Categorias">{cards_cat}</section>
  <section class="indice" id="idx-barraca" aria-label="Barracas" hidden>{cards_bar}</section>

  <div class="filtros" id="filtros" hidden>
    <button type="button" data-preco="ate10">até R$ 10</button>
    <button type="button" data-preco="11a20">R$ 11–20</button>
    <button type="button" data-preco="21a30">R$ 21–30</button>
    <button type="button" data-preco="31mais">R$ 31+</button>
  </div>

  <p class="contador" id="contador" hidden></p>
  <section class="lista" id="lista" aria-label="Pratos">{lista}</section>
  <p class="vazio" id="vazio" hidden>Nenhum prato encontrado.<br>
    <button type="button" class="limpar">limpar filtros</button></p>

  <aside class="convite">
    <p class="convite__titulo">Manda pro grupo da família 🖤</p>
    <p class="convite__texto">Alguém aí ainda está decidindo o que comer.</p>
    <a class="botao-share" href="{e(wa)}" target="_blank" rel="noopener">
      Compartilhar no WhatsApp</a>
  </aside>
</main>

<footer class="rodape">
  <p class="rodape__local"><a href="{e(mapa)}" target="_blank" rel="noopener">{e(endereco)}</a></p>
  <p class="rodape__credito">Desenvolvido com 🖤 por
    <a href="{e(LINKEDIN)}" target="_blank" rel="noopener">Marcelo Farias</a></p>
  <p class="rodape__aviso">Projeto voluntário e independente, sem vínculo com a Prefeitura
    de São Caetano do Sul ou com a organização da Festa Italiana. Cardápio e programação
    extraídos do material oficial; preços e atrações podem mudar.</p>
</footer>

<script src="app.js"></script>
</body>
</html>
"""


CSS = """/* Paleta e escala vêm de data/identidade-visual.json, medidas do PDF oficial. */
:root {
  --verde: #196B24; --verde-logo: #0F7645; --verde-escuro: #095A34;
  --vermelho: #EE0000; --vermelho-logo: #BB2121;
  --bege: #E5B67E; --cartao: #FFFFFF; --texto: #1A1A1A; --suave: #5C5245;
  --borda: #E3D5C2; --raio: 14px;
  --display: Georgia, "Times New Roman", serif;
  --corpo: system-ui, -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  color-scheme: light;
}
* { box-sizing: border-box; }
/* display: grid/flex nos containers sobrepõe o [hidden] do HTML; sem isto o
   índice e a lista aparecem juntos. */
[hidden] { display: none !important; }
body {
  margin: 0; background: var(--bege); color: var(--texto);
  font-family: var(--corpo); font-size: 16px; line-height: 1.45;
  -webkit-text-size-adjust: 100%;
}
.sr { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); }
a { color: var(--verde); }

/* ---- faixa de marca: rola embora ---- */
.marca { padding: 14px 16px 10px; }
.marca__linha { display: flex; align-items: center; gap: 12px; }
.marca__logo { width: auto; height: 56px; max-width: 70%; }
.marca__linha .botao-share--icone { margin-left: auto; }
.status {
  margin: 8px 0 0; font-size: 14px; font-weight: 600; color: var(--verde-escuro);
}
.status[data-aberta="1"]::before {
  content: ""; display: inline-block; width: 8px; height: 8px; margin-right: 7px;
  border-radius: 50%; background: var(--verde); vertical-align: 1px;
}

/* ---- faixa de ferramenta: gruda no topo ---- */
.ferramentas {
  position: sticky; top: 0; z-index: 10; background: var(--bege);
  padding: 8px 16px 10px; box-shadow: 0 6px 12px -8px rgba(0,0,0,.35);
}
.busca input {
  width: 100%; padding: 11px 14px; font: inherit; font-size: 16px;
  border: 1px solid var(--borda); border-radius: 999px; background: var(--cartao);
}
.busca input:focus-visible { outline: 3px solid var(--verde); outline-offset: 1px; }
.modos { display: flex; gap: 6px; margin-top: 8px; }
.modos button {
  flex: 1; padding: 8px 4px; font: inherit; font-size: 13px; font-weight: 600;
  border: 1px solid var(--borda); border-radius: 999px;
  background: var(--cartao); color: var(--suave); cursor: pointer;
}
.modos button[aria-pressed="true"] {
  background: var(--verde); border-color: var(--verde); color: #fff;
}

main { padding: 12px 16px 0; }

/* ---- trilha ---- */
.trilha { display: flex; align-items: center; gap: 10px; margin-bottom: 10px; }
.voltar {
  padding: 7px 12px; font: inherit; font-size: 14px; font-weight: 600;
  border: 1px solid var(--borda); border-radius: 999px;
  background: var(--cartao); color: var(--verde); cursor: pointer;
}
.trilha__titulo { margin: 0; font-family: var(--display); font-size: 20px; color: var(--verde); }

/* ---- índices (cards de categoria e barraca) ---- */
.indice { display: grid; gap: 8px; }
.card {
  display: grid; grid-template-columns: 44px 1fr auto 16px; align-items: center;
  gap: 10px; padding: 12px 14px; background: var(--cartao); border-radius: var(--raio);
  text-decoration: none; color: var(--texto); box-shadow: 0 1px 2px rgba(0,0,0,.1);
}
.card__icone { font-size: 26px; text-align: center; }
.card__numero {
  display: grid; place-items: center; width: 38px; height: 38px; border-radius: 50%;
  background: var(--verde); color: #fff; font-weight: 700; font-size: 14px;
}
.card__nome { font-weight: 600; line-height: 1.25; }
.card__contagem { color: var(--suave); font-size: 13px; font-variant-numeric: tabular-nums; }
.card__chevron { color: var(--vermelho-logo); font-size: 22px; line-height: 1; }

/* ---- filtros de preço ---- */
.filtros { display: flex; gap: 6px; overflow-x: auto; padding-bottom: 10px; }
.filtros button {
  flex: 0 0 auto; padding: 7px 13px; font: inherit; font-size: 13px; font-weight: 600;
  border: 1px solid var(--borda); border-radius: 999px;
  background: var(--cartao); color: var(--suave); cursor: pointer;
}
.filtros button[aria-pressed="true"] {
  background: var(--vermelho-logo); border-color: var(--vermelho-logo); color: #fff;
}
.contador { margin: 0 0 10px; font-size: 13px; color: var(--suave); }

/* ---- lista de pratos ---- */
.lista { display: grid; gap: 8px; }
.prato {
  padding: 12px 14px; background: var(--cartao); border-radius: var(--raio);
  box-shadow: 0 1px 2px rgba(0,0,0,.1);
}
.prato__topo { display: flex; align-items: baseline; gap: 10px; }
.prato__titulo {
  margin: 0; flex: 1; font-size: 16px; font-weight: 700; color: var(--verde);
  line-height: 1.25;
}
.prato__faixa {
  font-weight: 700; color: var(--verde); white-space: nowrap;
  font-variant-numeric: tabular-nums;
}
.prato__desc { margin: 4px 0 0; font-size: 14px; color: var(--texto); }
.prato__toggle {
  margin-top: 8px; padding: 5px 11px; font: inherit; font-size: 13px; font-weight: 600;
  border: 1px solid var(--borda); border-radius: 999px;
  background: transparent; color: var(--suave); cursor: pointer;
}
.ofertas { display: none; margin: 8px 0 0; padding: 0; list-style: none; }
.prato__toggle[aria-expanded="true"] + .ofertas { display: block; }
.oferta {
  display: grid; grid-template-columns: 30px 1fr auto; align-items: center; gap: 8px;
  padding: 6px 0; border-top: 1px solid var(--borda); font-size: 14px;
}
.oferta__num {
  display: grid; place-items: center; height: 22px; border-radius: 999px;
  background: var(--bege); color: var(--verde-escuro); font-size: 11px; font-weight: 700;
}
.oferta__nome { color: var(--suave); line-height: 1.2; }
.oferta__preco { font-weight: 700; font-variant-numeric: tabular-nums; }

/* Dentro de uma barraca o preço daquela barraca vai para o topo (o JS
   reescreve .prato__faixa); repetir o nome da barraca em cada prato seria
   redundante com a trilha. */
body[data-barraca-ativa] .lista .prato__toggle,
body[data-barraca-ativa] .lista .ofertas { display: none !important; }

.vazio { padding: 24px 0; text-align: center; color: var(--suave); }
.limpar {
  margin-top: 10px; padding: 8px 16px; font: inherit; font-weight: 600;
  border: 0; border-radius: 999px; background: var(--verde); color: #fff; cursor: pointer;
}

/* ---- convite para compartilhar ---- */
.convite {
  margin: 18px 0 0; padding: 16px; border-radius: var(--raio);
  background: var(--verde); color: #fff; text-align: center;
}
.convite__titulo { margin: 0; font-family: var(--display); font-size: 19px; }
.convite__texto { margin: 4px 0 12px; font-size: 14px; opacity: .9; }
.botao-share {
  display: inline-flex; align-items: center; justify-content: center; gap: 8px;
  padding: 11px 20px; border-radius: 999px; background: #fff; color: var(--verde);
  font-weight: 700; text-decoration: none;
}
.botao-share--icone {
  width: 42px; height: 42px; padding: 0; flex: 0 0 auto;
  background: var(--verde); color: #fff;
}

/* ---- rodapé ---- */
.rodape { margin-top: 22px; padding: 18px 16px 28px; text-align: center; font-size: 13px; }
.rodape__local { margin: 0 0 10px; font-weight: 600; }
.rodape__credito { margin: 0 0 12px; }
.rodape__aviso { margin: 0; color: var(--suave); font-size: 12px; line-height: 1.5; }

/* sem JS o índice não navega, então a lista completa fica visível */
.js .lista, .js .filtros, .js .contador { }

@media (min-width: 768px) {
  .marca, .ferramentas, main, .rodape { max-width: 760px; margin-inline: auto; }
  .ferramentas { border-radius: 0 0 var(--raio) var(--raio); }
  .marca__logo { height: 76px; }
  .indice { grid-template-columns: 1fr 1fr; }
  .prato__titulo { font-size: 17px; }
}
"""


JS = r"""(function () {
  'use strict';
  document.documentElement.classList.add('js');

  var body = document.body,
      lista = document.getElementById('lista'),
      pratos = Array.prototype.slice.call(lista.children),
      idx = { categoria: document.getElementById('idx-categoria'),
              barraca: document.getElementById('idx-barraca') },
      trilha = document.getElementById('trilha'),
      trilhaTitulo = document.getElementById('trilha-titulo'),
      filtros = document.getElementById('filtros'),
      contador = document.getElementById('contador'),
      vazio = document.getElementById('vazio'),
      convite = document.querySelector('.convite'),
      busca = document.getElementById('q');

  var nomes = {}, totais = {};
  document.querySelectorAll('#idx-categoria .card').forEach(function (c) {
    nomes['cat:' + c.dataset.cat] = c.querySelector('.card__nome').textContent;
  });
  document.querySelectorAll('#idx-barraca .card').forEach(function (c) {
    nomes['barraca:' + c.dataset.barraca] =
      c.querySelector('.card__numero').textContent + ' · ' +
      c.querySelector('.card__nome').textContent;
  });

  var estado = { modo: 'categoria', cat: '', barraca: '', q: '', preco: '' };

  // faixa original ("R$ 20,00 a R$ 30,00") para restaurar ao sair da barraca
  var faixaOriginal = new Map();
  pratos.forEach(function (el) {
    faixaOriginal.set(el, el.querySelector('.prato__faixa').textContent);
  });

  function semAcento(s) {
    return s.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
  }

  function lerURL() {
    var p = new URLSearchParams(location.search);
    estado.modo = p.get('modo') || (p.get('barraca') ? 'barraca' : p.get('cat') ? 'categoria' : 'categoria');
    estado.cat = p.get('cat') || '';
    estado.barraca = p.get('barraca') || '';
    estado.q = p.get('q') || '';
    estado.preco = p.get('preco') || '';
    if (p.get('modo') === 'tudo') estado.modo = 'tudo';
  }

  function montarURL() {
    var p = new URLSearchParams();
    if (estado.modo !== 'categoria') p.set('modo', estado.modo);
    if (estado.cat) p.set('cat', estado.cat);
    if (estado.barraca) p.set('barraca', estado.barraca);
    if (estado.q) p.set('q', estado.q);
    if (estado.preco) p.set('preco', estado.preco);
    var s = p.toString();
    return s ? '?' + s : location.pathname;
  }

  /* Mostrar a lista, e não o índice, quando há busca, filtro de preço, ou
     quando a pessoa entrou numa categoria/barraca. */
  function emLista() {
    return !!(estado.q || estado.preco || estado.cat || estado.barraca || estado.modo === 'tudo');
  }

  function aplicar() {
    var q = semAcento(estado.q.trim()), visiveis = 0;

    pratos.forEach(function (el) {
      var ok = true;
      if (estado.cat && el.dataset.cat !== estado.cat) ok = false;
      if (ok && estado.barraca &&
          el.dataset.barracas.indexOf(' ' + estado.barraca + ' ') === -1) ok = false;
      if (ok && estado.preco &&
          el.dataset.precos.indexOf(' ' + estado.preco + ' ') === -1) ok = false;
      if (ok && q && el.dataset.busca.indexOf(q) === -1) ok = false;
      el.hidden = !ok;
      if (ok) visiveis++;
    });

    // dentro de uma barraca, o topo mostra o preço praticado ali
    pratos.forEach(function (el) {
      var faixa = el.querySelector('.prato__faixa');
      if (estado.barraca && !el.hidden) {
        var o = el.querySelector('.oferta[data-barraca="' + estado.barraca + '"]');
        faixa.textContent = o ? o.querySelector('.oferta__preco').textContent
                              : faixaOriginal.get(el);
      } else {
        faixa.textContent = faixaOriginal.get(el);
      }
    });
    if (estado.barraca) body.dataset.barracaAtiva = estado.barraca;
    else delete body.dataset.barracaAtiva;

    var listando = emLista();
    idx.categoria.hidden = listando || estado.modo !== 'categoria';
    idx.barraca.hidden = listando || estado.modo !== 'barraca';
    lista.hidden = !listando;
    filtros.hidden = !listando;
    contador.hidden = !listando;
    vazio.hidden = !listando || visiveis > 0;
    convite.hidden = false;

    contador.textContent = visiveis + (visiveis === 1 ? ' prato' : ' pratos');

    var rotulo = estado.cat ? nomes['cat:' + estado.cat]
               : estado.barraca ? nomes['barraca:' + estado.barraca] : '';
    trilha.hidden = !rotulo;
    trilhaTitulo.textContent = rotulo || '';

    body.dataset.modo = estado.modo;
    document.querySelectorAll('.modos button').forEach(function (b) {
      b.setAttribute('aria-pressed', String(b.dataset.modo === estado.modo));
    });
    filtros.querySelectorAll('button').forEach(function (b) {
      b.setAttribute('aria-pressed', String(b.dataset.preco === estado.preco));
    });
    if (busca.value !== estado.q) busca.value = estado.q;
  }

  function navegar(push) {
    if (push !== false) history.pushState(estado, '', montarURL());
    aplicar();
  }

  /* voltar do sistema (Android) e do navegador devolvem ao nível anterior */
  window.addEventListener('popstate', function () { lerURL(); aplicar(); });

  document.querySelectorAll('.modos button').forEach(function (b) {
    b.addEventListener('click', function () {
      estado.modo = b.dataset.modo;
      estado.cat = estado.barraca = estado.preco = '';
      navegar();
      window.scrollTo(0, 0);
    });
  });

  document.addEventListener('click', function (ev) {
    var card = ev.target.closest('.indice .card');
    if (card) {
      ev.preventDefault();
      if (card.dataset.cat) { estado.cat = card.dataset.cat; estado.modo = 'categoria'; }
      else { estado.barraca = card.dataset.barraca; estado.modo = 'barraca'; }
      navegar();
      window.scrollTo(0, 0);
      return;
    }
    var t = ev.target.closest('.prato__toggle');
    if (t) {
      t.setAttribute('aria-expanded', t.getAttribute('aria-expanded') === 'true' ? 'false' : 'true');
      return;
    }
    var f = ev.target.closest('.filtros button');
    if (f) {
      estado.preco = estado.preco === f.dataset.preco ? '' : f.dataset.preco;
      navegar();
      return;
    }
    if (ev.target.closest('.voltar')) {
      history.back();
      return;
    }
    if (ev.target.closest('.limpar')) {
      estado.q = ''; estado.preco = '';
      navegar();
    }
  });

  var timer;
  busca.addEventListener('input', function () {
    clearTimeout(timer);
    timer = setTimeout(function () {
      estado.q = busca.value;
      history.replaceState(estado, '', montarURL());
      aplicar();
    }, 120);
  });

  /* ---- status: aberta agora / próxima abertura ---- */
  (function status() {
    var el = document.getElementById('status');
    var ev = JSON.parse(el.dataset.evento);
    var fmt = new Intl.DateTimeFormat('en-CA', {
      timeZone: 'America/Sao_Paulo', year: 'numeric', month: '2-digit', day: '2-digit',
      hour: '2-digit', minute: '2-digit', hour12: false
    });
    var p = {};
    fmt.formatToParts(new Date()).forEach(function (x) { p[x.type] = x.value; });
    var hoje = p.year + '-' + p.month + '-' + p.day;
    var agora = p.hour + ':' + p.minute;

    function hhmm(t) {
      var m = t.split(':');
      return m[1] === '00' ? m[0] + 'h' : m[0] + 'h' + m[1];
    }
    function janela(dia) {
      var d = new Date(dia + 'T12:00:00Z').getUTCDay(); // 0 dom .. 6 sab
      return ev.horarios[d === 0 ? 'domingo' : 'sabado'];
    }
    var DIAS = ['domingo', 'segunda', 'terça', 'quarta', 'quinta', 'sexta', 'sábado'];

    if (ev.dias.indexOf(hoje) !== -1) {
      var j = janela(hoje);
      if (agora >= j[0] && agora <= j[1]) {
        el.textContent = 'Aberta agora · até ' + hhmm(j[1]);
        el.dataset.aberta = '1';
        return;
      }
      if (agora < j[0]) {
        el.textContent = 'Abre hoje às ' + hhmm(j[0]);
        return;
      }
    }
    var prox = ev.dias.filter(function (d) { return d > hoje; })[0];
    if (!prox) { el.textContent = '33ª Festa Italiana · encerrada'; return; }
    var dt = new Date(prox + 'T12:00:00Z');
    el.textContent = 'Próxima: ' + DIAS[dt.getUTCDay()] + ' ' +
      prox.slice(8, 10) + '/' + prox.slice(5, 7) + ' às ' + hhmm(janela(prox)[0]);
  })();

  lerURL();
  history.replaceState(estado, '', montarURL());
  aplicar();
})();
"""


def otimizar_assets():
    from PIL import Image
    Image.init()
    destino = DIST / "assets"
    destino.mkdir(parents=True, exist_ok=True)
    origem = RAIZ / "assets" / "logo-festa-italiana.png"
    im = Image.open(origem).convert("RGBA")
    im.thumbnail((742, 742), Image.LANCZOS)
    saida = destino / "logo.webp"
    im.save(saida, "WEBP", quality=88, method=6)
    return origem.stat().st_size, saida.stat().st_size


def main():
    cardapio, categorias, evento = carregar()
    pratos = agrupar_pratos(cardapio, categorias)

    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir(parents=True)
    (DIST / "index.html").write_text(render_html(cardapio, categorias, evento, pratos),
                                     encoding="utf-8")
    (DIST / "style.css").write_text(CSS, encoding="utf-8")
    (DIST / "app.js").write_text(JS, encoding="utf-8")
    (DIST / ".nojekyll").write_text("", encoding="utf-8")
    antes, depois = otimizar_assets()

    itens = sum(len(p["ofertas"]) for p in pratos)
    kb = lambda p: p.stat().st_size / 1024
    print(f"{itens} itens em {len(pratos)} pratos, {len(cardapio['barracas'])} barracas")
    print(f"  index.html  {kb(DIST/'index.html'):7.1f} KB")
    print(f"  style.css   {kb(DIST/'style.css'):7.1f} KB")
    print(f"  app.js      {kb(DIST/'app.js'):7.1f} KB")
    print(f"  logo.webp   {depois/1024:7.1f} KB  (era {antes/1024:.1f} KB PNG)")


if __name__ == "__main__":
    main()
