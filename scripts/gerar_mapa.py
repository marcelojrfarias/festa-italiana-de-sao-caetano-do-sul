#!/usr/bin/env python3
"""Gera data/mapa.json — a geometria da festa, separada do cardápio.

O traçado aqui é APROXIMADO: veio do croqui de memória, medido em pixels sobre
uma captura do Google Maps (escala 50 m). Quando o mapa oficial chegar, remeça
os pixels sobre ele, troque as constantes abaixo e rode de novo — o formato de
saída e o resto do app não mudam.

Sistema de coordenadas: métrico local, x = leste, y = norte, em metros, com
origem no cruzamento R. Mariano Pamplona x R. Ceara. Nao ha lat/lng aqui de
proposito: chutar coordenada geografica seria inventar dado. Georreferenciar
depois e preencher um ponto e um azimute em `frame.origem`.
"""
import json
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

# --- calibração da captura -------------------------------------------------
M_POR_PX = 0.45          # barra de escala: ~110 px para 50 m
ORIGEM_PX = (800, 408)   # cruzamento Mariano Pamplona x Ceara


def m(px, py):
    """pixel da captura -> metros no frame local (y para cima)."""
    return (round((px - ORIGEM_PX[0]) * M_POR_PX, 1),
            round((ORIGEM_PX[1] - py) * M_POR_PX, 1))


def linha(*pts):
    return [m(*p) for p in pts]


# --- vias -------------------------------------------------------------------
VIAS = [
    {"id": "mariano-pamplona", "nome": "R. Mariano Pamplona", "largura_m": 9,
     "eixo": linha((770, 60), (795, 300), (800, 408), (838, 560), (870, 700), (884, 830))},
    {"id": "ceara", "nome": "R. Ceará", "largura_m": 9,
     "eixo": linha((744, 411), (900, 407), (1060, 403))},
    {"id": "vinte-e-oito-de-julho", "nome": "R. Vinte e Oito de Julho", "largura_m": 9,
     "eixo": linha((820, 702), (960, 698), (1090, 694))},
    {"id": "acesso-parque", "nome": "Acesso ao Parque Província de Treviso", "largura_m": 6,
     "eixo": linha((866, 760), (800, 775), (700, 800), (665, 820))},
    # as duas filas de barracas do parque se olham por cima destes caminhos
    {"id": "alameda-oeste", "nome": None, "largura_m": 5,
     "eixo": linha((665, 826), (560, 834), (430, 838))},
    {"id": "alameda-treviso", "nome": None, "largura_m": 5,
     "eixo": linha((700, 900), (712, 1000), (726, 1100), (734, 1175))},
]

# --- áreas de referência ----------------------------------------------------
AREAS = [
    {"id": "paroquia", "nome": "Paróquia São Caetano", "tipo": "referencia",
     "ponto": m(823, 632)},
    {"id": "parque-treviso", "nome": "Parque Província de Treviso", "tipo": "referencia",
     "ponto": m(700, 915)},
    {"id": "praca-matarazzo", "nome": "Praça Com. Ermelino Matarazzo", "tipo": "referencia",
     "ponto": m(990, 1000)},
]

# --- zonas e barracas -------------------------------------------------------
# (id, nome, via, azimute_frente, [(numero, px, py)])
# azimute = direcao para onde a barraca esta virada, graus no sentido horario a
# partir do norte. 90 = de frente para o leste.
ZONAS = [
    ("mariano-norte", "R. Mariano Pamplona — norte da R. Ceará", "mariano-pamplona", 90, [
        ("1", 733, 175), ("2", 748, 232), ("3", 757, 285), ("4", 770, 330),
        ("5", 775, 375), ("6", 782, 440), ("7", 798, 510), ("8", 806, 570),
        ("9", 818, 625),
    ]),
    ("mariano-sul-oeste", "R. Mariano Pamplona — trecho da Paróquia, lado oeste",
     "mariano-pamplona", 90, [
        ("10", 852, 458), ("11", 858, 512), ("12", 866, 570), ("13", 876, 620),
        ("14", 884, 655),
    ]),
    ("mariano-sul-leste", "R. Mariano Pamplona — trecho da Paróquia, lado leste",
     "mariano-pamplona", 270, [
        ("15", 928, 662), ("16", 962, 665), ("17", 995, 662), ("18", 880, 718),
        ("19", 884, 748),
    ]),
    ("vinte-e-oito", "R. Vinte e Oito de Julho", "vinte-e-oito-de-julho", 180, [
        ("20/21", 878, 782), ("22", 848, 812), ("23", 792, 808),
    ]),
    ("acesso-parque-norte", "Acesso ao parque — fila norte", "acesso-parque", 180, [
        ("24", 447, 793), ("25", 495, 790), ("26", 552, 793), ("27", 610, 790),
    ]),
    ("acesso-parque-sul", "Acesso ao parque — fila sul", "acesso-parque", 0, [
        ("28", 440, 878), ("29", 487, 880), ("30", 535, 882),
    ]),
    ("parque", "Dentro do Parque Província de Treviso", None, 90, [
        ("31", 712, 962), ("32", 718, 1002), ("33", 722, 1042), ("34", 730, 1082),
        ("35", 738, 1118), ("36", 745, 1152),
    ]),
]

LARGURA_PADRAO_M = 4.0    # frente da barraca
PROFUNDIDADE_PADRAO_M = 3.0


def main():
    zonas, barracas = [], []
    for zid, znome, via, azimute, pontos in ZONAS:
        zonas.append({"id": zid, "nome": znome, "via": via,
                      "barracas": [n for n, _, _ in pontos]})
        for numero, px, py in pontos:
            numeros = [int(n) for n in numero.split("/")]
            largura = LARGURA_PADRAO_M * len(numeros)  # a barraca dupla 20/21 é maior
            barracas.append({
                "numero": numero,
                "numeros": numeros,
                "zona": zid,
                "centro": list(m(px, py)),
                "largura_m": largura,
                "profundidade_m": PROFUNDIDADE_PADRAO_M,
                "azimute": azimute,
                "aproximado": True,
            })

    mapa = {
        "_schema": "festa-italiana/mapa@1",
        "_status": "aproximado",
        "_fonte": "croqui de memória sobre captura do Google Maps; substituir pelo mapa oficial",
        "_chave_de_juncao": "`numero` casa com barracas[].numero de data/cardapio.json",
        "frame": {
            "descricao": "Métrico local: x = leste, y = norte, em metros.",
            "unidade": "m",
            "origem": {
                "referencia": "Cruzamento R. Mariano Pamplona x R. Ceará",
                "latlng": None,
                "azimute_do_eixo_y": 0,
            },
            "georreferenciado": False,
        },
        "vias": VIAS,
        "areas": AREAS,
        "zonas": zonas,
        "barracas": barracas,
    }

    xs = [b["centro"][0] for b in barracas]
    ys = [b["centro"][1] for b in barracas]
    mapa["extensao"] = {"x": [min(xs), max(xs)], "y": [min(ys), max(ys)],
                        "largura_m": round(max(xs) - min(xs), 1),
                        "altura_m": round(max(ys) - min(ys), 1)}

    destino = RAIZ / "data" / "mapa.json"
    destino.write_text(json.dumps(mapa, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{destino.relative_to(RAIZ)}: {len(barracas)} barracas em {len(zonas)} zonas, "
          f"{mapa['extensao']['largura_m']} x {mapa['extensao']['altura_m']} m")


if __name__ == "__main__":
    main()
