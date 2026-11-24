import React from 'react';
import {C, FONT, SIZE, TITLE, W} from '../theme';

/** Pinned hook title. Never moves. */
export const TitleBar: React.FC<{tag: string; line1: string; line2: string}> = ({tag, line1, line2}) => (
  <div
    style={{
      position: 'absolute', left: 0, top: TITLE.y, width: W, height: TITLE.h, background: C.bg,
      display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 10,
      fontFamily: FONT, paddingTop: 20,
    }}
  >
    <div style={{background: C.accent, color: C.ink, fontWeight: 800, fontSize: SIZE.tag, padding: '6px 18px',
      borderRadius: 10, letterSpacing: -0.5}}>{tag}</div>
    <div style={{color: C.white, fontWeight: 800, fontSize: SIZE.title1, letterSpacing: -2, lineHeight: 1.15}}>{line1}</div>
    <div style={{color: C.accent, fontWeight: 900, fontSize: SIZE.title2, letterSpacing: -2.5, lineHeight: 1.1}}>{line2}</div>
  </div>
);
