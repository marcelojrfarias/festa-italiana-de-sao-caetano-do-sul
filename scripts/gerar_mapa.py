#!/usr/bin/env python3
"""Gera data/mapa.json — a geometria da festa, separada do cardápio.

O traçado vem do "MAPA DAS ENTIDADES" oficial da 33ª Festa Italiana, medido em
pixels sobre uma foto do banner montado na festa. O arranjo das barracas é o
oficial; a escala e a orientação ainda são estimadas (a foto tem perspectiva e
o banner não traz barra de escala), então `_status` continua "parcial" até
alguém passar o editor por cima.

Atenção: a numeração NÃO acompanha o percurso. Ela é por entidade, e os números
aparecem espalhados pelo mapa — 17 no topo, 01 no meio, 31 isolado na praça.

Sistema de coordenadas: métrico local, x = leste, y = norte, em metros, com
origem no cruzamento R. Mariano Pamplona x R. Vinte e Oito de Julho. Não há
lat/lng aqui de propósito: chutar coordenada geográfica seria inventar dado.
"""
import json
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

# --- calibração da foto do banner ------------------------------------------
# 0,105 m/px vem do espaçamento da fila 12-28-27-22: quatro barracas vizinhas
# em 222 px, com ~7 m de passo entre tendas.
M_POR_PX = 0.105
ORIGEM_PX = (1100, 960)   # cruzamento Mariano Pamplona x Vinte e Oito de Julho


def m(px, py):
    """pixel da captura -> metros no frame local (y para cima)."""
    return (round((px - ORIGEM_PX[0]) * M_POR_PX, 1),
            round((ORIGEM_PX[1] - py) * M_POR_PX, 1))


def linha(*pts):
    return [m(*p) for p in pts]


# --- vias, traçadas sobre o mapa oficial ------------------------------------
VIAS = [
    {"id": "mariano-pamplona", "nome": "R. Mariano Pamplona", "largura_m": 9,
     "eixo": linha((855, 200), (920, 500), (990, 800), (1075, 955), (1105, 1250))},
    {"id": "vinte-e-oito-de-julho", "nome": "R. Vinte e Oito de Julho", "largura_m": 9,
     "eixo": linha((1085, 952), (1250, 938), (1460, 925))},
    {"id": "alameda-norte", "nome": None, "largura_m": 6,
     "eixo": linha((150, 1196), (400, 1193), (610, 1190))},
    {"id": "alameda-travessa", "nome": None, "largura_m": 5,
     "eixo": linha((270, 1252), (400, 1248))},
    {"id": "alameda-parque", "nome": None, "largura_m": 6,
     "eixo": linha((648, 1300), (652, 1600), (658, 1920))},
]

def poli(*pts):
    return [m(*p) for p in pts]


# Massas do entorno, tracadas a olho sobre a foto do banner. So as que ajudam a
# se localizar: os quarteiroes a leste da via e o patio ao sul foram tirados de
# proposito — nao tem barraca neles e so enchiam o mapa de retangulo. Sao contexto
# para a pessoa se localizar — "estou do lado da igreja", "isso aqui e o parque" — e nao
# levantamento. Desenho proprio, simplificado; a arte do banner e dos organizadores.
AREAS = [
    {"id": "quadra-paroquia", "nome": "Paróquia São Caetano", "tipo": "edificado",
     "rotulo": True, "aproximado": True,
     "poligono": poli((495, 635), (700, 610), (875, 650), (880, 870), (600, 885), (490, 835))},
    {"id": "quadra-oeste", "nome": None, "tipo": "edificado", "aproximado": True,
     "poligono": poli((185, 790), (420, 760), (430, 1040), (195, 1060))},
    {"id": "largo", "nome": None, "tipo": "pavimento", "aproximado": True,
     "poligono": poli((150, 880), (905, 875), (910, 1225), (155, 1230))},
    {"id": "parque-treviso", "nome": "Parque Província de Treviso", "tipo": "verde",
     "rotulo": True, "aproximado": True,
     "poligono": poli((95, 1230), (910, 1225), (915, 1950), (100, 1955))},
]

# --- zonas e barracas, lidas do mapa oficial --------------------------------
# (id, nome, via, azimute_frente, [(numero, px, py)])
ZONAS = [
    ("mariano-oeste", "R. Mariano Pamplona — lado oeste", "mariano-pamplona", 90, [
        ("15", 825, 318), ("10", 840, 395), ("19", 855, 465), ("8", 875, 543),
        ("7", 890, 615), ("32", 925, 775), ("13", 938, 850),
    ]),
    ("mariano-leste", "R. Mariano Pamplona — lado leste", "mariano-pamplona", 270, [
        ("17", 868, 258), ("18", 900, 320), ("5", 962, 508), ("25", 972, 590),
        ("20/21", 1025, 802),   # duas tendas vizinhas: ponto médio de 21 e 20
    ]),
    ("vinte-e-oito", "R. Vinte e Oito de Julho — lado norte", "vinte-e-oito-de-julho", 180, [
        ("12", 1198, 930), ("28", 1272, 930), ("27", 1345, 930), ("22", 1420, 930),
    ]),
    ("mariano-sul", "R. Mariano Pamplona — abaixo do cruzamento", "mariano-pamplona", 270, [
        ("16", 1048, 1040), ("2", 1055, 1105), ("4", 1058, 1170), ("1", 1015, 1230),
    ]),
    ("praca", "Praça, a oeste da via", None, 90, [
        ("31", 915, 1090),
    ]),
    ("parque-norte", "Parque — alameda norte", "alameda-norte", 180, [
        ("3", 200, 1190), ("11", 268, 1190), ("29", 360, 1190),
        ("9", 428, 1190), ("24", 495, 1190), ("6", 565, 1190),
    ]),
    ("parque-travessa", "Parque — travessa", "alameda-travessa", 0, [
        ("30", 310, 1245), ("14", 378, 1245),
    ]),
    ("parque-alameda", "Parque — alameda sul", "alameda-parque", 90, [
        ("23", 628, 1560), ("26", 628, 1622), ("33", 628, 1685),
        ("36", 628, 1745), ("34", 628, 1805), ("35", 628, 1865),
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
                "rotulo": "/".join(f"{int(n):02d}" for n in numero.split("/")),
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
        "_status": "parcial",
        "_fonte": "MAPA DAS ENTIDADES oficial da 33ª Festa Italiana, medido sobre foto do banner",
        "_chave_de_juncao": "`numero` casa com barracas[].numero de data/cardapio.json",
        "frame": {
            "descricao": "Métrico local: x = leste, y = norte, em metros.",
            "unidade": "m",
            "origem": {
                "referencia": "Cruzamento R. Mariano Pamplona x R. Vinte e Oito de Julho",
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
