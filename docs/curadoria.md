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

Isto vive em `SINONIMOS` e `CORRECOES`, em `scripts/build_site.py`. A busca
continua aceitando a grafia impressa — quem lê "Gnochi" na placa digita
"Gnochi".

**7. O nome é o que está impresso, mais o sabor.** Salvo quando o próprio
cardápio usa outra forma em outro lugar: como ele escreve "Suco de Uva (Copo)"
em nove barracas, o suco de uva em lata é "Suco de Uva (Lata)", e não
"Suco (Lata) Uva".

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
