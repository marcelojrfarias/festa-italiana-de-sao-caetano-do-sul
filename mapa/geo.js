// Geometria do croqui da festa.
//
// Tudo trabalha no frame métrico local de data/mapa.json (x = leste, y = norte,
// em metros). A conversão para lat/lng é uma função pura aplicada só quando
// `frame.origem.latlng` for preenchido — enquanto for null, o croqui funciona
// igual, só não tem "você está aqui".

// Script simples, nao modulo ES: o app.js do site e um IIFE global e o build
// so concatena o texto deste arquivo. Um `export` aqui quebraria aquele bundle.
(function (raiz) {
  'use strict';

const RAIO_TERRA = 6378137;
  const rad = (g) => (g * Math.PI) / 180;
  const grau = (r) => (r * 180) / Math.PI;
  
  /** Metros no frame local -> [lat, lng]. null se o mapa não foi georreferenciado. */
  function metrosParaLatLng(frame, [x, y]) {
    const origem = frame?.origem?.latlng;
    if (!origem) return null;
    const [lat0, lng0] = origem;
    const giro = rad(frame.origem.azimute_do_eixo_y || 0);
    // gira o frame para alinhar o eixo y com o norte verdadeiro
    const leste = x * Math.cos(giro) + y * Math.sin(giro);
    const norte = -x * Math.sin(giro) + y * Math.cos(giro);
    const lat = lat0 + grau(norte / RAIO_TERRA);
    const lng = lng0 + grau(leste / (RAIO_TERRA * Math.cos(rad(lat0))));
    return [lat, lng];
  }
  
  /** [lat, lng] -> metros no frame local. null se o mapa não foi georreferenciado. */
  function latLngParaMetros(frame, [lat, lng]) {
    const origem = frame?.origem?.latlng;
    if (!origem) return null;
    const [lat0, lng0] = origem;
    const norte = rad(lat - lat0) * RAIO_TERRA;
    const leste = rad(lng - lng0) * RAIO_TERRA * Math.cos(rad(lat0));
    const giro = rad(frame.origem.azimute_do_eixo_y || 0);
    return [
      leste * Math.cos(giro) - norte * Math.sin(giro),
      leste * Math.sin(giro) + norte * Math.cos(giro),
    ];
  }
  
  /**
   * Os 4 cantos do retângulo da barraca, em metros.
   * `azimute` é a direção da frente, em graus no sentido horário a partir do norte.
   */
  function cantosDaBarraca(b) {
    const a = rad(b.azimute || 0);
    const frente = [Math.sin(a), Math.cos(a)];          // eixo da profundidade
    const lado = [Math.cos(a), -Math.sin(a)];           // eixo da largura (frente)
    const [cx, cy] = b.centro;
    const hp = (b.profundidade_m || 3) / 2;
    const hl = (b.largura_m || 4) / 2;
    return [[-1, -1], [1, -1], [1, 1], [-1, 1]].map(([sl, sp]) => [
      cx + lado[0] * hl * sl + frente[0] * hp * sp,
      cy + lado[1] * hl * sl + frente[1] * hp * sp,
    ]);
  }
  
  function distancia([ax, ay], [bx, by]) {
    return Math.hypot(bx - ax, by - ay);
  }
  
  /** Barraca mais próxima de um ponto em metros. */
  function barracaMaisProxima(barracas, ponto) {
    let melhor = null;
    let menor = Infinity;
    for (const b of barracas) {
      const d = distancia(b.centro, ponto);
      if (d < menor) { menor = d; melhor = b; }
    }
    return melhor && { barraca: melhor, distancia_m: Math.round(menor) };
  }

  raiz.metrosParaLatLng = metrosParaLatLng;
  raiz.latLngParaMetros = latLngParaMetros;
  raiz.cantosDaBarraca = cantosDaBarraca;
  raiz.distancia = distancia;
  raiz.barracaMaisProxima = barracaMaisProxima;
})(window.FestaMapa = window.FestaMapa || {});
