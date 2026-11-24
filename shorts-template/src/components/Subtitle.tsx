import React from 'react';
import {useCurrentFrame} from 'remotion';
import {C, FONT, SIZE, SUB, W} from '../theme';
import {FPS, enter} from '../motion';

export type Chunk = {from: number; to: number; words: {t: string; s: number; e: number}[]};
export type Seg = {i: number; speaker: string; abs: number; end: number; chunks: Chunk[]};

const SPEAKER: Record<string, string | null> = {N: null, L: '아줌마', W: '그 집 아내', D: '엉뚱한 데이브'};

/** Renders `text`, painting any phrase from `hl` in the accent colour. */
const Highlighted: React.FC<{text: string; hl: string[]; base: string}> = ({text, hl, base}) => {
  const parts: {s: string; on: boolean}[] = [];
  let rest = text;
  while (rest.length) {
    let best = -1;
    let bp = '';
    for (const h of hl) {
      const i = rest.indexOf(h);
      if (i >= 0 && (best < 0 || i < best)) {
        best = i;
        bp = h;
      }
    }
    if (best < 0) {
      parts.push({s: rest, on: false});
      break;
    }
    if (best > 0) parts.push({s: rest.slice(0, best), on: false});
    parts.push({s: bp, on: true});
    rest = rest.slice(best + bp.length);
  }
  return (
    <>
      {parts.map((p, i) => (
        <span key={i} style={{color: p.on ? C.accent : base}}>{p.s}</span>
      ))}
    </>
  );
};

/** One line, one fixed position, always. Quotes get a speaker tag in a fixed slot above. */
export const Subtitle: React.FC<{segs: Seg[]; highlight: string[]}> = ({segs, highlight}) => {
  const frame = useCurrentFrame();
  const t = frame / FPS;
  let cur: {seg: Seg; ch: Chunk} | null = null;
  for (const seg of segs)
    for (const ch of seg.chunks) if (t >= ch.from - 0.04 && t < ch.to - 0.02) cur = {seg, ch};
  // hold the last line of a segment until the next segment starts (avoid blank flicker)
  if (!cur) {
    for (const seg of segs) {
      const last = seg.chunks[seg.chunks.length - 1];
      const nextStart = segs.find((s) => s.abs > seg.abs)?.abs ?? Infinity;
      if (t >= last.from && t < Math.min(nextStart - 0.05, seg.end + 0.6)) cur = {seg, ch: last};
    }
  }
  if (!cur) return null;
  const speaker = SPEAKER[cur.seg.speaker];
  const text = cur.ch.words.map((w) => w.t).join(' ');
  const f0 = Math.round(cur.ch.from * FPS);
  const segStart = Math.round(cur.seg.chunks[0].from * FPS);
  const anim = enter(frame, f0 - 1, 10);
  return (
    <div style={{position: 'absolute', left: 0, top: SUB.y, width: W, height: SUB.h, fontFamily: FONT}}>
      {speaker && (
        <div style={{position: 'absolute', top: 44, width: W, display: 'flex', justifyContent: 'center',
          ...enter(frame, segStart - 1, 8)}}>
          <div style={{fontSize: SIZE.tag, fontWeight: 800, color: C.ink, background: C.quote,
            padding: '6px 18px', borderRadius: 999}}>{speaker}</div>
        </div>
      )}
      <div
        style={{
          position: 'absolute', top: 100, width: W, textAlign: 'center', fontSize: SIZE.sub, fontWeight: 800,
          letterSpacing: -1.5, lineHeight: 1.2, whiteSpace: 'nowrap', ...anim,
        }}
      >
        <Highlighted text={speaker ? `“${text}”` : text} hl={highlight} base={speaker ? C.quote : C.white} />
      </div>
    </div>
  );
};
