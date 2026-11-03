// Crayon Case: adds aged paper (uAge: yellowing, tide-ring stains, foxing, a fold crease, browned edges) and a ghost pass (an erased drawing: smeared, grey, half gone).
// Based on Lemo-Opuscar crayon-book/demo/gl.js (MIT).
// WebGL2 compositor: paper → crayon layers (adhesion by paper-tooth threshold) → watercolour layer (crayon resist) → final composite (paper-tooth emboss, vignette)
// Each crayon layer is a Canvas2D: RGB = crayon colour, A = pressure. The shader decides whether wax sticks by "pressure > depth of the paper-tooth pit".
export const W = 1920, H = 1080;

const VS = `#version 300 es
in vec2 p; out vec2 uv;
void main(){ uv = p*.5+.5; gl_Position = vec4(p,0,1); }`;

// Paper tooth: pixel coords → height [0,1] (1 = raised paper)
const TOOTH = `
float h21(vec2 p){ p = fract(p*vec2(123.34,456.21)); p += dot(p,p+45.32); return fract(p.x*p.y); }
float vn(vec2 p){ vec2 i=floor(p), f=fract(p); vec2 u=f*f*(3.-2.*f);
  return mix(mix(h21(i),h21(i+vec2(1,0)),u.x), mix(h21(i+vec2(0,1)),h21(i+vec2(1,1)),u.x), u.y); }
uniform float uToothScale;
float toothRaw(vec2 px){
  px /= uToothScale;
  float n = vn(px/1.35)*.34 + vn(px/2.9+17.)*.33 + vn(px/6.3+41.)*.21;
  n += (vn(vec2(px.x/10., px.y/1.9)+7.)-.5)*.22;   // long thin grooves along the fibre direction (horizontally dragged streaks)
  n += (vn(vec2(px.x/2.1, px.y/13.)+71.)-.5)*.08;
  return n;
}
float tooth(vec2 px){ return smoothstep(.16,.86,toothRaw(px)+.06); }
// Paper moves with the drawing: screen pixels → paper coords (pans with the camera; when zooming it crossfades between two octaves so the grain stays about 1 px on screen)
uniform vec3 uPC;
vec2 paperQ(vec2 uv, vec2 res){ vec2 sp = vec2(uv.x*res.x, (1.-uv.y)*res.y); return (sp - res*.5)/uPC.z + uPC.xy; }
float toothRawAt(vec2 uv, vec2 res, vec2 off){
  float L = log2(uPC.z); float k = floor(L), f = L - k;
  vec2 q = paperQ(uv, res);
  float a = toothRaw(q*exp2(k) + off), b = toothRaw(q*exp2(k+1.) + off + 37.1);
  return mix(a, b, smoothstep(0.,1.,f));
}
float toothAt(vec2 uv, vec2 res, vec2 off){ return smoothstep(.16,.86,toothRawAt(uv,res,off)+.06); }
// Aged paper (page coords, so stains move with the page)
uniform float uAge; uniform vec4 uStain[4]; uniform vec3 uFold;
vec3 aged(vec3 c, vec2 px){
  if (uAge <= 0.) return c;
  float b = vn(px/420.)*.55 + vn(px/150.+5.)*.3 + vn(px/38.+2.)*.15;           // uneven yellowing
  c *= mix(vec3(1.), vec3(.94,.88,.76), uAge*smoothstep(.3,.85,b));
  for (int i = 0; i < 4; i++) {                                                // dried water / tea rings
    vec4 S = uStain[i]; if (S.w <= 0.) continue;
    vec2 d = px - S.xy; float a = atan(d.y, d.x);
    float r = length(d)/S.z + (vn(vec2(a*3.1, float(i)*7.)) - .5)*.16 + (vn(px/24.)-.5)*.05;
    float inside = smoothstep(1.0, .9, r);
    float ring = exp(-pow((r-1.)/.022, 2.)) + .45*exp(-pow((r-.93)/.03, 2.));
    c *= mix(vec3(1.), vec3(.95,.9,.8), inside*S.w*uAge);
    c *= mix(vec3(1.), vec3(.8,.7,.55), clamp(ring,0.,1.)*S.w*uAge*.75);
  }
  float f1 = vn(px/5.5 + 91.), f2 = vn(px/60. + 13.);                           // foxing: small rust spots
  c *= mix(vec3(1.), vec3(.78,.62,.46), uAge*smoothstep(.86,.97,f1)*smoothstep(.45,.8,f2)*.7);
  if (uFold.z > 0.) {                                                          // one fold crease
    float x = px.x - (uFold.x + px.y*uFold.y);
    c *= 1. - uAge*uFold.z*(.10*exp(-x*x/30.) - .05*exp(-pow(x-6.,2.)/14.) + .03*smoothstep(0.,-260.,x));
  }
  return c;
}
`;

