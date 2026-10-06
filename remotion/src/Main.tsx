import React from 'react';
import {AbsoluteFill, Audio, Sequence, staticFile} from 'remotion';

import {BrandLayer} from './branding/BrandLayer';
import {ImageScene} from './scenes/ImageScene';
import {TextScene} from './scenes/TextScene';
import {RootProps, trackItems} from './types';

export const Main: React.FC<RootProps> = ({timeline}) => {
  const visuals = trackItems(timeline, 'visual');
  const texts = trackItems(timeline, 'text');
  const audios = trackItems(timeline, 'audio');
  const overlays = trackItems(timeline, 'overlay');

  return (
    <AbsoluteFill style={{backgroundColor: timeline.branding.background}}>
      {visuals.map((item) => (
        <Sequence
          key={item.item_id}
          name={`visual-${item.item_id}`}
          from={item.start_frame}
          durationInFrames={item.duration_frames}
        >
          {item.asset_id ? (
            <ImageScene item={item} />
          ) : (
            <TextScene item={item} branding={timeline.branding} asVisual />
          )}
        </Sequence>
      ))}

      {texts.map((item) => (
        <Sequence
          key={item.item_id}
          name={`text-${item.item_id}`}
          from={item.start_frame}
          durationInFrames={item.duration_frames}
        >
          <TextScene item={item} branding={timeline.branding} />
        </Sequence>
      ))}

      {audios.map((item) => (
        <Sequence
          key={item.item_id}
          name={`audio-${item.item_id}`}
          from={item.start_frame}
          durationInFrames={item.duration_frames}
        >
          <Audio
            src={staticFile(item.audio_id ?? 'placeholder-audio.wav')}
            volume={item.volume ?? 1}
          />
        </Sequence>
      ))}

      {overlays.map((item) => (
        <Sequence
          key={item.item_id}
          name={`overlay-${item.item_id}`}
          from={item.start_frame}
          durationInFrames={item.duration_frames}
        >
          <BrandLayer branding={timeline.branding} />
        </Sequence>
      ))}
    </AbsoluteFill>
  );
};
