import React from 'react';
import {AbsoluteFill, Audio, Easing, Img, Sequence, interpolate, spring, staticFile, useCurrentFrame} from 'remotion';
import data from './data.json';
import {ensureFonts} from '../fonts';

/* ------------------------------------------------------------------ */
/*  Cinematic look: full-bleed, one graded palette per beat, big hero  */
/*  props, diegetic text, objects that act out the narration.          */
/* ------------------------------------------------------------------ */

const FPS = 30;
const W = 1080;
const H = 1920;
const sec = (s: number) => Math.round(s * FPS);
const CREAM = '#F5EBD3';

type Word = {t: string; s: number; e: number};
type Seg = {i: number; abs: number; chunks: {words: Word[]}[]};
type Scene = {key: string; start: number; dur: number; segs: Seg[]};
const SCENES = data.scenes as Scene[];

/** scene-local frame where word w of segment j starts */
const at = (sc: Scene, j: number, w: number) => {
  const ws = sc.segs[j].chunks.flatMap((c) => c.words);
  return sec(ws[Math.min(w, ws.length - 1)].s - sc.start);
};

// ---------- motion vocabulary ----------
const spr = (f: number, start: number, cfg: {damping?: number; stiffness?: number; mass?: number} = {}) =>
  spring({frame: f - start, fps: FPS, config: {damping: 18, stiffness: 120, mass: 0.9, ...cfg}});
const settle = (f: number, start: number) => spr(f, start, {damping: 200, stiffness: 90}); // no overshoot
const lin = (f: number, a: number, b: number, ease = Easing.bezier(0.45, 0, 0.2, 1)) =>
  interpolate(f, [a, b], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: ease});
const mix = (a: number, b: number, p: number) => a + (b - a) * p;

// ---------- texture & grade ----------
const NOISE = (freq: number, oct = 2) =>
  `url("data:image/svg+xml;utf8,${encodeURIComponent(
    `<svg xmlns='http://www.w3.org/2000/svg' width='400' height='400'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='${freq}' numOctaves='${oct}' stitchTiles='stitch'/><feColorMatrix type='saturate' values='0'/></filter><rect width='100%' height='100%' filter='url(#n)'/></svg>`,
  )}")`;

/** Flat painted backdrop with chalky blotches (like a textured paper/board). */
const PaperBg: React.FC<{color: string}> = ({color}) => (
  <AbsoluteFill style={{background: color}}>
    <AbsoluteFill style={{backgroundImage: NOISE(0.006, 3), backgroundSize: '1400px 1400px', opacity: 0.35, mixBlendMode: 'soft-light'}} />
    <AbsoluteFill style={{background: 'radial-gradient(ellipse at 50% 35%, rgba(255,255,255,0.16), rgba(0,0,0,0) 60%)'}} />
  </AbsoluteFill>
);

/** Final grade: film grain + vignette + colour wash, applied over everything. */
const Grade: React.FC<{tint: string}> = ({tint}) => {
  const f = useCurrentFrame();
  const o = [0, 137, 251, 83][f % 4];
  return (
    <>
      <AbsoluteFill style={{background: tint, mixBlendMode: 'soft-light', opacity: 0.55}} />
      <AbsoluteFill style={{background: 'radial-gradient(ellipse at 50% 45%, rgba(0,0,0,0) 55%, rgba(20,10,0,0.42) 100%)'}} />
      <AbsoluteFill style={{backgroundImage: NOISE(0.9), backgroundSize: '400px 400px', backgroundPosition: `${o}px ${o * 1.7}px`,
        opacity: 0.16, mixBlendMode: 'overlay'}} />
    </>
  );
};

/** Illustration placed by centre, with soft contact shadow and gentle desaturation to sit in the palette. */
const Prop: React.FC<{src: string; x: number; y: number; w?: number; h?: number; rot?: number; scale?: number;
  opacity?: number; flip?: boolean; shadow?: number; children?: React.ReactNode}> = ({
  src, x, y, w, h, rot = 0, scale = 1, opacity = 1, flip, shadow = 0.28, children,
}) => (
  <div style={{position: 'absolute', left: x, top: y, transform: `translate(-50%,-50%) rotate(${rot}deg) scale(${scale})`,
    opacity, width: w, height: h}}>
    <Img src={staticFile(src)} style={{width: w ?? 'auto', height: h ?? 'auto', display: 'block',
      transform: flip ? 'scaleX(-1)' : undefined,
      filter: `saturate(0.82) sepia(0.08) drop-shadow(0 ${26 * scale}px ${30 * scale}px rgba(30,15,0,${shadow}))`}} />
    {children}
  </div>
);