// Paper base colour: low-frequency mottling
const FS_PAPER = `#version 300 es
precision highp float; in vec2 uv; out vec4 o;
uniform vec3 uPaper; uniform vec2 uRes; uniform vec2 uPoff;
${TOOTH}
void main(){
  vec2 px = paperQ(uv, uRes) + uPoff;
  float m = vn(px/180.)*.6 + vn(px/60.+9.)*.4;
  vec3 c = aged(uPaper * (0.975 + 0.035*m), px);
  o = vec4(c, 0.);
}`;

const FS_IMG = `#version 300 es
precision highp float; in vec2 uv; out vec4 o; uniform sampler2D uL;
void main(){ o = texture(uL, uv); }`;

// Silhouette backing: the background behind a character is left blank (a child draws the figure first, then the background around it)
const FS_KNOCK = `#version 300 es
precision highp float; in vec2 uv; out vec4 o;
uniform sampler2D uL; uniform vec3 uPaper; uniform vec2 uRes; uniform vec2 uPoff;
${TOOTH}
void main(){
  float m = texture(uL, uv).a;
  if (m < .5) discard;
  vec2 px = paperQ(uv, uRes) + uPoff;
  float n = vn(px/180.)*.6 + vn(px/60.+9.)*.4;
  o = vec4(aged(uPaper*(0.975+0.035*n), px), 0.);
}`;

// Crayon layer
const FS_CRAYON = `#version 300 es
precision highp float; in vec2 uv; out vec4 o;
uniform sampler2D uL; uniform vec2 uRes; uniform vec2 uGoff; uniform float uGain; uniform float uSoft; uniform float uGhost;
${TOOTH}
void main(){
  vec4 L = texture(uL, uv);
  if (uGhost > 0.) {   // erased: the wax smears sideways (eraser strokes), loses most of its body and goes grey
    vec2 px1 = 1./uRes; float acc = L.a; vec3 col = L.rgb*L.a; float wsum = 1.;
    for (int k = 1; k <= 6; k++) { float f = float(k)*1.5; vec2 o1 = vec2(f, f*.35)*px1;
      vec4 A = texture(uL, uv+o1), B = texture(uL, uv-o1); acc += A.a + B.a; col += A.rgb*A.a + B.rgb*B.a; wsum += 2.; }
    float sm = acc/wsum; vec3 sc = sm > .001 ? col/(acc+1e-4) : L.rgb;
    L.a = mix(L.a, sm, uGhost) * (1. - .42*uGhost);
    L.rgb = mix(sc, vec3(dot(sc, vec3(.3,.5,.2)))*vec3(.92,.9,.88), .75*uGhost);
  }
  if (L.a < .003) { o = vec4(0); return; }
  float t = toothAt(uv, uRes, uGoff);
  float a = clamp(L.a*uGain, 0., 1.);
  // the harder the pressure, the deeper it gets into the paper-tooth pits
  float thr = 1.0 - a*1.22;
  float cov = smoothstep(thr - uSoft, thr + uSoft, t);
  cov *= smoothstep(0.0, 0.18, a);
  vec3 c = L.rgb * (1.0 - 0.10*a*a);           // heavy pressure: thicker wax, deeper colour
  o = vec4(c, cov);
}`;

