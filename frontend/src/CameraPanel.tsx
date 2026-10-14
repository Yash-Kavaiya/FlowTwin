import { useEffect, useRef, useState } from "react";
import { api, type MapData, type WorldState } from "./api";

const FRAME_WIDTH = 640;
const MIN_INTERVAL_MS = 200; // about 5 frames per second; the next frame waits for the previous response
const ACCENT = "#bfd732";

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

interface Props {
  map: MapData;
  state: WorldState;
  onState: (s: WorldState) => void;
  onError: (message: string) => void;
}

type Point = [number, number];
// "calibrate" collects the four map corners; "verify" collects one click per held-out wait node.
type Picking = { kind: "calibrate"; points: Point[] } | { kind: "verify"; index: number; results: string[] } | null;

export function CameraPanel({ map, state, onState, onError }: Props) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const overlayRef = useRef<HTMLCanvasElement>(null);
  const stateRef = useRef(state);
  stateRef.current = state;
  const running = useRef(false);
  const frameId = useRef(0);
  const objectUrl = useRef<string | null>(null);
  const [active, setActive] = useState(false);
  const [picking, setPicking] = useState<Picking>(null);
  const [verified, setVerified] = useState<string[]>([]);
  const [info, setInfo] = useState<{ ack: number; server: Record<string, number>; fps: number } | null>(null);

  const checkNodes = map.nodes.filter((n) => n.kind === "wait");

  const stop = () => {
    running.current = false;
    setActive(false);
    setPicking(null);
    const video = videoRef.current;
    if (video) {
      (video.srcObject as MediaStream | null)?.getTracks().forEach((t) => t.stop());
      video.srcObject = null;
      video.removeAttribute("src");
      video.load();
    }
    if (objectUrl.current) URL.revokeObjectURL(objectUrl.current);
    objectUrl.current = null;
  };

  const loop = async () => {
    const video = videoRef.current!;
    const canvas = document.createElement("canvas");
    let last = performance.now();
    while (running.current) {
      const started = performance.now();
      const s = stateRef.current;
      // A frozen last frame must never be sent as a fresh observation: stop when the source has ended.
      const stream = video.srcObject as MediaStream | null;
      if (video.ended || (stream && stream.getVideoTracks().every((t) => t.readyState === "ended"))) {
        stop();
        onError(stream ? "Camera disconnected. Observations will go stale." : "Recorded clip finished.");
        return;
      }
      if (s.mode !== "SYNTHETIC" && !video.paused && video.readyState >= 2 && video.videoWidth > 0) {
        canvas.width = FRAME_WIDTH;
        canvas.height = Math.round((FRAME_WIDTH * video.videoHeight) / video.videoWidth);
        canvas.getContext("2d")!.drawImage(video, 0, 0, canvas.width, canvas.height);
        const blob = await new Promise<Blob | null>((r) => canvas.toBlob(r, "image/jpeg", 0.75));
        if (blob) {
          try {
            const sent = performance.now();
            const result = await api.frame(blob, s.session_id, ++frameId.current, s.mode);
            const now = performance.now();
            setInfo({ ack: now - sent, server: result.timings, fps: 1000 / (now - last) });
            last = now;
            onState(result.state);
          } catch {
            // Rejected frames (old session, busy) are expected around resets; the next frame retries.
          }
        }
      }
      await sleep(Math.max(0, MIN_INTERVAL_MS - (performance.now() - started)));
    }
  };

  const begin = () => {
    running.current = true;
    setActive(true);
    void loop();
  };

  const startCamera = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: { width: 1280, height: 720 }, audio: false });
      const video = videoRef.current!;
      video.srcObject = stream;
      await video.play();
      begin();
    } catch (e) {
      onError(`Camera unavailable: ${(e as Error).message}`);
    }
  };

  const playFile = async (file: File) => {
    const video = videoRef.current!;
    objectUrl.current = URL.createObjectURL(file);
    video.src = objectUrl.current;
    video.loop = false;
    try {
      await video.play();
      begin();
    } catch (e) {
      onError(`Clip could not be played: ${(e as Error).message}`);
    }
  };

  // A new session restarts the server's frame counter.
  useEffect(() => { frameId.current = 0; }, [state.session_id]);
  useEffect(() => stop, []);
  useEffect(() => { if (state.mode === "SYNTHETIC" && running.current) stop(); }, [state.mode]);
  useEffect(() => { setVerified([]); }, [state.calibration?.version, map.id]);

  const onOverlayClick = async (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!picking) return;
    const rect = e.currentTarget.getBoundingClientRect();
    // A click on the very edge of the view can land a hair outside 0..1.
    const unit = (v: number) => Math.min(1, Math.max(0, v));
    const point: Point = [unit((e.clientX - rect.left) / rect.width), unit((e.clientY - rect.top) / rect.height)];
    try {
      if (picking.kind === "calibrate") {
        const points = [...picking.points, point];
        if (points.length < 4) return setPicking({ kind: "calibrate", points });
        setPicking(null);
        await api.calibrate(points);
      } else {
        const node = checkNodes[picking.index];
        const { error_map_units } = await api.checkCalibration(point, [node.x, node.y]);
        const results = [...picking.results, `${node.label}: ${error_map_units} units off`];
        if (picking.index + 1 < checkNodes.length) return setPicking({ kind: "verify", index: picking.index + 1, results });
        setPicking(null);
        setVerified(results);
      }
    } catch (err) {
      setPicking(null);
      onError(`Calibration rejected: ${(err as Error).message}`);
    }
  };

  useEffect(() => {
    const canvas = overlayRef.current!;
    const { width, height } = canvas.getBoundingClientRect();
    canvas.width = width;
    canvas.height = height;
    const ctx = canvas.getContext("2d")!;
    ctx.clearRect(0, 0, width, height);
    ctx.font = "12px system-ui";
    ctx.lineWidth = 2;
    if (state.calibration && picking?.kind !== "calibrate") {
      for (const [id, polygon] of Object.entries(state.calibration.zones_image)) {
        const zone = state.zones[id]?.state;
        ctx.strokeStyle = zone === "BLOCKED" ? "#e5484d" : zone === "UNKNOWN" ? "#8b8d98" : ACCENT;
        ctx.beginPath();
        polygon.forEach(([x, y], i) => (i ? ctx.lineTo(x * width, y * height) : ctx.moveTo(x * width, y * height)));
        ctx.closePath();
        ctx.stroke();
        ctx.fillStyle = ctx.strokeStyle;
        ctx.fillText(`${id}: ${zone}`, polygon[0][0] * width + 4, polygon[0][1] * height + 14);
      }
    }
    if (active) {
      for (const d of state.camera.detections) {
        const [x1, y1, x2, y2] = d.box_n;
        ctx.strokeStyle = d.supported ? "#f5a524" : "#64748b";
        ctx.strokeRect(x1 * width, y1 * height, (x2 - x1) * width, (y2 - y1) * height);
        ctx.fillStyle = ctx.strokeStyle;
        const tag = d.supported ? "" : " (unsupported)";
        ctx.fillText(`${d.class} ${d.confidence.toFixed(2)}${tag}`, x1 * width + 3, y1 * height - 4);
      }
    }
    if (picking?.kind === "calibrate") {
      ctx.fillStyle = ACCENT;
      picking.points.forEach(([x, y], i) => {
        ctx.beginPath();
        ctx.arc(x * width, y * height, 5, 0, Math.PI * 2);
        ctx.fill();
        ctx.fillText(String(i + 1), x * width + 8, y * height + 4);
      });
    }
  }, [state, picking, active]);

  const synthetic = state.mode === "SYNTHETIC";
  const corner = ["top-left (1)", "top-right (2)", "bottom-right (3)", "bottom-left (4)"];

  return (
    <section className="panel camera">
      <h2>
        Camera <span className="tag">{synthetic ? "not used in SYNTHETIC" : state.mode}</span>
      </h2>
      <div className="video-box">
        <video ref={videoRef} muted playsInline />
        <canvas ref={overlayRef} onClick={onOverlayClick} className={picking ? "picking" : ""} />
        {!active && <div className="video-empty">{synthetic ? "Switch to LIVE to use the camera" : "Camera is off"}</div>}
      </div>
      {picking?.kind === "calibrate" && (
        <p className="hint">Click the paper map corner: <b>{corner[picking.points.length]}</b></p>
      )}
      {picking?.kind === "verify" && (
        <p className="hint">Click the centre of <b>{checkNodes[picking.index].label}</b> on the camera view</p>
      )}
      <div className="row">
        {state.mode === "LIVE" && !active && <button onClick={startCamera}>Start camera</button>}
        {state.mode === "REPLAY" && !active && (
          <label className="file">
            Choose recorded clip
            <input type="file" accept="video/*" onChange={(e) => e.target.files?.[0] && playFile(e.target.files[0])} />
          </label>
        )}
        {active && <button onClick={stop}>Stop</button>}
        {active && !picking && <button onClick={() => setPicking({ kind: "calibrate", points: [] })}>Calibrate</button>}
        {active && !picking && state.calibration && checkNodes.length > 0 && (
          <button onClick={() => setPicking({ kind: "verify", index: 0, results: [] })}>Verify</button>
        )}
        {picking && <button onClick={() => setPicking(null)}>Cancel</button>}
      </div>
      <p className="small">
        Calibration: {state.calibration ? `v${state.calibration.version}` : "none"}
        {verified.length > 0 && <> · held-out check: {verified.join(", ")} (map is {map.width} units wide)</>}
        {info && active && (
          <> · {info.fps.toFixed(1)} frames/s analyzed · send-to-ack {info.ack.toFixed(0)} ms (browser clock) ·
            prediction call {info.server.inference_ms} ms (server clock)</>
        )}
      </p>
    </section>
  );
}