/** Top typography: small label + big line, letters settle in one by one; swaps cross-fade. */
const Head: React.FC<{items: {at: number; label: string; big: string; color?: string}[]}> = ({items}) => {
  const f = useCurrentFrame();
  return (
    <>
      {items.map((it, k) => {
        const next = items[k + 1]?.at ?? Infinity;
        if (f < it.at || f > next + 8) return null;
        const out = Number.isFinite(next) ? 1 - lin(f, next, next + 7) : 1;
        const lab = settle(f, it.at);
        return (
          <div key={k} style={{position: 'absolute', top: 150, width: W, textAlign: 'center', fontFamily: 'Pretendard', opacity: out}}>
            <div style={{fontSize: 44, fontWeight: 700, color: CREAM, opacity: 0.72 * lab, letterSpacing: 2,
              transform: `translateY(${(1 - lab) * 10}px)`}}>{it.label}</div>
            <div style={{fontSize: 104, fontWeight: 900, color: it.color ?? CREAM, letterSpacing: -3, marginTop: 6,
              textShadow: '0 6px 18px rgba(40,20,0,0.18)', whiteSpace: 'nowrap'}}>
              {[...it.big].map((ch, i) => {
                const p = settle(f, it.at + 3 + i * 1.2);
                return (
                  <span key={i} style={{display: 'inline-block', opacity: p, transform: `translateY(${(1 - p) * 18}px)`,
                    filter: `blur(${(1 - p) * 6}px)`, whiteSpace: 'pre'}}>{ch}</span>
                );
              })}
            </div>
          </div>
        );
      })}
    </>
  );
};

const Wings: React.FC<{f: number; size: number; spread: number}> = ({f, size, spread}) => {
  const flap = Math.sin(f * 0.9) * 22;
  return (
    <>
      {[-1, 1].map((s) => (
        <Img key={s} src={staticFile('img/tenshi_wing1.png')} style={{position: 'absolute', width: size, left: '50%', top: '30%',
          transformOrigin: s < 0 ? '100% 70%' : '0% 70%',
          transform: `translate(${s < 0 ? -spread - size : spread}px, -50%) ${s > 0 ? 'scaleX(-1)' : ''} rotate(${s * (flap + 6)}deg)`}} />
      ))}
    </>
  );
};

/* ------------------------------ beats ------------------------------ */

const Party: React.FC<{sc: Scene}> = ({sc}) => {
  const f = useCurrentFrame();
  const D = sec(sc.dur);
  const pool = settle(f, 2);
  const tLady = at(sc, 1, 0);
  const m = spr(f, tLady, {damping: 22, stiffness: 70}); // layout morph to make room for the lady
  const beer = spr(f, at(sc, 0, 4), {damping: 14, stiffness: 110});
  const walk = lin(f, tLady + 4, tLady + sec(1.5), Easing.bezier(0.25, 0.1, 0.25, 1));
  const step = walk > 0 && walk < 1 ? Math.abs(Math.sin(f * 0.6)) * -14 : 0;
  const cam = interpolate(f, [0, D], [1.04, 1.1]);
  const ball = (f % 40) / 40;
  return (
    <AbsoluteFill style={{transform: `scale(${cam})`, transformOrigin: '50% 60%'}}>
      <AbsoluteFill>
        <Img src={staticFile('img/bg_outside_jutaku_yuyake.jpg')} style={{position: 'absolute', height: H, left: '50%',
          transform: `translateX(-50%) translateX(${mix(60, -40, f / D)}px) scale(1.08)`, filter: 'blur(7px) saturate(0.7)'}} />
      </AbsoluteFill>
      <Prop src="img/pool_ball.png" w={940} x={mix(540, 790, m)} y={mix(1300, 1380, m) + (1 - pool) * 160}
        scale={mix(1, 0.6, m)} opacity={pool} />
      <Prop src="img/beach_ball.png" w={150} x={mix(250, 640, m) + 0} y={mix(1040, 1160, m) - Math.sin(ball * Math.PI) * 90}
        rot={f * 4} scale={mix(1, 0.7, m)} opacity={pool} shadow={0.15} />
      <Prop src="img/beer_man.png" h={820} x={mix(900, 990, m)} y={mix(1680, 1640, m) + (1 - beer) * 700}
        rot={-6 + Math.sin(f * 0.12) * 1.5} scale={mix(1, 0.66, m)} />
      <Prop src="img/pet_dog_sanpo_woman.png" h={860} x={mix(-420, 380, walk)} y={1340 + step} />
      <Head items={[
        {at: at(sc, 0, 1), label: '이웃집', big: '마이크네 수영장 파티'},
        {at: at(sc, 1, 3), label: '잠깐 들른', big: '동네 아줌마'},
      ]} />
    </AbsoluteFill>
  );
};

