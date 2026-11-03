// Crayon Case demo: "Alder Street" (a fictional case). One page, one take, 29 s.
// World = the page, 2400×1350 (full page = CAM.s 0.8). Paper coordinates = world × 0.8.
import { layer, clear, line, fill, dab, text, ellipse, handCircle, smooth, CAM, BOIL, W, H, sx, sy } from './crayon.js';
import { group, clearGroup, part } from './rig.js';
import { bust } from './frame.js';
import { LOOKS } from './looks.js';
import { clamp, lerp, hash, track, ss } from '/core/lib.js';

const K = LOOKS.case;
export const DUR = 29;
const pr = (t, a, b) => clamp((t - a) / (b - a));
const hex = c => '#' + c.map(v => Math.round(v * 255).toString(16).padStart(2, '0')).join('');

// ——— timing (seconds) ———
const T = {
  title: [0.5, 2.9], date: [2.7, 4.2],
  ground: [4.4, 6.6], grass: [5.8, 8.6],
  trunk: [4.8, 6.4], crown: [5.2, 7.6], treeF: [6.6, 8.6],
  gable: [4.6, 6.8], roof: [5.2, 7.6], walls: [5.8, 7.8], door: [6.8, 8.0], attic: [7.0, 8.1], win: [7.2, 8.5],
  wallF: [6.6, 9.0], roofF: [7.0, 9.0], doorF: [7.8, 8.8], winF: [8.0, 8.9],
  path: [6.2, 7.6], pathF: [7.2, 8.8], fence: [6.0, 8.8],
  woman: [8.9, 10.7], womanF: [9.9, 11.0],
  erase: [11.4, 14.2], blue: [14.5, 15.8],
  stain: [16.0, 22.6],
  gloveL: [22.9, 23.7], gloveF: [23.7, 25.3],
};

// ——— camera: world centre + zoom ———
const camT = track([
  [0, [560, 300, 1.45]], [4.2, [560, 300, 1.45]], [8.6, [1220, 730, 0.92]], [9.2, [1250, 745, 0.96]],
  [11.0, [1346, 826, 1.38]], [15.9, [1346, 826, 1.38]], [18.4, [1300, 820, 0.86]], [22.7, [1300, 820, 0.86]],
  [25.5, [1880, 1036, 1.62]], [29, [1882, 1036, 1.68]],
]);

// ——— geometry (world) ———
const dx = 300, dy = 110;
const M = pts => pts.map(([x, y]) => [x + dx, y + dy]);
const A = [1030, 530], B = [1300, 508], Cc = [1518, 702], D = [1200, 724], Le = [830, 724];
const WIN = M([[968, 652], [1124, 640], [1124, 774], [968, 784]]);
const WOMAN = [1346, 894];
const GLOVE = smooth([[-112, 0], [-108, -26], [-82, -42], [-60, -74], [-46, -70], [-52, -46], [-32, -54], [-4, -80], [8, -72], [-14, -44], [18, -58], [30, -48], [-2, -28], [24, -26], [26, -14], [-8, -10], [16, 2], [8, 12], [-40, 10], [-70, 18], [-100, 20]].map(([x, y]) => [x + 1900, y + 1070]), 4);
const STEPS = Array.from({ length: 11 }, (_, i) => {
  const u = i / 10, x = lerp(1110, 1830, u), y = 1012 + Math.sin(u * Math.PI) * 70 + u * 30, sd = i % 2 ? 1 : -1;
  return [x + sd * 6, y - sd * 12, Math.atan2(30 + 220 * Math.cos(u * Math.PI) / 3.2, 720) - 1.57 + 0.0];
});

