// Croqui em SVG da Festa Italiana — sem dependência, sem tiles, sem rede.
//
//   import { criarCroqui } from './croqui.js';
//   const croqui = criarCroqui(elemento, mapa, { aoSelecionar: n => ... });
//
// Desenha no frame métrico local de data/mapa.json. O SVG usa y para baixo,
// então o eixo norte é invertido na projeção para tela.

import { cantosDaBarraca } from './geo.js';

const SVG = 'http://www.w3.org/2000/svg';
const el = (nome, attrs = {}) => {
  const n = document.createElementNS(SVG, nome);
  for (const [k, v] of Object.entries(attrs)) if (v != null) n.setAttribute(k, v);
  return n;
};

const ESTILO = `
.croqui { --verde:#196B24; --verde-escuro:#095A34; --vermelho:#EE0000;
  --vermelho-logo:#BB2121; --bege:#E5B67E; --papel:#FFF8EE; --tinta:#2B1D10;
  --asfalto:#E8DCC8; --meio-fio:#CBB795;
  background:var(--papel); touch-action:none; display:block; width:100%; height:100%; }
@media (prefers-color-scheme: dark) { .croqui {
  --papel:#14100B; --tinta:#F3E7D4; --asfalto:#2A2318; --meio-fio:#3D3423;
  --verde:#4CAF5B; --verde-escuro:#2E7D46; --vermelho:#FF5A4D; --bege:#4A3B27; } }
.croqui .via-base { stroke:var(--meio-fio); stroke-linecap:round; stroke-linejoin:round; fill:none; }
.croqui .via { stroke:var(--asfalto); stroke-linecap:round; stroke-linejoin:round; fill:none; }
.croqui .via-nome { fill:var(--tinta); opacity:.55; font:600 3px system-ui,sans-serif;
  letter-spacing:.12px; text-anchor:middle; }
.croqui .referencia { fill:var(--verde-escuro); opacity:.75; }
.croqui .referencia-nome { fill:var(--verde-escuro); font:600 3.4px system-ui,sans-serif;
  text-anchor:middle; opacity:.85; }
.croqui .barraca { fill:var(--verde); stroke:var(--papel); stroke-width:.35; cursor:pointer; }
.croqui .barraca:hover { fill:var(--verde-escuro); }
.croqui .barraca.selecionada { fill:var(--vermelho); }
.croqui .barraca.apagada { fill:var(--meio-fio); }
.croqui .barraca-num { fill:#fff; font:700 2.4px system-ui,sans-serif;
  paint-order:stroke; }
.croqui .barraca-num.pino { font-size:4px;
  text-anchor:middle; dominant-baseline:central; pointer-events:none; }
.croqui .voce { fill:#2F6FED; stroke:#fff; stroke-width:.5; }
.croqui .voce-raio { fill:#2F6FED; opacity:.15; }
`;