const Ask: React.FC<{sc: Scene}> = ({sc}) => {
  const f = useCurrentFrame();
  const D = sec(sc.dur);
  const cam = interpolate(f, [0, D], [1.0, 1.06]);
  const lady = settle(f, 0);
  const tw = at(sc, 0, 5);
  const wine = spr(f, tw, {damping: 16, stiffness: 100});
  return (
    <AbsoluteFill>
      <PaperBg color="#B98C80" />
      <AbsoluteFill style={{transform: `scale(${cam})`, transformOrigin: '60% 55%'}}>
        <Prop src="img/pet_dog_sanpo_woman.png" h={1450} x={600} y={1330 + (1 - lady) * 60} opacity={lady} />
        <Prop src="img/red_wine.png" h={620} x={mix(-320, 200, wine)} y={1480} rot={mix(-25, -7, wine) + Math.sin(f * 0.08) * 1.2} />
      </AbsoluteFill>
      <Head items={[
        {at: at(sc, 0, 1), label: '아줌마의 부탁', big: '남편 데이브한테'},
        {at: at(sc, 0, 10), label: '아줌마의 부탁', big: '문자 좀 해줘요'},
      ]} />
    </AbsoluteFill>
  );
};

// phone-in-hand geometry (screen rect inside smartphone_hand.png, as fractions)
const HAND = {w: 1077, h: 1200, sx: 0.3826, sy: 0.1033, sw: 0.3426, sh: 0.5483};

const Screen: React.FC<{children: React.ReactNode}> = ({children}) => (
  <div style={{position: 'absolute', inset: 0, background: '#FBFAF6', fontFamily: 'Pretendard', overflow: 'hidden'}}>{children}</div>
);

const HandPhone: React.FC<{img: string; height: number; x: number; y: number; rot?: number; scale?: number; flip?: boolean;
  children: React.ReactNode}> = ({img, height, x, y, rot = 0, scale = 1, flip, children}) => {
  const w = (HAND.w / HAND.h) * height;
  return (
    <div style={{position: 'absolute', left: x, top: y, width: w, height, transform: `translate(-50%,-50%) rotate(${rot}deg) scale(${scale})`,
      filter: 'drop-shadow(0 30px 40px rgba(20,30,20,0.3))'}}>
      <Img src={staticFile(img)} style={{width: w, height, transform: flip ? 'scaleX(-1)' : undefined, filter: 'saturate(0.85)'}} />
      <div style={{position: 'absolute', left: (flip ? 1 - HAND.sx - HAND.sw : HAND.sx) * w, top: HAND.sy * height,
        width: HAND.sw * w, height: HAND.sh * height, borderRadius: 6, overflow: 'hidden'}}>{children}</div>
    </div>
  );
};

const MSG = '나 마이크네서 와인 한 잔만 하고 갈게';

