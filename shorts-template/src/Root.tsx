import React from 'react';
import {Composition} from 'remotion';
import {Story} from './Story';
import data from './data.json';
import {H, W} from './theme';

export const Root: React.FC = () => (
  <Composition id="Story" component={Story} durationInFrames={Math.ceil(data.total * 30)} fps={30} width={W} height={H} />
);
