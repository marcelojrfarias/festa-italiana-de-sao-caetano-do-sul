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

## Estado atual: aproximado

**As posições ainda não são as reais.** Elas vieram de um croqui de memória
medido em pixels sobre uma captura do Google Maps, e `data/mapa.json` traz
`_status: "aproximado"` e `aproximado: true` em cada barraca. A página de
demonstração mostra um aviso enquanto isso for verdade. O que já está certo é a
**estrutura** — sete zonas, a ordem 1→36 ao longo do percurso e a junção com o
cardápio — e é isso que não muda quando a planta oficial chegar.

## Quando a planta oficial chegar

Abra `mapa/editor.html`, carregue a imagem da planta como fundo, alinhe-a pelas
ruas (escala, giro, e botão direito para arrastar) e mova cada barraca para o
lugar. Cada uma que você tocar perde o `aproximado`. No fim, "Exportar" baixa o
`mapa.json` para substituir o do repositório; quando não sobrar nenhuma
aproximada, o `_status` vira `conferido` e o aviso some sozinho.

Se a planta vier como uma lista ("barraca 12 na esquina da Ceará com a
Pamplona") em vez de desenho, o caminho é o mesmo, só sem imagem de fundo.

## O contrato com o app do cardápio

O mapa **não duplica** dado do cardápio. `data/mapa.json` só tem geometria e se
junta a `data/cardapio.json` pelo campo `numero`, que é 1:1 nos dois arquivos —
incluindo a barraca dupla, que é `"20/21"` nos dois lados. Quem mexe no cardápio
não precisa tocar no mapa, e vice-versa.

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
