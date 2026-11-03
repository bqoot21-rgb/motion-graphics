// Style frame: one picture-book page, "Alder Street, 1987" (a fictional case).
// ?look=base draws it with the base style's box; ?look=case with Crayon Case. Same geometry, same strokes.
import { layer, clear, line, fill, dab, text, ellipse, handCircle, smooth, CAM, BOIL } from './crayon.js';
import { group, clearGroup, part, tube } from './rig.js';
import { hash } from '/core/lib.js';
import { LOOKS } from './looks.js';

const F = layer(), LB = layer(), WX = layer(), WS = layer(), CL = group(), TT = layer();
const GH = group(), PS = group();
const hex = c => '#' + c.map(v => Math.round(v * 255).toString(16).padStart(2, '0')).join('');

// ——— a person: ≈2.6 heads tall, facing us ———
export function person(C, K, x, y, s, o = {}) {
  const P = pts => pts.map(([a, b]) => [x + a * s, y + b * s]);
  const lo = { col: K.ink, w: 7 * s, p: 0.95, boil: o.boil ?? 1 };
  const flat = { p: 0.8, gap: 8, w: 10, boil: 0 };
  // legs + shoes
  for (const sd of [-1, 1]) {
    part(C, tube(P([[sd * 22, -125], [sd * 24, -12]]), 30 * s), { ...flat, col: K.coat === K.wall ? K.ink : K.hair, seed: 400 + sd }, { ...lo, seed: 410 + sd });
    part(C, P(ellipse(sd * 30, -6, 26, 13, 20)), { ...flat, col: K.shoe, p: 0.95, seed: 420 + sd }, { ...lo, seed: 430 + sd });
  }
  // coat
  const coat = P(smooth([[-58, -300], [0, -308], [58, -300], [70, -240], [84, -110], [0, -102], [-84, -110], [-70, -240]], 6));
  part(C, coat, { ...flat, col: K.coat, p: 0.85, seed: 440, ang: 1.1, cross: true, crossP: 0.45 }, { ...lo, seed: 441 });
  line(C.l, P([[0, -296], [0, -112]]), { ...lo, w: 4 * s, seed: 442 });
  // arms + hands
  for (const sd of [-1, 1]) {
    part(C, tube(P([[sd * 60, -286], [sd * 76, -200], [sd * 80, -150]]), 30 * s, 26 * s), { ...flat, col: K.coat, p: 0.85, seed: 450 + sd, ang: 1.4 }, { ...lo, seed: 452 + sd });
    part(C, P(handCircle(sd * 82, -138, 17, 460 + sd, 0)), { ...flat, col: K.skin, p: o.skinP ?? 0.6, gap: 5, w: 7, seed: 462 + sd }, { ...lo, w: 5 * s, seed: 464 + sd });
  }
  // head + hair
  const head = P(handCircle(0, -362, 58, 470, 0));
  part(C, head, { ...flat, col: K.skin, p: o.skinP ?? 0.6, gap: 6, w: 8, seed: 471 }, { ...lo, seed: 472 });
  const hairOut = [[-62, -366], [-60, -405], [-22, -430], [24, -428], [58, -402], [62, -366]];
  const hair = P(smooth([...hairOut, [44, -390], [12, -396], [-20, -392], [-46, -388]], 6));
  part(C, hair, { ...flat, col: K.hair, p: 0.95, seed: 473, ang: 0.3 }, null, { occ: false });
  line(C.l, P(smooth(hairOut, 6, false)), { ...lo, seed: 474 });
  face(C, K, P, s, o);
}
function face(C, K, P, s, o) {
  const [l, r] = [P([[-20, -352]])[0], P([[20, -352]])[0]];
  if (K.face === 'cute') {
    dab(C.l, l[0], l[1], 7 * s, { col: K.ink, p: 1, seed: 480 }); dab(C.l, r[0], r[1], 7 * s, { col: K.ink, p: 1, seed: 481 });
    dab(C.l, l[0] + 2.5 * s, l[1] - 3 * s, 2.4 * s, { col: '#fbfaf4', p: 1, seed: 482, gap: 2, w: 3 }); dab(C.l, r[0] + 2.5 * s, r[1] - 3 * s, 2.4 * s, { col: '#fbfaf4', p: 1, seed: 483, gap: 2, w: 3 });
    const [cl, cr] = [P([[-36, -334]])[0], P([[36, -334]])[0]];
    dab(C.f, cl[0], cl[1], 11 * s, { col: '#ee8ea4', p: 0.8, seed: 484, sq: 0.7 }); dab(C.f, cr[0], cr[1], 11 * s, { col: '#ee8ea4', p: 0.8, seed: 485, sq: 0.7 });
    line(C.l, P([[-16, -330], [-6, -322], [6, -322], [16, -330]]), { col: K.ink, w: 5 * s, p: 0.95, seed: 486, boil: o.boil ?? 1 });
  } else {   // blank: two small dots, no catchlight, no cheeks, no mouth
    dab(C.l, l[0], l[1], 5.5 * s, { col: K.ink, p: 1, seed: 480, gap: 2.5, w: 4, over: 0.5 }); dab(C.l, r[0], r[1], 5.5 * s, { col: K.ink, p: 1, seed: 481, gap: 2.5, w: 4, over: 0.5 });
  }
}
// head and shoulders seen through a window
export function bust(C, K, x, y, s, o = {}) {
  const P = pts => pts.map(([a, b]) => [x + a * s, y + b * s]);
  const ld = o.draw ?? 1, fd = o.fdraw ?? 1;
  const lo = { col: K.ink, w: 6, p: 0.95, boil: o.boil ?? 1 };
  const D = (a, b) => Math.min(1, Math.max(0, (ld - a) / (b - a)));
  part(C, P(smooth([[-54, 0], [-40, -40], [0, -48], [40, -40], [54, 0]], 6)), { p: 0.85, gap: 7, w: 9, col: K.coat, seed: 500, boil: 0, draw: fd }, { ...lo, seed: 501, draw: D(0.45, 1) });
  part(C, P(handCircle(0, -80, 36, 502, 0)), { p: 0.6, gap: 6, w: 8, col: K.skin, seed: 503, boil: 0, draw: fd }, { ...lo, seed: 504, draw: D(0, 0.5) });
  const ho = [[-38, -96], [-34, -112], [0, -124], [34, -112], [38, -96]];
  part(C, P(smooth([...ho, [20, -108], [-12, -106]], 6)), { p: 0.95, gap: 6, w: 8, col: K.hair, seed: 505, boil: 0, draw: fd }, null, { occ: false });
  line(C.l, P(smooth(ho, 6, false)), { ...lo, seed: 506, draw: D(0.3, 0.75) });
  if ((o.face ?? 1) > 0) face(C, K, pts => P(pts.map(([a, b]) => [a * 0.62, -80 + (b + 352) * 0.62])), s, o);
}

