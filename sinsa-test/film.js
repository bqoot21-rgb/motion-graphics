// Crayon Case test with narration: "June 14th, 1998" (hook). One page, one take, 24.5 s.
// World 3200×2200 (paper coords = world × 0.6). TV close-up → the apartment block → down below the street → the basement door.
import { layer, clear, line, fill, dab, text, ellipse, handCircle, smooth, CAM, BOIL, sx, sy } from './crayon.js';
import { LOOKS } from './looks.js';
import { clamp, lerp, hash, track, ss } from '/core/lib.js';

const K = LOOKS.case;
export const DUR = 24.5;
const pr = (t, a, b) => clamp((t - a) / (b - a));

// ——— narration (Kokoro am_michael, speed 0.9); t = speech start ———
export const LINES = [
  { id: 'n1', t: 1.6, d: 7.76, text: 'June 14th, 1998, the night South Korea played Mexico in its first World Cup match.' },
  { id: 'n2', t: 10.0, d: 3.36, text: 'While the whole country was cheering in front of their TVs,' },
  { id: 'n3', t: 13.8, d: 6.079, text: 'a tragedy was quietly unfolding in a basement bar in Sinsa-dong, Gangnam, Seoul.' },
];
export const SUBS = LINES.map((L, i) => { const t0 = L.t - 0.1; let t1 = L.t + L.d + 0.5; const nx = LINES[i + 1]; if (nx) t1 = Math.min(t1, nx.t - 0.15); return { t0, t1, text: L.text }; });

// ——— timing ———
const T = {
  date: [0.4, 2.6], tv: [0.6, 3.6], screen: [3.0, 5.4], players: [5.0, 9.6], viewers: [2.0, 4.6],
  block: [8.8, 11.6], blockF: [9.6, 12.4], wins: [8.8, 12.6],
  street: [12.4, 14.2], under: [13.4, 16.4], stairs: [14.4, 16.8], sign: [15.0, 16.2], door: [15.8, 17.4], doorF: [16.6, 17.8],
  seep: [18.4, 23.2],
};

// ——— camera ———
const camT = track([
  [0, [1410, 742, 6.0]], [8.6, [1410, 742, 6.0]], [13.2, [1420, 860, 0.62]], [13.7, [1440, 900, 0.62]],
  [17.0, [2160, 1600, 0.95]], [19.4, [2120, 1800, 2.1]], [24.5, [2122, 1804, 2.25]],
]);

// ——— geometry ———
const win = (r, c) => ({ x: 520 + c * 380, y: 420 + r * 220, w: 260, h: 180 });
const HERO = win(1, 2);
const rect = (x, y, w, h) => [[x, y], [x + w, y], [x + w, y + h], [x, y + h]];
const WINS = []; for (let r = 0; r < 4; r++) for (let c = 0; c < 5; c++) if (!(r === 1 && c === 2)) WINS.push({ r, c, ...win(r, c), k: hash(r * 7 + c * 3.3) });
WINS.sort((a, b) => a.k - b.k);

// ——— events ———
export const EV = [];
const ev = (t, type, o = {}) => EV.push({ t: +t.toFixed(3), type, ...o });
ev(0, 'room'); ev(0, 'tvcrowd');
LINES.forEach(L => ev(L.t, 'voice', { id: L.id, dur: L.d }));
ev(T.date[0], 'write', { dur: T.date[1] - T.date[0], pan: -0.5 });
ev(T.tv[0], 'line', { dur: T.tv[1] - T.tv[0], pan: 0 }); ev(T.viewers[0], 'colour', { dur: T.viewers[1] - T.viewers[0], pan: 0 });
ev(T.screen[0], 'colour', { dur: T.screen[1] - T.screen[0], pan: 0 });
ev(T.block[0], 'line', { dur: T.block[1] - T.block[0], pan: 0 }); ev(T.wins[0], 'colour', { dur: T.wins[1] - T.wins[0], pan: 0.2 });
ev(T.street[0], 'line', { dur: T.street[1] - T.street[0], pan: -0.2 }); ev(T.under[0], 'colour', { dur: T.under[1] - T.under[0], pan: 0.2 });
ev(T.stairs[0], 'line', { dur: T.stairs[1] - T.stairs[0], pan: 0.3 }); ev(T.sign[0], 'write', { dur: T.sign[1] - T.sign[0], pan: 0.4 });
ev(T.door[0], 'line', { dur: T.door[1] - T.door[0], pan: 0 });
ev(13.4, 'below'); ev(18.4, 'seep', { dur: T.seep[1] - T.seep[0] }); ev(21.0, 'cheer');

// ——— layers ———
const F = layer(), KN = layer(), F2 = layer(), LB = layer(), WS = layer(), TT = layer(), FX = layer(), SUB = document.createElement('canvas');
SUB.width = 1920; SUB.height = 1080; Object.assign(SUB.style, { position: 'absolute', left: 0, top: 0 }); document.body.appendChild(SUB);

