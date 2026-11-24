// ---- Layout: three fixed zones (title / stage / subtitle) ----
export const W = 1080;
export const H = 1920;
export const TITLE = {y: 0, h: 400};
export const STAGE = {y: 400, h: 1080}; // square illustration stage
export const SUB = {y: 1480, h: 440}; // subtitle zone (line sits in the upper part; bottom ~200px is platform UI)

// ---- Type & colour system (keep it this small) ----
export const FONT = 'Pretendard';
export const C = {
  bg: '#0F1015',
  ink: '#1B1D24',
  white: '#FFFFFF',
  accent: '#FFD43B', // the only highlight colour
  quote: '#FFE8A3', // quoted speech
  danger: '#FF4D4F',
  chip: 'rgba(15,16,21,0.78)',
  blue: '#3478F6',
};
export const SIZE = {title1: 66, title2: 84, sub: 72, tag: 34, chip: 40};