// Watercolour layer: reads the previous pass (rgb + wax coverage a), multiplies by the watercolour transmission colour; wax resists it
const FS_WASH = `#version 300 es
precision highp float; in vec2 uv; out vec4 o;
uniform sampler2D uPrev; uniform sampler2D uW; uniform vec2 uRes; uniform vec3 uT; uniform vec2 uGoff;
uniform float uResist; uniform float uEdge; uniform float uGran; uniform float uR0; uniform float uR1; uniform float uCover;
${TOOTH}
void main(){
  vec4 P = texture(uPrev, uv);
  vec4 Wc = texture(uW, uv);
  float d = Wc.a;
  vec2 px = uv*uRes;
  if (d > .002) {
    float blur = textureLod(uW, uv, 4.0).a;
    float blur2 = textureLod(uW, uv, 2.0).a;
    float edge = clamp(d - blur, 0., 1.)*uEdge + clamp(d - blur2, 0., 1.)*uEdge*.6;   // tide marks: pigment pools at the edges
    float t = smoothstep(.16,.86, toothRaw(paperQ(uv,uRes)*0.55 + uGoff + 300.) + .06);
    vec2 wq = paperQ(uv, uRes);
    float lo = vn(wq/160.)*.5 + vn(wq/55.+3.)*.3 + vn(wq/19.+8.)*.2;                 // bloom density variation (cauliflower blooms)
    float gr = smoothstep(.35, .05, t);                                              // granulation settles only in the deepest paper-tooth pits
    float dd = d * (0.82 + 0.3*lo) * (1.0 + uGran*.45*gr) + edge;
    float wax = P.a;
    float res = 1.0 - uResist*smoothstep(uR0, uR1, wax);                            // crayon resist
    dd = clamp(dd*res, 0., 1.25);
    vec3 tr = mix(vec3(1.), uT, clamp(dd,0.,1.));
    tr *= mix(1.0, 0.82, clamp(dd-1.0,0.,1.)*4.);
    vec3 cm = P.rgb*tr;
    // cover mode (blood): the pigment covers the paper colour instead of filtering it, so hot pink stays hot pink on yellowed paper
    vec3 cv = mix(P.rgb, uT*(0.9 + 0.1*lo), clamp(dd*1.15,0.,1.)*.92) * mix(1.0, 0.8, clamp(dd-1.0,0.,1.)*4.);
    o = vec4(mix(cm, cv, uCover), P.a);
  } else o = P;
}`;

// Final composite: paper-tooth emboss (wax sits on the raised tooth, so the emboss goes over everything), warm vignette
const FS_FINAL = `#version 300 es
precision highp float; in vec2 uv; out vec4 o;
uniform sampler2D uS; uniform vec2 uRes; uniform float uVig; uniform float uEmb; uniform vec2 uPoff; uniform float uLift; uniform vec4 uLamp; uniform float uEdgeAge;
${TOOTH}
void main(){
  vec4 S = texture(uS, uv);
  vec2 du = vec2(1./uRes.x, 0.), dv = vec2(0., 1./uRes.y);
  float t0 = toothRawAt(uv, uRes, uPoff), tx = toothRawAt(uv+du, uRes, uPoff), ty = toothRawAt(uv-dv, uRes, uPoff);
  vec2 g = vec2(tx-t0, ty-t0);
  float waxSmooth = 1.0 - .55*S.a;                     // wax fills the paper tooth in a little
  float lit = 1.0 + (g.x*-.9 + g.y*.9)*uEmb*waxSmooth - (1.0-t0)*.035*waxSmooth;
  vec3 c = S.rgb*lit;
  c += S.a*.018*uLift;                                   // faint sheen of the wax
  vec2 q = uv-.5; q.x *= uRes.x/uRes.y;
  float v = 1.0 - uVig*dot(q,q);
  c *= mix(vec3(1.), vec3(1.0,.965,.9), clamp((1.0-v)*1.4,0.,1.)) * v;
  if (uEdgeAge > 0.) {  // browned, slightly ragged page edges
    vec2 e = min(uv, 1.-uv); e.x *= uRes.x/uRes.y;
    float d = min(e.x, e.y) + (vn(uv*vec2(31.,17.))-.5)*.035;
    c *= mix(vec3(1.), vec3(.74,.6,.42), uEdgeAge*smoothstep(.16,.0,d));
  }
  if (uLamp.w > 0.) {   // desk-lamp glow: a pool of warm yellow, edges falling off into warm dark
    vec2 d = (uv - uLamp.xy); d.x *= uRes.x/uRes.y;
    float fall = exp(-dot(d,d)/(uLamp.z*uLamp.z));
    vec3 lamp = mix(vec3(.46,.36,.30), vec3(1.07,1.0,.9), fall);
    c *= mix(vec3(1.), lamp, uLamp.w);
  }
  o = vec4(clamp(c,0.,1.), 1.);
}`;