const Phone: React.FC<{sc: Scene}> = ({sc}) => {
  const f = useCurrentFrame();
  const rise = spr(f, 0, {damping: 20, stiffness: 80});
  const tType = at(sc, 0, 0);
  const tSend = at(sc, 0, 1) + 4;
  const tList = at(sc, 0, 2);
  const tTwo = at(sc, 0, 4);
  const tGo = at(sc, 1, 0);
  const tWrong = at(sc, 1, 1);
  const tLand = at(sc, 1, 3) + 2;
  const go = spr(f, tGo, {damping: 22, stiffness: 70});
  const typed = Math.floor(MSG.length * lin(f, tType, tSend - 6, Easing.linear));
  const sent = settle(f, tSend);
  const slide = lin(f, tList, tList + 10);
  const hi = (k: number) => lin(f, tTwo + k * 4, tTwo + k * 4 + 8);
  const p2 = spr(f, tWrong, {damping: 20, stiffness: 80});
  // envelope flight from phone 1 to phone 2
  const fly = lin(f, tGo + 6, tLand, Easing.bezier(0.35, 0, 0.25, 1));
  const ex = mix(330, 790, fly);
  const ey = mix(1300, 1080, fly) - Math.sin(fly * Math.PI) * 520;
  const notif = spr(f, tLand, {damping: 14, stiffness: 140});
  const ripple = lin(f, tSend - 4, tSend + 8, Easing.out(Easing.quad));

  const chat = (
    <Screen>
      <div style={{height: 120, borderBottom: '2px solid #E6E3DA', display: 'flex', alignItems: 'flex-end', justifyContent: 'center',
        paddingBottom: 18, fontSize: 36, fontWeight: 800, color: '#2B2A27'}}>데이브</div>
      {sent > 0.01 && (
        <div style={{position: 'absolute', right: 24, bottom: 150 + (1 - sent) * -40, maxWidth: 400, background: '#4E8F6E',
          color: '#fff', fontSize: 34, fontWeight: 600, padding: '18px 24px', borderRadius: 30, opacity: sent, lineHeight: 1.35}}>{MSG}</div>
      )}
      <div style={{position: 'absolute', left: 18, right: 18, bottom: 26, height: 90, borderRadius: 45, background: '#EFEDE6',
        display: 'flex', alignItems: 'center', padding: '0 24px', fontSize: 30, color: '#2B2A27'}}>
        <span style={{flex: 1, whiteSpace: 'nowrap', overflow: 'hidden'}}>{sent > 0.5 ? '' : MSG.slice(0, typed)}
          {sent < 0.5 && f % 20 < 10 && <span style={{color: '#4E8F6E'}}>|</span>}</span>
        <div style={{width: 64, height: 64, borderRadius: 32, background: '#4E8F6E', position: 'relative'}}>
          <div style={{position: 'absolute', inset: -40 * ripple, borderRadius: '50%', border: `4px solid rgba(78,143,110,${1 - ripple})`}} />
        </div>
      </div>
    </Screen>
  );
  const rows = [
    {n: '데이브', sub: '최근 연락', c: '#D9925B'},
    {n: '데이브', sub: '저장된 지 2년', c: '#6F8FC9'},
  ];
  const list = (
    <Screen>
      <div style={{padding: '70px 26px 0'}}>
        <div style={{fontSize: 40, fontWeight: 800, color: '#2B2A27', marginBottom: 20}}>연락처</div>
        <div style={{height: 76, borderRadius: 20, background: '#EFEDE6', display: 'flex', alignItems: 'center', padding: '0 22px',
          fontSize: 32, color: '#2B2A27', fontWeight: 600}}>⌕ 데이브</div>
        {rows.map((r, k) => (
          <div key={k} style={{marginTop: 22, height: 120, borderRadius: 24, display: 'flex', alignItems: 'center', gap: 22,
            padding: '0 20px', background: `rgba(214,95,80,${0.16 * hi(k)})`, boxShadow: `inset 0 0 0 ${4 * hi(k)}px rgba(214,95,80,0.9)`}}>
            <div style={{width: 80, height: 80, borderRadius: 40, background: r.c, color: '#fff', fontSize: 38, fontWeight: 800,
              display: 'flex', alignItems: 'center', justifyContent: 'center'}}>D</div>
            <div>
              <div style={{fontSize: 38, fontWeight: 800, color: '#2B2A27'}}>{r.n}</div>
              <div style={{fontSize: 26, fontWeight: 500, color: '#8C877B', marginTop: 4}}>{r.sub}</div>
            </div>
          </div>
        ))}
      </div>
    </Screen>
  );
  const lock = (
    <Screen>
      <div style={{position: 'absolute', inset: 0, background: 'linear-gradient(180deg,#5B6E8C,#9A8DA8)'}} />
      <div style={{position: 'absolute', top: 120, width: '100%', textAlign: 'center', color: '#fff', fontSize: 110, fontWeight: 300}}>7:42</div>
      <div style={{position: 'absolute', left: 22, right: 22, top: 330, borderRadius: 30, background: 'rgba(255,255,255,0.88)',
        padding: '22px 26px', opacity: Math.min(1, notif * 1.5), transform: `translateY(${(1 - notif) * -40}px) scale(${0.9 + 0.1 * notif})`}}>
        <div style={{fontSize: 26, color: '#6B6760', fontWeight: 600}}>새 메시지</div>
        <div style={{fontSize: 32, color: '#2B2A27', fontWeight: 700, marginTop: 6, lineHeight: 1.3}}>{MSG}</div>
      </div>
    </Screen>
  );
  return (
    <AbsoluteFill>
      <PaperBg color="#6E9A86" />
      <HandPhone img="img/smartphone_hand.png" height={1750} x={mix(500, 300, go)} y={mix(1180, 1430, go) + (1 - rise) * 1100}
        rot={mix(0, -10, go)} scale={mix(1, 0.56, go)}>
        <div style={{position: 'absolute', inset: 0, transform: `translateX(${-100 * slide}%)`}}>{chat}</div>
        <div style={{position: 'absolute', inset: 0, transform: `translateX(${100 - 100 * slide}%)`}}>{list}</div>
      </HandPhone>
      {f > tWrong - 2 && (
        <HandPhone img="img/smartphone_hand2.png" height={1750} x={mix(1500, 800, p2)} y={1120} rot={mix(18, 9, p2)} scale={0.56} flip>
          {lock}
        </HandPhone>
      )}
      {fly > 0 && fly < 1 && (
        <div style={{position: 'absolute', left: ex, top: ey, width: 230, transform: `translate(-50%,-50%) rotate(${Math.sin(fly * 8) * 10}deg) scale(${mix(0.6, 1, Math.sin(fly * Math.PI))})`,
          filter: 'drop-shadow(0 16px 18px rgba(0,0,0,0.25))'}}>
          <Wings f={f} size={120} spread={70} />
          <Img src={staticFile('img/envelope_airmail.png')} style={{width: 230, position: 'relative'}} />
        </div>
      )}
      <Head items={[
        {at: at(sc, 0, 3), label: '연락처 검색', big: '데이브가 두 명'},
        {at: tWrong, label: '전송 완료', big: '엉뚱한 데이브에게', color: '#FFD9C2'},
      ]} />
    </AbsoluteFill>
  );
};

