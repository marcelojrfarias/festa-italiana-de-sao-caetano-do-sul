#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Extrai o cardápio da 33ª Festa Italiana de São Caetano do Sul para JSON.

A extração não depende de heurísticas de texto: ela usa a semântica visual do
PDF (fonte + cor de cada span), que é consistente nas 58 páginas do arquivo.

    Hermann-Black  #196B24  -> cabeçalho da barraca (número / nome / região)
    Arial-Bold     #EE0000  -> título da categoria
    Arial-Bold     #196B24  -> nome do prato, ou o preço quando começa com "R$"
    regular        #000000  -> descrição do prato

Uso:
    python3 scripts/extract_menu.py [caminho/do/cardapio.pdf]
"""
from __future__ import annotations

import json
import re
import sys
import unicodedata
from pathlib import Path

import pymupdf

RAIZ = Path(__file__).resolve().parent.parent
PDF_PADRAO = RAIZ / "docs" / "cardapio-33a-festa-italiana.pdf"
SAIDA = RAIZ / "data" / "cardapio.json"

VERDE = 0x196B24  # nome da barraca, título do prato e preço
VERMELHO = 0xEE0000  # título da categoria
PRETO = 0x000000  # descrição do prato

PRECO_RE = re.compile(r"^R\$\s*([\d.]+),(\d{2})$")
REGIAO_RE = re.compile(r"^Regi[ãa]o\s*[-–—]\s*(.+)$")

# Rótulos como aparecem no PDF -> categoria canônica. O PDF tem pequenas
# variações de digitação ("Porzioni - Porções", "Fogazza / Fogazza") que são
# normalizadas aqui sem perder o rótulo original de cada item.
CATEGORIAS = {
    "Antipasti – Entradas": ("antipasti", "Antipasti", "Entradas"),
    "Accompagnamenti – Acompanhamento": (
        "accompagnamenti",
        "Accompagnamenti",
        "Acompanhamentos",
    ),
    "Secondi Piatti – Pratos Principais": (
        "secondi_piatti",
        "Secondi Piatti",
        "Pratos Principais",
    ),
    "Porzioni – Porções": ("porzioni", "Porzioni", "Porções"),
    "Porzioni - Porções": ("porzioni", "Porzioni", "Porções"),
    "Panini – Lanches": ("panini", "Panini", "Lanches"),
    "Fogazza": ("fogazza", "Fogazza", "Fogazza"),
    "Fogazza / Fogazza": ("fogazza", "Fogazza", "Fogazza"),
    "Pizza": ("pizza", "Pizza", "Pizza"),
    "Pizza / Pizza": ("pizza", "Pizza", "Pizza"),
    "Insalata – Salada": ("insalata", "Insalata", "Salada"),
    "Dolci – Doces": ("dolci", "Dolci", "Doces"),
    "Gelato – Sorvete": ("gelato", "Gelato", "Sorvete"),
    "Bevande – Bebidas": ("bevande", "Bevande", "Bebidas"),
    "Menù Vegano – Menu Vegano": ("menu_vegano", "Menù Vegano", "Menu Vegano"),
    "Menu Completo – Combo": ("menu_completo", "Menu Completo", "Combo"),
}

# O PDF grafa algumas regiões de formas diferentes ("Friuli-Venezia Giulia" e
# "Friuli – Venezia Giulia"); aqui elas voltam ao nome oficial em italiano.
REGIOES = {
    "emilia-romagna": "Emilia-Romagna",
    "friuli-venezia-giulia": "Friuli-Venezia Giulia",
    "trentino-alto-adige": "Trentino-Alto Adige",
    "valle-d-aosta": "Valle d'Aosta",
}

# ordem em que as categorias aparecem no cardápio impresso
ORDEM_CATEGORIAS = [
    "antipasti",
    "accompagnamenti",
    "secondi_piatti",
    "fogazza",
    "pizza",
    "porzioni",
    "panini",
    "insalata",
    "menu_vegano",
    "menu_completo",
    "dolci",
    "gelato",
    "bevande",
]


def norm(texto: str) -> str:
    return re.sub(r"\s+", " ", texto.replace("\xa0", " ")).strip()


def slug(texto: str) -> str:
    texto = texto.replace("’", " ").replace("'", " ")
    ascii_ = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", ascii_.lower())).strip("-")


def spans_da_pagina(pagina) -> list[dict]:
    """Spans com texto, em ordem de leitura, unindo pedaços da mesma linha."""
    brutos = []
    for bloco in pagina.get_text("dict")["blocks"]:
        for linha in bloco.get("lines", []):
            for span in linha["spans"]:
                texto = norm(span["text"])
                if texto:
                    brutos.append(
                        {
                            "texto": texto,
                            "fonte": span["font"],
                            "cor": span["color"],
                            "y": round(span["bbox"][1], 1),
                            "x": round(span["bbox"][0], 1),
                            "negrito": "Bold" in span["font"],
                        }
                    )
    brutos.sort(key=lambda s: (s["y"], s["x"]))

    unidos: list[dict] = []
    for span in brutos:
        anterior = unidos[-1] if unidos else None
        mesma_linha = (
            anterior is not None
            and abs(anterior["y"] - span["y"]) < 2
            and anterior["fonte"] == span["fonte"]
            and anterior["cor"] == span["cor"]
            # o preço divide a linha com o título do prato: nunca juntar os dois
            and not PRECO_RE.match(span["texto"])
            and not PRECO_RE.match(anterior["texto"])
        )
        if mesma_linha:
            anterior["texto"] = norm(anterior["texto"] + " " + span["texto"])
        else:
            unidos.append(dict(span))
    return unidos


def classificar(span: dict) -> str:
    if "Hermann" in span["fonte"]:
        return "cabecalho"
    if span["negrito"] and span["cor"] == VERMELHO:
        return "categoria"
    if span["negrito"] and span["cor"] == VERDE:
        return "preco" if PRECO_RE.match(span["texto"]) else "prato"
    if not span["negrito"] and span["cor"] == PRETO:
        return "descricao"
    return "outro"


def para_centavos(texto: str) -> int:
    m = PRECO_RE.match(texto)
    return int(m.group(1).replace(".", "")) * 100 + int(m.group(2))


def ler_cabecalho(linhas: list[str]) -> tuple[str, list[int], str, str]:
    """['1', 'Nome', 'Região – Veneto'] -> (rótulo, números, nome, região)."""
    numero, regiao, nome = None, None, []
    for i, linha in enumerate(linhas):
        if i == 0:
            m = re.match(r"^(\d+(?:\s*/\s*\d+)*)\s*(?:[-–—]\s*(.*))?$", linha)
            if m:
                numero = re.sub(r"\s+", "", m.group(1))
                if m.group(2):
                    nome.append(m.group(2).strip())
                continue
        m = REGIAO_RE.match(linha)
        if m:
            regiao = norm(m.group(1))
            continue
        nome.append(linha)
    numeros = [int(n) for n in numero.split("/")] if numero else []
    return numero, numeros, norm(" ".join(nome)), regiao


def volume_ml(texto: str) -> int | None:
    """Volume declarado na descrição da bebida, em mililitros."""
    m = re.search(r"(\d+(?:[.,]\d+)?)\s*(ml|l\b|litros?)", texto, re.I)
    if not m:
        return None
    valor = float(m.group(1).replace(",", "."))
    return int(valor * 1000) if m.group(2).lower().startswith("l") else int(valor)


def unidades(texto: str) -> int | None:
    m = re.search(r"(\d+)\s*(?:unidades?|unità)", texto, re.I)
    return int(m.group(1)) if m else None


def extrair(caminho_pdf: Path) -> dict:
    doc = pymupdf.open(caminho_pdf)
    barracas: list[dict] = []
    cabecalho: list[str] = []
    barraca = categoria = prato = None

    def fechar_cabecalho():
        nonlocal cabecalho, barraca, categoria, prato
        if not cabecalho:
            return
        rotulo, numeros, nome, regiao = ler_cabecalho(cabecalho)
        cabecalho = []
        regiao_id = slug(regiao)
        barraca = {
            "numero": rotulo,
            "numeros": numeros,
            "nome": nome,
            "slug": slug(nome),
            "regiao_id": regiao_id,
            "regiao_italiana": REGIOES.get(regiao_id, regiao),
            "regiao_rotulo_pdf": regiao,
            "itens": [],
        }
        barracas.append(barraca)
        categoria = prato = None

    for n_pagina, pagina in enumerate(doc, start=1):
        if n_pagina == 1:  # capa
            continue
        for span in spans_da_pagina(pagina):
            tipo = classificar(span)
            if tipo == "cabecalho":
                cabecalho.append(span["texto"])
                continue
            fechar_cabecalho()
            if tipo == "categoria":
                categoria = span["texto"]
                prato = None
            elif tipo == "prato":
                # títulos longos quebram em várias linhas; como todo prato do
                # cardápio tem descrição, um título antes dela é continuação
                if prato is not None and not prato["descricao"]:
                    prato["titulo"] = norm(prato["titulo"] + " " + span["texto"])
                    continue
                canonica = CATEGORIAS[categoria]
                prato = {
                    "titulo": span["texto"],
                    "descricao": "",
                    "preco_centavos": None,
                    "categoria_id": canonica[0],
                    "categoria_it": canonica[1],
                    "categoria_pt": canonica[2],
                    "categoria_rotulo_pdf": categoria,
                    "pagina_pdf": n_pagina,
                }
                barraca["itens"].append(prato)
            elif tipo == "preco":
                if prato is not None and prato["preco_centavos"] is None:
                    prato["preco_centavos"] = para_centavos(span["texto"])
            elif tipo == "descricao":
                if prato is not None:
                    prato["descricao"] = norm(prato["descricao"] + " " + span["texto"])
        fechar_cabecalho()

    for b in barracas:
        precos = []
        for i, item in enumerate(b["itens"], start=1):
            centavos = item.pop("preco_centavos")
            precos.append(centavos)
            texto = "%s %s" % (item["titulo"], item["descricao"])
            item["id"] = "%s-%02d-%s" % (
                slug(b["numero"].replace("/", "-")),
                i,
                slug(item["titulo"])[:60],
            )
            item["preco"] = round(centavos / 100, 2)
            item["preco_formatado"] = "R$ %d,%02d" % (centavos // 100, centavos % 100)
            item["volume_ml"] = volume_ml(item["descricao"])
            item["unidades"] = unidades(texto)
            item["vegano"] = bool(re.search(r"\bveg[ae]n[oa]s?\b", texto, re.I))
            item["variacoes"] = (
                [norm(p) for p in item["titulo"].split(" / ")]
                if " / " in item["titulo"]
                else []
            )
            # ordem estável das chaves
            for chave in (
                "titulo",
                "descricao",
                "preco",
                "preco_formatado",
                "categoria_id",
                "categoria_it",
                "categoria_pt",
                "categoria_rotulo_pdf",
                "variacoes",
                "volume_ml",
                "unidades",
                "vegano",
                "pagina_pdf",
            ):
                item[chave] = item.pop(chave)
        vistas = []
        for item in b["itens"]:
            if item["categoria_id"] not in vistas:
                vistas.append(item["categoria_id"])
        b["categorias"] = vistas
        b["total_itens"] = len(b["itens"])
        b["preco_min"] = round(min(precos) / 100, 2)
        b["preco_max"] = round(max(precos) / 100, 2)

    itens = [i for b in barracas for i in b["itens"]]
    usadas = {i["categoria_id"] for i in itens}
    catalogo = []
    for cid in ORDEM_CATEGORIAS:
        if cid not in usadas:
            continue
        it, pt = next((v[1], v[2]) for v in CATEGORIAS.values() if v[0] == cid)
        catalogo.append(
            {
                "id": cid,
                "nome_it": it,
                "nome_pt": pt,
                "rotulos_no_pdf": sorted(
                    {i["categoria_rotulo_pdf"] for i in itens if i["categoria_id"] == cid}
                ),
                "total_itens": sum(1 for i in itens if i["categoria_id"] == cid),
            }
        )

    return {
        "evento": {
            "nome": "33ª Festa Italiana",
            "edicao": 33,
            "cidade": "São Caetano do Sul",
            "estado": "SP",
            "pais": "Brasil",
            "realizacao": [
                "Prefeitura de São Caetano do Sul",
                "Fundo Social de Solidariedade de São Caetano do Sul",
            ],
            "moeda": "BRL",
            "fonte": {
                "arquivo": caminho_pdf.name,
                "titulo": "Menu / Cardápio",
                "paginas": doc.page_count,
            },
        },
        "resumo": {
            "total_barracas": len(barracas),
            "total_itens": len(itens),
            "preco_min": min(i["preco"] for i in itens),
            "preco_max": max(i["preco"] for i in itens),
            "total_regioes_italianas": len({b["regiao_id"] for b in barracas}),
            "regioes_italianas": sorted({b["regiao_italiana"] for b in barracas}),
        },
        "categorias": catalogo,
        "barracas": barracas,
    }


def main() -> None:
    pdf = Path(sys.argv[1]) if len(sys.argv) > 1 else PDF_PADRAO
    dados = extrair(pdf)
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    SAIDA.write_text(
        json.dumps(dados, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        "%s: %d barracas, %d itens"
        % (SAIDA.name, dados["resumo"]["total_barracas"], dados["resumo"]["total_itens"])
    )


if __name__ == "__main__":
    main()
