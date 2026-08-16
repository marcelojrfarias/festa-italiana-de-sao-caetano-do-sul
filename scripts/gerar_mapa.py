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
import math
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


def retangulo(x0, y0, x1, y1):
    return [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]


# --- vias -------------------------------------------------------------------
# Retas e contínuas, atravessando o quadro de ponta a ponta. O traçado curvo que
# saiu da foto do banner era fiel ao desenho e ruim de ler: num croqui a rua
# serve de eixo de orientação, e eixo torto não orienta.
VIAS = [
    {"id": "mariano-pamplona", "nome": "R. Mariano Pamplona", "largura_m": 9,
     "eixo": [[-32.0, 110.0], [21.3, -125.0]]},
    {"id": "vinte-e-oito-de-julho", "nome": "R. Vinte e Oito de Julho", "largura_m": 9,
     "eixo": [[-11.0, 0.0], [60.0, 0.0]]},
]

# --- áreas de contexto ------------------------------------------------------
# Só o que ajuda a se localizar. Os quarteirões a leste da via, o pátio ao sul e
# o quarteirão a oeste da igreja saíram de propósito: não têm barraca e só
# enchiam o quadro de retângulo.
AREAS = [
    {"id": "igreja", "nome": "Paróquia São Caetano", "tipo": "edificado",
     "rotulo": True, "aproximado": True,
     "poligono": retangulo(-62.0, 10.0, -26.0, 38.0)},
    {"id": "largo", "nome": None, "tipo": "pavimento", "aproximado": True,
     "poligono": retangulo(-100.0, -28.0, -20.0, 9.0)},
    {"id": "parque-treviso", "nome": "Parque Província de Treviso", "tipo": "verde",
     "rotulo": True, "aproximado": True,
     "rotulo_ponto": [-80.0, -88.0],   # canto livre: as filas ocupam o meio e o topo
     "poligono": retangulo(-106.0, -105.0, -19.0, -28.0)},
]

# --- zonas e barracas, lidas do mapa oficial --------------------------------
# (id, nome, via, azimute_frente, [(numero, px, py)])
# O azimute e a direcao da frente. Quem tem via e encostado na calcada por
# calculo; quem nao tem (praca e parque) fica onde foi medido na foto.
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
    # medidas na foto, estas duas filas caíam sobre a borda do parque — a de cima
    # ficava até fora dele, no largo. Elas estão dentro do parque, então descem.
    ("parque-norte", "Parque — fila norte", None, 180, [
        ("3", 200, 1322), ("11", 268, 1322), ("29", 360, 1322),
        ("9", 428, 1322), ("24", 495, 1322), ("6", 565, 1322),
    ]),
    ("parque-travessa", "Parque — segunda fila", None, 0, [
        ("30", 310, 1417), ("14", 378, 1417),
    ]),
    ("parque-alameda", "Parque — fila sul", None, 90, [
        ("23", 628, 1560), ("26", 628, 1622), ("33", 628, 1685),
        ("36", 628, 1745), ("34", 628, 1805), ("35", 628, 1865),
    ]),
]

LARGURA_PADRAO_M = 4.0    # frente da barraca
PROFUNDIDADE_PADRAO_M = 3.0


def projetar(eixo, ponto):
    """Ponto mais proximo sobre a polilinha, e a distancia ate ele."""
    melhor, menor = eixo[0], float("inf")
    for a, b in zip(eixo, eixo[1:]):
        dx, dy = b[0] - a[0], b[1] - a[1]
        L2 = dx * dx + dy * dy
        t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((ponto[0] - a[0]) * dx + (ponto[1] - a[1]) * dy) / L2))
        q = (a[0] + t * dx, a[1] + t * dy)
        d = math.hypot(ponto[0] - q[0], ponto[1] - q[1])
        if d < menor:
            melhor, menor = q, d
    return melhor, menor


FOLGA_CALCADA_M = 1.5

# A 01 nao fica na calcada: ela fecha o fim da R. Mariano Pamplona, plantada no
# meio do leito. Encostar ela na guia como as outras seria fiel a regra e infiel
# a rua.
NO_EIXO = {"1"}


def encostar(centro, azimute, via, profundidade):
    """Empurra a barraca para fora do leito, ate a calcada.

    `azimute` e a direcao da frente, que olha para a rua; entao o lado de fora e
    o oposto. Assim a rua fica limpa entre duas filas que se encaram, em vez de
    as barracas cavalgarem o asfalto como ficava quando a posicao vinha so da
    medida em pixel sobre a foto.
    """
    a = math.radians(azimute)
    frente = (math.sin(a), math.cos(a))
    base, _ = projetar(via["eixo"], centro)
    d = via["largura_m"] / 2 + profundidade / 2 + FOLGA_CALCADA_M
    return [round(base[0] - frente[0] * d, 1), round(base[1] - frente[1] * d, 1)]


def main():
    zonas, barracas = [], []
    for zid, znome, via_id, azimute, pontos in ZONAS:
        zonas.append({"id": zid, "nome": znome, "via": via_id,
                      "barracas": [n for n, _, _ in pontos]})
        for numero, px, py in pontos:
            numeros = [int(n) for n in numero.split("/")]
            largura = LARGURA_PADRAO_M * len(numeros)  # a barraca dupla 20/21 é maior
            centro = list(m(px, py))
            via = next((v for v in VIAS if v["id"] == via_id), None)
            if via and numero in NO_EIXO:
                centro = [round(c, 1) for c in projetar(via["eixo"], centro)[0]]
            elif via:
                centro = encostar(centro, azimute, via, PROFUNDIDADE_PADRAO_M)
            barracas.append({
                "numero": numero,
                "rotulo": "/".join(f"{int(n):02d}" for n in numero.split("/")),
                "numeros": numeros,
                "zona": zid,
                "centro": centro,
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
