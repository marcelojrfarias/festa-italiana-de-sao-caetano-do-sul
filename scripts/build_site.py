#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Gera o site estático do cardápio em dist/.

Lê os quatro JSONs de data/ e escreve HTML com os 645 itens já renderizados.
A navegação (drill-down, busca, filtros) é melhoria progressiva: sem
JavaScript a página continua sendo o cardápio inteiro, rolável.

    python3 scripts/build_site.py
"""
import hashlib
import json, re, shutil, unicodedata, pathlib, html, collections

RAIZ = pathlib.Path(__file__).resolve().parent.parent
DADOS = RAIZ / "data"
DIST = RAIZ / "dist"

# Endereço canônico do site. Precisa ser declarado, não inferido: o GitHub
# continua atendendo o caminho antigo depois de um rename, e derivar a URL de
# location.pathname faria cada visitante que entrou pelo endereço legado
# propagar esse endereço no compartilhamento.
SITE = "https://marcelojrfarias.github.io/festa-italiana-de-sao-caetano-do-sul/"
UTM = "?utm_source=whatsapp&utm_medium=share&utm_campaign=cardapio-33a"
LINKEDIN = "https://www.linkedin.com/in/marcelojrfarias/"

# Ícones desenhados com primitivas simples (arco, linha, polígono). Emoji foram
# a maior fonte da aparência amadora da v1: renderizam no estilo cartoon de cada
# plataforma e brigam com o logo manuscrito da festa.
ICONES = {
    "massas": '<path d="M3.2 12.6h17.6a8.8 8.8 0 0 1-17.6 0Z"/>'
              '<path d="M6.5 9.5c1.2-2 2.4-2 3.6 0s2.4 2 3.6 0 2.4-2 3.6 0"/>'
              '<path d="M7.5 6c1-1.6 2-1.6 3 0s2 1.6 3 0 2-1.6 3 0"/>',
    "pizzas-e-fogazza": '<path d="M12 3.5 4.8 18.2a15 15 0 0 0 14.4 0Z"/>'
              '<circle cx="10.5" cy="12" r="1.1"/><circle cx="14" cy="15" r="1.1"/>',
    "lanches": '<path d="M4 8.5c0-2 3.6-3.5 8-3.5s8 1.5 8 3.5"/>'
              '<path d="M4 12.2c2 1.4 4.4 1 6-.2 1.6 1.4 4.4 1.4 6 0 1.6 1.2 3 1.4 4 .2"/>'
              '<path d="M4.5 15.5h15a2 2 0 0 1-2 2h-11a2 2 0 0 1-2-2Z"/>',
    # panela com vapor: cobre polenta ao ragu, carne assada e zuppa. Espeto lia
    # como rolo de macarrão e a silhueta de bife com osso virava uma cruz.
    "carnes-e-polenta": '<path d="M4.4 9.6h15.2v5.8a4 4 0 0 1-4 4H8.4a4 4 0 0 1-4-4Z"/>'
              '<path d="M4.4 11.8H2.6"/><path d="M19.6 11.8h1.8"/>'
              '<path d="M9.4 6.6c0-1.1 1-1.5 1-2.6"/><path d="M13.6 6.6c0-1.1 1-1.5 1-2.6"/>',
    "petiscos-e-porcoes": '<path d="M3.5 16.5 13 7l7.5 4.5v5Z"/>'
              '<circle cx="9" cy="14" r="1.2"/><circle cx="15.5" cy="13.5" r="1.1"/>',
    "doces": '<path d="M6.6 10h10.8L12 20.6Z"/>'
              '<path d="M6.9 10a5.1 5.1 0 0 1 10.2 0"/><path d="M8.6 13.6h6.8"/>',
    "bebidas-sem-alcool": '<path d="M6.5 8.5h11l-1.2 10a1.6 1.6 0 0 1-1.6 1.4H9.3a1.6 1.6 0 0 1-1.6-1.4Z"/>'
              '<path d="M13.5 8.5 16 3.5"/><path d="M6.9 12.5h10.2"/>',
    "bebidas-com-alcool": '<path d="M6 3.5h12l-1 6a5 5 0 0 1-10 0Z"/>'
              '<path d="M12 14.5v5"/><path d="M8.5 20h7"/>',
    "outros-pratos": '<path d="M7.2 3.4v5.2a2.5 2.5 0 0 0 5 0V3.4"/><path d="M9.7 11.1v9.5"/>'
              '<path d="M16.8 20.6V3.4c1.7 0 2.8 1.5 2.8 3.7s-1.1 3.7-2.8 3.7"/>',
}

def svg(inner, tam=24, classe="icone"):
    return (f'<svg class="{classe}" viewBox="0 0 24 24" width="{tam}" height="{tam}" fill="none" '
            f'stroke="currentColor" stroke-width="1.7" stroke-linecap="round" '
            f'stroke-linejoin="round" aria-hidden="true">{inner}</svg>')

CHEVRON = '<path d="M9 5l7 7-7 7"/>'
ALFINETE = ('<path d="M12 21s7-6.1 7-11a7 7 0 1 0-14 0c0 4.9 7 11 7 11Z"/>'
            '<circle cx="12" cy="10" r="2.5"/>')


# O alfinete aparece uma vez por oferta: eram 974 cópias do mesmo desenho,
# 267 KB dos 749 KB do HTML. Como <symbol> ele é escrito uma vez só e cada
# ponto de uso vira uma referência de ~90 bytes. Os atributos de traço ficam
# no <svg> que referencia, e não no <symbol>, para herdarem currentColor.
SPRITE = {"pin": ALFINETE, "seta": CHEVRON}


def usar(nome, tam=24, classe="icone"):
    # Sem os atributos de traço: eles vivem na regra .icone do CSS. Repetidos
    # 1018 vezes no HTML custavam mais que o próprio desenho.
    return (f'<svg class="{classe}" width="{tam}" height="{tam}" aria-hidden="true">'
            f'<use href="#i-{nome}"/></svg>')


def sprite_html():
    simbolos = "".join(f'<symbol id="i-{k}" viewBox="0 0 24 24">{v}</symbol>'
                       for k, v in SPRITE.items())
    return f'<svg class="sprite" aria-hidden="true">{simbolos}</svg>'

# Ordem de navegação: comida primeiro, bebida por último. A ordem do arquivo de
# categorias é por volume, o que jogaria bebida para o topo do índice.
ORDEM = ["massas", "pizzas-e-fogazza", "lanches", "carnes-e-polenta",
         "petiscos-e-porcoes", "doces", "bebidas-sem-alcool", "bebidas-com-alcool",
         "outros-pratos"]


def sem_acento(s):
    return "".join(c for c in unicodedata.normalize("NFD", s or "")
                   if unicodedata.category(c) != "Mn").lower()


def slug(texto):
    return re.sub(r"[^a-z0-9]+", "-", sem_acento(texto)).strip("-")


def chave_barraca(numero):
    """Identificador estável de barraca, usado na URL e nos data-attributes.

    O Lar Bom Repouso ocupa dois números e seu rótulo impresso é "20/21". A
    barra não pode ir para a URL nem para a lista separada por espaço em
    data-barracas — era o que quebrava: o card linkava para "20/21" enquanto
    os pratos gravavam "20 21", e a barraca inteira aparecia vazia.
    """
    return sem_acento(numero).replace("/", "-")


def moeda(v):
    return f"R$ {v:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")


def e(s):
    return html.escape(str(s), quote=True)


def ler_mapa():
    """Geometria do croqui + os dois scripts que a desenham.

    Vai tudo embutido no app.js em vez de virar requisicao separada: numa rua
    lotada, cada ida a rede a mais e uma chance de o mapa nao abrir.
    """
    mapa = json.loads((DADOS / "mapa.json").read_text(encoding="utf-8"))
    # `numero` e a chave de juncao com o cardapio; `chave` e a mesma barraca no
    # formato que vai para a URL e para os data-attributes. A regra e uma so,
    # chave_barraca(), para o mapa nao redescobrir que "20/21" vira "20-21".
    for b in mapa["barracas"]:
        b["chave"] = chave_barraca(b["numero"])
    fontes = "".join((RAIZ / "mapa" / n).read_text(encoding="utf-8")
                     for n in ("geo.js", "croqui.js"))
    return mapa, fontes


def carregar():
    ler = lambda n: json.loads((DADOS / n).read_text(encoding="utf-8"))
    return ler("cardapio.json"), ler("categorias-site.json"), ler("evento.json")


# ---- grafias diferentes para a mesma coisa ----
#
# O cardápio é escrito por 35 entidades, cada uma do seu jeito. "Gnochi" e
# "Gnocchi", "Suco Uva" e "Suco de Uva", "Cannoli Nutella" e "Cannoli Alla
# Nutella" são o mesmo prato em cards separados, e nenhum dos dois mostra em
# quantas barracas ele realmente está.
#
# A regra é estreita de propósito: entra aqui erro de grafia, palavra de
# ligação faltando ou o mesmo ingrediente escrito em outra língua. Nome válido
# diferente fica como está. Dos 80 pares parecidos que o cardápio tem, 15 são a
# mesma coisa; nos outros 65 "Al Pesto" não é "Al Sugo", "Panino" não é
# "Piadina" e "Copo" não é "Garrafa". Por isso o mapa é escrito à mão: nenhum
# limiar de semelhança separa esses dois grupos.

# Aplicado palavra a palavra, antes de tudo — pega também os títulos que não
# têm par, onde o erro não duplica card mas atrapalha quem busca "formaggio".
CORRECOES = {"gnochi": "Gnocchi", "sfitacciato": "Sfilacciato",
             "fomarggio": "Formaggio"}

# Aplicado ao título inteiro, já corrigido e normalizado.
SINONIMOS = {
    # concordância: maiale é masculino
    "panino alla maiale sfilacciato": "Panino Al Maiale Sfilacciato",
    "panino alla maiale sfilacciato affumicata": "Panino Al Maiale Sfilacciato Affumicata",
    # falta o "de"
    "suco uva (copo)": "Suco de Uva (Copo)",
    "suco uva (garrafa)": "Suco de Uva (Garrafa)",
    "suco uva integral (copo)": "Suco de Uva Integral (Copo)",
    "suco uva integral (garrafa)": "Suco de Uva Integral (Garrafa)",
    "copo de suco uva": "Suco de Uva (Copo)",
    # ordem invertida, mesma medida
    "copo vinho tinto": "Vinho Tinto (Copo)",
    "copo vinho quente": "Vinho Quente (Copo)",
    "chopp vinho": "Chopp de Vinho",
    "cannoli nutella": "Cannoli Alla Nutella",
    # doce de leite em três línguas
    "cannoli dulce di latte": "Cannoli Dolce di Latte",
    "cannoli al dulce de leche": "Cannoli Dolce di Latte",
    # só a vírgula
    "vinho tinto, seco ou suave (copo)": "Vinho Tinto Seco ou Suave (Copo)",
    "vinho tinto, seco ou suave (garrafa)": "Vinho Tinto Seco ou Suave (Garrafa)",
}


def canonizar(titulo):
    palavras = [CORRECOES.get(sem_acento(w), w) for w in titulo.split()]
    corrigido = " ".join(palavras)
    return SINONIMOS.get(sem_acento(corrigido), corrigido)


def conferir_sinonimos(cardapio):
    """Sinônimo que não casa com nada vira lixo silencioso: o título mudou no
    cardápio e o mapa continua apontando para o nome velho, sem juntar nada."""
    vistos = set()
    for barraca in cardapio["barracas"]:
        for item in barraca["itens"]:
            for titulo, _ in expandir_titulo(item):
                palavras = [CORRECOES.get(sem_acento(w), w) for w in titulo.split()]
                vistos.add(sem_acento(" ".join(palavras)))
                vistos.update(sem_acento(w) for w in titulo.split())
    orfas = sorted(set(SINONIMOS) - vistos) + sorted(set(CORRECOES) - vistos)
    if orfas:
        raise SystemExit("grafias sem correspondência no cardápio: "
                         + ", ".join(repr(o) for o in orfas))


# ---- famílias dentro de uma categoria ----
#
# Massas tem 84 pratos e Doces 107. Rolar 84 cards para achar o gnocchi é o
# mesmo problema que as categorias resolveram um nível acima, então a categoria
# ganha mais uma etapa: Categorias -> Massas -> Gnocchi -> os 6 pratos. A
# família sai do próprio nome do prato, porque quase todo título começa pelo
# tipo — Spaghetti, Penne, Crostata, Cannoli.
#
# Três regras seguram o resultado. Família não pode aninhar: "Spaghetti Al Sugo"
# entra em "Spaghetti", senão tocar em Spaghetti esconderia spaghetti. Família
# com menos de 3 pratos não vira card — uma tela a mais para chegar a 1 prato é
# trabalho, não atalho. E a etapa só existe onde a categoria é grande o
# bastante: em Lanches, 25 dos 28 pratos são panino, e a tela do meio seria um
# pedágio. Sobram Massas, Doces e Pizzas e Fogazza.
FAM_MIN = 3
FAM_CAT_MIN = 40
FAM_FAMILIAS_MIN = 3
LIGACAO = {"al", "alla", "ai", "alle", "allo", "di", "de", "con", "e", "a",
           "da", "ao", "com", "ou", "in", "della", "dei", "del"}


def _rotulo_familia(prefixo, membros):
    """Estende o rótulo até onde os membros concordam. A chave do filtro
    continua sendo o prefixo curto; só o texto do chip cresce. "Panna" vira
    "Panna Cotta", que é o que está escrito na barraca."""
    palavras = membros[0].split()
    for m in membros[1:]:
        w = m.split()
        palavras = palavras[:next((i for i, (a, b) in enumerate(zip(palavras, w))
                                   if sem_acento(a) != sem_acento(b)), min(len(palavras), len(w)))]
    while palavras and sem_acento(palavras[-1]) in LIGACAO:
        palavras.pop()
    rotulo = " ".join(palavras)
    return rotulo if len(rotulo) >= len(prefixo) else prefixo


def familias_da_categoria(titulos):
    contagem = collections.Counter()
    for t in titulos:
        w = t.split()
        for n in range(1, min(4, len(w)) + 1):
            if sem_acento(w[n - 1]) in LIGACAO:
                continue
            contagem[" ".join(w[:n])] += 1
    # prefixo mais curto primeiro — é ele que absorve os mais longos
    candidatos = sorted((p for p, n in contagem.items() if n >= FAM_MIN),
                        key=lambda p: (len(p.split()), -contagem[p], sem_acento(p)))
    familias, usados = [], set()
    for pref in candidatos:
        membros = [t for t in titulos
                   if (t == pref or t.startswith(pref + " ")) and t not in usados]
        if len(membros) >= FAM_MIN:
            usados.update(membros)
            familias.append({"chave": slug(pref), "prefixo": pref,
                             "rotulo": _rotulo_familia(pref, sorted(membros)),
                             "total": len(membros), "titulos": set(membros)})
    familias.sort(key=lambda f: (-f["total"], sem_acento(f["rotulo"])))
    if len(familias) < FAM_FAMILIAS_MIN:
        return []
    # o que não coube em família nenhuma vai para "Outros": sem isso a tela do
    # meio esconderia 24 doces, e nenhum caminho levaria ao tiramisù
    sobra = sorted(set(titulos) - {t for f in familias for t in f["titulos"]})
    if sobra:
        familias.append({"chave": "outros", "prefixo": "", "rotulo": "Outros",
                         "total": len(sobra), "titulos": set(sobra)})
    return familias


def mapear_familias(pratos):
    """Devolve (familias_por_categoria, familia_de_cada_titulo)."""
    por_cat = collections.defaultdict(list)
    for p in pratos:
        por_cat[p["categoria"]].append(p["titulo"])
    catalogo, de_titulo = {}, {}
    for cid, titulos in sorted(por_cat.items()):
        if len(titulos) < FAM_CAT_MIN:
            continue
        fs = familias_da_categoria(titulos)
        if not fs:
            continue
        catalogo[cid] = [{"chave": f["chave"], "rotulo": f["rotulo"], "total": f["total"]}
                         for f in fs]
        for f in fs:
            for t in f["titulos"]:
                de_titulo[t] = f["chave"]
    return catalogo, de_titulo


def agrupar_pratos(cardapio, categorias):
    """Um prato = um título. 645 itens viram ~365 pratos com faixa de preço.

    O mesmo prato aparece em até 10 barracas com preços diferentes; agrupar
    responde "onde tem tiramisù e por quanto" sem obrigar a varrer a lista.
    """
    atrib = categorias["atribuicoes"]
    conferir_sinonimos(cardapio)
    grupos = {}
    for barraca in cardapio["barracas"]:
        for item in barraca["itens"]:
          for titulo_original, desc_expandida in expandir_titulo(item):
            titulo_expandido = canonizar(titulo_original)
            chave = sem_acento(titulo_expandido)
            g = grupos.setdefault(chave, {
                "titulo": titulo_expandido, "cats": collections.Counter(),
                "ofertas": [], "descricoes": [], "grafias": set(),
                # o PDF lista sabores e formatos de massa num título só, separados
                # por "/"; o extrator já os separou e o gerador ignorava o campo
            })
            g["cats"][atrib[item["id"]]] += 1
            g["ofertas"].append({
                "num": barraca["numero"], "nome": barraca["nome"],
                "preco": item["preco"], "descricao": item["descricao"],
            })
            g["descricoes"].append(desc_expandida)
            # quem lê "Gnochi" na placa da barraca digita "Gnochi". O card
            # mostra a grafia certa, mas a busca precisa aceitar a impressa.
            g["grafias"].add(titulo_original)

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
            "busca": sem_acento(" ".join(sorted(g["grafias"] | {g["titulo"]}))
                                 + " " + " ".join(sorted(set(g["descricoes"])))),
        })
    pratos.sort(key=lambda p: sem_acento(p["titulo"]))

    # Três ordens, gravadas como posição em cada card e aplicadas no cliente
    # via CSS order — sem reordenar o DOM.
    #
    # "Popular" aqui é o número de barracas que vendem o prato. Não há dado de
    # venda; o que existe é a aposta de 35 entidades sobre o que sai. Bebida vem
    # depois da comida porque água está em 34 barracas por ser necessidade, não
    # por ser o que a pessoa foi comer na festa — sem essa separação, o topo da
    # lista volta a ser água.
    for pos, pr in enumerate(pratos):
        pr["ord_nome"] = pos
    for pos, pr in enumerate(sorted(pratos, key=lambda x: (x["min"], sem_acento(x["titulo"])))):
        pr["ord_preco"] = pos
    for pos, pr in enumerate(sorted(pratos, key=lambda x: (x["categoria"].startswith("bebidas"),
                                                           -len(x["ofertas"]),
                                                           sem_acento(x["titulo"])))):
        pr["ord_pop"] = pos
    return pratos


def faixa_preco(p):
    if p["min"] == p["max"]:
        return moeda(p["min"])
    # "R$ 15,00 a R$ 16,00" espremia o título do prato em três linhas
    return f"{moeda(p['min'])}–{moeda(p['max']).removeprefix('R$ ')}"


def bucket_preco(v):
    return "ate10" if v <= 10 else "11a20" if v <= 20 else "21a30" if v <= 30 else "31mais"


PREPOSICOES = {"al", "alla", "ai", "alle", "con", "in"}

# Casos em que a regra de expansão produz nome ruim. Conferidos à mão contra os
# 17 itens com variação; hoje só um precisa. A regra deriva o prefixo da
# primeira preposição do primeiro segmento, e aqui não há preposição nenhuma —
# "Merlot" e "Chardonnay" sairiam soltos, sem a palavra "Vinho".
EXPANSAO_MANUAL = {
    "27-17-vinho-fino-cabernet-merlot-chardonnay-copo": [
        "Vinho Fino Cabernet (Copo)",
        "Vinho Fino Merlot (Copo)",
        "Vinho Fino Chardonnay (Copo)",
    ],
}


def descricao_por_variacao(descricao, n):
    """Reparte a descrição entre as n variações, quando ela as enumera.

    "Massa Crocante recheada com Creme, Doce de Leite ou Nutella" descreve as
    três variações de "Cannoli Alla Crema / Dolce di Latte / Nutella", na mesma
    ordem. Sem repartir, os três pratos expandidos herdam a descrição inteira e
    "Cannoli Alla Crema" alega ter Doce de Leite e Nutella dentro.

    Só reparte quando a conta fecha: a enumeração precisa ter exatamente n itens
    e vir depois de um "com". Nas descrições de massa a enumeração está no meio
    da frase ("Macarrão Tipo Espaguete, Penne ou Gravatinha ao Molho de Tomate")
    e a função devolve None, mantendo a descrição original.
    """
    if " ou " not in descricao:
        return None
    cabeca, ultimo = descricao.rsplit(" ou ", 1)
    partes = [x.strip() for x in cabeca.split(",")]
    if " com " not in partes[0]:
        return None
    prefixo, primeiro = partes[0].rsplit(" com ", 1)
    itens = [primeiro] + partes[1:] + [ultimo]
    if len(itens) != n:
        return None
    return [f"{prefixo} com {x}" for x in itens]


def expandir_titulo(item):
    """Um item por sabor ou formato de massa.

    O PDF junta variações num título só, separadas por "/", em dois formatos:

      sabor   "Cannoli Alla Crema / Nutella / Fior di Latte"
              -> o primeiro segmento traz o prato; os demais são só o recheio,
                 e precisam receber o nome do prato de volta

      formato "Spaghetti / Penne Rigati / Farfalle Al Sugo"
              -> os segmentos são formatos e o molho vem grudado no último;
                 cada formato precisa receber o molho

    O que separa os dois é o tamanho: no formato de massa o primeiro segmento
    tem menos palavras que o último, porque o último carrega o molho.
    """
    # "recheada com Creme – sabores" está assim no PDF: a barraca não listou
    # quais. O traço pendurado não informa nada.
    desc = re.sub(r"\s*[–-]\s*sabores\s*$", "", item["descricao"])

    if item["id"] in EXPANSAO_MANUAL:
        return [(t, desc) for t in EXPANSAO_MANUAL[item["id"]]]
    v = item.get("variacoes") or []
    if len(v) < 2:
        return [(item["titulo"], desc)]

    primeiro, ultimo = v[0].split(), v[-1].split()
    if len(primeiro) < len(ultimo):
        sufixo = " ".join(ultimo[1:])
        titulos = [f"{x} {sufixo}" for x in v[:-1]] + [f"{ultimo[0]} {sufixo}"]
    else:
        base = ""
        for i, palavra in enumerate(primeiro):
            if palavra.lower() in PREPOSICOES:
                base = " ".join(primeiro[:i])
                break
        titulos = [v[0]] + [f"{base} {x}".strip() for x in v[1:]]

    descs = descricao_por_variacao(desc, len(titulos))
    return list(zip(titulos, descs if descs else [desc] * len(titulos)))


def render_prato(p, familia_de=None):
    # "Spaghetti / Penne Rigati / Farfalle Al Sugo" ocupava cinco linhas. O
    # primeiro segmento é o nome reconhecível do prato; os demais são as
    # alternativas, e a descrição já explica todas em português.

    nums = " ".join(chave_barraca(o["num"]) for o in p["ofertas"])
    buckets = " ".join(sorted({bucket_preco(o["preco"]) for o in p["ofertas"]}))
    # "onde fica isto" e a pergunta de quem esta de pe na festa, entao a linha da
    # barraca leva direto ao mapa, com ela selecionada
    ofertas = "".join(
        f'<li><a class="oferta" data-barraca="{e(chave_barraca(o["num"]))}" '
        f'data-ir-mapa="{e(chave_barraca(o["num"]))}" '
        f'href="?modo=mapa&amp;barraca={e(chave_barraca(o["num"]))}">'
        f'<span class="oferta__num">{e(o["num"])}</span>'
        f'<span class="oferta__nome">{e(o["nome"])}</span>'
        f'<span class="oferta__preco">{e(moeda(o["preco"]))}</span>'
        f'<span class="oferta__pin">{usar("pin", 15)}</span></a></li>'
        for o in p["ofertas"])
    n = len(p["ofertas"])
    # Com uma barraca só não há o que expandir, mas "onde encontro isto" é a
    # pergunta de quem está de pé na festa — então mostra direto. 302 dos 365
    # pratos caem neste caso: escondê-los atrás de nada deixava a maioria da
    # lista sem resposta.
    if n == 1:
        o = p["ofertas"][0]
        onde = (f'<a class="prato__onde" data-ir-mapa="{e(chave_barraca(o["num"]))}" '
                f'href="?modo=mapa&amp;barraca={e(chave_barraca(o["num"]))}">'
                f'<span class="oferta__num">{e(o["num"])}</span>'
                f'<span class="oferta__nome">{e(o["nome"])}</span>'
                f'<span class="oferta__pin">{usar("pin", 15)}</span></a>')
    else:
        onde = (f'<button class="prato__toggle" type="button" aria-expanded="false">'
                f'em {n} barracas</button>')
    return (
        f'<article class="prato" data-cat="{e(p["categoria"])}" '
        f'data-barracas=" {e(nums)} " data-precos=" {e(buckets)} " '
        f'data-fam="{e((familia_de or {}).get(p["titulo"], ""))}" '
        f'data-busca="{e(p["busca"])}" '
        f'data-ord-pop="{p["ord_pop"]}" data-ord-preco="{p["ord_preco"]}" '
        f'data-ord-nome="{p["ord_nome"]}">'
        f'<div class="prato__topo"><h3 class="prato__titulo">{e(p["titulo"])}</h3>'
        f'<span class="prato__faixa">{e(faixa_preco(p))}</span></div>'
        f'<p class="prato__desc">{e(p["descricao"])}</p>'
        f'{onde}<ul class="ofertas">{ofertas}</ul></article>')


def render_indices(cardapio, categorias, pratos, fam_catalogo):
    por_cat = collections.Counter(p["categoria"] for p in pratos)
    nomes = {c["id"]: c["nome"] for c in categorias["categorias"]}
    cards_cat = "".join(
        f'<a class="card" href="?cat={e(cid)}" data-cat="{e(cid)}">'
        f'<span class="card__icone">{svg(ICONES[cid], 26)}</span>'
        f'<span class="card__nome">{e(nomes[cid])}</span>'
        f'<span class="card__contagem">{por_cat[cid]}</span>'
        f'<span class="card__chevron">{usar("seta", 18)}</span></a>'
        for cid in ORDEM if por_cat[cid])

    cards_bar = "".join(
        f'<a class="card" href="?barraca={e(chave_barraca(b["numero"]))}" '
        f'data-barraca="{e(chave_barraca(b["numero"]))}">'
        f'<span class="card__numero">{e(b["numero"])}</span>'
        f'<span class="card__nome">{e(b["nome"])}</span>'
        f'<span class="card__contagem">{b["total_itens"]}</span>'
        f'<span class="card__chevron">{usar("seta", 18)}</span></a>'
        for b in sorted(cardapio["barracas"], key=lambda x: x["numeros"][0]))

    # todos os tipos de todas as categorias no mesmo bloco; o cliente esconde
    # os que não são da categoria aberta. São 35 cards no total — separar em
    # seções por categoria só multiplicaria elemento para o mesmo efeito.
    def cards_de(cid):
        fs = fam_catalogo[cid]
        tipos = "".join(
            f'<a class="card card--tipo" href="?cat={e(cid)}&amp;fam={e(f["chave"])}" '
            f'data-cat="{e(cid)}" data-fam="{e(f["chave"])}">'
            f'<span class="card__nome">{e(f["rotulo"])}</span>'
            f'<span class="card__contagem">{f["total"]}</span>'
            f'<span class="card__chevron">{usar("seta", 18)}</span></a>'
            for f in fs)
        # Sem esta saída, ver a categoria inteira exigia a aba "Tudo", que traz
        # os 363 pratos da festa. Fica por último: é o caminho de quem não quer
        # escolher tipo, não o primeiro que se oferece.
        total = sum(f["total"] for f in fs)
        return tipos + (
            f'<a class="card card--tipo card--todos" href="?cat={e(cid)}&amp;fam=todos" '
            f'data-cat="{e(cid)}" data-fam="todos">'
            f'<span class="card__nome">Ver todos</span>'
            f'<span class="card__contagem">{total}</span>'
            f'<span class="card__chevron">{usar("seta", 18)}</span></a>')

    cards_fam = "".join(cards_de(cid) for cid in ORDEM if cid in fam_catalogo)
    return cards_cat, cards_bar, cards_fam


def render_html(cardapio, categorias, evento, pratos, geo, versao,
                fam_catalogo, fam_de_titulo):
    cards_cat, cards_bar, cards_fam = render_indices(cardapio, categorias, pratos,
                                                     fam_catalogo)
    lista = "".join(render_prato(p, fam_de_titulo) for p in pratos)
    ev = evento["local"]
    endereco = f'{ev["endereco"]} — {ev["bairro"]}, {ev["cidade"]}/{ev["uf"]}'
    mapa = "https://www.google.com/maps/search/?api=1&query=" + \
           re.sub(r"\s+", "+", f'{ev["endereco"]} {ev["bairro"]} {ev["cidade"]}')

    msg = ("Achei um cardápio digital da Festa Italiana de SCS. Dá pra buscar por "
           "prato, comparar preço e encontrar a barraca no mapa. Tá me ajudando a "
           "decidir o que comer e pode te ajudar também: " + SITE + UTM)
    from urllib.parse import quote
    wa = "https://wa.me/?text=" + quote(msg, safe="")

    dados_js = json.dumps({"dias": evento["dias"], "horarios": evento["horarios"]},
                          ensure_ascii=False)
    # o número anunciado é o do cardápio oficial, que o validate_menu.py
    # confere contra o PDF; expandir variações infla a contagem interna
    # "itens" são as linhas do cardápio oficial, que o validate_menu.py confere
    # contra o PDF. "pratos" são os cards da tela — o mesmo prato vendido em 11
    # barracas é um card só. Usar a mesma palavra para os dois fazia o card do
    # WhatsApp prometer 645 e a tela mostrar 376.
    total = sum(len(b["itens"]) for b in cardapio["barracas"])
    distintos = len(pratos)
    nota_mapa = ("Posições conforme o mapa oficial das entidades. Toque numa barraca "
                 "para ver o cardápio dela."
                 if geo["_status"] != "aproximado" else
                 "Posições aproximadas.")

    return f"""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Cardápio da 33ª Festa Italiana — São Caetano do Sul</title>
