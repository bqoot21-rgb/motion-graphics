import React from 'react';
import {AbsoluteFill, Audio, Sequence, interpolate, Easing, staticFile, useCurrentFrame} from 'remotion';
import data from './data.json';
import {TitleBar} from './components/TitleBar';
import {Stage} from './components/Stage';
import {Subtitle, type Seg} from './components/Subtitle';
import {HIGHLIGHT, SCENES, wf} from './scenes';
import {C} from './theme';
import {ensureFonts} from './fonts';
import {sec} from './motion';

const TRANS = 9; // frames; the only transition in the film: push-in from the right

const SceneSlot: React.FC<{first: boolean; children: React.ReactNode}> = ({first, children}) => {
  const f = useCurrentFrame();
  const p = first ? 1 : interpolate(f, [0, TRANS], [0, 1], {extrapolateRight: 'clamp', easing: Easing.bezier(0.6, 0, 0.2, 1)});
  return (
    <AbsoluteFill style={{transform: `translateX(${(1 - p) * 100}%)`, boxShadow: p < 1 ? '-30px 0 60px rgba(0,0,0,0.35)' : 'none'}}>
      {children}
    </AbsoluteFill>
  );
};

export const Story: React.FC = () => {
  ensureFonts();
  const scenes = data.scenes as {key: string; start: number; dur: number; segs: Seg[]}[];
  const allSegs = scenes.flatMap((s) => s.segs);
  return (
    <AbsoluteFill style={{background: C.bg}}>
      <Stage>
        {scenes.map((s, k) => {
          const Comp = SCENES[s.key];
          return (
            <Sequence key={k} from={sec(s.start)} durationInFrames={sec(s.dur) + TRANS + 2} layout="none">
              <SceneSlot first={k === 0}>
                <Comp start={s.start} dur={s.dur} segs={s.segs} />
              </SceneSlot>
            </Sequence>
          );
        })}
      </Stage>
      <TitleBar tag="실화 썰" line1="문자 한 통 잘못 보냈다가" line2="남의 집 불륜 의심 폭발함" />
      <Subtitle segs={allSegs} highlight={HIGHLIGHT} />
      {/* voice */}
      {allSegs.map((g) => (
        <Sequence key={g.i} from={sec(g.abs)} layout="none">
          <Audio src={staticFile(`audio/${g.i}.mp3`)} />
        </Sequence>
      ))}
      {/* sfx: transitions + chips + the one hit */}
      {scenes.slice(1).map((s, k) => (
        <Sequence key={'w' + k} from={sec(s.start) - 3} layout="none">
          <Audio src={staticFile('sfx/whoosh.wav')} volume={0.5} />
        </Sequence>
      ))}
      {(() => {
        const c = scenes.find((s) => s.key === 'contact');
        if (!c) return null;
        return (
          <Sequence from={sec(c.start) + wf(c, 0, 4)} layout="none">
            <Audio src={staticFile('sfx/ding.wav')} volume={0.6} />
          </Sequence>
        );
      })()}
    </AbsoluteFill>
  );
};