export function styleFrame(comp, t, look) {
  const K = LOOKS[look] || LOOKS.case;
  CAM.x = 960; CAM.y = 540; CAM.s = 1;
  BOIL.amp = K.boil;
  [F, LB, WX, WS, TT].forEach(clear); clearGroup(CL); clearGroup(GH); clearGroup(PS);
  const ink = K.ink, bo = 0.6;
  const L = (pts, o = {}) => line(LB, pts, { col: ink, w: 8, p: 0.95, boil: bo, ...o });
  const Fi = (poly, o = {}) => fill(F, poly, { p: 0.8, gap: 10, w: 12, boil: 0, ...o });

  // sky strip and sun (a child's sky: a band at the top of the page)
  const skyB = []; for (let x = -40; x <= 1960; x += 60) skyB.push([x, 92 + 10 * Math.sin(x * 0.011) + 8 * hash(x)]);
  Fi([[-40, -20], [1960, -20], ...skyB.slice().reverse()], { col: K.sky, p: 0.62, gap: 12, w: 13, ang: 0.15, seed: 1 });
  const sunC = handCircle(1690, 205, 66, 2, 0);
  Fi(sunC, { col: K.sun, p: 0.85, seed: 3, cross: true, crossP: 0.5 });
  L(handCircle(1690, 205, 66, 4), { col: look === 'case' ? ink : '#ec8a3c', w: 7, seed: 5 });
  for (let k = 0; k < 9; k++) { const a = k / 9 * 6.283 + 0.2; L([[1690 + Math.cos(a) * 88, 205 + Math.sin(a) * 88], [1690 + Math.cos(a) * 124, 205 + Math.sin(a) * 124]], { col: look === 'case' ? K.sun : '#ec8a3c', w: 6, seed: 6 + k }); }

  // ground
  const gt = []; for (let x = -40; x <= 1960; x += 70) gt.push([x, 852 + 10 * Math.sin(x * 0.014) + 8 * hash(x + 3)]);
  Fi([...gt, [1960, 1100], [-40, 1100]], { col: K.grass, p: 0.7, gap: 12, w: 13, ang: 1.25, seed: 10, over: 10 });
  L(gt.filter(q => q[0] < 540), { col: K.grass, w: 7, seed: 11 }); L(gt.filter(q => q[0] > 1200), { col: K.grass, w: 7, seed: 12 });
  // path from the door
  const path = [[690, 852], [772, 852], [930, 1100], [560, 1100]];
  Fi(path, { col: look === 'case' ? '#b3a68b' : '#e7b867', p: 0.75, gap: 9, w: 11, ang: 0.1, seed: 13 });
  L([[690, 856], [560, 1090]], { w: 6, seed: 14 }); L([[772, 856], [930, 1090]], { w: 6, seed: 15 });

  // tree
  const trunk = [[248, 852], [252, 640], [300, 640], [304, 852]];
  Fi(trunk, { col: K.wood, p: 0.85, gap: 9, w: 11, ang: 1.5, seed: 20 });
  L([[248, 854], [252, 650]], { w: 7, seed: 21 }); L([[304, 854], [300, 650]], { w: 7, seed: 22 });
  const crown = []; for (let i = 0; i <= 72; i++) { const a = i / 72 * 6.283; const b = 1 + 0.09 * Math.abs(Math.sin(a * 4.5)); crown.push([276 + Math.cos(a) * 158 * b, 520 + Math.sin(a) * 140 * b]); }
  Fi(crown, { col: K.leaf, p: 0.72, gap: 12, w: 14, ang: 0.8, seed: 23, cross: true, crossP: 0.4 });
  L(crown, { w: 7.5, seed: 24 });

  // house (child perspective: gable front + slanted side wall)
  const A = [730, 420], B = [1000, 398], Cc = [1218, 592], D = [900, 614], Le = [530, 614];
  const side = [[900, 620], [1190, 594], [1190, 852], [900, 852]];
  Fi(side, { col: K.wall, p: 0.8, ang: 0.3, seed: 30, cross: true, crossP: 0.5 });
  const gable = [[560, 852], [560, 606], A, [900, 606], [900, 852]];
  Fi(gable, { col: K.wall, p: 0.82, ang: -0.5, seed: 31, cross: true, crossP: 0.5 });
  Fi([A, B, Cc, D], { col: K.roof, p: 0.8, gap: 11, w: 13, ang: 0.62, seed: 32 });
  Fi([Le, A, D, [D[0] - 28, D[1] + 4], [A[0], A[1] + 34], [Le[0] + 28, Le[1] + 4]], { col: K.roof, p: 0.88, gap: 7, w: 9, ang: 1.3, seed: 33 });
  const door = [[684, 852], [684, 742], [704, 724], [760, 724], [780, 742], [780, 852]];
  Fi(door, { col: K.wood, p: 0.9, gap: 8, w: 10, ang: 1.45, seed: 34 });
  Fi(ellipse(730, 528, 34, 34, 30), { col: K.winLit, p: 0.8, gap: 7, w: 9, seed: 35 });
  const win = [[968, 652], [1124, 640], [1124, 774], [968, 784]];
  Fi(win, { col: K.winLit, p: 0.9, gap: 8, w: 11, ang: 0.4, seed: 36, cross: true, crossP: 0.6 });
  // house lines
  L([Le, A, D], { seed: 40 }); L([A, B, Cc, D], { seed: 41 });
  L([[560, 610], [560, 852]], { seed: 42 }); L([[900, 616], [900, 852]], { seed: 43 }); L([[1190, 596], [1190, 852]], { seed: 44 });
  L([[530, 852], [1215, 852]], { seed: 45 });
  L([...door, door[0]], { w: 7, seed: 46 }); dab(F, 766, 792, 6, { col: ink, p: 1, seed: 47 });
  L(handCircle(730, 528, 34, 48), { w: 6, seed: 48 }); L([[696, 528], [764, 528]], { w: 5, seed: 49 });
  L([...win, win[0]], { w: 7, seed: 50 }); L([[1046, 646], [1046, 780]], { w: 6, seed: 51 }); L([[968, 712], [1124, 706]], { w: 6, seed: 52 });
  // picket fence
  for (let i = 0; i < 9; i++) { const x = 1250 + i * 64; L([[x, 902], [x, 820], [x + 12, 806], [x + 24, 820], [x + 24, 902]], { w: 6, seed: 60 + i }); }
  L([[1236, 840], [1830, 836]], { w: 6, seed: 70 }); L([[1236, 880], [1830, 878]], { w: 6, seed: 71 });

  // footprints in clear wax (white wax in the base): hidden until the stain passes
  const wax = K.wax || hex(K.paper);
  for (let i = 0; i < 9; i++) {
    const u = i / 8, x = 820 + u * 520, y = 905 + u * 120 + Math.sin(u * 3) * 20, sd = i % 2 ? 1 : -1;
    const fx = x + sd * 14, fy = y - sd * 6;
    fill(WX, ellipse(fx, fy, 11, 20, 18, 0, 6.283, -1.1), { col: wax, p: 1, gap: 4, w: 6, over: 1, seed: 80 + i, boil: 0 });
    fill(WX, ellipse(fx + 14, fy - 20, 8, 9, 14), { col: wax, p: 1, gap: 4, w: 6, over: 1, seed: 90 + i, boil: 0 });
  }
  // the stain (the style's one watercolour)
  const g = WS.g; g.fillStyle = '#000';
  for (let k = 0; k < 5; k++) {
    const pts = []; for (let i = 0; i < 60; i++) { const a = i / 60 * 6.283; const r = 1 + 0.12 * Math.sin(a * 3 + k) + 0.08 * (hash(i * 3 + k) - 0.5); pts.push([1070 + Math.cos(a) * (380 - k * 30) * r, 985 + Math.sin(a) * (120 - k * 9) * r]); }
    g.globalAlpha = 0.34; g.beginPath(); pts.forEach(([x, y], i) => i ? g.lineTo(x, y) : g.moveTo(x, y)); g.closePath(); g.fill();
  }
  g.globalAlpha = 1;

  // someone in the side window (Crayon Case: erased — only the smear is left)
  bust(GH, K, 1046, 784, 1, { boil: 1 });
  // the figure at the fence
  person(PS, K, 1560, 900, 0.86, { boil: 1 });
  // the clue: one glove on the path
  const glove = smooth([[748, 1004], [752, 978], [778, 962], [800, 930], [814, 934], [808, 958], [828, 950], [856, 924], [868, 932], [846, 960], [878, 946], [890, 956], [858, 976], [884, 978], [886, 990], [852, 994], [876, 1006], [868, 1016], [820, 1014], [790, 1022], [760, 1024]], 4);
  part(CL, glove, { col: K.clue, p: 1.0, gap: 6, w: 9, seed: 120, boil: 0, cross: true, crossP: 0.8 }, { col: ink, w: 6, p: 0.95, seed: 121, boil: bo });

  // title, written on the page in crayon
  text(TT, 'ALDER STREET, 1987', 92, 190, { font: K.title.font, weight: K.title.weight, size: K.title.size, col: ink, align: 'left', p: 0.95, seed: 9, track: look === 'case' ? 6 : 0 });

  comp.setAge(K.age, [[1480, 330, 175, 0.75], [300, 960, 125, 0.7], [1250, 150, 95, 0.5], [420, 300, 60, 0.6]], [1236, 0.015, 1]);
  comp.paperCam(CAM.x, CAM.y, 1);
  comp.begin(K.paper);
  comp.crayon(F.c); comp.crayon(WX.c); comp.crayon(LB.c);
  comp.wash(WS.c, { color: K.wash });
  comp.crayon(GH.f.c, { ghost: K.ghost }); comp.crayon(GH.l.c, { ghost: K.ghost });
  comp.group(PS);
  comp.crayon(CL.f.c); comp.crayon(CL.l.c);
  comp.crayon(TT.c);
  comp.finish({ vig: K.vig, edge: K.edge });
}
