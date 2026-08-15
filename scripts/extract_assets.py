#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Extrai os elementos gráficos da identidade visual do PDF do cardápio.

Salva em assets/:
  logo-festa-italiana.png   marca da 33ª Festa Italiana (com transparência)
  spaghetti.png             ilustração de espaguete usada nas bordas
  textura-fundo.jpg         fundo bege/estuque das páginas internas
  textura-fundo-capa.jpg    fundo de tijolos da capa
  faixa-patrocinadores.png  faixa de logos no rodapé das páginas internas
  selos-institucionais.png  Prefeitura + Fundo Social (recorte da capa)
  capa.jpg                  capa renderizada, para referência

Uso:
    python3 scripts/extract_assets.py [caminho/do/cardapio.pdf]
"""
from __future__ import annotations

import sys
from pathlib import Path

import pymupdf

RAIZ = Path(__file__).resolve().parent.parent
PDF_PADRAO = RAIZ / "docs" / "cardapio-33a-festa-italiana.pdf"
ASSETS = RAIZ / "assets"

# imagens embutidas identificadas por dimensão (largura, altura) em pixels
POR_DIMENSAO = {
    (742, 386): "logo-festa-italiana.png",
    (738, 541): "spaghetti.png",
    (1738, 1175): "textura-fundo.jpg",
    (855, 580): "textura-fundo-capa.jpg",
    (1361, 99): "faixa-patrocinadores.png",
}

# recortes da capa (pontos PDF: x0, y0, x1, y1)
RECORTES = {
    "selos-institucionais.png": (165, 272, 450, 318),
}


def salvar_imagem(doc: pymupdf.Document, xref: int, smask: int, destino: Path) -> None:
    pix = pymupdf.Pixmap(doc, xref)
    if pix.colorspace and pix.colorspace.n == 4:  # CMYK
        pix = pymupdf.Pixmap(pymupdf.csRGB, pix)
    if smask and destino.suffix == ".png":
        pix = pymupdf.Pixmap(pix, pymupdf.Pixmap(doc, smask))
    destino.write_bytes(pix.tobytes(destino.suffix.lstrip(".")))
    print("  %-26s %dx%d" % (destino.name, pix.width, pix.height))


def main() -> None:
    pdf = Path(sys.argv[1]) if len(sys.argv) > 1 else PDF_PADRAO
    doc = pymupdf.open(pdf)
    ASSETS.mkdir(parents=True, exist_ok=True)
    print("assets/")

    pendentes = dict(POR_DIMENSAO)
    for n_pagina in (1, 2):
        for img in doc[n_pagina - 1].get_images(full=True):
            xref, smask, largura, altura = img[0], img[1], img[2], img[3]
            nome = pendentes.pop((largura, altura), None)
            if nome:
                salvar_imagem(doc, xref, smask, ASSETS / nome)
    for dimensao, nome in pendentes.items():
        print("  AVISO: imagem %s (%s) não encontrada" % (nome, dimensao))

    capa = doc[0]
    for nome, caixa in RECORTES.items():
        pix = capa.get_pixmap(dpi=300, clip=pymupdf.Rect(*caixa))
        (ASSETS / nome).write_bytes(pix.tobytes("png"))
        print("  %-26s %dx%d" % (nome, pix.width, pix.height))

    pix = capa.get_pixmap(dpi=150)
    (ASSETS / "capa.jpg").write_bytes(pix.tobytes("jpg"))
    print("  %-26s %dx%d" % ("capa.jpg", pix.width, pix.height))


if __name__ == "__main__":
    main()
