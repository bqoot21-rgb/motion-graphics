import {continueRender, delayRender, staticFile} from 'remotion';

const faces: [string, string][] = [
  ['500', 'Pretendard-Medium.woff2'],
  ['700', 'Pretendard-Bold.woff2'],
  ['800', 'Pretendard-ExtraBold.woff2'],
  ['900', 'Pretendard-Black.woff2'],
];
let loaded = false;
export const ensureFonts = () => {
  if (loaded || typeof document === 'undefined') return;
  loaded = true;
  const h = delayRender('fonts');
  Promise.all(
    faces.map(([w, f]) => {
      const ff = new FontFace('Pretendard', `url(${staticFile('fonts/' + f)})`, {weight: w});
      return ff.load().then((x) => document.fonts.add(x));
    }),
  ).then(() => continueRender(h));
};
