import './index.css';
import {AbsoluteFill, Composition, Series} from 'remotion';
import {colors} from '../brand/tokens';
import {Act1Hook} from './scenes/Act1Hook';
import {Act2Manifesto} from './scenes/Act2Manifesto';
import {Act3Reveal} from './scenes/Act3Reveal';
import {Act4Features} from './scenes/Act4Features';
import {Act5Vision} from './scenes/Act5Vision';
import {Act6CTA} from './scenes/Act6CTA';
import {ProjectWatermark} from './components/ProjectWatermark';

// UPV-EARTH launch video · 1920x1080 @ 30fps · 5400 frames (3:00).
//
// Layout temporal (frames):
//   Act1 Hook       0    – 240   (8s)
//   Act2 Manifesto  240  – 600   (12s)
//   Act3 Reveal     600  – 780   (6s)
//   Act4 Tour       780  – 4620  (128s)
//   Act5 Vision     4620 – 4980  (12s)
//   Act6 CTA        4980 – 5400  (14s)

const LaunchVideo: React.FC = () => {
  return (
    <AbsoluteFill style={{backgroundColor: colors.bg}}>
      <ProjectWatermark />
      <Series>
        <Series.Sequence durationInFrames={240}>
          <Act1Hook />
        </Series.Sequence>
        <Series.Sequence durationInFrames={360}>
          <Act2Manifesto />
        </Series.Sequence>
        <Series.Sequence durationInFrames={180}>
          <Act3Reveal />
        </Series.Sequence>
        <Series.Sequence durationInFrames={3840}>
          <Act4Features />
        </Series.Sequence>
        <Series.Sequence durationInFrames={360}>
          <Act5Vision />
        </Series.Sequence>
        <Series.Sequence durationInFrames={420}>
          <Act6CTA />
        </Series.Sequence>
      </Series>
    </AbsoluteFill>
  );
};

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="LaunchVideo"
        component={LaunchVideo}
        durationInFrames={5400}
        fps={30}
        width={1920}
        height={1080}
      />
    </>
  );
};