<meta name="description" content="Cardápio completo da 33ª Festa Italiana de São Caetano do Sul: {total} itens de {len(cardapio['barracas'])} barracas, com preço e busca por prato.">
<meta name="theme-color" content="#196B24">
<meta property="og:title" content="Cardápio da 33ª Festa Italiana">
<meta property="og:description" content="O cardápio completo das {len(cardapio['barracas'])} barracas: {distintos} pratos, com preço. Procure o que quer comer.">
<meta property="og:type" content="website">
<meta property="og:url" content="{e(SITE)}">
<meta property="og:site_name" content="33ª Festa Italiana de São Caetano do Sul">
<meta property="og:locale" content="pt_BR">
<!-- URL absoluta: o WhatsApp não resolve caminho relativo no preview -->
<meta property="og:image" content="{e(SITE)}assets/og.png">
<meta property="og:image:type" content="image/png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="Logo da 33ª Festa Italiana de São Caetano do Sul">
<meta name="twitter:card" content="summary_large_image">
<link rel="canonical" href="{e(SITE)}">
<link rel="stylesheet" href="style.css?v={versao["css"]}">
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'><text y='26' font-size='26'>🍝</text></svg>">
</head>
<body data-modo="categoria">
{sprite_html()}

<header class="marca">
  <div class="marca__linha">
    <img class="marca__logo" src="assets/logo.webp" width="742" height="386"
         alt="33ª Festa Italiana de São Caetano do Sul">
    <a class="botao-share botao-share--icone" href="{e(wa)}" target="_blank" rel="noopener"
       aria-label="Compartilhar no WhatsApp">
      <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor"
           stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/>
        <line x1="8.6" y1="10.5" x2="15.4" y2="6.5"/><line x1="8.6" y1="13.5" x2="15.4" y2="17.5"/>
      </svg>
    </a>
  </div>
  <p class="status" id="status" data-evento='{dados_js}'>33ª Festa Italiana · São Caetano do Sul</p>