// ——— events for the mix ———
export const EV = [];
const ev = (t, type, o = {}) => EV.push({ t: +t.toFixed(3), type, ...o });
ev(0, 'room');
ev(T.title[0], 'write', { dur: T.title[1] - T.title[0], pan: -0.4 }); ev(T.date[0] + 0.15, 'write', { dur: T.date[1] - T.date[0] - 0.15, pan: -0.3 });
[[T.gable, 0], [T.roof, 0.1], [T.walls, 0.2], [T.ground, -0.3], [T.trunk, -0.6], [T.crown, -0.6], [T.fence, 0.6], [T.door, -0.05], [T.win, 0.2], [T.path, 0]].forEach(([[a, b], pan]) => ev(a, 'line', { dur: b - a, pan }));
[[T.grass, 0], [T.treeF, -0.6], [T.wallF, 0], [T.roofF, 0.1], [T.doorF, -0.1], [T.winF, 0.2], [T.pathF, 0]].forEach(([[a, b], pan]) => ev(a, 'colour', { dur: b - a, pan }));
ev(T.woman[0], 'line', { dur: T.woman[1] - T.woman[0], pan: 0.1, soft: 1 }); ev(T.womanF[0], 'colour', { dur: T.womanF[1] - T.womanF[0], pan: 0.1, soft: 1 });
ev(T.erase[0], 'erase', { dur: T.erase[1] - T.erase[0], pan: 0 });
ev(13.9, 'musicstop');
ev(T.blue[0], 'colour', { dur: T.blue[1] - T.blue[0], pan: 0 });
ev(T.stain[0], 'stain', { dur: T.stain[1] - T.stain[0] });
ev(T.gloveL[0], 'line', { dur: T.gloveL[1] - T.gloveL[0], pan: 0.2 });
ev(T.gloveF[0], 'pink', { dur: T.gloveF[1] - T.gloveF[0], pan: 0.2 });

// ——— layers ———
const F = layer(), F2 = layer(), WX = layer(), LB = layer(), WL = layer(), WS = layer(), TT = layer(), FX = layer();
const GH = group(), GLV = group();
const GA = { f: layer(), l: layer() }, GG = { f: layer(), l: layer() }, EM = layer();

function maskSplit(src, alive, ghost, mask) {
  for (const k of ['f', 'l']) {
    for (const [dst, op] of [[alive[k], 'destination-out'], [ghost[k], 'destination-in']]) {
      clear(dst); const g = dst.g; g.save(); g.globalCompositeOperation = 'source-over'; g.drawImage(src[k].c, 0, 0);
      g.globalCompositeOperation = op; g.drawImage(mask.c, 0, 0); g.restore();
    }
  }
}

