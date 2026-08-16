# Mapa da festa

Croqui em SVG das barracas da 33ª Festa Italiana. Sem build, sem dependência,
sem rede: são três arquivos estáticos que funcionam abertos de qualquer servidor
de arquivos — e, uma vez carregados, funcionam offline. Não usa tiles do Google
nem do OpenStreetMap, de propósito: o 4G no meio da festa não é confiável.

```
mapa/geo.js       projeção, retângulo da barraca, distância, georreferência
mapa/croqui.js    o renderizador (módulo ES, sem dependência)
mapa/index.html   página de demonstração — croqui + ficha da barraca
mapa/editor.html  ferramenta de traçado: vira a planta oficial em mapa.json
data/mapa.json    a geometria (gerada por scripts/gerar_mapa.py)
```

Para abrir localmente (módulos ES exigem servidor, não `file://`):

```bash
python3 -m http.server 8000
# http://localhost:8000/mapa/index.html
# http://localhost:8000/mapa/editor.html
```

## Estado atual: parcial

O arranjo das barracas é o do **"MAPA DAS ENTIDADES" oficial** da 33ª Festa
Italiana, medido em pixels sobre uma foto do banner montado na festa. As oito
zonas, quem é vizinho de quem e de que lado da rua cada barraca fica: tudo isso
é o oficial.

O que ainda não é exato é a **escala e a orientação**. A foto tem perspectiva e
o banner não traz barra de escala, então os 0,105 m/px saíram do espaçamento da
fila 12-28-27-22 — quatro tendas vizinhas, ~7 m de passo. Daí `_status:
"parcial"` e o aviso na página de demonstração.

> A numeração **não acompanha o percurso**. Ela é por entidade e aparece
> espalhada pelo mapa: 17 no topo, 01 no meio, 31 sozinha na praça, 35 e 36 no
> fundo do parque. Não dá para inferir vizinhança a partir do número.

## Para fechar a escala

Abra `mapa/editor.html`, carregue a foto do banner (ou a arte original) como
fundo, alinhe-a pelas ruas (escala, giro, e botão direito para arrastar) e
ajuste as barracas. Cada uma que você tocar perde o `aproximado`; quando não
sobrar nenhuma, o `_status` exportado vira `conferido` e o aviso some sozinho.

O que mais ajudaria aqui é **o arquivo original da arte do banner** (PDF ou PNG,
com os organizadores). Com ele dá para largar o traçado vetorial e usar a
própria ilustração oficial como fundo do mapa, com as barracas viradas áreas
clicáveis por cima — mais bonito, já familiar para quem viu o banner na rua, e
sem nenhum palpite de escala.

## O contrato com o app do cardápio

O mapa **não duplica** dado do cardápio. `data/mapa.json` só tem geometria e se
junta a `data/cardapio.json` pelo campo `numero`, que é 1:1 nos dois arquivos —
incluindo a barraca dupla, que é `"20/21"` nos dois lados. Quem mexe no cardápio
não precisa tocar no mapa, e vice-versa.

Há também `rotulo`, que é como o número aparece impresso no banner oficial
(`"01"`, `"08"`, `"20/21"`). Use `rotulo` para mostrar e `numero` para juntar.

```js
import { criarCroqui } from './mapa/croqui.js';

const croqui = criarCroqui(elemento, mapa, {
  aoSelecionar: (numero) => irPara(`#/barraca/${numero}`),
});

croqui.destacar(['3', '12', '27']);  // apaga o resto — amarra o mapa ao filtro de pratos
croqui.destacar(null);               // volta ao normal
croqui.selecionar('12');             // realça, como se tivesse sido tocada
croqui.marcarVoce([x, y], 15);       // ponto azul, em metros do frame local
croqui.enquadrar();                  // reenquadra
```

O caso de uso que fecha o ciclo é `destacar`: quem filtrou "sem glúten" ou
"cannoli" na lista vê no mapa só as barracas que atendem, sem o mapa saber o que
é glúten.

## O sistema de coordenadas

Métrico local: `x` para o leste, `y` para o norte, em metros, com origem no
cruzamento da R. Mariano Pamplona com a R. Ceará. **Não há lat/lng no arquivo**,
e isso é intencional — chutar coordenada geográfica seria inventar dado com cara
de medição.

Georreferenciar depois custa dois campos em `frame.origem`: a `latlng` da origem
e o `azimute_do_eixo_y`. A partir daí `metrosParaLatLng` passa a devolver
coordenada de verdade e o `marcarVoce` pode ser alimentado por
`navigator.geolocation` (que exige HTTPS). Nenhum outro arquivo muda.

Cada barraca é um retângulo: centro, `largura_m` (a frente, por onde se atende),
`profundidade_m` e `azimute` — a direção da frente, em graus no sentido horário
a partir do norte. `cantosDaBarraca()` devolve os quatro cantos.

## Detalhe de renderização

O croqui inteiro tem 250 × 440 m. Nesse enquadramento uma barraca de 4 m ocupa
~6 px e ninguém enxerga o número, então acima de 190 m de largura de quadro as
barracas viram pinos numerados e, ao aproximar, voltam ao retângulo em escala
real. O limiar é `LIMIAR_PINO_M` em `croqui.js`.
