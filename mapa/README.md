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

### Sobre a escala, e por que ela pode ficar como está

A arte original do banner não deve aparecer, então o traçado vetorial é o que
temos — e para o uso real ele basta. Duas estimativas independentes cercam o
valor adotado de 0,105 m/px: o espaçamento da fila 12-28-27-22 (quatro tendas
vizinhas, ~7 m de passo) dá 0,088–0,101, e a largura do leito da R. Mariano
Pamplona dá 0,110–0,146. A incerteza fica em torno de ±20%.

Isso não atrapalha achar barraca: ninguém navega por metro absoluto, navega pelo
arranjo relativo — que é o oficial e está exato. **Só atrapalha o ponto azul.**
±20% sobre 170 m desloca a ponta do mapa em ~34 m, então, se um dia houver
georreferência, trate a posição como orientação grosseira e não como precisão de
GPS.

### As ruas mandam na posição das barracas

As duas vias são **retas e contínuas**, atravessando o quadro de ponta a ponta.
O traçado curvo tirado da foto era fiel ao desenho e ruim de ler: num croqui a
rua é eixo de orientação, e eixo torto não orienta.

As barracas que pertencem a uma via não ficam onde a foto as mostrava — são
encostadas na calçada por cálculo, em `encostar()`: metade do leito, mais metade
da profundidade, mais 1,5 m de folga, na direção oposta à frente (que olha para
a rua). O resultado é que duas filas que se encaram deixam os 9 m de asfalto
livres entre elas, com 2,8 m de sobra além da guia — antes elas cavalgavam o
leito, porque a posição vinha só da medida em pixel.

Nas zonas sem via — a praça e o parque — as barracas ficam onde foram medidas.
As alamedas internas do parque não são desenhadas: no croqui elas só somavam
traço sem ajudar ninguém a se achar.

### O entorno é desenho próprio

`areas` traz três polígonos simplificados, marcados `aproximado: true`: a igreja
(um retângulo — não vale detalhar planta de edifício num croqui de festa), o
largo e o parque. Os quarteirões a leste, o pátio ao sul e o quarteirão a oeste
saíram: não têm barraca e só enchiam o quadro de retângulo. `rotulo_ponto` tira
o nome do parque de cima da fila 23-35, onde o centroide o colocava. Servem para
a pessoa se situar — "estou do lado da igreja", "isso aqui é o parque" — e não
como levantamento. A ilustração do banner é dos organizadores; o que está aqui é
redesenho simplificado.

## Como entra no site

`scripts/build_site.py` embute tudo no `app.js`: `geo.js`, `croqui.js` e o
`data/mapa.json` inteiro viram `window.FESTA_MAPA` mais o namespace
`window.FestaMapa`. Nenhuma requisição extra — numa rua lotada, cada ida a mais
à rede é uma chance de o mapa não abrir. Custo: `app.js` sai de 3,0 KB para
10,2 KB em gzip.

Por isso `geo.js` e `croqui.js` são scripts simples e não módulos ES: o `app.js`
do site é um IIFE global, e assim o build só concatena o texto dos arquivos, sem
cirurgia de regex no fonte.

A aba é o quarto modo (`?modo=mapa`), ao lado de Categorias/Barracas/Tudo, e
reaproveita o roteamento que já existe. O que faz ela valer a pena é acompanhar
a busca: quem procurou "cannoli" vê 12 barracas acesas e 23 apagadas, e toca na
mais perto. Da barraca, o botão "ver no mapa" faz o caminho de volta.

## O contrato com o app do cardápio

O mapa **não duplica** dado do cardápio. `data/mapa.json` só tem geometria e se
junta a `data/cardapio.json` pelo campo `numero`, que é 1:1 nos dois arquivos —
incluindo a barraca dupla, que é `"20/21"` nos dois lados. Quem mexe no cardápio
não precisa tocar no mapa, e vice-versa.

São **três** campos, e cada um serve a uma coisa:

| campo | para quê | barraca dupla |
| --- | --- | --- |
| `numero` | juntar com `data/cardapio.json` | `"20/21"` |
| `rotulo` | mostrar (é como sai impresso no banner) | `"20/21"` |
| `chave` | URL e `data-barraca` do site | `"20-21"` |

`chave` **não** está no arquivo: `build_site.py` a calcula na hora, com o mesmo
`chave_barraca()` que o resto do site usa. A barra não pode ir para a URL nem
para a lista separada por espaço em `data-barracas`. O croqui aceita qualquer um
dos três ao destacar ou selecionar, então quem consome não precisa saber a
diferença.

`conferir_juncao()` derruba o build se o mapa e o cardápio deixarem de casar.
Não é zelo excessivo: já quebrou calado uma vez, quando o formato da chave mudou
no site e a barraca dupla sumiu do mapa sem nenhum erro.