</header>

<div class="ferramentas">
  <form class="busca" role="search" onsubmit="return false">
    <label class="sr" for="q">Buscar prato</label>
    <input id="q" type="search" placeholder="Buscar…" autocomplete="off">
  </form>
  <nav class="modos" aria-label="Modo de visualização">
    <button type="button" data-modo="categoria" aria-pressed="true">Categorias</button>
    <button type="button" data-modo="barraca" aria-pressed="false">Barracas</button>
    <button type="button" data-modo="tudo" aria-pressed="false">Tudo</button>
    <button type="button" data-modo="mapa" aria-pressed="false">Mapa</button>
  </nav>
</div>

<main>
  <div class="trilha" id="trilha" hidden>
    <button class="voltar" type="button" aria-label="Voltar">{usar("seta", 18, "icone voltar__seta")}</button>
    <h2 class="trilha__titulo" id="trilha-titulo"></h2>
    <button class="trilha__mapa" type="button" id="ver-no-mapa" hidden>{usar("pin", 15)}ver no mapa</button>
  </div>

  <section class="indice" id="idx-categoria" aria-label="Categorias">{cards_cat}</section>
  <section class="indice" id="idx-barraca" aria-label="Barracas" hidden>{cards_bar}</section>
  <section class="indice" id="idx-familia" aria-label="Tipos de prato" hidden>{cards_fam}</section>

  <div class="filtros" id="filtros" hidden>
    <button type="button" data-preco="ate10">até R$ 10</button>
    <button type="button" data-preco="11a20">R$ 11–20</button>
    <button type="button" data-preco="21a30">R$ 21–30</button>
    <button type="button" data-preco="31mais">R$ 31+</button>
  </div>

  <div class="ordenacao" id="ordenacao" hidden>
    <span class="ordenacao__rotulo">Ordenar</span>
    <button type="button" data-ord="pop" aria-pressed="true">Populares</button>
    <button type="button" data-ord="preco" aria-pressed="false">Preço</button>
    <button type="button" data-ord="nome" aria-pressed="false">Nome</button>
  </div>

  <p class="contador" id="contador" hidden></p>

  <section class="mapa" id="mapa" aria-label="Mapa das barracas" hidden>
    <div class="mapa__tela" id="mapa-tela"></div>
    <p class="mapa__nota">{e(nota_mapa)}</p>
  </section>

  <section class="lista" id="lista" aria-label="Pratos">{lista}</section>
  <p class="vazio" id="vazio" hidden>Nenhum prato encontrado.<br>
    <button type="button" class="limpar">limpar filtros</button></p>

  <aside class="convite">
    <p class="convite__titulo">Manda pra quem vai contigo 😉</p>
    <p class="convite__texto">Vale mandar pra amigo, família e até no grupo do prédio</p>
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
    extraídos do material oficial; preços e atrações podem mudar.<br>Medimos acessos de forma anônima, sem cookies.</p>
