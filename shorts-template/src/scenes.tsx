import React from 'react';
import {useCurrentFrame} from 'remotion';
import {Actor, Backdrop, Chip, GROUND} from './components/Stage';
import {Phone} from './components/Phone';
import type {Seg} from './components/Subtitle';
import {C} from './theme';
import {enter, kenBurns, pop, ramp, sec} from './motion';

export type SceneProps = {start: number; dur: number; segs: Seg[]};

/** local frame of word `w` in segment `j` of this scene */
export const wf = (p: SceneProps, j: number, w = 0) => {
  const words = p.segs[j].chunks.flatMap((c) => c.words);
  return sec(words[Math.min(w, words.length - 1)].s - p.start);
};
export const sf = (p: SceneProps, j: number) => sec(p.segs[j].abs - p.start);

/** Swap chip text over time; each new chip enters the same way, same place. */
const Chips: React.FC<{items: {at: number; text: string; danger?: boolean}[]}> = ({items}) => {
  const f = useCurrentFrame();
  const cur = [...items].reverse().find((i) => f >= i.at);
  if (!cur) return null;
  return <Chip text={cur.text} danger={cur.danger} style={enter(f, cur.at, 16)} />;
};

export const PoolScene: React.FC<SceneProps> = (p) => {
  const f = useCurrentFrame();
  const D = sec(p.dur);
  const ladyIn = sf(p, 1);
  const walk = ramp(f, ladyIn, ladyIn + sec(1.2));
  const pan = 30 * walk; // camera drifts toward the newcomer
  const ladyX = -280 + 490 * walk;
  const bob = walk > 0 && walk < 1 ? -Math.abs(Math.sin(f * 0.55)) * 12 : 0;
  const z = kenBurns(f, D, 1.0, 1.07);
  return (
    <div style={{position: 'absolute', inset: 0, transform: `scale(${z}) translateX(${pan}px)`, transformOrigin: '50% 70%'}}>
      <Backdrop src="img/bg_outside_jutaku.jpg" scale={1} x={60} />
      <Actor src="img/pool_asobu_couple.png" x={640} h={430} y={GROUND + 10} style={enter(f, 3)} />
      <Actor src="img/beer_man.png" x={930} h={520} style={enter(f, wf(p, 0, 4))} />
      <Actor src="img/pet_dog_sanpo_woman.png" x={ladyX} h={560} y={GROUND + bob} />
      <Chips items={[{at: wf(p, 0, 2), text: '마이크네 수영장 파티'}, {at: ladyIn + sec(0.4), text: '동네 아줌마 등장'}]} />
    </div>
  );
};

export const AskScene: React.FC<SceneProps> = (p) => {
  const f = useCurrentFrame();
  const z = kenBurns(f, sec(p.dur), 1.0, 1.05);
  const wine = pop(f, wf(p, 0, 5));
  return (
    <div style={{position: 'absolute', inset: 0, transform: `scale(${z})`, transformOrigin: '35% 60%'}}>
      <Backdrop src="img/bg_outside_jutaku.jpg" scale={1.3} x={-120} y={-40} dim={0.12} />
      <Actor src="img/pet_dog_sanpo_woman.png" x={400} h={900} y={GROUND + 40} />
      <Actor src="img/red_wine.png" x={840} h={400} y={GROUND - 120} shadow={false}
        style={{opacity: wine.opacity, transform: `scale(${wine.scale})`}} />
      <Chips items={[{at: 6, text: '아줌마의 부탁'}]} />
    </div>
  );
};

export const ContactScene: React.FC<SceneProps> = (p) => {
  const f = useCurrentFrame();
  const hit = wf(p, 0, 4); // "두"
  const ph = pop(f, 0, 0.92);
  const push = 1 + 0.06 * ramp(f, hit, hit + 12);
  const names = [
    {name: '다니엘', color: '#F4A259'},
    {name: '데이브', color: '#5B8DEF', flag: ramp(f, hit, hit + 6)},
    {name: '데이브', color: '#7AC27A', flag: ramp(f, hit + 4, hit + 10)},
    {name: '데보라', color: '#E86FA6'},
    {name: '드웨인', color: '#9C7CF0'},
  ];
  return (
    <div style={{position: 'absolute', inset: 0}}>
      <Backdrop src="img/bg_outside_jutaku.jpg" scale={1.15} dim={0.5} blur={8} />
      <div style={{position: 'absolute', inset: 0, transform: `scale(${push})`, transformOrigin: '50% 45%'}}>
        <Phone title="연락처" contacts={names}
          style={{left: 260, top: 60, opacity: ph.opacity, transform: `scale(${ph.scale})`}} />
      </div>
      <Chips items={[{at: 6, text: '연락처에서 “데이브” 찾기'}, {at: hit, text: '데이브가 두 명?!', danger: true}]} />
    </div>
  );
};

export const SCENES: Record<string, React.FC<SceneProps>> = {pool: PoolScene, ask: AskScene, contact: ContactScene};
export const HIGHLIGHT = ['수영장 파티', '동네 아줌마', '와인 한 잔', '두 명'];
export const ACCENT = C.accent;