```js
import { criarCroqui } from './mapa/croqui.js';

const croqui = criarCroqui(elemento, mapa, {
  aoSelecionar: (numero) => irPara(`#/barraca/${numero}`),
});

croqui.destacar(['3', '12', '27']);  // apaga o resto — amarra o mapa ao filtro de pratos
croqui.destacar(null);               // volta ao normal
croqui.selecionar('12');             // realça sem disparar `aoSelecionar`
croqui.marcarVoce([x, y], 15);       // ponto azul, em metros do frame local
croqui.enquadrar();                  // reenquadra
```

O caso de uso que fecha o ciclo é `destacar`: quem filtrou "sem glúten" ou
"cannoli" na lista vê no mapa só as barracas que atendem, sem o mapa saber o que
é glúten.

### Cores: as do app, e só

O croqui não tem paleta própria nem tema escuro. Ele lê os tokens do site —
`--papel`, `--papel-linha`, `--cartao`, `--verde-suave`, `--dourado`,
`--tinta-fraca` — e só cai no valor de reserva quando roda nas páginas avulsas
do mapa, que não os definem.

As barracas são a **mesma pílula dourada** do `.card__numero` das listas
(`--dourado` sobre `#3A2A12`), pelo mesmo motivo que levou eles à pílula: um
círculo não comporta `"20/21"`. Selecionada fica verde com texto branco, apagada
fica na cor da linha do papel.

**O projeto inteiro é claro, e só.** Não há `prefers-color-scheme` em lugar
nenhum — nem no croqui, nem no site, nem nestas páginas avulsas, que declaram
`color-scheme: light` e repetem os tokens do app. Ter tema próprio já custou
caro uma vez: o croqui seguia o sistema e ficava preto no meio de uma página
bege.

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

### Gestos

Pan e pinça são **um gesto só**: o croqui guarda o ponto do mundo que estava sob
o meio dos dedos e mantém ele ali enquanto eles se movem. Com um dedo a distância
não muda, o fator de escala vira 1 e sobra pan puro — sem código separado.

Isso não é elegância gratuita. A primeira versão abria um arrasto por ponteiro,
cada um com o próprio instantâneo do viewBox, e os dois se sobrescreviam a cada
movimento: com dois dedos o mapa tremia e escorregava, sem dar zoom nenhum.

Pelo mesmo motivo, no site o toque na barraca **não** intercepta o ponteiro — se
um dos dedos da pinça cair sobre uma barraca, o SVG precisa vê-lo. Vale como
toque só se o dedo mal saiu do lugar (8 px). No editor é o contrário: lá o
arrasto move a barraca, então ele fica com o ponteiro.

### O que tem tamanho de tela e o que tem tamanho de mapa

Pílulas das barracas, nomes de rua e nomes de área **não** escalam com o zoom:
são rótulos, e rótulo que cresce junto com o desenho vira cartaz. O croqui
recompõe o `transform` deles a cada quadro (`ajustarEscalaPinos`), o que é só
troca de atributo, sem refazer nós.

O que escala é o que representa o mundo: ruas, quadras, largo e parque.

O nome da rua não fica fixo no meio da linha — ele pousa no trecho da via mais
longe das barracas, dentre os que valem. Fixar no meio punha o rótulo bem no
cruzamento, justo onde a rua é mais cheia.

Três regras decidem se um trecho vale, e vieram todas de defeito visto na tela:

- **fica sobre o leito**, nunca ao lado — o nome fora da rua não diz de que rua
  se trata;
- **o texto inteiro cabe no quadro**, não só a âncora, senão o fim do nome sai
  cortado na borda;
- **não encosta em outro nome de rua**, que se cruzariam no cruzamento, onde as
  duas passam;
- **o texto inteiro fica sobre o trecho de rua**, e não só a âncora — senão
  metade do nome cai no vazio depois do fim do asfalto.

E os nomes são **recolocados quando o gesto termina**, não fixados no
enquadramento inicial: o bom lugar depende da vista. Com o mapa todo na tela a
Vinte e Oito só cabe perto do cruzamento; quem aproxima o trecho leste tem ali
uma rua larga e vazia, que é onde o nome deve estar. Recalcular a cada quadro
faria o rótulo saltitar enquanto o dedo se move, então só ao soltar.

O nome mais longo escolhe primeiro: ele tem menos lugar onde caber, e com o
curto escolhendo antes ele tomava a única vaga que servia ao outro — o segundo
nome simplesmente sumia do mapa.

## Detalhe de renderização

O croqui inteiro tem 250 × 440 m. Nesse enquadramento uma barraca de 4 m ocupa
~6 px e ninguém enxerga o número, então acima de 190 m de largura de quadro as
barracas viram pinos numerados e, ao aproximar, voltam ao retângulo em escala
real. O limiar é `LIMIAR_PINO_M` em `croqui.js`.
