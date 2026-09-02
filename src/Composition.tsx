import {
  AbsoluteFill,
  Audio,
  Composition,
  Easing,
  interpolate,
  OffthreadVideo,
  Sequence,
  staticFile,
  useCurrentFrame,
} from "remotion";
import { duckCurve } from "./duckCurve";

export const FPS = 30;
export const DURATION_IN_FRAMES = 2264;

// Beat grid of the smooth-jazz bed (86 BPM, see the track's own bar
// structure) — the punch-in zoom below snaps on every beat instead of the
// footage's own cuts, so the edit reads as "cut to the beat" of the music.
const MUSIC_BPM = 86;
const BEATS_PER_BAR = 4;
const FRAMES_PER_BEAT = (60 / MUSIC_BPM) * FPS;

const useBeatPunchScale = (frame: number) => {
  const beatIndex = Math.floor(frame / FRAMES_PER_BEAT);
  const framesSinceBeat = frame - beatIndex * FRAMES_PER_BEAT;
  const isDownbeat = beatIndex % BEATS_PER_BAR === 0;
  const peak = isDownbeat ? 1.065 : 1.03;
  return interpolate(framesSinceBeat, [0, 14], [peak, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });
};

const VideoLayer: React.FC = () => {
  const frame = useCurrentFrame();
  const scale = useBeatPunchScale(frame);

  return (
    <AbsoluteFill style={{ backgroundColor: "black" }}>
      <AbsoluteFill
        style={{
          transform: `scale(${scale})`,
          filter: "contrast(1.08) saturate(1.18)",
        }}
      >
        <OffthreadVideo src={staticFile("source.mp4")} />
      </AbsoluteFill>
      <AbsoluteFill
        style={{
          boxShadow: "inset 0 0 240px 70px rgba(0,0,0,0.45)",
          pointerEvents: "none",
        }}
      />
    </AbsoluteFill>
  );
};

const HOOK_DURATION = 66;

const HookText: React.FC = () => {
  const frame = useCurrentFrame();
  const opacity = interpolate(
    frame,
    [0, 10, HOOK_DURATION - 15, HOOK_DURATION],
    [0, 1, 1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );
  const scale = interpolate(frame, [0, 10], [0.85, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.back(1.6)),
  });

  return (
    <AbsoluteFill
      style={{ justifyContent: "flex-start", alignItems: "center" }}
    >
      <div
        style={{
          marginTop: 160,
          opacity,
          transform: `scale(${scale})`,
          fontFamily: "Helvetica, Arial, sans-serif",
          fontWeight: 800,
          fontSize: 64,
          lineHeight: 1.15,
          color: "white",
          textAlign: "center",
          textShadow: "0 4px 24px rgba(0,0,0,0.6)",
          padding: "0 60px",
        }}
      >
        POV: you survive
        <br />
        90 minutes of{" "}
        <span style={{ color: "#ff5fa2" }}>hot mobility</span> 🔥
      </div>
    </AbsoluteFill>
  );
};

const CTA_DURATION = 95;

const CtaText: React.FC = () => {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [0, 20], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const y = interpolate(frame, [0, 20], [30, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });
  const pulse = 1 + Math.sin(frame / 8) * 0.03;

  return (
    <AbsoluteFill
      style={{
        justifyContent: "flex-end",
        alignItems: "center",
        paddingBottom: 210,
      }}
    >
      <div
        style={{
          opacity,
          transform: `translateY(${y}px) scale(${pulse})`,
          background: "rgba(0,0,0,0.55)",
          borderRadius: 999,
          padding: "20px 40px",
          display: "flex",
          alignItems: "center",
          gap: 12,
        }}
      >
        <span style={{ fontSize: 34 }}>📍</span>
        <span
          style={{
            fontFamily: "Helvetica, Arial, sans-serif",
            fontWeight: 800,
            fontSize: 34,
            color: "white",
          }}
        >
          Book your class — link in bio
        </span>
      </div>
    </AbsoluteFill>
  );
};

export const TikTokPromo: React.FC = () => {
  return (
    <AbsoluteFill style={{ backgroundColor: "black" }}>
      <VideoLayer />
      <Audio
        src={staticFile("jazz-bed.m4a")}
        volume={(frame) => duckCurve[frame] ?? 0}
      />
      <Sequence durationInFrames={HOOK_DURATION}>
        <HookText />
      </Sequence>
      <Sequence
        from={DURATION_IN_FRAMES - CTA_DURATION}
        durationInFrames={CTA_DURATION}
      >
        <CtaText />
      </Sequence>
    </AbsoluteFill>
  );
};

export const MyComposition = () => {
  return (
    <Composition
      id="TikTokPromo"
      component={TikTokPromo}
      durationInFrames={DURATION_IN_FRAMES}
      fps={FPS}
      width={1080}
      height={1920}
    />
  );
};