</footer>

<script src="app.js?v={versao["js"]}"></script>
<!-- Cloudflare Web Analytics: sem cookie e sem dado pessoal, então não exige
     banner de consentimento. type=module já adia a execução. O beacon rastreia
     pushState sozinho, que é como toda a navegação interna funciona aqui. -->
<script type="module" src="https://static.cloudflareinsights.com/beacon.min.js"
        data-cf-beacon='{{"token": "e88175fb06234c31a1a44aea5455f6e8"}}'></script>
</body>
</html>
"""


CSS_ONDE = """
/* a linha da barraca leva ao mapa; o alfinete é o que avisa isso */
.prato__onde, .oferta { color: inherit; text-decoration: none; }
.oferta__pin { display: grid; place-items: center; color: var(--verde); opacity: .75; }
.prato__onde:active .oferta__pin, .oferta:active .oferta__pin { opacity: 1; }
.ofertas li { list-style: none; }
"""

CSS_MAPA = """
/* --- mapa ---------------------------------------------------------------- */
.mapa { margin: 0 0 var(--gap); }
.mapa__tela { height: min(68vh, 560px); border-radius: 14px; overflow: hidden;
  background: var(--papel); border: 1px solid var(--papel-linha); touch-action: none; }
.mapa__falha { display: grid; place-content: center; padding: 1.5rem; text-align: center;
  color: var(--tinta-fraca); font-size: .9rem; line-height: 1.5; }
