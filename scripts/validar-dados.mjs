#!/usr/bin/env node
/**
 * Valida os arquivos de dados do cardapio.
 *
 * Roda em duas camadas:
 *   1. Estrutura  - valida cada arquivo contra o JSON Schema correspondente
 *                   (subconjunto de JSON Schema, sem dependencias externas).
 *   2. Integridade - regras entre arquivos, que JSON Schema nao consegue expressar:
 *                   ids unicos, categorias/restricoes existentes, precos coerentes.
 *
 * Uso: node scripts/validar-dados.mjs
 */

import { readFileSync, existsSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const raiz = join(dirname(fileURLToPath(import.meta.url)), '..');
const erros = [];
const avisos = [];

const erro = (arquivo, caminho, msg) => erros.push(`${arquivo}${caminho ? ` ${caminho}` : ''}: ${msg}`);
const aviso = (arquivo, caminho, msg) => avisos.push(`${arquivo}${caminho ? ` ${caminho}` : ''}: ${msg}`);

function ler(caminhoRelativo) {
  const absoluto = join(raiz, caminhoRelativo);
  if (!existsSync(absoluto)) {
    erro(caminhoRelativo, '', 'arquivo nao encontrado');
    return null;
  }
  try {
    return JSON.parse(readFileSync(absoluto, 'utf8'));
  } catch (e) {
    erro(caminhoRelativo, '', `JSON invalido — ${e.message}`);
    return null;
  }
}

/* ---------------------------------------------------------------- camada 1 */

const tipoDe = (v) => (v === null ? 'null' : Array.isArray(v) ? 'array' : typeof v === 'number' ? 'number' : typeof v);

function resolverRef(ref, schemaRaiz) {
  // suporta apenas refs locais no formato #/$defs/nome
  const partes = ref.replace(/^#\//, '').split('/');
  return partes.reduce((no, parte) => (no ? no[parte] : undefined), schemaRaiz);
}

function validarSchema(valor, schema, schemaRaiz, arquivo, caminho = '') {
  if (schema.$ref) return validarSchema(valor, resolverRef(schema.$ref, schemaRaiz), schemaRaiz, arquivo, caminho);

  if (schema.enum && !schema.enum.includes(valor)) {
    erro(arquivo, caminho, `valor "${valor}" fora do permitido (${schema.enum.join(', ')})`);
    return;
  }

  if (schema.type) {
    const aceitos = Array.isArray(schema.type) ? schema.type : [schema.type];
    const tipo = tipoDe(valor);
    const compativel = aceitos.includes(tipo) || (tipo === 'number' && aceitos.includes('integer') && Number.isInteger(valor));
    if (!compativel) {
      erro(arquivo, caminho, `esperado ${aceitos.join(' ou ')}, recebido ${tipo}`);
      return;
    }
  }

  if (typeof valor === 'string') {
    if (schema.minLength !== undefined && valor.length < schema.minLength) erro(arquivo, caminho, 'nao pode ficar vazio');
    if (schema.pattern && !new RegExp(schema.pattern).test(valor)) erro(arquivo, caminho, `"${valor}" nao segue o formato esperado (${schema.pattern})`);
  }

  if (typeof valor === 'number') {
    if (schema.minimum !== undefined && valor < schema.minimum) erro(arquivo, caminho, `deve ser >= ${schema.minimum}`);
    if (schema.maximum !== undefined && valor > schema.maximum) erro(arquivo, caminho, `deve ser <= ${schema.maximum}`);
  }

  if (Array.isArray(valor)) {
    if (schema.minItems !== undefined && valor.length < schema.minItems) erro(arquivo, caminho, `precisa de pelo menos ${schema.minItems} item(ns)`);
    if (schema.uniqueItems && new Set(valor.map((v) => JSON.stringify(v))).size !== valor.length) erro(arquivo, caminho, 'contem itens repetidos');
    if (schema.items) valor.forEach((item, i) => validarSchema(item, schema.items, schemaRaiz, arquivo, `${caminho}[${i}]`));
  }

  if (valor !== null && typeof valor === 'object' && !Array.isArray(valor)) {
    for (const obrigatorio of schema.required ?? []) {
      if (valor[obrigatorio] === undefined) erro(arquivo, caminho, `campo obrigatorio ausente: "${obrigatorio}"`);
    }
    for (const [chave, conteudo] of Object.entries(valor)) {
      const subSchema = schema.properties?.[chave];
      if (subSchema) validarSchema(conteudo, subSchema, schemaRaiz, arquivo, `${caminho}.${chave}`);
      else if (schema.additionalProperties === false) erro(arquivo, caminho, `campo desconhecido: "${chave}"`);
    }
  }
}

function validarArquivo(caminhoDados, caminhoSchema) {
  const dados = ler(caminhoDados);
  const schema = ler(caminhoSchema);
  if (!dados || !schema) return null;
  validarSchema(dados, schema, schema, caminhoDados);
  return dados;
}

/* ---------------------------------------------------------------- camada 2 */

const indice = validarArquivo('data/index.json', 'schemas/index.schema.json');
const categorias = validarArquivo('data/taxonomia/categorias.json', 'schemas/categorias.schema.json');
const restricoes = validarArquivo('data/taxonomia/restricoes.json', 'schemas/restricoes.schema.json');

const idsCategoria = new Set((categorias?.categorias ?? []).map((c) => c.id));
const idsAlergeno = new Set((restricoes?.alergenos ?? []).map((a) => a.id));
const idsDieta = new Set((restricoes?.dietas ?? []).map((d) => d.id));

if (indice) {
  const idsEdicao = (indice.edicoes ?? []).map((e) => e.id);
  if (!idsEdicao.includes(indice.edicaoAtual)) {
    erro('data/index.json', '.edicaoAtual', `"${indice.edicaoAtual}" nao esta na lista de edicoes`);
  }
  const repetidos = idsEdicao.filter((id, i) => idsEdicao.indexOf(id) !== i);
  if (repetidos.length) erro('data/index.json', '.edicoes', `ids repetidos: ${[...new Set(repetidos)].join(', ')}`);

  for (const edicao of indice.edicoes ?? []) {
    const base = join('data', edicao.caminho);
    const arquivoFesta = join(base, 'festa.json');
    const arquivoCardapio = join(base, 'cardapio.json');

    const festa = validarArquivo(arquivoFesta, 'schemas/festa.schema.json');
    const cardapio = validarArquivo(arquivoCardapio, 'schemas/cardapio.schema.json');

    if (festa) {
      if (festa.id !== edicao.id) erro(arquivoFesta, '.id', `"${festa.id}" difere do id no index ("${edicao.id}")`);
      if (festa.ano !== edicao.ano) erro(arquivoFesta, '.ano', `${festa.ano} difere do ano no index (${edicao.ano})`);

      const { inicio, fim, dias = [] } = festa.funcionamento ?? {};
      if (inicio && fim && inicio > fim) erro(arquivoFesta, '.funcionamento', `inicio (${inicio}) e posterior ao fim (${fim})`);
      dias.forEach((dia, i) => {
        const onde = `.funcionamento.dias[${i}]`;
        if (inicio && fim && (dia.data < inicio || dia.data > fim)) erro(arquivoFesta, onde, `data ${dia.data} fora do periodo ${inicio}–${fim}`);
        // fechamento antes da abertura e legitimo quando a barraca vira a madrugada (ex.: 18:00–01:00)
        if (dia.abertura === dia.fechamento) erro(arquivoFesta, onde, 'abertura e fechamento sao iguais');
      });
      const datas = dias.map((d) => d.data);
      const datasRepetidas = datas.filter((d, i) => datas.indexOf(d) !== i);
      if (datasRepetidas.length) erro(arquivoFesta, '.funcionamento.dias', `datas repetidas: ${[...new Set(datasRepetidas)].join(', ')}`);

      const idsInfo = (festa.informacoes ?? []).map((b) => b.id);
      const infoRepetida = idsInfo.filter((id, i) => idsInfo.indexOf(id) !== i);
      if (infoRepetida.length) erro(arquivoFesta, '.informacoes', `ids repetidos: ${[...new Set(infoRepetida)].join(', ')}`);
    }

    if (cardapio) {
      if (cardapio.edicaoId !== edicao.id) erro(arquivoCardapio, '.edicaoId', `"${cardapio.edicaoId}" difere do id no index ("${edicao.id}")`);

      const idsBarraca = new Set();
      const numerosBarraca = new Map();
      const idsPrato = new Set();

      for (const barraca of cardapio.barracas ?? []) {
        const ondeBarraca = `.barracas[${barraca.id}]`;
        if (idsBarraca.has(barraca.id)) erro(arquivoCardapio, ondeBarraca, 'id de barraca repetido');
        idsBarraca.add(barraca.id);

        if (numerosBarraca.has(barraca.numero)) {
          erro(arquivoCardapio, ondeBarraca, `numero ${barraca.numero} ja usado pela barraca "${numerosBarraca.get(barraca.numero)}"`);
        }
        numerosBarraca.set(barraca.numero, barraca.id);

        if (!(barraca.pratos ?? []).length) aviso(arquivoCardapio, ondeBarraca, 'barraca sem nenhum prato');

        for (const prato of barraca.pratos ?? []) {
          const onde = `${ondeBarraca}.pratos[${prato.id}]`;
          if (idsPrato.has(prato.id)) erro(arquivoCardapio, onde, 'id de prato repetido — ids de prato precisam ser unicos no cardapio inteiro (sao a chave dos favoritos)');
          idsPrato.add(prato.id);

          if (!idsCategoria.has(prato.categoria)) erro(arquivoCardapio, onde, `categoria "${prato.categoria}" nao existe em data/taxonomia/categorias.json`);

          const { contem = [], podeConter = [], adequadoPara = [] } = prato.restricoes ?? {};
          for (const id of [...contem, ...podeConter]) {
            if (!idsAlergeno.has(id)) erro(arquivoCardapio, onde, `alergeno "${id}" nao existe em data/taxonomia/restricoes.json`);
          }
          for (const id of adequadoPara) {
            if (!idsDieta.has(id)) erro(arquivoCardapio, onde, `dieta "${id}" nao existe em data/taxonomia/restricoes.json`);
          }
          for (const id of contem) {
            if (podeConter.includes(id)) erro(arquivoCardapio, onde, `"${id}" aparece em contem e em podeConter ao mesmo tempo`);
          }

          // coerencia entre o que o prato contem e as dietas que ele declara atender
          const conflitos = [
            ['gluten', 'sem-gluten'], ['leite', 'sem-lactose'],
            ['leite', 'vegano'], ['ovo', 'vegano'],
            ['peixe', 'vegetariano'], ['frutos-do-mar', 'vegetariano'],
            ['peixe', 'vegano'], ['frutos-do-mar', 'vegano'],
          ];
          for (const [alergeno, dieta] of conflitos) {
            if (contem.includes(alergeno) && adequadoPara.includes(dieta)) {
              erro(arquivoCardapio, onde, `contradicao: contem "${alergeno}" mas se declara "${dieta}"`);
            }
          }
          if (adequadoPara.includes('vegano') && !adequadoPara.includes('vegetariano')) {
            aviso(arquivoCardapio, onde, 'e vegano mas nao esta marcado como vegetariano — o filtro de vegetarianos nao vai encontra-lo');
          }

          const variacoes = prato.variacoes ?? [];
          if (variacoes.length) {
            if (prato.preco !== null && prato.preco !== undefined) {
              erro(arquivoCardapio, onde, 'tem variacoes e tambem preco unico — use um ou outro');
            }
            const idsVariacao = variacoes.map((v) => v.id);
            if (new Set(idsVariacao).size !== idsVariacao.length) erro(arquivoCardapio, onde, 'ids de variacao repetidos');
            if (variacoes.every((v) => v.preco === null)) aviso(arquivoCardapio, onde, 'nenhuma variacao tem preco definido');
          } else if (prato.preco === null || prato.preco === undefined) {
            aviso(arquivoCardapio, onde, 'sem preco definido — a interface vai exibir "a definir"');
          }
        }
      }
    }
  }
}

/* ---------------------------------------------------------------- resultado */

for (const a of avisos) console.warn(`  aviso  ${a}`);
for (const e of erros) console.error(`  ERRO   ${e}`);

console.log('');
if (erros.length) {
  console.error(`✗ ${erros.length} erro(s) e ${avisos.length} aviso(s). Corrija os erros antes de publicar.`);
  process.exit(1);
}
console.log(`✓ Dados validos${avisos.length ? ` (${avisos.length} aviso(s))` : ''}.`);
