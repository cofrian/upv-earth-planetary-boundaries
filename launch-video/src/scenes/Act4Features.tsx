import React from 'react';
import {AbsoluteFill, Sequence} from 'remotion';
import {colors} from '../../brand/tokens';
import {TourScene} from '../components/TourScene';
import {RagSourcesOverlay} from '../components/RagSourcesOverlay';
import {StackZoom} from '../components/StackZoom';
import {UploadScene} from './UploadScene';

import dashboardCursor from '../../public/recordings/01-dashboard.cursor.json';
import analysisCursor from '../../public/recordings/02-analysis.cursor.json';
import papersCursor from '../../public/recordings/03-papers.cursor.json';
import detailCursor from '../../public/recordings/04-paper-detail.cursor.json';
import chatCursor from '../../public/recordings/06-chat-rag.cursor.json';

// Frame budget (Act 4 total: 3708 frames = 123.6s @ 30fps)
//   1 Dashboard      540  (18s)
//   2 Analysis       462  (15.4s)
//   3 Papers         308  (10.3s)
//   4 Paper detail   462  (15.4s)
//   5 Upload PDF     768  (25.6s · jump-cut over the wait, long dwell on results)
//   6 Chat RAG       576  (19.2s)
//   7 Stack          700  (23.3s · reduced dwell on architecture)
//   subtotal:       3816
//   – 6 crossfades of 18 frames: 108
//   TOTAL:          3708 ✓
const SCHEDULE = [
  {dur: 540, gap: 18},
  {dur: 462, gap: 18},
  {dur: 308, gap: 18},
  {dur: 462, gap: 18},
  {dur: 768, gap: 18},
  {dur: 576, gap: 18},
  {dur: 700, gap: 0},
];

function buildStarts() {
  const starts: number[] = [];
  let t = 0;
  for (const item of SCHEDULE) {
    starts.push(t);
    t += item.dur - item.gap;
  }
  return starts;
}

export const Act4Features: React.FC = () => {
  const starts = buildStarts();

  return (
    <AbsoluteFill style={{backgroundColor: colors.bgSoft}}>
      <Sequence from={starts[0]} durationInFrames={SCHEDULE[0].dur}>
        <TourScene
          url="upv-earth.upv.es/dashboard"
          title="Dashboard"
          description="30,508 papers indexed with SPECTER2 · live coverage by boundary"
          videoSrc="recordings/01-dashboard.webm"
          events={dashboardCursor.events}
          durationInFrames={SCHEDULE[0].dur}
          videoStartFrame={45}
        />
      </Sequence>
      <Sequence from={starts[1]} durationInFrames={SCHEDULE[1].dur}>
        <TourScene
          url="upv-earth.upv.es/analysis"
          title="Exploratory analysis"
          description="Temporal and thematic patterns across all nine boundaries"
          videoSrc="recordings/02-analysis.webm"
          events={analysisCursor.events}
          durationInFrames={SCHEDULE[1].dur}
          videoStartFrame={120}
        />
      </Sequence>
      <Sequence from={starts[2]} durationInFrames={SCHEDULE[2].dur}>
        <TourScene
          url="upv-earth.upv.es/papers"
          title="Browse the corpus"
          description="Semantic search · filter by boundary, year, department"
          videoSrc="recordings/03-papers.webm"
          events={papersCursor.events}
          durationInFrames={SCHEDULE[2].dur}
          videoStartFrame={45}
        />
      </Sequence>
      <Sequence from={starts[3]} durationInFrames={SCHEDULE[3].dur}>
        <TourScene
          url="upv-earth.upv.es/papers/…"
          title="Every paper, in context"
          description="Similar work surfaced by SPECTER2 embedding distance"
          videoSrc="recordings/04-paper-detail.webm"
          events={detailCursor.events}
          durationInFrames={SCHEDULE[3].dur}
          videoStartFrame={60}
        />
      </Sequence>
      <Sequence from={starts[4]} durationInFrames={SCHEDULE[4].dur}>
        <UploadScene
          url="upv-earth.upv.es/upload"
          title="Drop a PDF. Get nine answers."
          description="SPECTER2 → similarity → boundary scoring · end to end in seconds"
          durationInFrames={SCHEDULE[4].dur}
        />
      </Sequence>
      <Sequence from={starts[5]} durationInFrames={SCHEDULE[5].dur}>
        <TourScene
          url="upv-earth.upv.es · assistant"
          title="Ask the corpus directly"
          description="Retrieval-Augmented Generation grounded in the papers it cites"
          videoSrc="recordings/06-chat-rag.webm"
          events={chatCursor.events}
          durationInFrames={SCHEDULE[5].dur}
          videoStartFrame={60}
          overlay={<RagSourcesOverlay startFrame={210} />}
        />
      </Sequence>
      <Sequence from={starts[6]} durationInFrames={SCHEDULE[6].dur}>
        <StackZoom durationInFrames={SCHEDULE[6].dur} />
      </Sequence>
    </AbsoluteFill>
  );
};
