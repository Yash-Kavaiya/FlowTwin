export type ZoneStateName = "CLEAR" | "BLOCKED" | "UNKNOWN";
export type Mode = "SYNTHETIC" | "LIVE" | "REPLAY";

export interface UseCase { buyer: string; problem: string; response: string; metric: string }
export interface MapSummary { id: string; name: string; use_case: UseCase }

export interface MapData {
  id: string;
  name: string;
  use_case: UseCase;
  structures: { kind: string; label?: string; x: number; y: number; w: number; d: number; h: number }[];
  workers?: { path: [number, number][]; speed: number }[];
  width: number;
  height: number;
  nodes: { id: string; label: string; kind: string; x: number; y: number }[];
  edges: { a: string; b: string; zone?: string }[];
  zones: { id: string; label: string; polygon: [number, number][] }[];
}

export interface Detection {
  class: string;
  confidence: number;
  box_n: [number, number, number, number];
  supported: boolean;
  zones: string[];
}

export interface FlowEvent {
  event_id: string;
  server_time: number;
  kind: string;
  input_mode?: Mode;
  zone_id?: string;
  old_state?: ZoneStateName;
  new_state?: ZoneStateName;
  evidence_id?: string;
  frame_id?: number;
  old_plan_version?: number;
  new_plan_version?: number;
  decision_reason?: string;
}

export interface WorldState {
  session_id: string;
  mode: Mode;
  map_id: string;
  server_time: number;
  zones: Record<string, {
    state: ZoneStateName; reason: string; state_age_s: number;
    observation_age_s: number | null; evidence_id: string | null;
  }>;
  vehicle: {
    status: string; x: number; y: number; node: string; next: string | null; goal: string | null;
    held: boolean; pause_zone: string | null; reason: string; plan_version: number; route: string[];
    estimated_remaining_s: number | null; estimated_direct_remaining_s: number | null;
    elapsed_s: number; waiting_s: number; distance: number; plan_changes: number;
  };
  view: { ok: boolean; reason: string };
  camera: { age_s: number | null; last_frame_id: number; detections: Detection[] };
  calibration: { version: number; image_points: [number, number][]; zones_image: Record<string, [number, number][]> } | null;
  detector: { model: string; backend: string; device: string; gpu: string | null };
  events: FlowEvent[];
  kpis: {
    source: string; deliveries: number; avg_delivery_s: number | null; avg_waiting_s: number | null;
    reroutes: number; blocked_events: number; unknown_events: number; inventory_fill: number;
  };
  fleet: { enabled: boolean; vehicles: FleetVehicle[]; note: string };
  ops: {
    counts: Record<"QUEUED" | "IN_TRANSIT" | "PACKED" | "DISPATCHED", number>;
    truck_load: number; truck_capacity: number; trucks_departed: number; inbound_deliveries: number;
    orders: { id: string; product: string; sku: string; slot: string; units: number; status: string; vehicle: string | null }[];
    alerts: { level: "critical" | "warning" | "info"; text: string }[];
    traffic: Record<string, number>;
  };
}

export interface AnalyticsSample {
  t: number; throughput_per_min: number; utilisation_pct: number; paused: number; queue: number;
  stock_fill_pct: number; blocked_zones: number;
}

export interface FrameResult {
  frame_id: number;
  timings: Record<string, number>;
  quality: { ok: boolean; reason: string; brightness: number; sharpness: number };
  state: WorldState;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, init);
  if (!res.ok) {
    let detail = res.statusText;
    try { detail = (await res.json()).detail ?? detail; } catch { /* body was not JSON */ }
    throw new Error(`${res.status}: ${detail}`);
  }
  return res.json();
}

const post = <T,>(path: string, body?: unknown) =>
  request<T>(path, {
    method: "POST",
    headers: body === undefined ? undefined : { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });

export interface Rack {
  id: string; structure_index: number; label: string; units: number; capacity: number; fill: number; low_slots: number;
  slots: { slot: string; sku: string; product: string; qty: number; capacity: number }[];
}
export interface InventoryReport { source: string; racks: Rack[]; units: number; capacity: number; fill: number }

export interface FleetVehicle { id: string; kind: string; order: string | null; status: string; x: number; y: number; route: string[]; goal: string | null; legs_done: number }

export interface GpuReport {
  info: { cuda_available: boolean; device: string | null; torch: string | null; cuda_runtime: string | null;
    tensorrt: string | null; total_memory_mb: number | null };
  stats: { cuda_available: boolean; process_allocated_mb?: number; device_used_mb?: number; device_total_mb?: number;
    utilization_pct?: number | null; utilization_source?: string };
  detector: { backend: string; model: string; half?: boolean; preprocess?: string };
  latency: Record<string, { n: number; p50_ms: number; p95_ms: number }>;
  frames_analyzed: number;
}

export interface Comparison {
  rows: { name: string; faster: string; static: { makespan_s: number; waiting_s: number }; dynamic: { makespan_s: number; waiting_s: number } }[];
  total_makespan_s: { static: number; dynamic: number };
}

export const api = {
  comparison: () => request<Comparison>("/api/comparison"),
  gpu: () => request<GpuReport>("/api/gpu"),
  inventory: () => request<InventoryReport>("/api/inventory"),
  analytics: () => request<{ history: AnalyticsSample[] }>("/api/analytics"),
  fleet: (enabled: boolean) => post<WorldState>("/api/fleet", { enabled }),
  map: () => request<MapData>("/api/map"),
  maps: () => request<MapSummary[]>("/api/maps"),
  chooseMap: (id: string) => post<WorldState>("/api/map", { id }),
  state: () => request<WorldState>("/api/state"),
  status: () => request<Record<string, unknown>>("/api/status"),
  metrics: () => request<Record<string, unknown>>("/api/metrics"),
  startOrder: () => post<WorldState>("/api/orders"),
  reset: (mode?: Mode) => post<WorldState>("/api/demo/reset", mode ? { mode } : {}),
  setZone: (zone_id: string, state: ZoneStateName) => post<WorldState>("/api/sim/zone", { zone_id, state }),
  pause: (paused: boolean) => post<WorldState>("/api/sim/pause", { paused }),
  checkCalibration: (image: [number, number], map: [number, number]) =>
    post<{ error_map_units: number }>("/api/calibration/check", { image, map }),
  calibrate: (image_points: [number, number][]) =>
    post<{ version: number }>("/api/calibration", { image_points }),
  frame: (blob: Blob, sessionId: string, frameId: number, mode: Mode) =>
    request<FrameResult>("/api/frame", {
      method: "POST",
      body: blob,
      headers: {
        "Content-Type": "image/jpeg",
        "X-Session-Id": sessionId,
        "X-Frame-Id": String(frameId),
        "X-Input-Mode": mode,
      },
    }),
};
