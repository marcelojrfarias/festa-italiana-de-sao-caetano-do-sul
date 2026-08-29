# Curadoria do cardápio

Como cada item impresso do cardápio vira um ou mais pratos na tela.

Isto é uma regra para pessoa ou modelo seguir lendo
`docs/cardapio-33a-festa-italiana.pdf`, não um algoritmo. Já houve a tentativa
de deduzir a decisão do texto: 214 linhas de expressão regular para 149 itens,
e cada rodada revelava uma forma nova de enumerar. O cardápio foi escrito por
35 entidades, cada uma do seu jeito, e não segue regra de forma nenhuma.

O resultado da curadoria vive em `data/expansao.json`. Item que não está lá
aparece na tela exatamente como está impresso.

## O princípio

**Um prato na tela é uma coisa que a pessoa pode pedir apontando.** Se dá para
dizer "quero esse" na barraca, é um item.

O valor do site está nisto. Um card que diz "Cannoli Alla Crema / Mousse Al
Cioccolato / Nutella / Fior di Latte" não ajuda ninguém a decidir o que comer,
e não aparece para quem busca "nutella".

## As regras

**1. Sabor vira item.** Se o item impresso oferece sabores, recheios, molhos ou
marcas entre os quais a pessoa escolhe, cada escolha vira um prato. Não importa
se a lista está no título ou só na descrição. Não importa se o nome está em
italiano ou em português: se é pizza de queijo, é um item de pizza de queijo.

**2. A descrição acompanha o sabor.** Cada prato recebe a descrição do sabor
dele, nunca a lista inteira. O cannoli de creme não pode dizer "recheada com
Creme, Doce de Leite ou Nutella", e a farfalle não pode dizer "Macarrão Tipo
Espaguete, Penne ou Gravatinha" — os dois erros já estiveram no ar.

Quando a descrição enumera na mesma ordem do título, é só parear. Quando ela
descreve tudo de uma vez, escreva a de cada prato a partir dela, sem
acrescentar informação que o cardápio não deu.

**3. Ingrediente não é sabor.** A pergunta que separa os dois: *a pessoa escolhe
entre eles, ou recebe todos juntos?*

- "Pizza Alla Salsiccia Calabrese, Cipolle e Catupiry" — recebe os três. Um item.
- "Gelato Al Cioccolato, Alla Fragola e Alla Crema" — escolhe um. Três itens.

Os dois têm a mesma forma. Só o sentido separa: a vírgula da pizza lista o que
vem junto, a do gelato lista o que se escolhe.

**Escolher parte de um prato também é escolher.** Isto aqui já esteve errado
neste documento, com o argumento de que a pessoa "leva mortadela de qualquer
jeito":

- "Piadina com Mortadela e Requeijão ou Muçarela" — dois itens, um com
  requeijão e outro com muçarela.
- "Vinho Seco ou Suave (Copo)" — dois itens.
- "Suco Integral de Uva ou Laranja (Copo)" — dois itens.

O que vale é se existe uma escolha a fazer na barraca, não se ela é do prato
inteiro ou de um ingrediente dele. Antes dessa correção, oito barracas vendiam
vinho seco sem que houvesse um card de vinho seco, e o suco de laranja não
existia na tela.

**4. Medida é atributo, tipo é item.** "Com Gás" e "Sem Gás" são escolha: dois
itens. "510 ml" é quanto vem: desce para a descrição. Copo, garrafa, jarra e
meia garrafa são itens próprios quando o cardápio cobra preço diferente por
cada um, porque aí são coisas diferentes de pedir.

**5. Versão do mesmo produto é um item; produto diferente é outro.**
"Coca Cola Normal e Zero" é uma marca com duas versões — um item, com "Normal e
Zero" na descrição. "Heineken Zero" é cerveja sem álcool — item próprio, não é
a mesma cerveja com opção.

**6. Mesma coisa escrita de outro jeito é um item só.** Entra aqui erro de
grafia ("Gnochi", "Sfitacciato", "Fomarggio"), palavra de ligação faltando
("Suco Uva", "Chopp Vinho"), ordem invertida ("Copo Vinho Tinto") e o mesmo
ingrediente em outra língua ("Dulce de Leche" e "Dolce di Latte"). Não entra
nome válido diferente: "Al Pesto" não é "Al Sugo", "Panino" não é "Piadina".

O critério que decide os casos duvidosos: **se a descrição em português é a
mesma, é o mesmo prato**. Foi assim que "Fogazza Alla Calabrese e Mozzarella"
e "Fogazza Alla Salsiccia Calabrese e Mozzarella" viraram um card — as duas
dizem "Massa Frita recheada com Linguiça Calabresa e Muçarela". E foi assim
que "Fogazza Al Pollo con Catupiry" e "Fogazza Al Pollo Formaggio Cremoso"
continuaram separadas: uma diz catupiry, a outra requeijão.

