#!/usr/bin/env python3
"""Aponta itens do cardápio que talvez precisem de linha em data/expansao.json.

A expansão é decidida à mão, item a item, porque o cardápio não segue regra —
ver o comentário em build_site.py. Esta é a rede de proteção para quando o
cardápio mudar: heurística aqui só levanta a mão, nunca transforma nada. Falso
alarme custa uma olhada; falso silêncio custa um prato errado no ar por semanas,
que é o que já aconteceu.

Sai com erro quando algum item tem cara de enumerar sabor e não está na tabela.
Se for alarme falso, a saída é registrar o item na tabela com a linha única que
ele já tem — decisão registrada vale mais que exceção no código.
"""
import json
import pathlib
import re
import sys
import unicodedata

RAIZ = pathlib.Path(__file__).resolve().parent.parent
DADOS = RAIZ / "data"


def sem_acento(s):
    return "".join(c for c in unicodedata.normalize("NFD", s or "")
                   if unicodedata.category(c) != "Mn").lower()


# Cada sinal aponta uma forma de enumerar que o cardápio já usou.
SINAIS = [
    # "(1/2 Garrafa)" tem barra e não é enumeração
    ("barra no título", lambda t, d: "/" in re.sub(r"\d\s*/\s*\d", "", t)),
    ("travessão e vírgula no título", lambda t, d: ("–" in t or " - " in t) and "," in t),
    ('"sabores" no plural na descrição', lambda t, d: re.search(r"\bsabores\b", sem_acento(d))),
    ("título de embalagem com lista na descrição",
     lambda t, d: sem_acento(t).split(" ")[0] in {"refrigerante", "cerveja", "agua", "suco", "h2o"}
                  and re.search(r"[/–]| e ", d or "")),
]


def main():
    cardapio = json.loads((DADOS / "cardapio.json").read_text(encoding="utf-8"))
    expansao = json.loads((DADOS / "expansao.json").read_text(encoding="utf-8"))["itens"]

    suspeitos = []
    for barraca in cardapio["barracas"]:
        for item in barraca["itens"]:
            if item["id"] in expansao:
                continue
            achados = [nome for nome, teste in SINAIS
                       if teste(item["titulo"], item["descricao"] or "")]
            if achados:
                suspeitos.append((barraca["numero"], item, achados))

    total = sum(len(b["itens"]) for b in cardapio["barracas"])
    print(f"{total} itens no cardápio, {len(expansao)} com expansão decidida.")
    if not suspeitos:
        print("Nenhum item fora da tabela tem cara de enumerar sabor.")
        return 0

    print(f"\n{len(suspeitos)} item(ns) para decidir à mão:\n")
    for numero, item, achados in suspeitos:
        print(f"  [{numero}] {item['id']}")
        print(f"        {item['titulo']}")
        print(f"        {item['descricao']}")
        print(f"        sinal: {', '.join(achados)}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
