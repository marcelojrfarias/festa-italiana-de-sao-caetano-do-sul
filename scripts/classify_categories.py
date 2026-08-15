#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Classifica os 645 itens do cardápio nas categorias de navegação do site.

As categorias impressas no PDF são italianas e desbalanceadas para navegar:
"Secondi Piatti" sozinha tem 160 itens e mistura massa, carne e pizza, enquanto
"Insalata" tem 1. Este script reagrupa tudo em 9 categorias em português,
dimensionadas pelo que o cardápio realmente tem.

A saída (data/categorias-site.json) é revisável e versionada: o build lê o
mapeamento pronto em vez de re-adivinhar. Para corrigir um item, edite o valor
em `atribuicoes` — ou acrescente uma entrada em REVISAO_MANUAL aqui e regere.

    python3 scripts/classify_categories.py
"""
import json, re, unicodedata, collections, pathlib

RAIZ = pathlib.Path(__file__).resolve().parent.parent
ENTRADA = RAIZ / "data" / "cardapio.json"
SAIDA = RAIZ / "data" / "categorias-site.json"

CATEGORIAS = [
    ("doces",              "Doces"),
    ("bebidas-sem-alcool", "Bebidas sem álcool"),
    ("massas",             "Massas"),
    ("bebidas-com-alcool", "Bebidas com álcool"),
    ("pizzas-e-fogazza",   "Pizzas e Fogazza"),
    ("lanches",            "Lanches"),
    ("petiscos-e-porcoes", "Petiscos e Porções"),
    ("carnes-e-polenta",   "Carnes e Polenta"),
    ("outros-pratos",      "Outros pratos"),
]

# Correções conferidas à mão. A heurística lê texto; estes casos ela erra.
REVISAO_MANUAL = {
    # Sobremesa que vive na categoria "Menù Vegano" do PDF e por isso não casa
    # com nenhuma regra de doce.
    "26-09-panna-cotta-vegana-ai-frutti-rossi": ("doces", "sobremesa listada em Menù Vegano"),
}

ALCOOL = r"(cerveja|chopp|chope|vinho|caipir|amarula|conhaque|licor|aperol|spritz|whisky|vodka|gin\b|sangria|prosecco|espumante|campari|limoncell|grappa|cachac|alcoolic|quentao)"
MASSA  = r"(spaghetti|spagueti|macarr|penne|ravioli|ravioles|gnoch|nhoque|gnocc|lasanha|lasagn|talharim|tagliat|fettuc|capellet|capelet|tortel|canelon|cannellon|rondelli|farfalle|rigatoni|fusilli|conchiglion|nioqui|\bmassa\b|zuppa di cappelletti)"
PIZZA  = r"(pizza|fogazza|focaccia|calzone|piadina)"
CARNE  = r"(frango|carne|bovin|suin|porco|pernil|linguic|salsicc|calabres|costel|filet|bife|panceta|bacon|lombo|almond|polpett|peixe|bacalhau|baccala|camarao|fraldinha|picanha|maiale|pollo|manzo|pesce|porchetta|capretto|spiedo|ragu)"


def sem_acento(s):
    return "".join(c for c in unicodedata.normalize("NFD", s or "")
                   if unicodedata.category(c) != "Mn").lower()


def classificar(item):
    """Categoria de navegação de um item, pelo texto e pela categoria do PDF."""
    cid = item["categoria_id"]
    titulo = sem_acento(item["titulo"])
    texto = titulo + " || " + sem_acento(item["descricao"])

    if cid == "bevande":
        return "bebidas-com-alcool" if re.search(ALCOOL, texto) else "bebidas-sem-alcool"
    if cid in ("dolci", "gelato"):
        return "doces"
    if cid == "panini":
        return "lanches"
    if cid in ("pizza", "fogazza") or re.search(PIZZA, titulo):
        return "pizzas-e-fogazza"
    if re.search(MASSA, texto):
        return "massas"
    if cid in ("antipasti", "porzioni", "accompagnamenti", "insalata"):
        return "petiscos-e-porcoes"
    if re.search(CARNE, texto) or "polenta" in titulo:
        return "carnes-e-polenta"
    return "outros-pratos"


def main():
    cardapio = json.loads(ENTRADA.read_text(encoding="utf-8"))
    itens = [i for b in cardapio["barracas"] for i in b["itens"]]

    ids = {i["id"] for i in itens}
    orfas = set(REVISAO_MANUAL) - ids
    if orfas:
        raise SystemExit(f"REVISAO_MANUAL aponta para id inexistente: {sorted(orfas)}")

    atribuicoes, revisados = {}, {}
    for item in itens:
        cat = classificar(item)
        if item["id"] in REVISAO_MANUAL:
            cat, motivo = REVISAO_MANUAL[item["id"]]
            revisados[item["id"]] = {"categoria": cat, "motivo": motivo}
        atribuicoes[item["id"]] = cat

    contagem = collections.Counter(atribuicoes.values())
    faltando = [c for c, _ in CATEGORIAS if not contagem[c]]
    if faltando:
        raise SystemExit(f"categoria sem nenhum item: {faltando}")
    if len(atribuicoes) != len(itens):
        raise SystemExit("ids duplicados no cardápio")

    SAIDA.write_text(json.dumps({
        "_descricao": "Categorias de navegação do site, derivadas de data/cardapio.json. "
                      "Edite `atribuicoes` para corrigir um item; o build obedece este arquivo.",
        "_gerado_por": "scripts/classify_categories.py",
        "categorias": [{"id": c, "nome": n, "ordem": i, "total": contagem[c]}
                       for i, (c, n) in enumerate(CATEGORIAS)],
        "revisao_manual": revisados,
        "atribuicoes": dict(sorted(atribuicoes.items())),
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"{len(itens)} itens -> {SAIDA.relative_to(RAIZ)}")
    for c, nome in CATEGORIAS:
        print(f"  {contagem[c]:4d}  {nome}")
    print(f"  ---- {sum(contagem.values())}")
    if revisados:
        print(f"revisão manual: {len(revisados)} item(ns)")


if __name__ == "__main__":
    main()