Isto vive em `SINONIMOS` e `CORRECOES`, em `scripts/build_site.py`. A busca
continua aceitando a grafia impressa — quem lê "Gnochi" na placa digita
"Gnochi".

**7. O nome é o que está impresso, mais o sabor.** Salvo quando o próprio
cardápio usa outra forma em outro lugar: como ele escreve "Suco de Uva (Copo)"
em nove barracas, o suco de uva em lata é "Suco de Uva (Lata)", e não
"Suco (Lata) Uva".

**Quantificador e marcação vão entre parênteses, no fim, numa grafia só.**
Recipiente, volume, tamanho, número de unidades e marcações como
"(Vegetariano)" saem do meio do nome e viram sufixo. O cardápio escreve a
mesma bruschetta de quatro jeitos — "- 3 Unità", "– 3 Unità", "– 3 unità" —
e o nome do prato tem de ser um só para os cards juntarem.

    Refrigerante 350 ml Coca Cola   ->  Refrigerante Coca Cola (350 ml)
    Pizza Tradizionale 18 cm Al Formaggio -> Pizza Tradizionale Al Formaggio (18 cm)
    Bruschetta Al Pomodoro – 3 Unità -> Bruschetta Al Pomodoro (3 unità)

Recipiente com preço próprio fica no título porque é outra coisa de comprar:
o copo de vinho custa R$ 10 e a garrafa R$ 35. Já a medida ("200 ml", "1
litro") desce para a descrição, e não se repete lá o que o título já diz.

**Porção e tamanho seguem a mesma forma.** "Fetta di Pizza Margherita" e
"Pizza Intera Margherita" são a mesma pizza da mesma barraca em duas medidas, e
ficavam em pontos distantes da lista, começando por palavras diferentes. Viram
"Pizza Margherita (Fatia)" e "Pizza Margherita (Inteira)", que é o que a pessoa
compara. O mesmo para "(Pequeno)" e "(Grande)", e para a quantidade em
"(1 unità)" e "(8 unità)".

**9. O título é em português; o nome italiano fica ao lado, com bandeira.**
O objetivo do site é a pessoa achar o que quer comer, e o idioma não pode ser
a barreira. Mas o nome italiano é o que está na placa da barraca, é por ele
que ela vai pedir, e faz parte do que a festa é — então não some: vira campo
próprio no card, entre o título e a descrição.

O teste para traduzir ou não é um só: **como o brasileiro chama isso?**

    fica em italiano     Spaghetti, Penne, Farfalle, Ravioli, Cappelletti,
                         Pizza, Fogazza, Calzone, Piadina, Focaccia,
                         Cannoli, Gelato, Panna Cotta, Tiramisù, Bruschetta,
                         Polenta, Caponata, Strudel, Antipasto

    traduz               Gnocchi -> Nhoque      Panino -> Sanduíche
                         Crostata -> Torta      Budino -> Pudim
                         Capretto -> Cabrito    Lasagne -> Lasanha
                         Fetta -> Fatia         Porzioni -> Porção

Ninguém pede "gnocchi" aqui, mas também ninguém pede "espaguete à moda
italiana" quando o nome é spaghetti. Prato sem nome corrente em português —
Sfogliatella, Zuccotto, Crostoli, Panzanella — mantém o nome italiano e conta
com a descrição.

O nome em português é a chave de agrupamento, então dois nomes italianos que
querem dizer a mesma coisa viram um card sozinhos: "Panino Al Manzo
Sfilacciato" e "Panino Alla Carne Sfilacciata" são o mesmo "Sanduíche de
Carne Desfiada". A busca aceita os dois idiomas.

Todo prato de comida tem descrição. Os únicos com descrição curta são bebidas,
onde o nome já se explica sozinho. E descrição que vira eco do título em
português sai do card: "Torta de Limão" não precisa dizer "Torta de Limão"
embaixo.

**10. A categoria é parte da curadoria.** Bolinho de bacalhau é petisco, não
carne; as duas sopas do cardápio ficam juntas; combo não é massa. Quando a
regra automática de `scripts/classify_categories.py` erra, a correção vai em
`REVISAO_MANUAL`, com o motivo escrito.

**8. Não inventar.** Quando o cardápio anuncia sabores mas não diz quais
("Massa Crocante recheada com Creme – sabores"), o item fica um só e a frase
pendurada sai. Quando a descrição é só a palavra "Sabores", o card fica sem
descrição.

## Quando o cardápio mudar

`scripts/conferir_curadoria.py` compara o texto de cada item com o texto que
estava valendo quando a curadoria foi feita, e derruba o build quando algo
mudou. Ele não adivinha nada: só diz *quais* itens precisam de decisão nova.

Para cada item apontado, abra a página da barraca no PDF, aplique as regras
acima e atualize `data/expansao.json`. Depois rode o script de novo para
registrar o texto novo.