.mapa__nota { margin: .55rem .2rem 0; font-size: .78rem; line-height: 1.4;
  color: var(--tinta-fraca); }
.trilha__mapa { display: inline-flex; align-items: center; gap: 6px;
  flex: none; min-height: 44px; padding: .35rem .9rem;
  font: inherit; font-size: .82rem; color: var(--verde); background: none;
  border: 1px solid var(--papel-linha); border-radius: 999px; cursor: pointer; }
.modos button { padding-inline: .6rem; }
"""

CSS = """/* Paleta medida do PDF oficial (data/identidade-visual.json), organizada em
   rampa. O bege #E5B67E do impresso não é usado chapado: em área grande ele lê
   como cor padrão, não como superfície escolhida. Aqui ele vira o papel claro
   do fundo e reaparece saturado só como acento, no número da barraca. */
@font-face {
  font-family: "Bevan";
  src: url("assets/fonts/bevan-latin-400.woff2") format("woff2");
  font-weight: 400; font-style: normal; font-display: swap;
}

:root {
  --papel: #EFE4D4;
  --papel-linha: #DFCEB4;
  --cartao: #FFFFFF;
  --tinta: #1F1A14;          /* preto quente, não puro */
  --tinta-fraca: #726553;    /* cinza enviesado para a temperatura do papel */
  --verde: #0F5F28;
  --verde-fundo: #08351A;
  --verde-suave: #E7EFE6;
  --vermelho: #B02020;
  --dourado: #D6A25E;

  --sombra-1: 0 1px 2px rgba(31,26,20,.05);
  --sombra-2: 0 2px 5px rgba(31,26,20,.07), 0 1px 2px rgba(31,26,20,.04);
  --sombra-3: 0 10px 28px rgba(8,53,26,.18);

  --e1: 4px; --e2: 8px; --e3: 12px; --e4: 16px; --e5: 24px; --e6: 32px;
  --raio: 16px;

  --display: "Bevan", Georgia, serif;
  --corpo: system-ui, -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  color-scheme: light;
}
* { box-sizing: border-box; }
/* display:grid/flex nos containers sobrepõe o [hidden] do HTML */
[hidden] { display: none !important; }
body {
  margin: 0; background: var(--papel); color: var(--tinta);
  font-family: var(--corpo); font-size: 16px; line-height: 1.45;
  -webkit-text-size-adjust: 100%;
}
.sr { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); }
a { color: var(--verde); }
:focus-visible { outline: 3px solid var(--verde); outline-offset: 2px; border-radius: 4px; }
.sprite { position: absolute; width: 0; height: 0; overflow: hidden; }
.icone { flex: 0 0 auto; fill: none; stroke: currentColor; stroke-width: 1.7;
         stroke-linecap: round; stroke-linejoin: round; }

/* ---- faixa de marca: rola embora ---- */
.marca { padding: var(--e3) var(--e4) var(--e2); }
.marca__linha { display: flex; align-items: center; gap: var(--e3); }
.marca__logo { width: auto; height: auto; max-height: 54px; max-width: 100%; }
.marca__linha .botao-share--icone { margin-left: auto; }
.status {
  display: flex; align-items: center; gap: 7px;
  margin: var(--e2) 0 0; font-size: 13px; font-weight: 600;
  letter-spacing: .02em; color: var(--verde-fundo);
}
.status::before {
  content: ""; width: 7px; height: 7px; border-radius: 50%;
  background: var(--tinta-fraca); flex: 0 0 auto;
}
.status[data-aberta="1"]::before { background: var(--verde); }

/* ---- faixa de ferramenta: a espinha verde do app ---- */
.ferramentas {
  position: sticky; top: 0; z-index: 10;
  background: var(--verde-fundo); padding: var(--e3) var(--e4);
  display: grid; gap: var(--e2);
}
/* Itens de grid e flex nascem com min-width:auto e não encolhem abaixo do
   próprio conteúdo. Sem estes zeros a barra de ferramentas estoura a tela em
   320px e em qualquer nível de zoom ou fonte aumentada. */
.ferramentas > * { min-width: 0; }
.busca input {
  width: 100%; padding: 11px var(--e4); font: inherit; font-size: 16px;
  border: 0; border-radius: 999px; background: var(--cartao); color: var(--tinta);
}
.busca input::placeholder { color: var(--tinta-fraca); }
.modos { display: flex; flex-wrap: wrap; gap: 6px; }
.modos button {
  /* max-content impede que a palavra seja cortada; com flex-wrap no pai, o
     botão que não couber desce para a linha seguinte. É o que mantém os três
     modos legíveis com fonte do sistema aumentada. */
  flex: 1 1 auto; min-width: max-content; padding: 12px 10px; font: inherit; font-size: 13px; font-weight: 600;
  border: 1px solid rgba(255,255,255,.28); border-radius: 999px;
  background: transparent; color: #EFE4D4; cursor: pointer;
}
.modos button[aria-pressed="true"] {
  background: var(--cartao); border-color: var(--cartao); color: var(--verde-fundo);
}

main { padding: var(--e4) var(--e4) 0; }

/* ---- trilha: o momento de display ---- */
/* Grade em vez de linha: o botão do mapa roubava 107px da largura e o nome da
   barraca 24, com 83 caracteres, quebrava em nove linhas num título de 142px.
   O título passa a ocupar a largura toda e o botão desce, alinhado com ele. */
.trilha {
  display: grid; grid-template-columns: 44px 1fr; align-items: start;
  gap: var(--e2) var(--e3); margin-bottom: var(--e4);
}
.trilha__titulo, .trilha__mapa { grid-column: 2; }
.trilha__mapa { justify-self: start; }
.voltar {
  display: grid; place-items: center; width: 44px; height: 44px; flex: 0 0 auto;
  padding: 0; border: 1px solid var(--papel-linha); border-radius: 50%;
  background: var(--cartao); color: var(--verde); cursor: pointer;
}
.voltar__seta { transform: rotate(180deg); }
.trilha__titulo {
  margin: 0; font-family: var(--display); font-weight: 400; font-size: 23px;
  line-height: 1.1; letter-spacing: .01em; color: var(--verde-fundo);
  text-wrap: balance;
}

/* ---- índices ---- */
.indice { display: grid; gap: var(--e2); }
.card {
  display: grid; grid-template-columns: auto 1fr auto 18px; align-items: center;
  gap: var(--e3); padding: var(--e3) var(--e4); background: var(--cartao);
  border-radius: var(--raio); box-shadow: var(--sombra-2);
  text-decoration: none; color: var(--tinta);
  transition: box-shadow .16s ease, transform .16s ease;
}
.card:active { transform: translateY(1px); box-shadow: var(--sombra-1); }
.card__icone {
  display: grid; place-items: center; width: 44px; height: 44px;
  border-radius: 50%; background: var(--verde-suave); color: var(--verde);
}
.card__numero {
  /* pílula, não círculo: a barraca dupla imprime "20/21" e estourava o círculo */
  display: grid; place-items: center; min-width: 40px; height: 40px;
  padding: 0 9px; border-radius: 999px;
  background: var(--dourado); color: #3A2A12;
  font-weight: 700; font-size: 14px; font-variant-numeric: tabular-nums;
}
.card__nome { min-width: 0; font-weight: 600; line-height: 1.25; }
.card__contagem {
  color: var(--tinta-fraca); font-size: 13px; font-variant-numeric: tabular-nums;
}
.card__chevron { display: grid; place-items: center; color: var(--papel-linha); }
/* o tipo não tem ícone próprio: sem a primeira coluna o nome ocupa a largura */
.card--tipo { grid-template-columns: 1fr auto 18px; min-height: 60px; }
.card--todos {
  background: transparent; box-shadow: none; border: 1px solid var(--papel-linha);
}
.card--todos .card__nome { font-weight: 600; color: var(--tinta-fraca); }

