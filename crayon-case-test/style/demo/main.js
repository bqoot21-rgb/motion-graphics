// Entry: ?test=frame&look=base|case renders the style frame; otherwise the film (film.js)
import { makeComp } from './gl.js';
import { BOIL } from './crayon.js';
const Q = new URLSearchParams(location.search);
const comp = makeComp(document.getElementById('gl'));
window.DUR = 1;
await Promise.all(['400 40px Freesentation', '600 40px Freesentation', '700 40px Gaegu'].map(f => document.fonts.load(f)));
if (Q.get('test') === 'frame') {
  const { styleFrame } = await import('./frame.js');
  window.render = t => { BOIL.step = Math.floor(t * 12); styleFrame(comp, t, Q.get('look') || 'case'); };
} else {
  const M = await import('./film.js');
  window.DUR = M.DUR; window.EV = M.EV;
  window.render = t => { BOIL.step = Math.floor(t * 12 + 1e-6); M.frame(comp, t); };
}
window.READY = true;
