import React from 'react';
import {CalculateMetadataFunction, Composition} from 'remotion';

import {Main} from './Main';
import squareDummy from './timeline/square-dummy.json';
import verticalDummy from './timeline/vertical-dummy.json';
import {RootProps} from './types';

const calculateMetadata: CalculateMetadataFunction<RootProps> = ({props}) => ({
  durationInFrames: props.timeline.duration_frames,
  fps: props.timeline.fps,
  width: props.timeline.width,
  height: props.timeline.height,
});

export const Root: React.FC = () => (
  <>
    <Composition
      id="MLBBVertical"
      component={Main}
      defaultProps={{timeline: verticalDummy}}
      calculateMetadata={calculateMetadata}
    />
    <Composition
      id="SquarePost"
      component={Main}
      defaultProps={{timeline: squareDummy}}
      calculateMetadata={calculateMetadata}
    />
  </>
);
