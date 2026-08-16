// Croqui em SVG da Festa Italiana — sem dependência, sem tiles, sem rede.
//
//   import { criarCroqui } from './croqui.js';
//   const croqui = criarCroqui(elemento, mapa, { aoSelecionar: n => ... });
//
// Desenha no frame métrico local de data/mapa.json. O SVG usa y para baixo,
// então o eixo norte é invertido na projeção para tela.

(function (raiz) {
  'use strict';
  const cantosDaBarraca = raiz.cantosDaBarraca;

const SVG = 'http://www.w3.org/2000/svg';
  const el = (nome, attrs = {}) => {
    const n = document.createElementNS(SVG, nome);
    for (const [k, v] of Object.entries(attrs)) if (v != null) n.setAttribute(k, v);
    return n;
  };
  
  // Sem paleta propria e sem tema escuro: o croqui usa os tokens do app
  // (`--papel`, `--dourado`, ...) e so cai no valor de reserva quando roda nas
  // paginas avulsas do mapa, que nao os definem. Assim ele nunca desencontra do
  // resto da interface — que e clara de proposito.
  const ESTILO = `
  .croqui { background:var(--papel,#EFE4D4); touch-action:none;
    display:block; width:100%; height:100%; }
  .croqui .via { fill:none; stroke:var(--papel-linha,#DFCEB4);
    stroke-linecap:round; stroke-linejoin:round; }
  .croqui .via-nome { fill:var(--tinta-fraca,#7B6E5D); font:600 3px var(--corpo,system-ui),sans-serif;
    letter-spacing:.12px; text-anchor:middle;
    stroke:var(--papel-linha,#DFCEB4); stroke-width:.9; paint-order:stroke; }
  .croqui .area { stroke:none; }
  .croqui .area.edificado { fill:var(--cartao,#FFFFFF); }
  .croqui .area.verde { fill:var(--verde-suave,#E7EFE6); }
  .croqui .area.pavimento { fill:var(--papel-linha,#DFCEB4); opacity:.55; }
  .croqui .area-nome { fill:var(--tinta-fraca,#7B6E5D); font:600 3.2px var(--corpo,system-ui),sans-serif;
    text-anchor:middle; stroke:var(--papel,#EFE4D4); stroke-width:1.1; paint-order:stroke; }
  /* mesma pilula dourada do .card__numero das listas */
  .croqui .barraca { fill:var(--dourado,#D6A25E); cursor:pointer; }
  .croqui .barraca.selecionada { fill:var(--verde,#0F5F28); }
  .croqui .barraca.apagada { fill:var(--papel-linha,#DFCEB4); }
  .croqui .barraca-num { fill:#3A2A12; font:700 4px var(--corpo,system-ui),sans-serif;
    text-anchor:middle; dominant-baseline:central; pointer-events:none; }
  .croqui .barraca.selecionada ~ .barraca-num { fill:#FFFFFF; }
  .croqui .barraca.apagada ~ .barraca-num { fill:var(--tinta-fraca,#7B6E5D); }
  .croqui .voce { fill:#2F6FED; stroke:#fff; stroke-width:.5; }
  .croqui .voce-raio { fill:#2F6FED; opacity:.15; }
  `;

  function criarCroqui(hospedeiro, mapa, opcoes = {}) {
    const { aoSelecionar, aoArrastar, editavel = false, margem_m = 10 } = opcoes;
  
    const svg = el('svg', { class: 'croqui', xmlns: SVG });
    const folha = el('style');
    folha.textContent = ESTILO;
    svg.append(folha);
    const camadas = {};
    for (const nome of ['areas', 'vias', 'referencias', 'barracas', 'voce']) {
      camadas[nome] = el('g', { class: `camada-${nome}` });
      svg.append(camadas[nome]);
    }
    hospedeiro.replaceChildren(svg);
  
    let selecionada = null;
    let filtro = null;              // Set de números em destaque, ou null
    let vb = null;                  // viewBox corrente, em metros
  
    // --- projeção metros -> tela (y invertido) --------------------------------
    const P = ([x, y]) => `${x},${-y}`;
  
    function limites() {
      // so as barracas e as referencias mandam no enquadramento: as ruas seguem
      // adiante e sairiam do quadro, encolhendo a festa ate virar um borrao.
      const pts = [];
      for (const b of mapa.barracas) pts.push(...cantosDaBarraca(b));
      for (const a of mapa.areas || []) if (a.ponto) pts.push(a.ponto);
      for (const a of mapa.areas || []) if (a.poligono) pts.push(...a.poligono);
      const xs = pts.map((p) => p[0]);
      const ys = pts.map((p) => p[1]);
      return {
        x: Math.min(...xs) - margem_m, y: -Math.max(...ys) - margem_m,
        w: Math.max(...xs) - Math.min(...xs) + margem_m * 2,
        h: Math.max(...ys) - Math.min(...ys) + margem_m * 2,
      };
    }
  
    function enquadrar() {
      const b = limites();
      svg.setAttribute('viewBox', `${b.x} ${b.y} ${b.w} ${b.h}`);
      return { ...b };
    }
  
    // --- desenho --------------------------------------------------------------
    function desenharVias() {
      const g = camadas.vias;
      g.replaceChildren();
      for (const via of mapa.vias || []) {
        const d = via.eixo.map(P).join(' ');
        g.append(el('polyline', { class: 'via', points: d, 'stroke-width': via.largura_m || 8 }));
      }
      for (const via of mapa.vias || []) {
        if (!via.nome) continue;
        const eixo = via.eixo;
        const i = Math.floor(eixo.length / 2);
        const [a, b] = [eixo[Math.max(0, i - 1)], eixo[Math.min(eixo.length - 1, i)]];
        const ang = (Math.atan2(-(b[1] - a[1]), b[0] - a[0]) * 180) / Math.PI;
        const t = el('text', {
          class: 'via-nome', x: 0, y: 1.1,
          transform: `translate(${P(eixo[i])}) rotate(${((ang + 90) % 180) - 90})`,
        });
        t.textContent = via.nome;
        g.append(t);
      }
    }
  
    function desenharAreas() {
      const g = camadas.areas;
      g.replaceChildren();
      for (const a of mapa.areas || []) {
        if (!a.poligono) continue;
        g.append(el('polygon', { class: `area ${a.tipo || ''}`, points: a.poligono.map(P).join(' ') }));
      }
    }
  
    function desenharReferencias() {
      const g = camadas.referencias;
      g.replaceChildren();
      for (const a of mapa.areas || []) {
        if (!a.nome) continue;
        if (a.ponto) {
          g.append(el('circle', { class: 'referencia', cx: a.ponto[0], cy: -a.ponto[1], r: 1.6 }));
          const t = el('text', { class: 'referencia-nome', x: a.ponto[0], y: -a.ponto[1] - 3 });
          t.textContent = a.nome;
          g.append(t);
        } else if (a.rotulo && a.poligono) {
          const n = a.poligono.length;
          const cx = a.poligono.reduce((s, q) => s + q[0], 0) / n;
          const cy = a.poligono.reduce((s, q) => s + q[1], 0) / n;
          const t = el('text', { class: 'area-nome', x: cx, y: -cy });
          t.textContent = a.nome;
          g.append(t);
        }
      }
    }
  
    /** Quanto o quadro cresceu desde o enquadramento inicial. */
    function fatorPino() {
      return (vb ? vb.w : AJUSTE.w) / AJUSTE.w;
    }

    /**
     * A pilula acompanha o zoom para manter o mesmo tamanho na tela, como
     * marcador de mapa. Sem isso ela cresceria junto com o desenho e o engoliria.
     * So o transform muda — nada de refazer 35 grupos por quadro.
     */
    function ajustarEscalaPinos() {
      if (editavel) return;
      const f = fatorPino();
      for (const grupo of camadas.barracas.children) {
        grupo.setAttribute('transform', `${grupo.dataset.base} scale(${f})`);
      }
    }

    function desenharBarracas() {
      const g = camadas.barracas;
      g.replaceChildren();
      for (const b of mapa.barracas) {
        const [cx, cy] = b.centro;
        const apagada = filtro && !filtro.has(b.numero) &&
          !(b.chave && filtro.has(b.chave)) &&
          !b.numeros.some((n) => filtro.has(String(n)));
        const eSelecionada = selecionada != null &&
          (selecionada === b.numero || selecionada === b.chave ||
           b.numeros.some((n) => String(n) === String(selecionada)));
        const classe = `barraca${eSelecionada ? ' selecionada' : ''}${apagada ? ' apagada' : ''}`;
        const texto = b.rotulo || b.numero;

        if (editavel) {
          // no editor a barraca e desenhada como e: retangulo em escala real,
          // virado para o azimute, porque e isso que se esta ajustando ali
          const grupo = el('g', {
            transform: `translate(${cx},${-cy}) rotate(${(b.azimute || 0) - 90})`,
            'data-numero': b.numero,
          });
          grupo.append(el('rect', {
            class: classe,
            x: -(b.profundidade_m || 3) / 2, y: -(b.largura_m || 4) / 2,
            width: b.profundidade_m || 3, height: b.largura_m || 4, rx: 0.4,
          }));
          const t = el('text', {
            class: 'barraca-num', 'font-size': 2.2,
            transform: `rotate(${90 - (b.azimute || 0)})`,
          });
          t.textContent = texto;
          grupo.append(t);
          ligarPonteiro(grupo, b);
          g.append(grupo);
          continue;
        }

        // No mapa e sempre a pilula das listas. Retangulo "em escala real" daria
        // ideia de precisao que este mapa nao tem: as posicoes carregam ~20% de
        // incerteza e os 4x3 m sao valor padrao, nao medida de ninguem.
        const base = `translate(${cx},${-cy})`;
        const grupo = el('g', { transform: base, 'data-numero': b.numero });
        grupo.dataset.base = base;
        const larg = Math.max(8.4, 2.5 * texto.length + 3);
        grupo.append(el('rect', { class: classe, x: -larg / 2, y: -4.2,
                                  width: larg, height: 8.4, rx: 4.2 }));
        const t = el('text', { class: 'barraca-num', 'font-size': texto.length > 2 ? 3.4 : 4 });
        t.textContent = texto;
        grupo.append(t);
        ligarPonteiro(grupo, b);
        g.append(grupo);
      }
      ajustarEscalaPinos();
    }

    const TOLERANCIA_TOQUE = 8;   // px: acima disso o dedo estava navegando, nao tocando

    function ligarPonteiro(grupo, barraca) {
      if (editavel && aoArrastar) {
        // no editor o arrasto move a barraca, entao ele fica com o ponteiro
        grupo.addEventListener('pointerdown', (ev) => {
          ev.stopPropagation();
          selecionar(barraca.numero, true);
          iniciarArrasto(ev, barraca);
        });
        return;
      }
      // No site o ponteiro NAO pode ser interceptado: se um dos dedos da pinca
      // cair sobre uma barraca, o SVG precisa ve-lo mesmo assim. Entao deixa
      // passar e so trata como toque se mal saiu do lugar e estava sozinho.
      let inicio = null;
      grupo.addEventListener('pointerdown', (ev) => {
        inicio = { x: ev.clientX, y: ev.clientY, id: ev.pointerId };
      });
      grupo.addEventListener('pointerup', (ev) => {
        if (!inicio || ev.pointerId !== inicio.id) return;
        const andou = Math.hypot(ev.clientX - inicio.x, ev.clientY - inicio.y);
        inicio = null;
        if (andou <= TOLERANCIA_TOQUE) selecionar(barraca.numero, true);
      });
      grupo.addEventListener('pointercancel', () => { inicio = null; });
    }
  
    function redesenhar() {
      desenharAreas();
      desenharVias();
      desenharReferencias();
      desenharBarracas();
    }
  
    // --- interação ------------------------------------------------------------
    function telaParaMetros(ev) {
      const p = svg.createSVGPoint();
      p.x = ev.clientX; p.y = ev.clientY;
      const m = p.matrixTransform(svg.getScreenCTM().inverse());
      return [m.x, -m.y];
    }
  
    function iniciarArrasto(ev, barraca) {
      const inicio = telaParaMetros(ev);
      const centro0 = [...barraca.centro];
      const mover = (e) => {
        const p = telaParaMetros(e);
        aoArrastar(barraca, [
          +(centro0[0] + p[0] - inicio[0]).toFixed(1),
          +(centro0[1] + p[1] - inicio[1]).toFixed(1),
        ]);
      };
      const soltar = () => {
        window.removeEventListener('pointermove', mover);
        window.removeEventListener('pointerup', soltar);
      };
      window.addEventListener('pointermove', mover);
      window.addEventListener('pointerup', soltar);
    }
  
    // --- pan e pinca ---------------------------------------------------------
    // Um gesto so, para um ou dois dedos: guarda o ponto do mundo que estava sob
    // o meio dos dedos e mantem ele ali enquanto eles se movem. Com um dedo a
    // distancia nao muda, o fator vira 1 e sobra pan puro.
    //
    // O bug que isto conserta: antes cada ponteiro abria o proprio arrasto, com
    // o proprio instantaneo do viewBox, e os dois se sobrescreviam a cada
    // movimento — o mapa tremia e fugia com dois dedos.
    vb = enquadrar();
    const AJUSTE = { ...vb };
    const MIN_M = 12;                       // nao adianta passar disso: barraca tem 4 m
    const MAX_M = AJUSTE.w * 1.6;

    /** Prende o centro do quadro ao conteudo: sem isto da para navegar ate o
     *  vazio e perder o mapa de vista, sem pista de como voltar. */
    function limitar(q) {
      const cx = Math.min(AJUSTE.x + AJUSTE.w, Math.max(AJUSTE.x, q.x + q.w / 2));
      const cy = Math.min(AJUSTE.y + AJUSTE.h, Math.max(AJUSTE.y, q.y + q.h / 2));
      return { x: cx - q.w / 2, y: cy - q.h / 2, w: q.w, h: q.h };
    }

    const aplicar = () => svg.setAttribute('viewBox', `${vb.x} ${vb.y} ${vb.w} ${vb.h}`);


    const ativos = new Map();               // pointerId -> {x, y} em coordenadas de tela
    let ancora = null;

    function medir() {
      const ps = [...ativos.values()];
      if (!ps.length) return null;
      const meio = {
        x: ps.reduce((t, q) => t + q.x, 0) / ps.length,
        y: ps.reduce((t, q) => t + q.y, 0) / ps.length,
      };
      const dist = ps.length >= 2 ? Math.hypot(ps[1].x - ps[0].x, ps[1].y - ps[0].y) : 0;
      return { meio, dist };
    }

    /** Refaz o instantaneo — tambem ao entrar ou sair um dedo, senao o mapa salta. */
    function ancorar() {
      const m = medir();
      if (!m) { ancora = null; return; }
      const r = svg.getBoundingClientRect();
      ancora = {
        vb: { ...vb }, r, dist: m.dist,
        mundo: {
          x: vb.x + (m.meio.x - r.left) * vb.w / r.width,
          y: vb.y + (m.meio.y - r.top) * vb.h / r.height,
        },
      };
    }

    function aoMover(ev) {
      if (!ativos.has(ev.pointerId)) return;
      ativos.set(ev.pointerId, { x: ev.clientX, y: ev.clientY });
      if (!ancora) return;
      const m = medir();
      const { r, mundo } = ancora;
      let k = 1;
      if (ancora.dist > 0 && m.dist > 0) k = ancora.dist / m.dist;  // dedos afastam -> quadro encolhe
      let w = Math.min(MAX_M, Math.max(MIN_M, ancora.vb.w * k));
      k = w / ancora.vb.w;                                          // k depois do limite
      const h = ancora.vb.h * k;
      vb = limitar({
        x: mundo.x - (m.meio.x - r.left) * w / r.width,
        y: mundo.y - (m.meio.y - r.top) * h / r.height,
        w, h,
      });
      aplicar();
      ajustarEscalaPinos();
    }

    function aoSoltar(ev) {
      if (!ativos.delete(ev.pointerId)) return;
      ancorar();                            // o dedo que ficou continua de onde esta
      if (!ativos.size) {
        window.removeEventListener('pointermove', aoMover);
        window.removeEventListener('pointerup', aoSoltar);
        window.removeEventListener('pointercancel', aoSoltar);
      }
    }

    svg.addEventListener('pointerdown', (ev) => {
      if (ativos.size === 0) {
        window.addEventListener('pointermove', aoMover);
        window.addEventListener('pointerup', aoSoltar);
        window.addEventListener('pointercancel', aoSoltar);
      }
      ativos.set(ev.pointerId, { x: ev.clientX, y: ev.clientY });
      ancorar();
    });

    svg.addEventListener('wheel', (ev) => {
      ev.preventDefault();
      const r = svg.getBoundingClientRect();
      const mundo = {
        x: vb.x + (ev.clientX - r.left) * vb.w / r.width,
        y: vb.y + (ev.clientY - r.top) * vb.h / r.height,
      };
      const alvo = vb.w * (ev.deltaY > 0 ? 1.12 : 1 / 1.12);
      const w = Math.min(MAX_M, Math.max(MIN_M, alvo));
      const h = vb.h * (w / vb.w);
      vb = limitar({
        x: mundo.x - (ev.clientX - r.left) * w / r.width,
        y: mundo.y - (ev.clientY - r.top) * h / r.height,
        w, h,
      });
      aplicar();
      ajustarEscalaPinos();
    }, { passive: false });

    function selecionar(numero, porToque) {
      selecionada = numero;
      desenharBarracas();
      // so o toque avisa quem escuta: selecionar por codigo (vindo da URL, por
      // exemplo) nao pode disparar navegacao, senao o app entra em loop consigo
      if (porToque && aoSelecionar) aoSelecionar(numero, mapa.barracas.find((b) => b.numero === numero));
    }
  
    /** Apaga tudo que não estiver na lista — para amarrar o mapa ao filtro de pratos. */
    function destacar(numeros) {
      filtro = numeros ? new Set(numeros.map(String)) : null;
      desenharBarracas();
    }
  
    /** Ponto azul. `posicao` em metros do frame local, `precisao_m` opcional. */
    function marcarVoce(posicao, precisao_m = 0) {
      camadas.voce.replaceChildren();
      if (!posicao) return;
      const [x, y] = posicao;
      if (precisao_m > 0) camadas.voce.append(el('circle', { class: 'voce-raio', cx: x, cy: -y, r: precisao_m }));
      camadas.voce.append(el('circle', { class: 'voce', cx: x, cy: -y, r: 2 }));
    }
  
    redesenhar();
    desenharBarracas();
    return { svg, redesenhar, enquadrar: () => { vb = enquadrar(); }, selecionar, destacar, marcarVoce,
             get selecionada() { return selecionada; } };
  }

  raiz.criarCroqui = criarCroqui;
})(window.FestaMapa = window.FestaMapa || {});