function subtitle(t) {
  const g = SUB.getContext('2d'); g.clearRect(0, 0, 1920, 1080);
  const s = SUBS.find(s => t >= s.t0 && t < s.t1); if (!s) return;
  g.font = '400 50px Freesentation'; g.textAlign = 'center'; g.textBaseline = 'alphabetic';
  const words = s.text.split(' '), rows = []; let cur = '';
  for (const w of words) { const n = cur ? cur + ' ' + w : w; if (g.measureText(n).width > 1500 && cur) { rows.push(cur); cur = w; } else cur = n; }
  rows.push(cur);
  const a = clamp(Math.min((t - s.t0) / 0.12, (s.t1 - t) / 0.12));
  rows.forEach((r, i) => {
    const y = 1080 - 70 - (rows.length - 1 - i) * 62;
    g.globalAlpha = a; g.shadowColor = 'rgba(20,16,12,0.85)'; g.shadowBlur = 14; g.shadowOffsetY = 2;
    g.lineWidth = 4; g.strokeStyle = 'rgba(30,24,18,0.55)'; g.lineJoin = 'round'; g.strokeText(r, 960, y);
    g.shadowBlur = 0; g.fillStyle = '#ffffff'; g.fillText(r, 960, y);
  });
  g.globalAlpha = 1;
}