/* ---- filtros ---- */
.filtros {
  display: flex; gap: 6px; overflow-x: auto; padding-bottom: var(--e3);
  scrollbar-width: none;
}
.filtros::-webkit-scrollbar { display: none; }
.filtros button {
  flex: 0 0 auto; padding: 12px var(--e3); font: inherit; font-size: 13px; font-weight: 600;
  border: 1px solid var(--papel-linha); border-radius: 999px;
  background: var(--cartao); color: var(--tinta-fraca); cursor: pointer;
}
.filtros button[aria-pressed="true"] {
  background: var(--vermelho); border-color: var(--vermelho); color: #fff;
}
.ordenacao {
  display: flex; flex-wrap: wrap; align-items: center; gap: 6px;
  margin-bottom: var(--e3);
}
.ordenacao__rotulo {
  font-size: 12px; font-weight: 700; letter-spacing: .06em;
  text-transform: uppercase; color: var(--tinta-fraca); margin-right: 2px;
}
.ordenacao button {
  flex: 0 0 auto; min-width: max-content;
  padding: 12px var(--e3); font: inherit; font-size: 13px; font-weight: 600;
  border: 1px solid var(--papel-linha); border-radius: 999px;
  background: var(--cartao); color: var(--tinta-fraca); cursor: pointer;
}
.ordenacao button[aria-pressed="true"] {
  background: var(--verde); border-color: var(--verde); color: #fff;
}

.contador {
  margin: 0 0 var(--e3); font-size: 12px; font-weight: 600; letter-spacing: .06em;
  text-transform: uppercase; color: var(--tinta-fraca);
}

/* ---- pratos ---- */
.lista { display: grid; gap: var(--e2); }
.prato {
  padding: var(--e3) var(--e4); background: var(--cartao);
  border-radius: var(--raio); box-shadow: var(--sombra-2);
}
.prato__topo { display: flex; flex-wrap: wrap; align-items: baseline; gap: var(--e3); }
.prato__titulo {
  margin: 0; flex: 1; min-width: 0; font-size: 16px; font-weight: 700; line-height: 1.3;
  color: var(--verde); text-wrap: balance;
}
.prato__faixa {
  font-size: 15px; font-weight: 700; color: var(--tinta); white-space: nowrap;
  font-variant-numeric: tabular-nums;
}
.prato__desc { margin: var(--e1) 0 0; font-size: 14px; color: var(--tinta-fraca); }
.prato__titulo, .prato__desc, .card__nome, .oferta__nome, .trilha__titulo {
  overflow-wrap: break-word;
}
.prato__onde {
  display: grid; grid-template-columns: auto 1fr auto; align-items: center; gap: var(--e2);
  margin: var(--e3) 0 0; padding-top: var(--e2);
  border-top: 1px solid var(--papel); font-size: 13px;
}
.prato__toggle {
  margin-top: var(--e3); padding: 12px var(--e3); font: inherit; font-size: 13px;
  font-weight: 600; border: 1px solid var(--papel-linha); border-radius: 999px;
  background: transparent; color: var(--tinta-fraca); cursor: pointer;
}
.ofertas { display: none; margin: var(--e3) 0 0; padding: 0; list-style: none; }
.prato__toggle[aria-expanded="true"] + .ofertas { display: block; }
.oferta {
  display: grid; grid-template-columns: auto 1fr auto auto; align-items: center; gap: var(--e2);
  padding: var(--e2) 0; border-top: 1px solid var(--papel); font-size: 14px;
}
.oferta__num, .prato__onde .oferta__num {
  display: grid; place-items: center; min-width: 26px; height: 22px;
  padding: 0 6px; border-radius: 999px;
  background: var(--dourado); color: #3A2A12;
  font-size: 11px; font-weight: 700; font-variant-numeric: tabular-nums;
}
.oferta__nome { min-width: 0; color: var(--tinta-fraca); line-height: 1.2; }
.oferta__preco { font-weight: 700; font-variant-numeric: tabular-nums; }

/* dentro de uma barraca o preço vai para o topo; repetir o nome dela em cada
   prato seria redundante com a trilha */
body[data-barraca-ativa] .lista .prato__toggle,
body[data-barraca-ativa] .lista .prato__onde,
body[data-barraca-ativa] .lista .ofertas { display: none !important; }

.vazio { padding: var(--e6) 0; text-align: center; color: var(--tinta-fraca); }
.limpar {
  margin-top: var(--e3); padding: 9px var(--e5); font: inherit; font-weight: 700;
  border: 0; border-radius: 999px; background: var(--verde); color: #fff; cursor: pointer;
}

/* ---- convite ---- */
.convite {
  margin-top: var(--e5); padding: var(--e5) var(--e4); border-radius: var(--raio);
  background: var(--verde-fundo); color: var(--papel); text-align: center;
  box-shadow: var(--sombra-3);
}
.convite__titulo {
  margin: 0; font-family: var(--display); font-weight: 400; font-size: 21px;
  line-height: 1.15; color: #fff; text-wrap: balance;
}
.convite__texto { margin: var(--e2) 0 var(--e4); font-size: 14px; opacity: .85; }
.botao-share {
  display: inline-flex; align-items: center; justify-content: center; gap: var(--e2);
  padding: 12px var(--e5); border-radius: 999px; background: var(--cartao);
  color: var(--verde-fundo); font-weight: 700; text-decoration: none;
  /* com zoom alto o rótulo é maior que a tela: quebra em vez de estourar */
  max-width: 100%; overflow-wrap: break-word;
}
.botao-share--icone {
  /* 44x44 é o alvo de toque mínimo recomendado */
  width: 44px; height: 44px; padding: 0; flex: 0 0 auto;
  background: var(--verde); color: #fff;
}

/* ---- rodapé ---- */
.rodape {
  margin-top: var(--e6); padding: var(--e5) var(--e4) var(--e6);
  border-top: 1px solid var(--papel-linha); text-align: center; font-size: 13px;
}
.rodape__local { margin: 0 0 var(--e3); font-weight: 600; }
.rodape__credito { margin: 0 0 var(--e4); }
.rodape__aviso {
  margin: 0; color: var(--tinta-fraca); font-size: 12px; line-height: 1.5;
  max-width: 46ch; margin-inline: auto;
}

@media (prefers-reduced-motion: reduce) {
  * { transition: none !important; animation: none !important; }
}

