# festa-italiana

Dados estruturados do cardápio e da identidade visual da **33ª Festa Italiana de
São Caetano do Sul**, extraídos do PDF oficial do menu (58 páginas).

## O que tem aqui

| Arquivo | Conteúdo |
| --- | --- |
| `data/cardapio.json` | 35 barracas (numeradas de 1 a 36) e **645 itens** com título, descrição, preço e categoria |
| `data/identidade-visual.json` | Paleta, tipografia, escala tipográfica, logo, elementos gráficos e layout |
| `assets/` | Logo com transparência, texturas de fundo, faixa de patrocinadores, selos institucionais e capa |
| `docs/cardapio-33a-festa-italiana.pdf` | PDF de origem |
| `scripts/` | Extratores e validador (reprodutíveis) |
| `data/mapa.json` | Geometria das 35 barracas, conforme o mapa oficial das entidades |
| `mapa/` | Croqui em SVG e o editor de planta ([detalhes](mapa/README.md)) |

## Como regerar

```bash
pip install pymupdf
python3 scripts/extract_menu.py       # -> data/cardapio.json
python3 scripts/extract_identity.py   # -> data/identidade-visual.json
python3 scripts/extract_assets.py     # -> assets/
python3 scripts/validate_menu.py      # confere o JSON contra o PDF
python3 scripts/gerar_mapa.py         # -> data/mapa.json
```

A extração não usa heurística de texto: ela lê a semântica visual de cada span
do PDF (fonte + cor), que é consistente nas 58 páginas.

| Estilo no PDF | Significado |
| --- | --- |
| `Hermann-Black` `#196B24` | Número, nome e região da barraca |
| `Arial Bold` `#EE0000` | Cabeçalho de categoria |
| `Arial Bold` `#196B24` | Título do prato — ou o preço, quando começa com `R$` |
| Regular `#000000` | Descrição do prato |

## Estrutura de `data/cardapio.json`

```jsonc
{
  "evento":   { "nome": "33ª Festa Italiana", "edicao": 33, "cidade": "São Caetano do Sul", ... },
  "resumo":   { "total_barracas": 35, "total_itens": 645, "preco_min": 4.0, "preco_max": 90.0,
                "total_regioes_italianas": 20, ... },
  "categorias": [ { "id": "dolci", "nome_it": "Dolci", "nome_pt": "Doces", "total_itens": 133, ... } ],
  "barracas": [
    {
      "numero": "1",                    // rótulo impresso ("20/21" na barraca dupla)
      "numeros": [1],                   // números normalizados
      "nome": "Grupo Espírita Seara das Fraternidades",
      "slug": "grupo-espirita-seara-das-fraternidades",
      "regiao_id": "veneto",
      "regiao_italiana": "Veneto",      // nome oficial normalizado
      "regiao_rotulo_pdf": "Veneto",    // como está impresso
      "categorias": ["secondi_piatti", "porzioni", "dolci", "bevande"],
      "total_itens": 25,
      "preco_min": 4.0,
      "preco_max": 30.0,
      "itens": [
        {
          "id": "1-01-spaghetti-al-sugo",
          "titulo": "Spaghetti Al Sugo",
          "descricao": "Macarrão Tipo Espaguete ao Molho de Tomate",
          "preco": 30.0,
          "preco_formatado": "R$ 30,00",
          "categoria_id": "secondi_piatti",
          "categoria_it": "Secondi Piatti",
          "categoria_pt": "Pratos Principais",
          "categoria_rotulo_pdf": "Secondi Piatti – Pratos Principais",
          "variacoes": [],              // sabores quando o título traz "A / B / C"
          "volume_ml": null,            // derivado da descrição de bebidas
          "unidades": null,             // derivado de "3 unidades", "8 unità"
          "vegano": false,
          "pagina_pdf": 2               // rastreabilidade até a página de origem
        }
      ]
    }
  ]
}
```

### Além dos campos pedidos

O cardápio traz informação útil que também foi capturada: a **região italiana**
que cada barraca representa (as 20 regiões da Itália estão presentes), a
**numeração impressa** (a barraca do Lar Bom Repouso ocupa os números 20 e 21),
**volume das bebidas**, **quantidade por porção**, **sabores/variações** de um
mesmo item, marcação **vegana** e a **página do PDF** de cada item.

## Validação

`scripts/validate_menu.py` confere o JSON contra o PDF e passa em todas as
checagens:

- 645 itens, todos com título, descrição, preço e categoria;
- o multiconjunto de preços do JSON é idêntico ao dos 645 `R$` do PDF;
- todo título e toda descrição existem **literalmente** no texto do PDF;
- nomes, números e regiões das barracas conferem, e a numeração 1–36 não tem buracos;
- ids únicos e preços na faixa de R$ 4,00 a R$ 90,00.

## Identidade visual

**Paleta**

| Cor | Hex | Uso |
| --- | --- | --- |
| Verde festa | `#196B24` | Nome da barraca, título do prato e preço |
| Vermelho festa | `#EE0000` | Cabeçalho de categoria |
| Verde do logo | `#0F7645` | Marca (igreja, arco, letreiro) |
| Vermelho do logo | `#BB2121` | Marca (“33ª”, arco, coração) e aba lateral |
| Verde escuro | `#095A34` | Título “MENU / CARDÁPIO” da capa |
| Bege estuque | `#E5B67E` | Fundo das páginas |
| Branco | `#FFFFFF` | Cartão de conteúdo |
| Preto | `#000000` | Descrição dos pratos |

**Tipografia**

- **Hermann Black** — display, única fonte embutida no PDF; nome/número da barraca e o título da capa.
- **Arial Bold** — títulos de prato, preços e categorias.
- **Calibri** (e Arial regular) — descrições.

**Logo** — `assets/logo-festa-italiana.png` (742 × 386, fundo transparente):
silhueta da Igreja Matriz de São Caetano dentro de um arco verde-e-vermelho,
chapéu de chef, “33ª” em vermelho, “Festa” em capitulares serifadas, “Italiana”
em manuscrita, bandeira da Itália e a assinatura “SÃO CAETANO DO SUL”.

**Motivos** — parreira com cachos de uva e lâmpadas de varal no topo, parede de
tijolos nas laterais, cartão branco de cantos arredondados, abas verde/vermelha
nas bordas e espaguete ilustrado no rodapé.