export function frame(comp, t) {
  const [cx, cy, cs] = camT(t); CAM.x = cx; CAM.y = cy; CAM.s = cs;
  BOIL.amp = K.boil * lerp(1, 0.3, ss(pr(t, 21.5, 23.5)));
  [F, KN, F2, LB, WS, TT, FX].forEach(clear);
  const ink = K.ink, bo = 0.6;
  const L = (pts, o = {}) => line(LB, pts, { col: ink, w: 8, p: 0.95, boil: bo, ...o });
  const Fi = (poly, o = {}) => fill(F, poly, { p: 0.8, gap: 10, w: 12, boil: 0, ...o });
  const F2i = (poly, o = {}) => fill(F2, poly, { p: 0.8, gap: 10, w: 12, boil: 0, ...o });
  const P = (k, d = 0, e = 1) => { const [a, b] = T[k]; return pr(t, lerp(a, b, d), lerp(a, b, e)); };
  const knock = poly => { const g = KN.g; g.fillStyle = '#000'; g.beginPath(); poly.forEach(([x, y], i) => i ? g.lineTo(sx(x), sy(y)) : g.moveTo(sx(x), sy(y))); g.closePath(); g.fill(); };

  // ——— the apartment block (drawn while we pull out) ———
  const B = { x0: 400, x1: 2400, y0: 300, y1: 1300 };
  Fi(rect(B.x0, B.y0, B.x1 - B.x0, B.y1 - B.y0), { col: K.wall, p: 0.72, ang: -0.5, seed: 1, cross: true, crossP: 0.45, draw: P('blockF') });
  L([[B.x0, B.y1], [B.x0, B.y0], [B.x1, B.y0], [B.x1, B.y1]], { seed: 2, draw: P('block') });
  Fi([[B.x0 - 40, B.y0], [B.x1 + 40, B.y0], [B.x1 + 10, B.y0 - 50], [B.x0 - 10, B.y0 - 50]], { col: K.roof, p: 0.85, seed: 3, draw: P('blockF', 0.3, 1) });
  L([[B.x0 - 40, B.y0], [B.x0 - 10, B.y0 - 50], [B.x1 + 10, B.y0 - 50], [B.x1 + 40, B.y0]], { seed: 4, draw: P('block', 0.2, 1) });
  // every other window: lit, a small TV, people with their arms up (two poses on twos)
  const pose = Math.floor(t * 6) % 2;
  WINS.forEach((w, i) => {
    const u0 = i / WINS.length * 0.8, lp = P('wins', u0, u0 + 0.2), cp = P('wins', u0 + 0.1, u0 + 0.3);
    const R = rect(w.x, w.y, w.w, w.h); knock(R);
    F2i(R, { col: K.skin, p: 0.7, gap: 9, w: 11, ang: 0.4, seed: 10 + i, draw: cp });
    L([...R, R[0]], { w: 6, seed: 40 + i, draw: lp });
    if (cp > 0.8) {
      const tx = w.x + w.w * 0.55, ty = w.y + 40;
      F2i(rect(tx, ty, 70, 52), { col: K.hair, p: 0.95, gap: 6, w: 8, seed: 70 + i }); F2i(rect(tx + 8, ty + 8, 54, 36), { col: K.winLit, p: 0.95, gap: 5, w: 7, seed: 100 + i });
      const px = w.x + 60 + (i % 3) * 14, up = (pose + i) % 2;
      dab(F2, px, w.y + w.h - 26, 22, { col: K.hair, p: 0.95, seed: 130 + i });
      L([[px - 16, w.y + w.h - 34], [px - 30, w.y + w.h - (up ? 92 : 80)]], { w: 6, seed: 160 + i });
      L([[px + 16, w.y + w.h - 34], [px + 30, w.y + w.h - (up ? 80 : 92)]], { w: 6, seed: 190 + i });
    }
  });

  // ——— the hero window: the match on TV ———
  const H = HERO, HR = rect(H.x, H.y, H.w, H.h); knock(HR);
  F2i(HR, { col: K.skin, p: 0.62, gap: 8, w: 10, ang: 0.4, seed: 220 });
  L([...HR, HR[0]], { w: 7, seed: 221 }); L([[H.x + H.w / 2, H.y], [H.x + H.w / 2, H.y + 30]], { w: 4, seed: 222, draw: P('tv', 0.6, 1) });
  const tv = rect(1352, 690, 118, 86), scr = rect(1362, 699, 98, 62);
  F2i(tv, { col: K.hair, p: 0.95, gap: 5, w: 7, ang: 1.2, seed: 223, draw: P('screen', 0, 0.5) });
  F2i(scr, { col: K.grass, p: 0.9, gap: 4, w: 6, ang: 0.2, seed: 224, draw: P('screen', 0.3, 1) });
  L([...tv, tv[0]], { w: 5, seed: 225, draw: P('tv', 0, 0.6) }); L([...scr, scr[0]], { w: 3.5, seed: 226, draw: P('tv', 0.3, 0.8) });
  L([[1390, 690], [1372, 664]], { w: 3.5, seed: 227, draw: P('tv', 0.6, 0.9) }); L([[1430, 690], [1452, 662]], { w: 3.5, seed: 228, draw: P('tv', 0.65, 0.95) });
  L([[1370, 776], [1366, 796]], { w: 4, seed: 229, draw: P('tv', 0.7, 1) }); L([[1452, 776], [1456, 796]], { w: 4, seed: 230, draw: P('tv', 0.75, 1) });
  // the match: two little teams, a ball that jumps on the beat (substitution, 12 fps)
  if (t > T.players[0]) {
    const st = Math.floor(t * 3);
    L([[1411, 701], [1411, 759]], { col: '#e8dfc8', w: 1.6, p: 0.8, seed: 231 }); L(handCircle(1411, 730, 10, 232), { col: '#e8dfc8', w: 1.4, p: 0.8, seed: 233 });
    L([[1362, 718], [1374, 718], [1374, 742], [1362, 742]], { col: '#e8dfc8', w: 1.4, p: 0.8, seed: 234 }); L([[1460, 718], [1448, 718], [1448, 742], [1460, 742]], { col: '#e8dfc8', w: 1.4, p: 0.8, seed: 235 });
    for (let k = 0; k < 6; k++) {
      const side = k < 3 ? -1 : 1, px = 1411 + side * (12 + (k % 3) * 11) + (hash(k + st * 1.7) - 0.5) * 8, py = 712 + (k % 3) * 16 + (hash(k * 3 + st) - 0.5) * 6;
      dab(F2, px, py, 3.6, { col: side < 0 ? K.coat : K.wood, p: 1, gap: 1.5, w: 2.2, over: 0, seed: 240 + k }); L([[px, py + 3], [px - 2, py + 9]], { w: 1.4, seed: 270 + k }); L([[px, py + 3], [px + 2, py + 9]], { w: 1.4, seed: 280 + k });
    }
    const bx = 1411 + Math.sin(st * 1.9) * 22, by = 730 + Math.cos(st * 1.3) * 12;
    dab(F2, bx, by, 2.4, { col: '#f1ead6', p: 1, gap: 1.2, w: 1.8, over: 0, seed: 250 });
  }
  // the family watching, from behind: two heads, arms up when the crowd roars
  const vp = P('viewers');
  if (vp > 0) {
    const cheer = t > 6.5 && Math.floor(t * 4) % 2 === 0;
    [[1322, 832, 26], [1500, 828, 30]].forEach(([x, y, r], i) => {
      const head = ellipse(x, y, r, r, 30, Math.PI, Math.PI * 2);
      fill(F2, head, { col: K.hair, p: 0.95, gap: 5, w: 7, seed: 260 + i, boil: 0, draw: vp });
      L(head, { w: 5, seed: 262 + i, draw: vp });
      if (cheer) { L([[x - r, y - 6], [x - r - 14, y - 52]], { w: 5, seed: 264 + i }); L([[x + r, y - 6], [x + r + 14, y - 52]], { w: 5, seed: 266 + i }); }
    });
  }
  // the date, written on the window
  text(TT, 'JUNE 14, 1998', sx(1290), sy(668), { font: K.title.font, weight: K.title.weight, col: ink, align: 'left', p: 0.95, size: 9.5 * CAM.s, track: 0.8 * CAM.s, reveal: P('date'), seed: 9 });

  // ——— the street, and what is under it (child logic: a cut-away) ———
  L([[-60, 1300], [3260, 1302]], { seed: 300, draw: P('street') });
  const UG = [[1700, 1340], [2800, 1340], [2800, 1960], [1700, 1960]];
  Fi([[1600, 1320], [2900, 1320], [2900, 2060], [1600, 2060]], { col: K.wood, p: 0.5, gap: 13, w: 13, ang: 1.0, seed: 301, draw: P('under') });
  knock(UG);
  F2i([[1700, 1900], [2800, 1900], [2800, 1960], [1700, 1960]], { col: K.wall, p: 0.7, gap: 8, w: 10, ang: 0.1, seed: 302, draw: P('under', 0.3, 1) });
  L([...UG, UG[0]], { seed: 303, draw: P('under') }); L([[1700, 1900], [2800, 1900]], { w: 6, seed: 304, draw: P('under', 0.5, 1) });
  // stairs down from the pavement
  const steps = []; for (let i = 0; i <= 10; i++) { const x = 2760 - i * 38, y = 1300 + i * 54; steps.push([x, y], [x - 38, y]); }
  L(steps, { w: 6, seed: 305, draw: P('stairs') });
  // the sign at street level
  F2i(rect(2570, 1150, 210, 90), { col: K.hair, p: 0.95, gap: 6, w: 8, seed: 306, draw: P('sign') });
  L([...rect(2570, 1150, 210, 90), [2570, 1150]], { w: 6, seed: 307, draw: P('sign') }); L([[2675, 1240], [2675, 1300]], { w: 6, seed: 308, draw: P('sign') });
  text(TT, 'BAR', sx(2675), sy(1214), { font: K.title.font, weight: K.title.weight, col: '#e8dfc8', align: 'center', p: 0.9, size: 58 * CAM.s, track: 6 * CAM.s, reveal: P('sign', 0.4, 1), seed: 19 });
  // the door: closed
  const door = [[2050, 1900], [2050, 1716], [2170, 1716], [2170, 1900]];
  F2i(door, { col: K.wood, p: 0.92, gap: 8, w: 10, ang: 1.45, seed: 310, draw: P('doorF') });
  L([...door], { w: 7, seed: 311, draw: P('door') }); if (t > T.door[1]) dab(F2, 2152, 1812, 6, { col: ink, p: 1, seed: 312 });
  L([[2030, 1900], [2190, 1900]], { w: 5, seed: 313, draw: P('door', 0.6, 1) });

  // ——— under the door: hot pink, spreading slowly (blood as a cover-mode wash) ———
  const gs = ss(P('seep'));
  if (gs > 0) {
    const g = WS.g; g.fillStyle = '#000';
    for (let k = 0; k < 4; k++) {
      g.globalAlpha = 0.4; g.beginPath();
      const rx = 40 + 150 * gs - k * 10, ry = 7 + 22 * gs - k * 2, cx0 = 2112 - 10 * gs;
      for (let i = 0; i <= 64; i++) {
        const a = i / 64 * 6.283;
        const r = 1 + 0.16 * Math.sin(a * 3 + k) + 0.1 * Math.sin(a * 7 + 1.3 * k) + 0.05 * (hash(i + k * 9) - 0.5);
        const x = cx0 + Math.cos(a) * rx * r, y = Math.max(1898, 1904 + Math.sin(a) * ry * r * (Math.sin(a) > 0 ? 1.3 : 0.4));
        i ? g.lineTo(sx(x), sy(y)) : g.moveTo(sx(x), sy(y));
      }
      g.closePath(); g.fill();
    }
    g.globalAlpha = 1;
  }

  // ——— composite ———
  comp.setAge(K.age, [[2600 * 0.6, 600 * 0.6, 220 * 0.6, 0.7], [500 * 0.6, 1700 * 0.6, 160 * 0.6, 0.7], [1500 * 0.6, 180 * 0.6, 120 * 0.6, 0.5], [3000 * 0.6, 1900 * 0.6, 90 * 0.6, 0.6]], [1980 * 0.6, 0.015, 1]);
  comp.paperCam(CAM.x * 0.6, CAM.y * 0.6, CAM.s / 0.6);
  comp.begin(K.paper);
  comp.crayon(F.c); comp.knock(KN.c); comp.crayon(F2.c); comp.crayon(LB.c);
  if (gs > 0) comp.wash(WS.c, { color: K.blood, cover: 1, resist: 0.4, edge: 1.0 });
  comp.crayon(TT.c);
  comp.finish({ vig: K.vig, edge: K.edge });
  subtitle(t);
}
