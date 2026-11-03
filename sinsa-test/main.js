import { makeComp } from './gl.js';
import { BOIL } from './crayon.js';
const comp = makeComp(document.getElementById('gl'));
await Promise.all(['400 50px Freesentation', '600 40px Freesentation'].map(f => document.fonts.load(f)));
const M = await import('./film.js');
window.DUR = M.DUR; window.EV = M.EV; window.SUBS = M.SUBS;
window.render = t => { BOIL.step = Math.floor(t * 12 + 1e-6); M.frame(comp, t); };
window.READY = true;
