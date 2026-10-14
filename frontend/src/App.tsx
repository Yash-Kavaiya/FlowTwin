import { useCallback, useEffect, useRef, useState } from "react";
import { api, type AnalyticsSample, type Comparison, type GpuReport, type InventoryReport, type MapData, type MapSummary, type Mode, type WorldState } from "./api";
import { CameraPanel } from "./CameraPanel";
import { Scene } from "./Scene";

const STATUS_TEXT: Record<string, string> = {
  IDLE: "Idle, no active order",
  MOVING: "Moving",
  PAUSED_NO_ROUTE: "Paused: no feasible route",
  PAUSED_UNKNOWN: "Paused: route needs an unobserved zone",
  PAUSED_CONFLICT: "Paused: obstruction on the current edge",
  PAUSED_OPERATOR: "Paused by the operator",
  WAITING_BLOCKED: "Waiting on a blocked route",
  DONE: "Delivered",
};

const UNREACHABLE = "Backend unreachable";

const time = (t: number) => new Date(t * 1000).toLocaleTimeString();

function Engineering() {
  const [data, setData] = useState<{ status: unknown; metrics: unknown } | null>(null);
  const [open, setOpen] = useState(false);
  useEffect(() => {
    if (!open) return;
    const load = async () => {
      try { setData({ status: await api.status(), metrics: await api.metrics() }); } catch { /* retried on the next poll */ }
    };
    void load();
    const timer = setInterval(load, 2000);
    return () => clearInterval(timer);
  }, [open]);
  return (
    <details className="panel" onToggle={(e) => setOpen((e.target as HTMLDetailsElement).open)}>
      <summary>Engineering: measured values</summary>
      <pre>{data ? JSON.stringify(data, null, 2) : "loading"}</pre>
    </details>
  );
}

/** Small line chart drawn as SVG. No chart library, so the demo has nothing to download. */
function Spark({ samples, field, label, unit }: { samples: AnalyticsSample[]; field: keyof AnalyticsSample; label: string; unit: string }) {
  const values = samples.map((s) => s[field]);
  const max = Math.max(1, ...values);
  const points = values.map((v, i) => `${(i / Math.max(1, values.length - 1)) * 300},${44 - (v / max) * 40}`).join(" ");
  const latest = values.length ? values[values.length - 1] : 0;
  return (
    <div className="spark">
      <div><span>{label}</span><b>{latest}{unit}</b></div>
      <svg viewBox="0 0 300 46" preserveAspectRatio="none" role="img" aria-label={`${label} over time`}>
        <line x1="0" y1="45" x2="300" y2="45" />
        {values.length > 1 && <polyline points={points} />}
      </svg>
    </div>
  );
}

