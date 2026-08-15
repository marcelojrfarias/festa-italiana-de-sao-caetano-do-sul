#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Extrai a identidade visual do PDF do cardápio para data/identidade-visual.json.

As cores de texto, as fontes e as cores vetoriais são medidas diretamente no
PDF (contagem de caracteres por estilo e por cor). As cores das ilustrações
(logo, fundo) são amostradas dos bitmaps embutidos. O papel de cada cor/fonte
no layout — "título do prato", "cabeçalho de categoria" etc. — vem da leitura
do documento e está anotado abaixo.

Uso:
    python3 scripts/extract_identity.py [caminho/do/cardapio.pdf]
"""
from __future__ import annotations

import collections
import json
import sys
from pathlib import Path

import pymupdf

RAIZ = Path(__file__).resolve().parent.parent
PDF_PADRAO = RAIZ / "docs" / "cardapio-33a-festa-italiana.pdf"
SAIDA = RAIZ / "data" / "identidade-visual.json"

PAPEL_DAS_CORES = {
    "#196B24": ("verde-festa", "Nome e número da barraca, título do prato e preço"),
    "#EE0000": ("vermelho-festa", "Cabeçalho de categoria (Antipasti, Dolci, ...)"),
    "#000000": ("preto-texto", "Descrição do prato em português"),
    "#095A34": ("verde-escuro", "Título MENU / CARDÁPIO na capa"),
}

PAPEL_DAS_FONTES = {
    "Hermann-Black": (
        "display",
        "Nome e número da barraca, região e o título MENU / CARDÁPIO",
        "Fonte embutida no PDF (subconjunto JAMCWA+Hermann-Black), serifada "
        "condensada de peso Black",
    ),
    "Arial-BoldMT": (
        "titulo",
        "Título do prato, preço e cabeçalho de categoria",
        "Arial Bold; equivalentes livres: Liberation Sans Bold, Arimo Bold, Inter Bold",
    ),
    "Calibri": (
        "corpo",
        "Descrição do prato (fonte predominante nas descrições)",
        "Calibri; equivalentes livres: Carlito, Lato",
    ),
    "ArialMT": ("corpo", "Descrição do prato em parte das páginas", "Arial Regular"),
    "TimesNewRomanPSMT": ("corpo", "Uso pontual em descrições", "Times New Roman"),
}


def hexa(inteiro: int) -> str:
    return "#%06X" % inteiro


def cor_dominante(caminho: Path) -> str:
    pix = pymupdf.Pixmap(caminho)
    if pix.alpha:
        pix = pymupdf.Pixmap(pix, 0)
    _, pixel = pix.color_topusage()
    return "#%02X%02X%02X" % tuple(pixel[:3])


def medir(doc: pymupdf.Document) -> tuple[collections.Counter, collections.Counter, collections.Counter]:
    cores, fontes, vetores = (collections.Counter() for _ in range(3))
    for pagina in doc:
        for bloco in pagina.get_text("dict")["blocks"]:
            for linha in bloco.get("lines", []):
                for span in linha["spans"]:
                    texto = span["text"].strip()
                    if not texto:
                        continue
                    cores[hexa(span["color"])] += len(texto)
                    fontes[span["font"]] += len(texto)
        for desenho in pagina.get_drawings():
            if desenho.get("fill"):
                rgb = tuple(int(round(c * 255)) for c in desenho["fill"])
                vetores["#%02X%02X%02X" % rgb] += 1
    return cores, fontes, vetores


def main() -> None:
    pdf = Path(sys.argv[1]) if len(sys.argv) > 1 else PDF_PADRAO
    doc = pymupdf.open(pdf)
    cores, fontes, vetores = medir(doc)
    assets = RAIZ / "assets"

    paleta = []
    for cor, (nome, papel) in PAPEL_DAS_CORES.items():
        paleta.append(
            {
                "nome": nome,
                "hex": cor,
                "papel": papel,
                "caracteres_no_pdf": cores.get(cor, 0),
            }
        )
    paleta += [
        {
            "nome": "verde-logo",
            "hex": "#0F7645",
            "papel": "Verde da marca: igreja, arco e palavra “Festa/Italiana” no logo",
            "caracteres_no_pdf": 0,
        },
        {
            "nome": "vermelho-logo",
            "hex": "#BB2121",
            "papel": "Vermelho da marca: “33ª”, arco e coração do logo; aba lateral direita",
            "caracteres_no_pdf": 0,
        },
        {
            "nome": "bege-fundo",
            "hex": cor_dominante(assets / "textura-fundo.jpg")
            if (assets / "textura-fundo.jpg").exists()
            else "#E5B67E",
            "papel": "Fundo de estuque/terracota das páginas",
            "caracteres_no_pdf": 0,
        },
        {
            "nome": "branco-cartao",
            "hex": "#FFFFFF",
            "papel": "Cartão branco arredondado onde o cardápio é impresso",
            "caracteres_no_pdf": 0,
        },
    ]

    tipografia = []
    for fonte, (papel, uso, nota) in PAPEL_DAS_FONTES.items():
        if fontes.get(fonte):
            tipografia.append(
                {
                    "familia": fonte,
                    "papel": papel,
                    "uso": uso,
                    "observacao": nota,
                    "caracteres_no_pdf": fontes[fonte],
                    "embutida_no_pdf": fonte == "Hermann-Black",
                }
            )
    tipografia.sort(key=lambda f: -f["caracteres_no_pdf"])

    dados = {
        "evento": "33ª Festa Italiana — São Caetano do Sul",
        "origem": {
            "arquivo": pdf.name,
            "paginas": doc.page_count,
            "metodo": "cores e fontes medidas span a span no PDF; cores de "
            "ilustração amostradas dos bitmaps embutidos",
        },
        "paleta": paleta,
        "tipografia": tipografia,
        "escala_tipografica_pt": {
            "capa_menu": 67.2,
            "capa_cardapio": 39.7,
            "barraca_nome": 16.8,
            "prato_titulo": 11.0,
            "categoria": 10.2,
            "descricao": 9.4,
        },
        "logo": {
            "arquivo": "assets/logo-festa-italiana.png",
            "dimensoes_px": [742, 386],
            "descricao": "Marca da 33ª Festa Italiana: silhueta da Igreja Matriz "
            "de São Caetano dentro de um arco verde-e-vermelho, chapéu de chef, "
            "numeral “33ª” em vermelho, palavra “Festa” em capitulares serifadas, "
            "“Italiana” em manuscrita, bandeira da Itália e assinatura "
            "“SÃO CAETANO DO SUL”.",
            "cores_principais": ["#0F7645", "#BB2121", "#FFFFFF"],
            "fundo": "transparente (PNG com canal alfa)",
        },
        "elementos_graficos": [
            {
                "arquivo": "assets/textura-fundo.jpg",
                "uso": "Fundo das páginas internas (estuque bege + parede de tijolos)",
            },
            {
                "arquivo": "assets/textura-fundo-capa.jpg",
                "uso": "Fundo da capa (parede de tijolos)",
            },
            {
                "arquivo": "assets/spaghetti.png",
                "uso": "Espaguete ilustrado nas bordas inferiores",
            },
            {
                "arquivo": "assets/faixa-patrocinadores.png",
                "uso": "Faixa de patrocinadores no rodapé das páginas internas",
            },
            {
                "arquivo": "assets/selos-institucionais.png",
                "uso": "Selos da Prefeitura e do Fundo Social de Solidariedade",
            },
            {
                "arquivo": "assets/capa.jpg",
                "uso": "Capa renderizada do cardápio",
            },
        ],
        "motivos_visuais": [
            "Parreira com cachos de uva e lâmpadas de varal no topo de cada página",
            "Parede de tijolos aparentes nas laterais",
            "Cartão branco de cantos arredondados sobre o fundo bege",
            "Abas laterais verde (esquerda) e vermelha (direita) na altura do rodapé",
            "Massa de espaguete ilustrada no canto inferior",
            "Bandeira da Itália e chapéu de chef como assinatura da marca",
        ],
        "layout_pagina": {
            "formato": "A4 retrato (595 x 842 pt)",
            "cartao_conteudo_pt": [45, 156, 550, 746],
            "aba_lateral_esquerda": {"cor": "#0B7646", "rect_pt": [-16, 402, 108, 422]},
            "aba_lateral_direita": {"cor": "#BB2121", "rect_pt": [486, 402, 609, 422]},
            "estrutura_do_item": "título do prato à esquerda em verde/negrito, preço "
            "alinhado à direita em coluna própria e descrição em preto logo abaixo "
            "do título",
        },
        "vetores_mais_usados": [
            {"hex": cor, "ocorrencias": n} for cor, n in vetores.most_common(6)
        ],
    }

    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    SAIDA.write_text(
        json.dumps(dados, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print("%s: %d cores, %d fontes" % (SAIDA.name, len(paleta), len(tipografia)))


if __name__ == "__main__":
    main()
