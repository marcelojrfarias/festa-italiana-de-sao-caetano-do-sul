#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Confere data/cardapio.json contra o PDF original.

Checagens:
  1. todo item tem título, descrição, preço e categoria;
  2. o multiconjunto de preços do JSON é idêntico ao do texto bruto do PDF
     (mesmo valor, mesma quantidade de ocorrências) — pega item perdido,
     duplicado ou com preço trocado;
  3. todo título e toda descrição existem literalmente no texto do PDF —
     pega texto inventado, truncado ou concatenado errado;
  4. todo nome/número/região de barraca aparece no texto do PDF;
  5. números das barracas formam a sequência 1..36 sem buracos;
  6. ids de item são únicos e preços estão numa faixa plausível.

Uso:
    python3 scripts/validate_menu.py [caminho/do/cardapio.pdf]
"""
from __future__ import annotations

import collections
import json
import re
import sys
from pathlib import Path

import pymupdf

RAIZ = Path(__file__).resolve().parent.parent
PDF_PADRAO = RAIZ / "docs" / "cardapio-33a-festa-italiana.pdf"
JSON = RAIZ / "data" / "cardapio.json"


def norm(texto: str) -> str:
    return re.sub(r"\s+", " ", texto.replace("\xa0", " ")).strip()


def main() -> int:
    pdf = Path(sys.argv[1]) if len(sys.argv) > 1 else PDF_PADRAO
    dados = json.loads(JSON.read_text(encoding="utf-8"))
    doc = pymupdf.open(pdf)
    bruto = norm(" ".join(pagina.get_text() for pagina in doc))

    itens = [(b, i) for b in dados["barracas"] for i in b["itens"]]
    erros: list[str] = []

    def checar(condicao: bool, mensagem: str) -> None:
        if not condicao:
            erros.append(mensagem)

    # 1. campos obrigatórios
    for b, item in itens:
        for campo in ("titulo", "descricao", "preco", "categoria_id"):
            checar(
                bool(item.get(campo)),
                "barraca %s: item %r sem %s" % (b["numero"], item["titulo"], campo),
            )

    # 2. preços: multiconjunto JSON == multiconjunto PDF
    precos_pdf = collections.Counter(re.findall(r"R\$\s*([\d.]+,\d{2})", bruto))
    precos_json = collections.Counter(
        "%d,%02d" % divmod(round(i["preco"] * 100), 100) for _, i in itens
    )
    for valor in sorted(set(precos_pdf) | set(precos_json)):
        checar(
            precos_pdf[valor] == precos_json[valor],
            "preço R$ %s: %d no PDF, %d no JSON"
            % (valor, precos_pdf[valor], precos_json[valor]),
        )

    # 3. textos literais
    for b, item in itens:
        for campo in ("titulo", "descricao"):
            checar(
                norm(item[campo]) in bruto,
                "barraca %s: %s ausente do PDF: %r"
                % (b["numero"], campo, item[campo]),
            )

    # 4/5. barracas
    numeros: list[int] = []
    for b in dados["barracas"]:
        checar(norm(b["nome"]) in bruto, "nome fora do PDF: %r" % b["nome"])
        checar(
            norm(b["regiao_rotulo_pdf"]) in bruto,
            "região fora do PDF: %r" % b["regiao_rotulo_pdf"],
        )
        checar(
            len(b["itens"]) == b["total_itens"],
            "barraca %s: total_itens inconsistente" % b["numero"],
        )
        numeros.extend(b["numeros"])
    checar(
        numeros == list(range(1, max(numeros) + 1)),
        "numeração das barracas com falha: %s" % numeros,
    )

    # 6. ids e faixa de preço
    ids = [i["id"] for _, i in itens]
    duplicados = [k for k, v in collections.Counter(ids).items() if v > 1]
    checar(not duplicados, "ids repetidos: %s" % duplicados[:5])
    fora = [i["titulo"] for _, i in itens if not 1 <= i["preco"] <= 200]
    checar(not fora, "preços fora da faixa esperada: %s" % fora[:5])
    checar(
        len(itens) == dados["resumo"]["total_itens"]
        and len(dados["barracas"]) == dados["resumo"]["total_barracas"],
        "resumo inconsistente com os dados",
    )

    print("PDF ............. %s (%d páginas)" % (pdf.name, doc.page_count))
    print("barracas ........ %d" % len(dados["barracas"]))
    print("itens ........... %d" % len(itens))
    print("preços no PDF ... %d" % sum(precos_pdf.values()))
    print("regiões ......... %d" % dados["resumo"]["total_regioes_italianas"])
    if erros:
        print("\nFALHAS (%d):" % len(erros))
        for e in erros[:40]:
            print("  -", e)
        return 1
    print("\nOK: todas as checagens passaram.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