function sh(gl, type, src) { const s = gl.createShader(type); gl.shaderSource(s, src); gl.compileShader(s); if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(s) + '\n' + src.slice(0, 200)); return s; }
function prog(gl, fs) {
  const p = gl.createProgram(); gl.attachShader(p, sh(gl, gl.VERTEX_SHADER, VS)); gl.attachShader(p, sh(gl, gl.FRAGMENT_SHADER, fs));
  gl.bindAttribLocation(p, 0, 'p'); gl.linkProgram(p); if (!gl.getProgramParameter(p, gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(p));
  const u = {}; const n = gl.getProgramParameter(p, gl.ACTIVE_UNIFORMS);
  for (let i = 0; i < n; i++) { const a = gl.getActiveUniform(p, i); u[a.name] = gl.getUniformLocation(p, a.name); }
  return { p, u };
}

export function makeComp(canvas, w = W, h = H) {
  const gl = canvas.getContext('webgl2', { preserveDrawingBuffer: true, premultipliedAlpha: false, antialias: false, alpha: false });
  if (!gl) throw new Error('no webgl2');
  const buf = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, buf);
  gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]), gl.STATIC_DRAW);
  gl.enableVertexAttribArray(0); gl.vertexAttribPointer(0, 2, gl.FLOAT, false, 0, 0);
  const P = { img: prog(gl, FS_IMG), knock: prog(gl, FS_KNOCK), paper: prog(gl, FS_PAPER), crayon: prog(gl, FS_CRAYON), wash: prog(gl, FS_WASH), final: prog(gl, FS_FINAL) };
  function tex(mip) {
    const t = gl.createTexture(); gl.bindTexture(gl.TEXTURE_2D, t);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, mip ? gl.LINEAR_MIPMAP_LINEAR : gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
    return t;
  }
  function target() {
    const t = tex(false); gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA8, w, h, 0, gl.RGBA, gl.UNSIGNED_BYTE, null);
    const f = gl.createFramebuffer(); gl.bindFramebuffer(gl.FRAMEBUFFER, f); gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, t, 0);
    return { t, f };
  }
  const T = [target(), target()]; let cur = 0;
  const layerTex = tex(false), washTex = tex(true);
  gl.pixelStorei(gl.UNPACK_PREMULTIPLY_ALPHA_WEBGL, false);
  gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, true);
  let toothScale = 1; let pc = [0, 0, 1];
  let age = { a: 0, stains: [], fold: [0, 0, 0] }, curPaper = [0.957, 0.937, 0.890];
  function use(pr, extra = {}) {
    gl.useProgram(pr.p);
    if (pr.u.uRes) gl.uniform2f(pr.u.uRes, w, h);
    if (pr.u.uToothScale) gl.uniform1f(pr.u.uToothScale, toothScale);
    if (pr.u.uPC) gl.uniform3f(pr.u.uPC, pc[0], pc[1], pc[2]);
    if (pr.u.uAge) {
      gl.uniform1f(pr.u.uAge, age.a); gl.uniform3f(pr.u.uFold, ...age.fold);
      const st = new Float32Array(16); age.stains.slice(0, 4).forEach((v, i) => st.set(v, i * 4));
      gl.uniform4fv(pr.u['uStain[0]'], st);
    }
    for (const k in extra) { const l = pr.u[k]; if (!l) continue; const v = extra[k]; if (Array.isArray(v)) (v.length === 2 ? gl.uniform2f : gl.uniform3f).call(gl, l, ...v); else gl.uniform1f(l, v); }
  }
  const draw = () => gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
  gl.viewport(0, 0, w, h);
  return {
    gl,
    set toothScale(v) { toothScale = v; },
    paperCam(x, y, z) { pc = [x, y, z]; },
    setAge(a, stains = [], fold = [0, 0, 0]) { age = { a, stains, fold }; },   // stains: [x, y, r, strength] in page px; fold: [x, slope, strength]   // paper coords: camera centre (in paper pixels) and relative zoom
    begin(paper = [0.957, 0.937, 0.890], poff = [0, 0]) {
      curPaper = paper;
      gl.bindFramebuffer(gl.FRAMEBUFFER, T[cur].f); gl.disable(gl.BLEND);
      use(P.paper, { uPaper: paper, uPoff: poff }); draw();
    },
    knock(cv, paper = curPaper, poff = [0, 0]) {
      gl.activeTexture(gl.TEXTURE0); gl.bindTexture(gl.TEXTURE_2D, layerTex);
      gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, cv);
      gl.bindFramebuffer(gl.FRAMEBUFFER, T[cur].f); gl.disable(gl.BLEND);
      use(P.knock, { uPaper: paper, uPoff: poff }); gl.uniform1i(P.knock.u.uL, 0); draw();
    },
    group(C, o = {}) { this.knock(C.k.c); this.crayon(C.f.c, o); this.crayon(C.l.c, o); },
    crayon(cv, { goff = [0, 0], gain = 1, soft = 0.07, ghost = 0, clear = false } = {}) {
      gl.activeTexture(gl.TEXTURE0); gl.bindTexture(gl.TEXTURE_2D, layerTex);
      gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, cv);
      gl.bindFramebuffer(gl.FRAMEBUFFER, T[cur].f);
      gl.enable(gl.BLEND);
      if (clear) gl.blendFuncSeparate(gl.ZERO, gl.ONE, gl.ONE, gl.ONE_MINUS_SRC_ALPHA);   // clear wax: no colour, only coverage (it resists a wash)
      else gl.blendFuncSeparate(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA, gl.ONE, gl.ONE_MINUS_SRC_ALPHA);
      use(P.crayon, { uGoff: goff, uGain: gain, uSoft: soft, uGhost: ghost }); gl.uniform1i(P.crayon.u.uL, 0); draw();
      gl.disable(gl.BLEND);
    },
    wash(cv, { color = [0.16, 0.2, 0.46], goff = [0, 0], resist = 0.93, edge = 1.6, gran = 0.6, r0 = 0.12, r1 = 0.55, cover = 0 } = {}) {
      gl.activeTexture(gl.TEXTURE1); gl.bindTexture(gl.TEXTURE_2D, washTex);
      gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, cv); gl.generateMipmap(gl.TEXTURE_2D);
      gl.activeTexture(gl.TEXTURE0); gl.bindTexture(gl.TEXTURE_2D, T[cur].t);
      const nx = 1 - cur; gl.bindFramebuffer(gl.FRAMEBUFFER, T[nx].f); gl.disable(gl.BLEND);
      use(P.wash, { uT: color, uGoff: goff, uResist: resist, uEdge: edge, uGran: gran, uR0: r0, uR1: r1, uCover: cover });
      gl.uniform1i(P.wash.u.uPrev, 0); gl.uniform1i(P.wash.u.uW, 1); draw();
      cur = nx;
    },
    image(cv) {   // a pre-rendered image (book page): plain alpha over, not passed through the paper tooth again
      gl.activeTexture(gl.TEXTURE0); gl.bindTexture(gl.TEXTURE_2D, layerTex);
      gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, cv);
      gl.bindFramebuffer(gl.FRAMEBUFFER, T[cur].f);
      gl.enable(gl.BLEND); gl.blendFuncSeparate(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA, gl.ZERO, gl.ONE);
      use(P.img); gl.uniform1i(P.img.u.uL, 0); draw(); gl.disable(gl.BLEND);
    },
    finish({ vig = 0.32, emb = 0.55, poff = [0, 0], lift = 1, lamp = [0.5, 0.5, 1, 0], edge = 0 } = {}) {
      gl.bindFramebuffer(gl.FRAMEBUFFER, null); gl.disable(gl.BLEND);
      gl.activeTexture(gl.TEXTURE0); gl.bindTexture(gl.TEXTURE_2D, T[cur].t);
      use(P.final, { uVig: vig, uEmb: emb, uPoff: poff, uLift: lift, uEdgeAge: edge }); gl.uniform4f(P.final.u.uLamp, ...lamp); gl.uniform1i(P.final.u.uS, 0); draw();
    },
  };
}
