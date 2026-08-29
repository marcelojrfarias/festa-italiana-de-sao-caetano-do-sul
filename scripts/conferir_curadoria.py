#!/usr/bin/env python3
"""Acusa itens do cardápio cuja curadoria pode ter ficado velha.

A decisão de quando um item vira vários pratos é tomada à mão, lendo o PDF —
a regra está em docs/curadoria.md. Este script não decide nada e não adivinha:
compara o texto de cada item com o texto que valia quando a decisão foi
tomada, e aponta o que mudou, sumiu ou apareceu.

É objetivo de propósito. A versão anterior procurava "cara de enumerar sabor"
com expressão regular, e o problema dela era o mesmo da inferência que
substituiu: item novo sem sinal nenhum passava calado, e prato errado ficava
semanas no ar.

    python3 scripts/conferir_curadoria.py            confere
    python3 scripts/conferir_curadoria.py --registrar grava o texto atual
"""
import hashlib
import json
import pathlib
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
EXPANSAO = RAIZ / "data" / "expansao.json"
CARDAPIO = RAIZ / "data" / "cardapio.json"


def impressao(item):
    cru = f'{item["titulo"]}\x1f{item["descricao"] or ""}'
    return hashlib.sha256(cru.encode("utf-8")).hexdigest()[:12]


def main():
    dados = json.loads(EXPANSAO.read_text(encoding="utf-8"))
    cardapio = json.loads(CARDAPIO.read_text(encoding="utf-8"))
    itens = {it["id"]: it for b in cardapio["barracas"] for it in b["itens"]}
    atual = {i: impressao(it) for i, it in itens.items()}
    registrado = dados.get("origem", {})

    if "--registrar" in sys.argv:
        dados["origem"] = dict(sorted(atual.items()))
        EXPANSAO.write_text(json.dumps(dados, ensure_ascii=False, indent=1) + "\n",
                            encoding="utf-8")
        print(f"registrado o texto de {len(atual)} itens.")
        return 0

    sumidos = sorted(set(registrado) - set(atual))
    novos = sorted(set(atual) - set(registrado))
    mudados = sorted(i for i in set(atual) & set(registrado)
                     if atual[i] != registrado[i])
    orfas = sorted(set(dados["itens"]) - set(atual))

    print(f"{len(atual)} itens no cardápio, {len(dados['itens'])} com expansão decidida.")
    if not (sumidos or novos or mudados or orfas):
        print("Curadoria em dia: nenhum item mudou desde a última decisão.")
        return 0

    print("\nDecidir à mão, seguindo docs/curadoria.md:\n")
    for rotulo, ids in (("saiu do cardápio", sumidos), ("entrou no cardápio", novos),
                        ("texto mudou", mudados),
                        ("tem expansão mas não existe mais", orfas)):
        for i in ids:
            it = itens.get(i)
            print(f"  [{rotulo}] {i}")
            if it:
                print(f"      {it['titulo']}")
                print(f"      {it['descricao']}")
    print("\nDepois de atualizar data/expansao.json, rode com --registrar.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