const BEATS: Record<string, {C: React.FC<{sc: Scene}>; tint: string}> = {
  party: {C: Party, tint: '#F2B27A'},
  ask: {C: Ask, tint: '#E9A48F'},
  phone: {C: Phone, tint: '#9CC7A8'},
};

const XF = 10; // cross-dissolve + settle-in between beats

const Slot: React.FC<{first: boolean; children: React.ReactNode}> = ({first, children}) => {
  const f = useCurrentFrame();
  const p = first ? 1 : lin(f, 0, XF);
  return <AbsoluteFill style={{opacity: p, transform: `scale(${mix(1.05, 1, p)})`, overflow: 'hidden'}}>{children}</AbsoluteFill>;
};

export const Cine: React.FC = () => {
  ensureFonts();
  const segs = SCENES.flatMap((s) => s.segs);
  const sfx = (name: string, t: number, vol = 0.5) => (
    <Sequence key={name + t} from={Math.max(0, Math.round(t))} layout="none">
      <Audio src={staticFile(`sfx/${name}.wav`)} volume={vol} />
    </Sequence>
  );
  const S = Object.fromEntries(SCENES.map((s) => [s.key, s]));
  const g = (k: string) => sec(S[k].start);
  return (
    <AbsoluteFill style={{background: '#222', overflow: 'hidden'}}>
      {SCENES.map((sc, k) => {
        const B = BEATS[sc.key];
        return (
          <Sequence key={k} from={sec(sc.start)} durationInFrames={sec(sc.dur) + XF + 2} layout="none">
            <Slot first={k === 0}>
              <B.C sc={sc} />
              <Grade tint={B.tint} />
            </Slot>
          </Sequence>
        );
      })}
      {segs.map((s) => (
        <Sequence key={'v' + s.i} from={sec(s.abs)} layout="none">
          <Audio src={staticFile(`audio/${s.i}.mp3`)} />
        </Sequence>
      ))}
      {sfx('pop', g('party') + at(S.party, 0, 1), 0.35)}
      {sfx('pop', g('party') + at(S.party, 0, 4), 0.4)}
      {sfx('whoosh', g('party') + at(S.party, 1, 0), 0.4)}
      {sfx('whoosh', g('ask') - 4, 0.35)}
      {sfx('pop', g('ask') + at(S.ask, 0, 5), 0.4)}
      {sfx('whoosh', g('phone') - 4, 0.35)}
      {sfx('tick', g('phone') + at(S.phone, 0, 1), 0.6)}
      {sfx('ding', g('phone') + at(S.phone, 0, 4), 0.35)}
      {sfx('whoosh', g('phone') + at(S.phone, 1, 0), 0.5)}
      {sfx('ding', g('phone') + at(S.phone, 1, 3) + 2, 0.5)}
    </AbsoluteFill>
  );
};

export const CINE_FRAMES = Math.ceil(data.total * FPS);