export function frame(comp, t) {
  const [cx, cy, cs] = camT(t); CAM.x = cx; CAM.y = cy; CAM.s = cs;
  BOIL.amp = K.boil * lerp(1, 0.3, ss(pr(t, 25.6, 27.5)));
  [F, F2, WX, LB, WL, WS, TT, FX, EM].forEach(clear); clearGroup(GH); clearGroup(GLV);
  const ink = K.ink, bo = 0.6;
  const L = (pts, o = {}) => line(LB, pts, { col: ink, w: 8, p: 0.95, boil: bo, ...o });
  const Fi = (poly, o = {}) => fill(F, poly, { p: 0.8, gap: 10, w: 12, boil: 0, ...o });
  const P = (k, d = 0, e = 1) => { const [a, b] = T[k]; return pr(t, lerp(a, b, d), lerp(a, b, e)); };

  // title + date, written in crayon on the page
  const tw = { font: K.title.font, weight: K.title.weight, col: ink, align: 'left', p: 0.95 };
  text(TT, 'ALDER STREET', sx(300), sy(262), { ...tw, size: 70 * CAM.s, track: 6 * CAM.s, reveal: P('title'), seed: 9 });
  text(TT, 'NOV. 14, 1987', sx(304), sy(352), { ...tw, size: 50 * CAM.s, track: 4 * CAM.s, reveal: P('date'), seed: 19 });

  // ground + grass
  const gt = []; for (let x = -60; x <= 2460; x += 70) gt.push([x, 962 + 10 * Math.sin(x * 0.014) + 8 * hash(x + 3)]);
  Fi([...gt, [2460, 1420], [-60, 1420]], { col: K.grass, p: 0.7, gap: 12, w: 13, ang: 1.25, seed: 10, over: 10, draw: P('grass') });
  L(gt.filter(q => q[0] < 840), { col: K.grass, w: 7, seed: 11, draw: P('ground') }); L(gt.filter(q => q[0] > 1500), { col: K.grass, w: 7, seed: 12, draw: P('ground', 0.2, 1) });
  // path
  const path = M([[690, 852], [772, 852], [930, 1240], [560, 1240]]);
  Fi(path, { col: '#b3a68b', p: 0.75, gap: 9, w: 11, ang: 0.1, seed: 13, draw: P('pathF') });
  L(M([[690, 856], [560, 1230]]), { w: 6, seed: 14, draw: P('path') }); L(M([[772, 856], [930, 1230]]), { w: 6, seed: 15, draw: P('path', 0.15, 1) });
  // tree
  const trunk = M([[248, 852], [252, 640], [300, 640], [304, 852]]);
  Fi(trunk, { col: K.wood, p: 0.85, gap: 9, w: 11, ang: 1.5, seed: 20, draw: P('treeF') });
  L(M([[248, 854], [252, 650]]), { w: 7, seed: 21, draw: P('trunk') }); L(M([[304, 854], [300, 650]]), { w: 7, seed: 22, draw: P('trunk', 0.2, 1) });
  const crown = []; for (let i = 0; i <= 72; i++) { const a = i / 72 * 6.283 + 1.6; const b = 1 + 0.09 * Math.abs(Math.sin(a * 4.5)); crown.push([576 + Math.cos(a) * 158 * b, 630 + Math.sin(a) * 140 * b]); }
  Fi(crown, { col: K.leaf, p: 0.72, gap: 12, w: 14, ang: 0.8, seed: 23, cross: true, crossP: 0.4, draw: P('treeF', 0.2, 1) });
  L(crown, { w: 7.5, seed: 24, draw: P('crown') });
  // house
  const side = M([[900, 620], [1190, 594], [1190, 852], [900, 852]]);
  Fi(side, { col: K.wall, p: 0.8, ang: 0.3, seed: 30, cross: true, crossP: 0.5, draw: P('wallF', 0.3, 1) });
  const gable = [...M([[560, 852], [560, 606]]), A, ...M([[900, 606], [900, 852]])];
  Fi(gable, { col: K.wall, p: 0.82, ang: -0.5, seed: 31, cross: true, crossP: 0.5, draw: P('wallF', 0, 0.75) });
  Fi([A, B, Cc, D], { col: K.roof, p: 0.8, gap: 11, w: 13, ang: 0.62, seed: 32, draw: P('roofF') });
  Fi([Le, A, D, [D[0] - 28, D[1] + 4], [A[0], A[1] + 34], [Le[0] + 28, Le[1] + 4]], { col: K.roof, p: 0.88, gap: 7, w: 9, ang: 1.3, seed: 33, draw: P('roofF', 0.3, 1) });
  const door = M([[684, 852], [684, 742], [704, 724], [760, 724], [780, 742], [780, 852]]);
  Fi(door, { col: K.wood, p: 0.9, gap: 8, w: 10, ang: 1.45, seed: 34, draw: P('doorF') });
  Fi(ellipse(1030, 638, 34, 34, 30), { col: K.winLit, p: 0.8, gap: 7, w: 9, seed: 35, draw: P('attic') });
  Fi(WIN, { col: K.skin, p: 0.75, gap: 8, w: 11, ang: 0.4, seed: 36, cross: true, crossP: 0.5, draw: P('winF') });   // lit: ash
  fill(F2, WIN, { col: K.winLit, p: 0.95, gap: 8, w: 11, ang: -0.7, seed: 37, cross: true, crossP: 0.7, boil: 0, draw: P('blue') });   // nobody home
  L([Le, A, D], { seed: 40, draw: P('gable') }); L([A, B, Cc, D], { seed: 41, draw: P('roof') });
  L(M([[560, 610], [560, 852]]), { seed: 42, draw: P('walls') }); L(M([[900, 616], [900, 852]]), { seed: 43, draw: P('walls', 0.15, 1) }); L(M([[1190, 596], [1190, 852]]), { seed: 44, draw: P('walls', 0.3, 1) });
  L(M([[530, 852], [1215, 852]]), { seed: 45, draw: P('ground', 0.1, 0.8) });
  L([...door, door[0]], { w: 7, seed: 46, draw: P('door') }); if (t > T.door[1]) dab(F, 1066, 902, 6, { col: ink, p: 1, seed: 47 });
  L(handCircle(1030, 638, 34, 48), { w: 6, seed: 48, draw: P('attic') }); L([[996, 638], [1064, 638]], { w: 5, seed: 49, draw: P('attic', 0.5, 1) });
  line(WL, [...WIN, WIN[0]], { col: ink, w: 7, p: 0.95, seed: 50, boil: bo, draw: P('win') });
  line(WL, M([[1046, 646], [1046, 780]]), { col: ink, w: 6, p: 0.95, seed: 51, boil: bo, draw: P('win', 0.5, 1) });
  line(WL, M([[968, 712], [1124, 706]]), { col: ink, w: 6, p: 0.95, seed: 52, boil: bo, draw: P('win', 0.6, 1) });
  // fence, with the gate open
  for (let i = 0; i < 9; i++) { if (i === 4) continue; const x = 1550 + i * 64; L([[x, 1012], [x, 930], [x + 12, 916], [x + 24, 930], [x + 24, 1012]], { w: 6, seed: 60 + i, draw: P('fence', i * 0.07, i * 0.07 + 0.4) }); }
  L([[1536, 950], [1790, 948]], { w: 6, seed: 70, draw: P('fence', 0.4, 0.75) }); L([[1866, 948], [2130, 946]], { w: 6, seed: 71, draw: P('fence', 0.5, 0.85) });
  L([[1536, 990], [1790, 989]], { w: 6, seed: 72, draw: P('fence', 0.55, 0.9) }); L([[1866, 989], [2130, 988]], { w: 6, seed: 73, draw: P('fence', 0.6, 1) });

  // clear-wax footprints: on the page from the first frame, invisible until the stain
  const wax = hex(K.paper);
  STEPS.forEach(([x, y, a], i) => {
    fill(WX, ellipse(x, y, 11, 21, 18, 0, 6.283, a), { col: wax, p: 1, gap: 4, w: 6, over: 1, seed: 80 + i, boil: 0 });
    fill(WX, ellipse(x + Math.cos(a - 1.57) * 26, y + Math.sin(a - 1.57) * 26, 8, 9, 14), { col: wax, p: 1, gap: 4, w: 6, over: 1, seed: 95 + i, boil: 0 });
  });

  // the woman in the window, then rubbed out
  if (t > T.woman[0]) {
    bust(GH, K, WOMAN[0], WOMAN[1], 1, { draw: P('woman'), fdraw: P('womanF'), face: t > T.womanF[1] - 0.3 ? 1 : 0, boil: 1 });
    // eraser mask: short back-and-forth passes, top to bottom
    const u = P('erase');
    if (u > 0) {
      const zz = []; for (let r = 0; r <= 11; r++) { const y = 762 + r * 12; zz.push(r % 2 ? [1418, y] : [1272, y]); }
      let len = 0; const seg = []; for (let i = 1; i < zz.length; i++) seg.push(Math.hypot(zz[i][0] - zz[i - 1][0], zz[i][1] - zz[i - 1][1]));
      const total = seg.reduce((a, b) => a + b, 0); let left = total * u;
      const g = EM.g; g.save(); g.strokeStyle = '#000'; g.lineCap = 'round'; g.lineJoin = 'round'; g.lineWidth = 46 * CAM.s;
      g.beginPath(); g.moveTo(sx(zz[0][0]), sy(zz[0][1])); let head = zz[0];
      for (let i = 1; i < zz.length && left > 0; i++) { const k = Math.min(1, left / seg[i - 1]); head = [lerp(zz[i - 1][0], zz[i][0], k), lerp(zz[i - 1][1], zz[i][1], k)]; g.lineTo(sx(head[0]), sy(head[1])); left -= seg[i - 1]; }
      g.stroke(); if (u >= 1) { g.fillStyle = '#000'; g.fillRect(sx(1260), sy(740), 180 * CAM.s, 170 * CAM.s); } g.restore();
      // eraser crumbs near the working edge (24 fps), brushed off at the end
      if (u < 1) for (let k = 0; k < 7; k++) { const h1 = hash(k * 7.3 + Math.floor(t * 24) * 0.37); dab(FX, head[0] + (h1 - 0.5) * 60, head[1] + 8 + hash(k * 3.1 + Math.floor(t * 12)) * 26, 2.5 + 2 * hash(k), { col: '#6d655c', p: 0.7, seed: 300 + k, gap: 2, w: 3, over: 0 }); }
    }
    maskSplit(GH, GA, GG, EM);
  }

  // the stain spreading across the lawn (24 fps)
  const gs = ss(P('stain'));
  if (gs > 0) {
    const g = WS.g; g.fillStyle = '#000';
    const c0 = [lerp(1150, 1470, gs), lerp(1040, 1078, gs)];
    for (let k = 0; k < 5; k++) {
      const rx = (520 - k * 34) * gs + 20, ry = (132 - k * 10) * Math.sqrt(gs) + 10;
      g.globalAlpha = 0.34; g.beginPath();
      for (let i = 0; i < 64; i++) { const a = i / 64 * 6.283; const r = 1 + 0.12 * Math.sin(a * 3 + k) + 0.07 * (hash(i * 3 + k) - 0.5) + 0.05 * Math.sin(a * 7 + t * 0.6); const x = sx(c0[0] + Math.cos(a) * rx * r), y = sy(c0[1] + Math.sin(a) * ry * r); i ? g.lineTo(x, y) : g.moveTo(x, y); }
      g.closePath(); g.fill();
    }
    g.globalAlpha = 1;
  }

  // the glove at the gate: drawn, then coloured hot pink
  if (t > T.gloveL[0]) part(GLV, GLOVE, { col: K.clue, p: 1.0, gap: 6, w: 9, seed: 120, boil: 0, cross: true, crossP: 0.8, draw: P('gloveF') }, { col: ink, w: 6, p: 0.95, seed: 121, boil: bo, draw: P('gloveL') });

  // ——— composite ———
  comp.setAge(K.age, [[2050 * 0.8, 430 * 0.8, 210 * 0.8, 0.75], [380 * 0.8, 1180 * 0.8, 140 * 0.8, 0.7], [1500 * 0.8, 170 * 0.8, 110 * 0.8, 0.5], [760 * 0.8, 560 * 0.8, 70 * 0.8, 0.6]], [1545 * 0.8, 0.015, 1]);
  comp.paperCam(CAM.x * 0.8, CAM.y * 0.8, CAM.s / 0.8);
  comp.begin(K.paper);
  comp.crayon(F.c); comp.crayon(WX.c, { clear: true }); comp.crayon(F2.c); comp.crayon(LB.c);
  if (gs > 0) comp.wash(WS.c, { color: K.wash, resist: 0.95, r0: 0.78, r1: 0.97, edge: 2.0 });
  if (t > T.woman[0]) { comp.crayon(GA.f.c); comp.crayon(GA.l.c); comp.crayon(GG.f.c, { ghost: 1 }); comp.crayon(GG.l.c, { ghost: 1 }); }
  comp.crayon(WL.c); comp.crayon(FX.c);
  if (t > T.gloveL[0]) { comp.crayon(GLV.f.c); comp.crayon(GLV.l.c); }
  comp.crayon(TT.c);
  comp.finish({ vig: K.vig, edge: K.edge });
}
