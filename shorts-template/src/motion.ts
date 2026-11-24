import {Easing, interpolate, spring} from 'remotion';

// The whole film uses only these motions.
export const FPS = 30;

/** Calm entrance: fade + 28px rise, no overshoot. */
export const enter = (frame: number, at: number, dist = 28) => {
  const p = spring({frame: frame - at, fps: FPS, config: {damping: 200}, durationInFrames: 14});
  return {opacity: p, transform: `translateY(${(1 - p) * dist}px)`};
};

/** Emphasis pop: small, single overshoot. */
export const pop = (frame: number, at: number, from = 0.86) => {
  const p = spring({frame: frame - at, fps: FPS, config: {damping: 13, mass: 0.6, stiffness: 160}});
  return {opacity: Math.min(1, p * 2), scale: from + (1 - from) * p};
};

/** Slow camera drift for every shot. */
export const kenBurns = (frame: number, dur: number, from = 1.0, to = 1.06) =>
  interpolate(frame, [0, dur], [from, to], {extrapolateRight: 'clamp', easing: Easing.inOut(Easing.quad)});

/** Eased 0..1 between two frames. */
export const ramp = (frame: number, a: number, b: number) =>
  interpolate(frame, [a, b], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.bezier(0.33, 0, 0.2, 1),
  });

export const sec = (s: number) => Math.round(s * FPS);