export function criarCroqui(hospedeiro, mapa, opcoes = {}) {
  const { aoSelecionar, aoArrastar, editavel = false, margem_m = 25 } = opcoes;

  const svg = el('svg', { class: 'croqui', xmlns: SVG });
  const folha = el('style');
  folha.textContent = ESTILO;
  svg.append(folha);
  const camadas = {};
  for (const nome of ['vias', 'referencias', 'barracas', 'voce']) {
    camadas[nome] = el('g', { class: `camada-${nome}` });
    svg.append(camadas[nome]);
  }
  hospedeiro.replaceChildren(svg);

  let selecionada = null;
  let filtro = null;              // Set de números em destaque, ou null

  // --- projeção metros -> tela (y invertido) --------------------------------
  const P = ([x, y]) => `${x},${-y}`;

  function limites() {
    // so as barracas e as referencias mandam no enquadramento: as ruas seguem
    // adiante e sairiam do quadro, encolhendo a festa ate virar um borrao.
    const pts = [];
    for (const b of mapa.barracas) pts.push(...cantosDaBarraca(b));
    for (const a of mapa.areas || []) if (a.ponto) pts.push(a.ponto);
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
      g.append(el('polyline', { class: 'via-base', points: d, 'stroke-width': (via.largura_m || 8) + 1.5 }));
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

  function desenharReferencias() {
    const g = camadas.referencias;
    g.replaceChildren();
    for (const a of mapa.areas || []) {
      if (!a.ponto) continue;
      g.append(el('circle', { class: 'referencia', cx: a.ponto[0], cy: -a.ponto[1], r: 1.6 }));
      const t = el('text', { class: 'referencia-nome', x: a.ponto[0], y: -a.ponto[1] - 3 });
      t.textContent = a.nome;
      g.append(t);
    }
  }

  // Um retangulo de 4 m tem ~6 px quando o quadro inteiro cabe na tela. Abaixo
  // desse zoom a barraca vira pino numerado; ao aproximar, volta a escala real.
  const LIMIAR_PINO_M = 90;

  function desenharBarracas() {
    const g = camadas.barracas;
    g.replaceChildren();
    const pino = (vb?.w ?? Infinity) > LIMIAR_PINO_M;
    for (const b of mapa.barracas) {
      const [cx, cy] = b.centro;
      const grupo = el('g', {
        transform: `translate(${cx},${-cy}) rotate(${(b.azimute || 0) - 90})`,
        'data-numero': b.numero,
      });
      const apagada = filtro && !b.numeros.some((n) => filtro.has(String(n))) && !filtro.has(b.numero);
      const classe = `barraca${b.numero === selecionada ? ' selecionada' : ''}${apagada ? ' apagada' : ''}`;
      if (pino) {
        // a barraca dupla tem rotulo "20/21": o pino cresce com o texto, senao corta
        const texto = b.rotulo || b.numero;
        const larg = Math.max(8.4, 2.5 * texto.length + 3);
        grupo.append(el('rect', { class: classe, x: -larg / 2, y: -4.2,
                                  width: larg, height: 8.4, rx: 4.2 }));
        const rot = el('text', {
          class: 'barraca-num pino', 'font-size': texto.length > 2 ? 3.4 : 4,
          transform: `rotate(${90 - (b.azimute || 0)})`,
        });
        rot.textContent = texto;
        grupo.append(rot);
        ligarPonteiro(grupo, b);
        g.append(grupo);
        continue;
      }
      grupo.append(el('rect', {
        class: `barraca${b.numero === selecionada ? ' selecionada' : ''}${apagada ? ' apagada' : ''}`,
        x: -(b.profundidade_m || 3) / 2, y: -(b.largura_m || 4) / 2,
        width: b.profundidade_m || 3, height: b.largura_m || 4, rx: 0.4,
      }));
      const t = el('text', { class: 'barraca-num', transform: `rotate(${90 - (b.azimute || 0)})` });
      t.textContent = b.rotulo || b.numero;
      grupo.append(t);
      ligarPonteiro(grupo, b);
      g.append(grupo);
    }
  }

  let vb = null;

  function ligarPonteiro(grupo, barraca) {
    grupo.addEventListener('pointerdown', (ev) => {
      ev.stopPropagation();
      selecionar(barraca.numero);
      if (editavel && aoArrastar) iniciarArrasto(ev, barraca);
    });
  }

  function redesenhar() {
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

  // pan e zoom
  vb = enquadrar();
  const aplicar = () => svg.setAttribute('viewBox', `${vb.x} ${vb.y} ${vb.w} ${vb.h}`);
  svg.addEventListener('wheel', (ev) => {
    ev.preventDefault();
    const k = ev.deltaY > 0 ? 1.12 : 1 / 1.12;
    const p = svg.createSVGPoint();
    p.x = ev.clientX; p.y = ev.clientY;
    const m = p.matrixTransform(svg.getScreenCTM().inverse());
    const antes = vb.w > LIMIAR_PINO_M;
    vb = { x: m.x - (m.x - vb.x) * k, y: m.y - (m.y - vb.y) * k, w: vb.w * k, h: vb.h * k };
    aplicar();
    if (antes !== vb.w > LIMIAR_PINO_M) desenharBarracas();
  }, { passive: false });
  svg.addEventListener('pointerdown', (ev) => {
    const p0 = { x: ev.clientX, y: ev.clientY };
    const vb0 = { ...vb };
    const escala = vb.w / svg.clientWidth;
    const mover = (e) => {
      vb = { ...vb0, x: vb0.x - (e.clientX - p0.x) * escala, y: vb0.y - (e.clientY - p0.y) * escala };
      aplicar();
    };
    const soltar = () => {
      window.removeEventListener('pointermove', mover);
      window.removeEventListener('pointerup', soltar);
    };
    window.addEventListener('pointermove', mover);
    window.addEventListener('pointerup', soltar);
  });

  function selecionar(numero) {
    selecionada = numero;
    desenharBarracas();
    if (aoSelecionar) aoSelecionar(numero, mapa.barracas.find((b) => b.numero === numero));
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
