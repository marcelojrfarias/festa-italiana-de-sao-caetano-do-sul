/**
 * Tipos dos dados estaticos da Festa Italiana.
 *
 * Espelham os JSON Schemas em /schemas. Ao mudar um schema, mude aqui tambem —
 * `node scripts/validar-dados.mjs` valida os dados, mas nao valida estes tipos.
 */

/** Data no formato ISO `AAAA-MM-DD`. */
export type DataISO = string;
/** Hora no formato 24h `HH:MM`. */
export type Hora = string;
/** Identificador em kebab-case: `[a-z0-9-]+`. */
export type Id = string;

/* ------------------------------------------------------------------ indice */

export type StatusEdicao = 'rascunho' | 'publicada' | 'arquivada';

export interface ResumoEdicao {
  id: Id;
  ano: number;
  rotulo: string;
  /** Caminho da pasta da edicao, relativo a /data. Ex.: `edicoes/2026`. */
  caminho: string;
  status: StatusEdicao;
}

export interface IndiceDados {
  /** Versao do formato dos arquivos. Incrementar em mudanca incompativel. */
  versaoDados: number;
  /** Id da edicao que o app abre por padrao. */
  edicaoAtual: Id;
  edicoes: ResumoEdicao[];
}

/* -------------------------------------------------------------- taxonomia */

export interface Categoria {
  id: Id;
  rotulo: string;
  icone?: string;
  ordem: number;
}

export interface TermoRestricao {
  id: Id;
  rotulo: string;
  icone?: string;
  descricao?: string;
}

export interface Categorias {
  categorias: Categoria[];
}

export interface Restricoes {
  /** O que o prato pode CONTER — usado em filtros de exclusao. */
  alergenos: TermoRestricao[];
  /** O que o prato pode ATENDER — usado em filtros de inclusao. */
  dietas: TermoRestricao[];
}

/* ------------------------------------------------------------------ festa */

export interface Endereco {
  logradouro: string;
  numero?: string;
  complemento?: string;
  bairro?: string;
  cidade: string;
  /** Sigla do estado com 2 letras maiusculas. */
  estado: string;
  cep?: string;
}

export interface Coordenadas {
  latitude: number;
  longitude: number;
}

export interface Local {
  nome: string;
  endereco: Endereco;
  coordenadas?: Coordenadas | null;
  /** Texto livre em Markdown: transporte, estacionamento, acessibilidade. */
  comoChegar?: string;
}

export interface DiaDeFuncionamento {
  data: DataISO;
  abertura: Hora;
  /** Pode ser menor que `abertura` quando a festa vira a madrugada (18:00 → 01:00). */
  fechamento: Hora;
  observacao?: string;
}

export interface Funcionamento {
  /** Nome IANA do fuso. Sempre `America/Sao_Paulo` aqui. */
  fusoHorario: string;
  inicio: DataISO;
  fim: DataISO;
  observacao?: string;
  dias: DiaDeFuncionamento[];
}

/** Bloco de conteudo livre: programacao de shows, o que levar, regras etc. */
export interface BlocoDeInformacao {
  id: Id;
  titulo: string;
  icone?: string;
  ordem: number;
  /** Markdown. Renderizar com sanitizacao. */
  conteudo: string;
}

export interface Contato {
  site?: string;
  instagram?: string;
  facebook?: string;
  whatsapp?: string;
  telefone?: string;
  email?: string;
}

export interface Festa {
  id: Id;
  ano: number;
  nome: string;
  subtitulo?: string;
  descricao?: string;
  local: Local;
  funcionamento: Funcionamento;
  informacoes?: BlocoDeInformacao[];
  contato?: Contato;
}

/* --------------------------------------------------------------- cardapio */

export interface VariacaoDePrato {
  id: Id;
  /** Ex.: "Meia porção", "Taça", "Garrafa". */
  nome: string;
  /** `null` quando o preco ainda nao foi definido. */
  preco: number | null;
}

export interface RestricoesDoPrato {
  /** Alergenos presentes na receita. */
  contem: Id[];
  /** Alergenos possiveis por contaminacao cruzada no preparo. */
  podeConter?: Id[];
  /** Dietas que o prato atende. Declarado explicitamente, nunca deduzido. */
  adequadoPara: Id[];
}

export interface Prato {
  /** Unico no cardapio inteiro — e a chave usada nos favoritos do usuario. */
  id: Id;
  nome: string;
  descricao?: string;
  categoria: Id;
  /** Preco unico. Use `null` para "a definir". Deve ser `null` se houver `variacoes`. */
  preco?: number | null;
  /** Tamanhos/opcoes do mesmo prato. Vazio quando ha preco unico. */
  variacoes?: VariacaoDePrato[];
  restricoes: RestricoesDoPrato;
  destaque?: boolean;
  /** Caminho relativo a pasta publica de imagens, ou `null`. */
  imagem?: string | null;
  ordem?: number;
  /** `false` esconde o prato sem apagar o historico. */
  ativo?: boolean;
}

export interface LocalizacaoDaBarraca {
  setor?: string;
  /** Referencia em texto livre. Ex.: "ao lado do palco principal". */
  referencia?: string;
  /** Posicao relativa (0–1) sobre a imagem do mapa da festa, quando houver. */
  coordenadas?: { x: number; y: number } | null;
}

export interface Barraca {
  id: Id;
  /** Numero exibido na barraca. Unico dentro da edicao. */
  numero: number;
  titulo: string;
  descricao?: string;
  /** Entidade responsavel pela barraca, quando aplicavel. */
  responsavel?: string;
  localizacao?: LocalizacaoDaBarraca;
  ativa?: boolean;
  ordem?: number;
  pratos: Prato[];
}

export interface Cardapio {
  edicaoId: Id;
  /** Codigo ISO 4217. `BRL` aqui. */
  moeda: string;
  atualizadoEm?: DataISO;
  observacao?: string;
  barracas: Barraca[];
}

/* ------------------------------------------- dados do usuario (dispositivo) */

/** Versao do formato guardado no dispositivo. Incrementar exige migracao. */
export type VersaoArmazenamento = 1;

export interface BuscaRecente {
  termo: string;
  /** Timestamp ISO 8601 de quando a busca foi feita. */
  em: string;
}

export interface FiltrosSalvos {
  categorias: Id[];
  /** Alergenos que o usuario quer EVITAR. */
  evitar: Id[];
  /** Dietas que o prato precisa atender. */
  exigir: Id[];
}

export interface PreferenciasDoUsuario {
  tema: 'claro' | 'escuro' | 'sistema';
  /** Filtros aplicados automaticamente ao abrir o app. */
  filtrosPadrao: FiltrosSalvos;
}

/**
 * Formato guardado em localStorage.
 *
 * Chaves (ver docs/arquitetura-de-dados.md):
 *   festa-italiana:v1:preferencias         → PreferenciasDoUsuario   (vale para todas as edicoes)
 *   festa-italiana:v1:buscas-recentes      → BuscaRecente[]          (vale para todas as edicoes)
 *   festa-italiana:v1:<edicaoId>:favoritos → Id[] de pratos          (por edicao)
 */
export interface DadosLocais {
  preferencias: PreferenciasDoUsuario;
  buscasRecentes: BuscaRecente[];
  favoritosPorEdicao: Record<Id, Id[]>;
}
