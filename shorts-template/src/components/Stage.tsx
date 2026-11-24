import React from 'react';
import {AbsoluteFill, Img, staticFile} from 'remotion';
import {C, FONT, SIZE, STAGE, W} from '../theme';

/** Square stage: everything visual lives in here and is clipped to it. */
export const Stage: React.FC<{children: React.ReactNode}> = ({children}) => (
  <div style={{position: 'absolute', left: 0, top: STAGE.y, width: W, height: STAGE.h, overflow: 'hidden'}}>
    {children}
  </div>
);

/** Background illustration, cover-fit, softened so characters read first. */
export const Backdrop: React.FC<{src: string; scale: number; x?: number; y?: number; dim?: number; blur?: number}> = ({
  src, scale, x = 0, y = 0, dim = 0.08, blur = 3,
}) => (
  <AbsoluteFill>
    <Img src={staticFile(src)} style={{position: 'absolute', height: '100%', left: '50%', top: 0,
      transform: `translateX(-50%) translate(${x}px, ${y}px) scale(${scale * 1.04})`, filter: `blur(${blur}px)`}} />
    <AbsoluteFill style={{background: `linear-gradient(180deg, rgba(0,0,0,0) 55%, rgba(0,0,0,${0.18 + dim}) 100%)`}} />
    <AbsoluteFill style={{background: `rgba(10,10,20,${dim})`}} />
  </AbsoluteFill>
);

export const GROUND = 1010; // every character stands on this line

/** Character / prop placed by its bottom-centre on the ground line (or any y). */
export const Actor: React.FC<{src: string; x: number; h: number; y?: number; style?: React.CSSProperties;
  flip?: boolean; shadow?: boolean}> = ({src, x, h, y = GROUND, style, flip, shadow = true}) => (
  <div style={{position: 'absolute', left: x, top: y, width: 0, height: 0, ...style}}>
    {shadow && (
      <div style={{position: 'absolute', left: -h * 0.28, top: -14, width: h * 0.56, height: 28, borderRadius: '50%',
        background: 'rgba(0,0,0,0.22)', filter: 'blur(8px)'}} />
    )}
    <Img src={staticFile(src)} style={{position: 'absolute', height: h, left: '50%', bottom: 0,
      transform: `translateX(-50%) ${flip ? 'scaleX(-1)' : ''}`}} />
  </div>
);

/** The single on-stage label slot (top-left). One chip per shot. */
export const Chip: React.FC<{text: string; style?: React.CSSProperties; danger?: boolean}> = ({text, style, danger}) => (
  <div style={{position: 'absolute', left: 44, top: 44, fontFamily: FONT, fontSize: SIZE.chip, fontWeight: 800,
    color: C.white, background: danger ? C.danger : C.chip, padding: '12px 24px', borderRadius: 16,
    letterSpacing: -1, ...style}}>{text}</div>
);
