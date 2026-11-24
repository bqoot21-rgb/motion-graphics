import React from 'react';
import {C, FONT} from '../theme';

export type Contact = {name: string; color: string; flag?: number}; // flag 0..1 highlight strength

/** Generic phone mock (no brand), real typography. */
export const Phone: React.FC<{title: string; contacts?: Contact[]; children?: React.ReactNode; style?: React.CSSProperties}> = ({
  title, contacts, children, style,
}) => (
  <div style={{position: 'absolute', width: 560, height: 980, borderRadius: 72, background: '#15161B', padding: 18,
    boxShadow: '0 40px 80px rgba(0,0,0,0.35)', fontFamily: FONT, ...style}}>
    <div style={{width: '100%', height: '100%', borderRadius: 56, background: '#F5F6FA', overflow: 'hidden',
      position: 'relative'}}>
      <div style={{position: 'absolute', top: 18, left: '50%', transform: 'translateX(-50%)', width: 150, height: 36,
        borderRadius: 18, background: '#15161B'}} />
      <div style={{paddingTop: 84, height: 150, background: '#fff', borderBottom: '2px solid #E4E6EC', textAlign: 'center',
        fontSize: 40, fontWeight: 800, color: C.ink, letterSpacing: -1}}>{title}</div>
      {contacts && (
        <div style={{padding: '18px 22px'}}>
          {contacts.map((c, i) => (
            <div key={i} style={{display: 'flex', alignItems: 'center', gap: 22, height: 108, padding: '0 18px',
              borderRadius: 22, marginBottom: 6,
              background: c.flag ? `rgba(255,77,79,${0.12 * c.flag})` : 'transparent',
              boxShadow: c.flag ? `inset 0 0 0 ${5 * c.flag}px ${C.danger}` : 'none'}}>
              <div style={{width: 72, height: 72, borderRadius: 36, background: c.color, color: '#fff',
                display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 34, fontWeight: 800}}>
                {c.name[0]}
              </div>
              <div style={{fontSize: 42, fontWeight: 700, color: C.ink, letterSpacing: -1}}>{c.name}</div>
            </div>
          ))}
        </div>
      )}
      {children}
    </div>
  </div>
);