@media (min-width: 768px) {
  .marca, .ferramentas, main, .rodape { max-width: 780px; margin-inline: auto; }
  .ferramentas { border-radius: 0 0 var(--raio) var(--raio); }
  .marca__logo { height: 72px; }
  .indice { grid-template-columns: 1fr 1fr; }
  .trilha__titulo { font-size: 27px; }
}
"""


JS = r"""(function () {
  'use strict';
  document.documentElement.classList.add('js');

  /* Com scrollRestoration em 'auto' o navegador devolve, ao voltar, a posição
     de rolagem que ele guardou — que pode ser maior que o documento novo,
     porque aqui todas as telas são o mesmo documento com conteúdo trocado. O
     resultado é papel em branco abaixo do rodapé. Assumimos o controle. */
  if ('scrollRestoration' in history) history.scrollRestoration = 'manual';

  var body = document.body,
      lista = document.getElementById('lista'),
      pratos = Array.prototype.slice.call(lista.children),
      idx = { categoria: document.getElementById('idx-categoria'),
              barraca: document.getElementById('idx-barraca'),
              familia: document.getElementById('idx-familia') },
      trilha = document.getElementById('trilha'),
      trilhaTitulo = document.getElementById('trilha-titulo'),
      filtros = document.getElementById('filtros'),
      ordenacao = document.getElementById('ordenacao'),
      contador = document.getElementById('contador'),
      vazio = document.getElementById('vazio'),
      convite = document.querySelector('.convite'),
      busca = document.getElementById('q');

  var nomes = {}, totais = {};
  document.querySelectorAll('#idx-categoria .card').forEach(function (c) {
    nomes['cat:' + c.dataset.cat] = c.querySelector('.card__nome').textContent;
  });
  document.querySelectorAll('#idx-familia .card').forEach(function (c) {
    nomes['fam:' + c.dataset.cat + ':' + c.dataset.fam] =
      c.querySelector('.card__nome').textContent;
  });
  document.querySelectorAll('#idx-barraca .card').forEach(function (c) {
    nomes['barraca:' + c.dataset.barraca] =
      c.querySelector('.card__numero').textContent + ' · ' +
      c.querySelector('.card__nome').textContent;
  });

  var estado = { modo: 'categoria', cat: '', barraca: '', q: '', preco: '', fam: '', ord: 'pop' };
  var FAMILIAS = window.FESTA_FAMILIAS || {};
  var ordAplicada = null;   // reordenar 376 cards só quando a ordem muda

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
    estado.fam = p.get('fam') || '';
    estado.ord = p.get('ord') || 'pop';
    if (p.get('modo') === 'tudo') estado.modo = 'tudo';
  }

  function montarURL() {
    var p = new URLSearchParams();
    if (estado.modo !== 'categoria') p.set('modo', estado.modo);
    if (estado.cat) p.set('cat', estado.cat);
    if (estado.barraca) p.set('barraca', estado.barraca);
    if (estado.q) p.set('q', estado.q);
    if (estado.preco) p.set('preco', estado.preco);
    if (estado.fam) p.set('fam', estado.fam);
    if (estado.ord && estado.ord !== 'pop') p.set('ord', estado.ord);
    var s = p.toString();
    return s ? '?' + s : location.pathname;
  }

  /* Categorias grandes ganham uma parada antes da lista: Massas mostra
     Spaghetti, Penne, Gnocchi… em vez de 84 cards de uma vez. Busca e filtro de
     preço pulam a parada — quem digitou "gnocchi" já disse o que quer. */
  function noIndiceTipos() {
    return estado.modo === 'categoria' && !!estado.cat && !estado.barraca &&
           !estado.fam && !estado.q && !estado.preco && !!FAMILIAS[estado.cat];
  }

  /* Mostrar a lista, e não o índice, quando há busca, filtro de preço, ou
     quando a pessoa entrou numa categoria/barraca. */
  function emLista() {
    if (noIndiceTipos()) return false;
    return !!(estado.q || estado.preco || estado.fam || estado.cat || estado.barraca ||
              estado.modo === 'tudo');
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
      if (ok && estado.fam && estado.fam !== 'todos' &&
          el.dataset.fam !== estado.fam) ok = false;
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

    // a ordem é aplicada por CSS order, sem mexer no DOM
    if (estado.ord !== ordAplicada) {
      var campo = 'ord' + estado.ord.charAt(0).toUpperCase() + estado.ord.slice(1);
      pratos.forEach(function (el) { el.style.order = el.dataset[campo]; });
      ordAplicada = estado.ord;
    }

    var listando = emLista();
    var tipos = noIndiceTipos();
    idx.categoria.hidden = listando || tipos || estado.modo !== 'categoria';
    idx.barraca.hidden = listando || estado.modo !== 'barraca';
    idx.familia.hidden = !tipos;
    if (tipos) {
      idx.familia.querySelectorAll('.card').forEach(function (c) {
        c.hidden = c.dataset.cat !== estado.cat;
      });
    }
    lista.hidden = !listando;
    filtros.hidden = !listando;
    ordenacao.hidden = !listando;
    contador.hidden = !listando;
    vazio.hidden = !listando || visiveis > 0;
    convite.hidden = false;

    contador.textContent = visiveis + (visiveis === 1 ? ' prato' : ' pratos');

    var rotulo = estado.cat ? nomes['cat:' + estado.cat]
               : estado.barraca ? nomes['barraca:' + estado.barraca] : '';
    // o título carrega os dois degraus: de onde veio e onde está
    if (rotulo && estado.cat && estado.fam && estado.fam !== 'todos') {
      rotulo += ' · ' + (nomes['fam:' + estado.cat + ':' + estado.fam] || '');
    }
    trilha.hidden = !rotulo;
    trilhaTitulo.textContent = rotulo || '';

    body.dataset.modo = estado.modo;
    document.querySelectorAll('.modos button').forEach(function (b) {
      b.setAttribute('aria-pressed', String(b.dataset.modo === estado.modo));
    });
    filtros.querySelectorAll('button').forEach(function (b) {
      b.setAttribute('aria-pressed', String(b.dataset.preco === estado.preco));
    });
    ordenacao.querySelectorAll('button').forEach(function (b) {
      b.setAttribute('aria-pressed', String(b.dataset.ord === estado.ord));
    });
    if (busca.value !== estado.q) busca.value = estado.q;

    // se o conteúdo encolheu e a rolagem ficou além do fim, puxa de volta
    var limite = Math.max(0, document.documentElement.scrollHeight - window.innerHeight);
    if (window.scrollY > limite) window.scrollTo(0, limite);
  }

  function guardarRolagem() {
    var atual = history.state || {};
    atual.y = window.scrollY;
    history.replaceState(atual, '', location.href);
  }

  function navegar(push) {
    if (push !== false) {
      var novo = {}; for (var k in estado) novo[k] = estado[k]; novo.y = 0;
      history.pushState(novo, '', montarURL());
    }
    aplicar();
  }

  /* voltar do sistema (Android) e do navegador devolvem ao nível anterior */
  window.addEventListener('popstate', function (ev) {
    lerURL();
    aplicar();
    window.scrollTo(0, (ev.state && ev.state.y) || 0);
  });

  document.querySelectorAll('.modos button').forEach(function (b) {
    b.addEventListener('click', function () {
      guardarRolagem();
      estado.modo = b.dataset.modo;
      estado.cat = estado.barraca = estado.preco = estado.fam = '';
      navegar();
      window.scrollTo(0, 0);
    });
  });

  document.addEventListener('click', function (ev) {
    var card = ev.target.closest('.indice .card');
    if (card) {
      ev.preventDefault();
      guardarRolagem();
      if (card.dataset.fam) {
        estado.cat = card.dataset.cat; estado.fam = card.dataset.fam;
        estado.modo = 'categoria';
      } else if (card.dataset.cat) {
        // o tipo escolhido é de outra categoria: manter filtraria tudo para fora
        estado.cat = card.dataset.cat; estado.fam = ''; estado.modo = 'categoria';
      } else {
        estado.barraca = card.dataset.barraca; estado.fam = ''; estado.modo = 'barraca';
      }
      navegar();
      window.scrollTo(0, 0);
      return;
    }
    var t = ev.target.closest('.prato__toggle');
    if (t) {
      t.setAttribute('aria-expanded', t.getAttribute('aria-expanded') === 'true' ? 'false' : 'true');
      return;
    }
    var o = ev.target.closest('.ordenacao button');
    if (o) {
      estado.ord = o.dataset.ord;
      navegar();
      window.scrollTo(0, 0);
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
      estado.q = ''; estado.preco = ''; estado.fam = '';
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

  /* Monta os links de compartilhamento a partir do <link rel="canonical">.
     Deliberadamente NÃO usa location.pathname: o GitHub segue atendendo o
     caminho antigo depois de um rename, e quem entrasse por ele passaria a
     espalhar o endereço legado. */
  (function share() {
    var canonical = document.querySelector('link[rel="canonical"]');
    var base = canonical ? canonical.href : location.origin + location.pathname;
    var msg = 'Achei um cardápio digital da Festa Italiana de SCS. Dá pra buscar por ' +
              'prato, comparar preço e encontrar a barraca no mapa. Tá me ajudando a ' +
              'decidir o que comer e pode te ajudar também: ' +
              base + '?utm_source=whatsapp&utm_medium=share&utm_campaign=cardapio-33a';
    var href = 'https://wa.me/?text=' + encodeURIComponent(msg);
    document.querySelectorAll('.botao-share').forEach(function (a) { a.href = href; });
  })();

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


JS_MAPA = r"""
/* --- aba do mapa ----------------------------------------------------------
   Roda depois do app: o croqui e montado na primeira vez que a aba abre, e
   passa a acompanhar a busca e o filtro de preco — quem procurou "cannoli" ve
   no mapa so as barracas que tem. */
(function () {
  'use strict';
  var alvo = document.getElementById('mapa-tela'),
      secao = document.getElementById('mapa'),
      lista = document.getElementById('lista'),
      contador = document.getElementById('contador'),
      filtros = document.getElementById('filtros'),
      verNoMapa = document.getElementById('ver-no-mapa'),
      pratos = Array.prototype.slice.call(lista.children),
      croqui = null,
      falhou = false;

  function semAcento(s) {
    return s.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
  }

  function estadoURL() {
    var p = new URLSearchParams(location.search);
    return { modo: p.get('modo') || '', barraca: p.get('barraca') || '',
             q: p.get('q') || '', preco: p.get('preco') || '' };
  }

  function irPara(numero, barraca) {
    var p = new URLSearchParams(location.search);
    p.delete('modo'); p.delete('cat');
    p.set('barraca', (barraca && barraca.chave) || numero);
    // `y` no estado: o app guarda a rolagem ali para restaurar no voltar, e um
    // pushState com estado nulo deixaria esse contrato pela metade
    history.pushState({ y: 0 }, '', '?' + p.toString());
    window.dispatchEvent(new PopStateEvent('popstate'));
    window.scrollTo(0, 0);
  }

  function montar() {
    if (croqui || falhou) return;
    // aba em branco e o pior desfecho: se o croqui nao subir, diz o que houve
    // em vez de mostrar nada e deixar a pessoa achando que o site quebrou
    try {
      croqui = window.FestaMapa.criarCroqui(alvo, window.FESTA_MAPA,
                                            { aoSelecionar: irPara });
    } catch (erro) {
      falhou = true;
      alvo.textContent = 'Não consegui desenhar o mapa neste navegador. '
        + 'A aba Barracas tem a mesma lista.';
      alvo.className = 'mapa__falha';
      if (window.console) console.error('croqui:', erro);
    }
  }

  function sincronizar() {
    var st = estadoURL(), noMapa = st.modo === 'mapa';
    secao.hidden = !noMapa;
    if (!noMapa) { verNoMapa.hidden = !st.barraca; return; }
    verNoMapa.hidden = true;
    lista.hidden = true;
    filtros.hidden = true;
    montar();

    // so a busca guia o mapa. O filtro de preco quase nao separa barraca nenhuma
    // — ate "R$ 10" acende as 35, porque toda barraca vende algo barato —, entao
    // ele nao aparece aqui e tambem nao entra nesta conta, para o que esta aceso
    // corresponder ao que a tela mostra.
    var q = semAcento(st.q.trim()), vistas = {}, n = 0;
    pratos.forEach(function (el) {
      if (q && el.dataset.busca.indexOf(q) === -1) return;
      el.dataset.barracas.trim().split(/\s+/).forEach(function (b) {
        if (!vistas[b]) { vistas[b] = 1; n++; }
      });
    });
    contador.hidden = false;
    if (st.barraca) {
      // olhando UMA barraca: acende so ela. Nao da para usar as barracas dos
      // pratos visiveis — o mesmo prato e vendido em varias, e o mapa acenderia
      // quase todas.
      var b = null;
      window.FESTA_MAPA.barracas.forEach(function (x) { if (x.chave === st.barraca) b = x; });
      if (croqui) { croqui.destacar([st.barraca]); croqui.selecionar(st.barraca); }
      contador.textContent = 'barraca ' + ((b && (b.rotulo || b.numero)) || st.barraca);
      return;
    }
    var filtrando = !!st.q;
    if (croqui) {
      // a seleção é só um reflexo da URL: sem `barraca` nela, nada fica verde.
      // Antes ela era definida e nunca limpa, então ao voltar de uma barraca a
      // pílula continuava acesa sem nada apagado em volta e sem trilha — um
      // estado que não queria dizer coisa nenhuma.
      croqui.selecionar(null);
      croqui.destacar(filtrando ? Object.keys(vistas) : null);
    }
    contador.textContent = filtrando
      ? n + (n === 1 ? ' barraca' : ' barracas')
      : window.FESTA_MAPA.barracas.length + ' barracas no mapa';
  }

  // do prato para o mapa: link de verdade (funciona colado, aberto em aba nova),
  // mas interceptado para nao recarregar a pagina inteira no meio da festa
  document.addEventListener('click', function (ev) {
    var a = ev.target.closest('a[data-ir-mapa]');
    if (!a || ev.metaKey || ev.ctrlKey || ev.shiftKey || ev.button) return;
    ev.preventDefault();
    var p = new URLSearchParams(location.search);
    p.delete('cat');
    p.set('modo', 'mapa');
    p.set('barraca', a.dataset.irMapa);
    history.pushState({ y: 0 }, '', '?' + p.toString());
    window.dispatchEvent(new PopStateEvent('popstate'));
    window.scrollTo(0, 0);
  });

  verNoMapa.addEventListener('click', function () {
    var p = new URLSearchParams(location.search);
    p.set('modo', 'mapa');
    history.pushState({ y: 0 }, '', '?' + p.toString());
    window.dispatchEvent(new PopStateEvent('popstate'));
  });

  window.addEventListener('popstate', sincronizar);
  document.addEventListener('click', function () { setTimeout(sincronizar, 0); });
  document.getElementById('q').addEventListener('input', function () {
    setTimeout(sincronizar, 260);
  });
  sincronizar();
})();
"""


def conferir_juncao(cardapio, mapa):
    """O mapa e o cardapio sao mantidos separados e so se encontram pela chave.

    Ja quebrou uma vez sem ninguem notar: mudou o formato da chave no site e a
    barraca dupla sumiu do mapa. Aqui o build para, em vez de publicar torto.
    """
    site = {chave_barraca(b["numero"]) for b in cardapio["barracas"]}
    geo = {b["chave"] for b in mapa["barracas"]}
    if site != geo:
        so_site, so_mapa = sorted(site - geo), sorted(geo - site)
        raise SystemExit(
            "data/mapa.json e data/cardapio.json nao se juntam mais.\n"
            f"  so no cardapio: {so_site or 'nenhuma'}\n"
            f"  so no mapa:     {so_mapa or 'nenhuma'}")


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

    # Imagem do card de compartilhamento. Precisa ser PNG ou JPEG (WhatsApp não
    # é confiável com WebP em preview) e o logo é composto sobre fundo sólido —
    # ele tem canal alfa e ficaria ilegível sobre o fundo escuro do app.
    cartao = Image.new("RGB", (1200, 630), (239, 228, 212))
    marca = Image.open(origem).convert("RGBA")
    largura = 760
    marca = marca.resize((largura, round(marca.height * largura / marca.width)), Image.LANCZOS)
    cartao.paste(marca, ((1200 - marca.width) // 2, (630 - marca.height) // 2 - 24), marca)
    faixa = Image.new("RGB", (1200, 26), (8, 53, 26))
    cartao.paste(faixa, (0, 630 - 26))
    og = destino / "og.png"
    cartao.save(og, "PNG", optimize=True)

    # a display é self-hosted: sem requisição externa e sem fallback silencioso
    fontes = destino / "fonts"
    fontes.mkdir(exist_ok=True)
    for f in (RAIZ / "assets" / "fonts").iterdir():
        shutil.copy2(f, fontes / f.name)
    return origem.stat().st_size, saida.stat().st_size, og.stat().st_size


def main():
    cardapio, categorias, evento = carregar()
    ids = {i["id"] for b in cardapio["barracas"] for i in b["itens"]}
    orfas = set(EXPANSAO_MANUAL) - ids
    if orfas:
        raise SystemExit(f"EXPANSAO_MANUAL aponta para id inexistente: {sorted(orfas)}")
    mapa, fontes_mapa = ler_mapa()
    pratos = agrupar_pratos(cardapio, categorias)
    conferir_juncao(cardapio, mapa)

    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir(parents=True)

    fam_catalogo, fam_de_titulo = mapear_familias(pratos)
    mapa_js = ("window.FESTA_MAPA = "
               + json.dumps(mapa, ensure_ascii=False, separators=(",", ":")) + ";\n"
               + "window.FESTA_FAMILIAS = "
               + json.dumps(fam_catalogo, ensure_ascii=False, separators=(",", ":")) + ";\n")
    css_txt = CSS + CSS_ONDE + CSS_MAPA
    js_txt = mapa_js + JS + fontes_mapa + JS_MAPA
    # style.css e app.js tem nome fixo, entao quem ja visitou o site pode receber
    # o index.html novo com o app.js velho do cache — foi o que fez a aba Mapa
    # aparecer sem nada dentro. A assinatura do conteudo na URL corta isso.
    versao = {k: hashlib.sha256(t.encode("utf-8")).hexdigest()[:10]
              for k, t in (("css", css_txt), ("js", js_txt))}

    (DIST / "index.html").write_text(
        render_html(cardapio, categorias, evento, pratos, mapa, versao,
                    fam_catalogo, fam_de_titulo),
        encoding="utf-8")
    (DIST / "style.css").write_text(css_txt, encoding="utf-8")
    (DIST / "app.js").write_text(js_txt, encoding="utf-8")
    (DIST / ".nojekyll").write_text("", encoding="utf-8")
    antes, depois, tam_og = otimizar_assets()

    itens = sum(len(b["itens"]) for b in cardapio["barracas"])
    linhas = sum(len(p["ofertas"]) for p in pratos)
    kb = lambda p: p.stat().st_size / 1024
    print(f"{itens} itens do PDF -> {linhas} linhas (variações expandidas) "
          f"em {len(pratos)} pratos, {len(cardapio['barracas'])} barracas")
    print(f"  index.html  {kb(DIST/'index.html'):7.1f} KB")
    print(f"  style.css   {kb(DIST/'style.css'):7.1f} KB")
    print(f"  app.js      {kb(DIST/'app.js'):7.1f} KB")
    print(f"  logo.webp   {depois/1024:7.1f} KB  (era {antes/1024:.1f} KB PNG)")
    print(f"  og.png      {tam_og/1024:7.1f} KB  (card do WhatsApp, 1200x630)")


if __name__ == "__main__":
    main()