function OperationsPanel({ state }: { state: WorldState }) {
  const [history, setHistory] = useState<AnalyticsSample[]>([]);
  const on = state.fleet.enabled;
  useEffect(() => {
    if (!on) { setHistory([]); return; }
    const load = () => api.analytics().then((a) => setHistory(a.history)).catch(() => undefined);
    load();
    const timer = setInterval(load, 2000);
    return () => clearInterval(timer);
  }, [on, state.session_id]);
  const { ops } = state;
  return (
    <section className="panel">
      <h2>Operations <span className="tag">SIMULATED</span></h2>
      {ops.alerts.length > 0 && (
        <ul className="alerts">
          {ops.alerts.map((a) => <li key={a.text} className={`alert-${a.level}`}>{a.text}</li>)}
        </ul>
      )}
      {!on ? <p className="small">Turn on Operations (button over the 3D view) to run the fleet, orders and trucks.</p> : (
        <>
          <div className="flow">
            <div><b>{ops.counts.QUEUED}</b><span>queued</span></div>
            <div><b>{ops.counts.IN_TRANSIT}</b><span>in transit</span></div>
            <div><b>{ops.counts.PACKED}</b><span>packing</span></div>
            <div><b>{ops.counts.DISPATCHED}</b><span>dispatched</span></div>
          </div>
          <p className="small">
            Outbound truck {ops.truck_load}/{ops.truck_capacity} loaded
            <span className="meter"><i style={{ width: `${(100 * ops.truck_load) / ops.truck_capacity}%` }} /></span>
            {ops.trucks_departed} departed, {ops.inbound_deliveries} inbound deliveries
          </p>
          <Spark samples={history} field="throughput_per_min" label="Orders completed in the last minute" unit="" />
          <Spark samples={history} field="utilisation_pct" label="Vehicles moving" unit="%" />
          <Spark samples={history} field="queue" label="Orders waiting" unit="" />
          <table>
            <thead><tr><th>Order</th><th>Item</th><th>Vehicle</th><th>Status</th></tr></thead>
            <tbody>
              {ops.orders.map((o) => (
                <tr key={o.id}>
                  <td>{o.id}</td><td>{o.units} x {o.product}</td><td>{o.vehicle ?? "–"}</td>
                  <td className={`status-${o.status}`}>{o.status.replace("_", " ").toLowerCase()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </section>
  );
}

const STAGE_LABEL: Record<string, string> = {
  preprocess_ms: "Preprocess", model_ms: "Model", postprocess_ms: "Postprocess", inference_ms: "Whole prediction call",
};

function GpuPanel() {
  const [gpu, setGpu] = useState<GpuReport | null>(null);
  useEffect(() => {
    const load = () => api.gpu().then(setGpu).catch(() => undefined);
    load();
    const timer = setInterval(load, 2000);
    return () => clearInterval(timer);
  }, []);
  if (!gpu) return null;
  const { info, stats, detector, latency } = gpu;
  return (
    <section className="panel">
      <h2>Accelerator <span className="tag">MEASURED</span></h2>
      <dl className="grid">
        <dt>Device</dt>
        <dd className={info.cuda_available ? "" : "warn"}>{info.cuda_available ? info.device : "No CUDA device (CPU)"}</dd>
        <dt>Backend</dt>
        <dd>{detector.backend}{detector.preprocess ? `, preprocess ${detector.preprocess}` : ""}</dd>
        <dt>Stack</dt>
        <dd>
          {info.torch ? `PyTorch ${info.torch}` : "PyTorch not installed"}
          {info.cuda_runtime ? `, CUDA ${info.cuda_runtime}` : ""}{info.tensorrt ? `, TensorRT ${info.tensorrt}` : ""}
        </dd>
        {stats.cuda_available && (
          <>
            <dt>GPU memory</dt>
            <dd>{stats.device_used_mb} / {stats.device_total_mb} MB in use (this process {stats.process_allocated_mb} MB)</dd>
            <dt>GPU load</dt>
            <dd>{stats.utilization_pct != null ? `${stats.utilization_pct}%` : "not exposed"} <span className="muted">({stats.utilization_source})</span></dd>
          </>
        )}
      </dl>
      {Object.keys(latency).length > 0 && (
        <table>
          <thead><tr><th>Stage</th><th>p50 ms</th><th>p95 ms</th><th>n</th></tr></thead>
          <tbody>
            {Object.entries(latency).map(([k, v]) => (
              <tr key={k} className={k === "inference_ms" ? "total" : ""}>
                <td>{STAGE_LABEL[k] ?? k}</td><td>{v.p50_ms}</td><td>{v.p95_ms}</td><td>{v.n}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}

function ComparisonPanel({ mapId }: { mapId: string }) {
  const [data, setData] = useState<Comparison | null>(null);
  const [open, setOpen] = useState(false);
  useEffect(() => {
    setData(null);
    if (open) api.comparison().then(setData).catch(() => undefined);
  }, [open, mapId]);
  return (
    <details className="panel" onToggle={(e) => setOpen((e.target as HTMLDetailsElement).open)}>
      <summary>Fixed route vs replanning <span className="tag">SIMULATED</span></summary>
      {!data ? <p className="small">running the scenario set</p> : (
        <>
          <table>
            <thead><tr><th>Scenario</th><th>Fixed s</th><th>Replan s</th><th>Faster</th></tr></thead>
            <tbody>
              {data.rows.map((r) => (
                <tr key={r.name}>
                  <td>{r.name}</td><td>{r.static.makespan_s}</td><td>{r.dynamic.makespan_s}</td>
                  <td>{r.faster === "static" ? "fixed" : r.faster === "dynamic" ? "replan" : "tie"}</td>
                </tr>
              ))}
              <tr className="total"><td>Total</td><td>{data.total_makespan_s.static}</td><td>{data.total_makespan_s.dynamic}</td><td /></tr>
            </tbody>
          </table>
          <p className="small">Same obstruction schedule, speed and start for both. Simulated seconds, computed by the backend on request.</p>
        </>
      )}
    </details>
  );
}

export function App() {
  const [map, setMap] = useState<MapData | null>(null);
  const [maps, setMaps] = useState<MapSummary[]>([]);
  const [state, setState] = useState<WorldState | null>(null);
  const [error, setError] = useState("");
  const [clearance, setClearance] = useState(10);
  const [evidence, setEvidence] = useState<string | null>(null);
  const [inventory, setInventory] = useState<InventoryReport | null>(null);
  const [heatmap, setHeatmap] = useState(false);
  const [trafficHeat, setTrafficHeat] = useState(false);
  const [selected, setSelected] = useState<number | null>(null);
  const newest = useRef(0);

  // Polls and frame responses race; only a newer server snapshot may replace the current one.
  const accept = useCallback((s: WorldState) => {
    if (s.server_time < newest.current) return;
    newest.current = s.server_time;
    setState(s);
  }, []);

  const run = useCallback(async (action: () => Promise<WorldState>) => {
    try {
      setError("");
      accept(await action());
    } catch (e) {
      setError((e as Error).message);
    }
  }, [accept]);

  useEffect(() => {
    api.maps().then(setMaps).catch((e) => setError(e.message));
    const poll = () => api.state()
      .then((s) => { accept(s); setError((e) => (e === UNREACHABLE ? "" : e)); })
      .catch(() => setError(UNREACHABLE));
    poll();
    const timer = setInterval(poll, 400);
    return () => clearInterval(timer);
  }, [accept]);

  // The drawn map follows the use case reported by the backend.
  const mapId = state?.map_id;
  useEffect(() => {
    if (mapId) api.map().then(setMap).catch((e) => setError(e.message));
  }, [mapId]);

  // Stock changes only when a delivery completes, so a slow poll is enough.
  useEffect(() => {
    setSelected(null);
    const load = () => api.inventory().then(setInventory).catch(() => undefined);
    load();
    const timer = setInterval(load, 3000);
    return () => clearInterval(timer);
  }, [mapId]);

  if (!map || !state) return <div className="loading">Connecting to FlowTwin backend. {error}</div>;

  const v = state.vehicle;
  const k = state.kpis;
  const racks = inventory?.racks ?? [];
  const rack = racks.find((r) => r.structure_index === selected) ?? null;
  const synthetic = state.mode === "SYNTHETIC";
  const fresh = synthetic || state.view.ok;
  const rerouted = v.estimated_remaining_s !== null && v.estimated_direct_remaining_s !== null
    && v.estimated_remaining_s > v.estimated_direct_remaining_s + 0.05;
  const paused = v.status.startsWith("PAUSED");
  const blockedPause = paused && !v.held;
  const waitTotal = v.estimated_direct_remaining_s !== null ? clearance + v.estimated_direct_remaining_s : null;

  return (
    <div className="app">
      <header>
        <h1>Flow<span>Twin</span></h1>
        <span className={`badge mode-${state.mode}`}>INPUT: {state.mode}</span>
        <span className={`badge ${fresh ? "ok" : "stale"}`}>
          {synthetic ? "NO CAMERA OBSERVATION" : fresh
            ? `OBSERVATION FRESH (${state.camera.age_s ?? "?"} s old)`
            : `VIEW UNKNOWN: ${state.view.reason}`}
        </span>
        <span className="badge plain">{state.detector.backend} · {state.detector.model}{state.detector.gpu ? ` · ${state.detector.gpu}` : ""}</span>
        <span className="spacer" />
        <label className="mode-select">
          Input mode
          <select value={state.mode} onChange={(e) => run(() => api.reset(e.target.value as Mode))}>
            <option value="SYNTHETIC">SYNTHETIC (manual)</option>
            <option value="LIVE">LIVE (camera)</option>
            <option value="REPLAY">REPLAY (recorded clip)</option>
          </select>
        </label>
      </header>

      <main>
        <Scene map={map} state={state} racks={racks} heatmap={heatmap} trafficHeat={trafficHeat} selected={selected} onSelect={setSelected} />
        <div className="kpis">
          <div><b>{k.deliveries}</b><span>deliveries</span></div>
          <div><b>{k.avg_delivery_s ?? "–"}</b><span>avg delivery s</span></div>
          <div><b>{k.avg_waiting_s ?? "–"}</b><span>avg waiting s</span></div>
          <div><b>{k.reroutes}</b><span>reroutes</span></div>
          <div><b>{k.blocked_events}</b><span>blocked events</span></div>
          <div><b>{1 + state.fleet.vehicles.length}</b><span>vehicles</span></div>
          <div><b>{racks.length ? `${Math.round(k.inventory_fill * 100)}%` : "–"}</b><span>stock fill</span></div>
          <em>{k.source}; simulated seconds</em>
        </div>
        <div className="scene-tools">
          <button className={state.fleet.enabled ? "on" : ""} onClick={() => run(() => api.fleet(!state.fleet.enabled))}
            title={state.fleet.note}>
            {state.fleet.enabled ? "Operations: on" : "Operations: off"}
          </button>
          {state.fleet.enabled && (
            <button className={trafficHeat ? "on" : ""} onClick={() => setTrafficHeat(!trafficHeat)}>Traffic heat</button>
          )}
          {racks.length > 0 && (
            <button className={heatmap ? "on" : ""} onClick={() => setHeatmap(!heatmap)}>Stock heatmap</button>
          )}
        </div>
        {rack && (
          <div className="rack-card">
            <h2>{rack.id} inventory <span className="tag">SIMULATED</span> <button className="link" onClick={() => setSelected(null)}>close</button></h2>
            <p>{rack.units} / {rack.capacity} units ({Math.round(rack.fill * 100)}% full), {rack.low_slots} slots low</p>
            <table>
              <thead><tr><th>Slot</th><th>Product</th><th>SKU</th><th>Qty</th></tr></thead>
              <tbody>
                {rack.slots.map((s) => (
                  <tr key={s.slot} className={s.qty <= s.capacity * 0.15 ? "low" : ""}>
                    <td>{s.slot}</td><td>{s.product}</td><td>{s.sku}</td><td>{s.qty}/{s.capacity}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {error && <div className="error" onClick={() => setError("")}>{error}</div>}
        {evidence && (
          <div className="evidence" onClick={() => setEvidence(null)}>
            <img src={`/api/evidence/${evidence}`} alt="Recorded evidence frame" />
            <span>EVIDENCE FRAME (recorded, not live). Click to close.</span>
          </div>
        )}
      </main>

      <aside>
        <section className="panel usecase">
          <h2>Use case</h2>
          <div className="tabs">
            {maps.map((m) => (
              <button key={m.id} className={m.id === state.map_id ? "active" : ""}
                onClick={() => m.id !== state.map_id && run(() => api.chooseMap(m.id))}>
                {m.name}
              </button>
            ))}
          </div>
          <p><b>{map.use_case.buyer}.</b> {map.use_case.problem}</p>
          <p className="small">{map.use_case.response}</p>
          <p className="small">Pilot metric: {map.use_case.metric}</p>
        </section>

        <CameraPanel map={map} state={state} onState={accept} onError={setError} />

        <section className="panel">
          <h2>Order and decision</h2>
          <div className="row">
            <button className="primary" onClick={() => run(api.startOrder)}>Start delivery</button>
            {v.status !== "IDLE" && v.status !== "DONE" && (
              <button onClick={() => run(() => api.pause(!v.held))}>{v.held ? "Resume" : "Pause"}</button>
            )}
            <button onClick={() => run(() => api.reset())}>Reset</button>
          </div>
          <dl>
            <dt>Vehicle <span className="tag">SIMULATED</span></dt>
            <dd className={paused ? "warn" : ""}>{STATUS_TEXT[v.status] ?? v.status}</dd>
            <dt>Route</dt>
            <dd>{v.route.length ? v.route.join(" > ") : "none"} <span className="muted">(plan v{v.plan_version})</span></dd>
            <dt>Time to dispatch <span className="tag">ESTIMATED</span></dt>
            <dd>{v.status === "IDLE" ? "no active order" : v.status === "DONE" ? "delivered"
              : v.estimated_remaining_s !== null ? `${v.estimated_remaining_s} simulated s` : "no route"}</dd>
            <dt>Why</dt>
            <dd>{v.reason || "no decision yet"}</dd>
          </dl>
          {(rerouted || blockedPause) && waitTotal !== null && (
            <div className="compare">
              <h3>Compare decisions <span className="tag">ESTIMATED</span></h3>
              <p>Reroute now: {v.estimated_remaining_s !== null ? `${v.estimated_remaining_s} s` : "not possible"}</p>
              <p>
                Wait for clearance:{" "}
                <input type="number" min={0} value={clearance} onChange={(e) => setClearance(Math.max(0, Number(e.target.value)))} />{" "}
                s assumed + {v.estimated_direct_remaining_s} s = <b>{waitTotal.toFixed(1)} s</b>
              </p>
              <p className="small">The clearance time is your assumption, not a prediction.</p>
            </div>
          )}
          {synthetic && (
            <div className="zones">
              <h3>Manual obstructions <span className="tag">SYNTHETIC</span></h3>
              {map.zones.map((z) => {
                const blocked = state.zones[z.id]?.state === "BLOCKED";
                return (
                  <button key={z.id} className={blocked ? "blocked" : ""}
                    onClick={() => run(() => api.setZone(z.id, blocked ? "CLEAR" : "BLOCKED"))}>
                    {blocked ? `Clear ${z.label}` : `Block ${z.label}`}
                  </button>
                );
              })}
            </div>
          )}
        </section>

        <OperationsPanel state={state} />
        <GpuPanel />
        <ComparisonPanel mapId={state.map_id} />
        <Engineering />
      </aside>

      <footer>
        <h2>Event timeline</h2>
        <ol>
          {[...state.events].reverse().map((e) => (
            <li key={e.event_id} className={`event kind-${e.kind}`}>
              <span className="muted">{time(e.server_time)}</span>
              <span className="tag">{e.input_mode}</span>
              {e.kind === "zone"
                ? <b className={`zone-${e.new_state}`}>{e.zone_id}: {e.old_state} to {e.new_state}</b>
                : <b>{e.kind}</b>}
              <span>{e.decision_reason}</span>
              {e.evidence_id && <button className="link" onClick={() => setEvidence(e.evidence_id!)}>evidence</button>}
            </li>
          ))}
        </ol>
      </footer>
    </div>
  );
}
