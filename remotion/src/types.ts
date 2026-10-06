export type TrackType = 'visual' | 'text' | 'audio' | 'overlay';

export type TimelineItem = {
  item_id: string;
  start_frame: number;
  duration_frames: number;
  scene_id?: string;
  asset_id?: string;
  fit?: string;
  motion?: string;
  text?: string;
  style?: string;
  audio_id?: string;
  volume?: number;
  template_id?: string;
};

export type TimelineTrack = {
  track_id: string;
  type: string;
  items: TimelineItem[];
};

export type Branding = {
  handle: string;
  background: string;
  primary: string;
  secondary: string;
  accent: string;
  text: string;
  muted: string;
};

export type Timeline = {
  schema_version: string;
  job_id: string;
  composition_id: string;
  width: number;
  height: number;
  fps: number;
  duration_frames: number;
  branding: Branding;
  tracks: TimelineTrack[];
};

export type RootProps = {
  timeline: Timeline;
  meta?: {
    job_id?: string;
    account?: string;
  };
};

export const trackItems = (timeline: Timeline, type: string): TimelineItem[] =>
  timeline.tracks.find((t) => t.type === type)?.items ?? [];
