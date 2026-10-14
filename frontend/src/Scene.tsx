import { useEffect, useRef } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { CSS2DObject, CSS2DRenderer } from "three/examples/jsm/renderers/CSS2DRenderer.js";
import type { MapData, Rack, WorldState, ZoneStateName } from "./api";
import {
  AMBER, LIME, buildFleetVehicle, buildStructure, buildVehicle, buildWorker, floorTexture, hazardTexture, materials,
  signTexture,
} from "./models";

// Brand accent (lime) is the active route; red, gray and amber keep their operational meaning.
const ZONE_STYLE: Record<ZoneStateName, { color: number; opacity: number }> = {
  CLEAR: { color: 0xffffff, opacity: 0.05 },
  BLOCKED: { color: 0xe5484d, opacity: 0.6 },
  UNKNOWN: { color: 0x8b8d98, opacity: 0.5 },
};
const VIEW_DIRECTION = new THREE.Vector3(0.5, 0.6, 0.78).normalize();
const WALL_HEIGHT = 13;
const LANE_GREY = 0x4b5057;

function label(text: string, className: string): CSS2DObject {
  const el = document.createElement("div");
  el.className = className;
  el.textContent = text;
  return new CSS2DObject(el);
}

interface Handles {
  zones: Record<string, { mesh: THREE.Mesh; label: CSS2DObject; name: string }>;
  route: THREE.Group;
  vehicle: THREE.Group;
  beacon: THREE.MeshStandardMaterial;
  vehicleLabel: CSS2DObject;
  target: THREE.Vector3;
  placed: boolean;
  toWorld: (x: number, y: number, h?: number) => THREE.Vector3;
  scene: THREE.Scene;
  fleet: Record<string, { group: THREE.Group; beacon: THREE.MeshStandardMaterial; target: THREE.Vector3 }>;
  heat: Record<number, THREE.Mesh>;
  outline: Record<number, THREE.LineSegments>;
  lanes: Record<string, THREE.MeshStandardMaterial>;
  clock: THREE.Clock;
  departure: { truck: THREE.Object3D | null; home: THREE.Vector3; away: THREE.Vector3; seen: number; started: number };
}

interface Props {
  map: MapData;
  state: WorldState | null;
  racks: Rack[];
  heatmap: boolean;
  trafficHeat: boolean;
  selected: number | null;
  onSelect: (structureIndex: number | null) => void;
}

/** Fill level as a colour: red when nearly empty, amber in the middle, lime when full. */
function fillColor(fill: number): THREE.Color {
  const low = new THREE.Color(0xe5484d), mid = new THREE.Color(AMBER), high = new THREE.Color(LIME);
  return fill < 0.5 ? low.lerp(mid, fill * 2) : mid.lerp(high, (fill - 0.5) * 2);
}

export function Scene({ map, state, racks, heatmap, trafficHeat, selected, onSelect }: Props) {
  const hostRef = useRef<HTMLDivElement>(null);
  const handles = useRef<Handles | null>(null);
  const selectRef = useRef(onSelect);
  selectRef.current = onSelect;

  useEffect(() => {
    const host = hostRef.current!;
    const W = map.width, H = map.height;
    const toWorld = (x: number, y: number, h = 0) => new THREE.Vector3(x - W / 2, h, y - H / 2);
    const nodeById = Object.fromEntries(map.nodes.map((n) => [n.id, n]));
    const textures: THREE.Texture[] = [];

    const scene = new THREE.Scene();
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.15;
    host.appendChild(renderer.domElement);
    const labels = new CSS2DRenderer();
    labels.domElement.className = "scene-labels";
    host.appendChild(labels.domElement);

    const camera = new THREE.PerspectiveCamera(30, 1, 1, 800);
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.target.set(0, 1, 0);
    controls.enablePan = false;
    controls.enableDamping = true;
    controls.minDistance = 45;
    controls.maxDistance = 320;
    controls.maxPolarAngle = 1.42; // never below the floor
    let userMoved = false;
    controls.addEventListener("start", () => { userMoved = true; });

    scene.add(new THREE.HemisphereLight(0xffffff, 0x2a2d31, 1.1));
    const sun = new THREE.DirectionalLight(0xfff4e0, 2.4);
    sun.position.set(55, 110, 45);
    sun.castShadow = true;
    sun.shadow.mapSize.set(2048, 2048);
    sun.shadow.bias = -0.0006;
    Object.assign(sun.shadow.camera, { left: -90, right: 90, top: 90, bottom: -90, near: 1, far: 320 });
    scene.add(sun);

    const solid = (obj: THREE.Object3D) => obj.traverse((o) => {
      if ((o as THREE.Mesh).isMesh) { o.castShadow = true; o.receiveShadow = true; }
    });
    const flat = (w: number, d: number, material: THREE.Material, pos: THREE.Vector3, rotation = 0) => {
      const mesh = new THREE.Mesh(new THREE.PlaneGeometry(w, d), material);
      mesh.rotation.set(-Math.PI / 2, 0, rotation);
      mesh.position.copy(pos);
      mesh.receiveShadow = true;
      scene.add(mesh);
      return mesh;
    };

    // Slab and sealed-concrete floor
    const slab = new THREE.Mesh(new THREE.BoxGeometry(W + 8, 1.2, H + 8), materials.dark);
    slab.position.y = -0.62;
    slab.receiveShadow = true;
    scene.add(slab);
    const concrete = floorTexture();
    concrete.repeat.set(4, 2.4);
    textures.push(concrete);
    flat(W + 8, H + 8, new THREE.MeshStandardMaterial({ map: concrete, roughness: 0.85, metalness: 0.05 }), new THREE.Vector3(0, 0, 0));

    // Building shell on the two far sides, with columns, a brand band and the site sign
    const shell = new THREE.Group();
    const backZ = -H / 2 - 4, backX = -W / 2 - 4;
    const wallZ = new THREE.Mesh(new THREE.BoxGeometry(W + 8.6, WALL_HEIGHT, 0.6), materials.wall);
    wallZ.position.set(0, WALL_HEIGHT / 2, backZ - 0.3);
    const wallX = new THREE.Mesh(new THREE.BoxGeometry(0.6, WALL_HEIGHT, H + 8.6), materials.wall);
    wallX.position.set(backX - 0.3, WALL_HEIGHT / 2, 0);
    shell.add(wallZ, wallX);
    const bandZ = new THREE.Mesh(new THREE.BoxGeometry(W + 8, 0.5, 0.1), materials.lime);
    bandZ.position.set(0, WALL_HEIGHT - 0.6, backZ + 0.06);
    const bandX = new THREE.Mesh(new THREE.BoxGeometry(0.1, 0.5, H + 8), materials.lime);
    bandX.position.set(backX + 0.06, WALL_HEIGHT - 0.6, 0);
    shell.add(bandZ, bandX);
    for (let x = -W / 2 - 4; x <= W / 2 + 4.1; x += (W + 8) / 6) {
      const column = new THREE.Mesh(new THREE.BoxGeometry(1, WALL_HEIGHT, 1), materials.machineDark);
      column.position.set(x, WALL_HEIGHT / 2, backZ + 0.5);
      shell.add(column);
    }
    for (let z = -H / 2 - 4; z <= H / 2 + 4.1; z += (H + 8) / 4) {
      const column = new THREE.Mesh(new THREE.BoxGeometry(1, WALL_HEIGHT, 1), materials.machineDark);
      column.position.set(backX + 0.5, WALL_HEIGHT / 2, z);
      shell.add(column);
    }
    solid(shell);
    scene.add(shell);
    const sign = signTexture("FlowTwin", map.name);
    textures.push(sign);
    const signMesh = new THREE.Mesh(new THREE.PlaneGeometry(30, 7.5), new THREE.MeshBasicMaterial({ map: sign }));
    signMesh.position.set(backX + 0.12, WALL_HEIGHT - 5.4, 0);
    signMesh.rotation.y = Math.PI / 2;
    scene.add(signMesh);

    // Travel lanes with painted edge lines
    const lanes: Handles["lanes"] = {};
    const lineMaterial = new THREE.MeshStandardMaterial({ color: 0xf2c81a, roughness: 0.6 });
    for (const e of map.edges) {
      const a = toWorld(nodeById[e.a].x, nodeById[e.a].y), b = toWorld(nodeById[e.b].x, nodeById[e.b].y);
      const length = a.distanceTo(b), angle = -Math.atan2(b.z - a.z, b.x - a.x);
      const mid = a.clone().add(b).multiplyScalar(0.5);
      // One material per lane so the traffic heat can tint each lane on its own.
      const laneMaterial = new THREE.MeshStandardMaterial({ color: LANE_GREY, roughness: 0.8 });
      lanes[[e.a, e.b].sort().join("-")] = laneMaterial;
      flat(length + 3.6, 3.6, laneMaterial, mid.clone().setY(0.02), angle);
      const normal = new THREE.Vector3(-(b.z - a.z), 0, b.x - a.x).normalize();
      for (const side of [-1.9, 1.9]) {
        flat(length, 0.18, lineMaterial, mid.clone().addScaledVector(normal, side).setY(0.035), angle);
      }
    }
    // Stop markings at the nodes; wait points are yellow
    for (const n of map.nodes) {
      const ring = new THREE.Mesh(
        new THREE.RingGeometry(1.25, 1.75, 32),
        new THREE.MeshStandardMaterial({ color: n.kind === "wait" ? 0xf2c81a : 0xf1f3f4, roughness: 0.6 }),
      );
      ring.rotation.x = -Math.PI / 2;
      ring.position.copy(toWorld(n.x, n.y, 0.05));
      ring.receiveShadow = true;
      scene.add(ring);
      if (n.kind !== "aisle") {
        const l = label(n.label, "node-label");
        l.position.copy(toWorld(n.x, n.y, 2.4));
        scene.add(l);
      }
    }

    // Use-case structures (racking, trailers, machines): orientation only, never observed.
    const departure: Handles["departure"] = {
      truck: null, home: new THREE.Vector3(), away: new THREE.Vector3(), seen: -1, started: -1,
    };
    const models: THREE.Object3D[] = [];
    const belts: { parcels: THREE.Mesh[]; half: number }[] = [];
    const heat: Handles["heat"] = {}, outline: Handles["outline"] = {};
    map.structures.forEach((s, index) => {
      const model = buildStructure(s);
      model.position.copy(toWorld(s.x, s.y, 0));
      model.userData.structureIndex = index;
      solid(model);
      scene.add(model);
      models.push(model);
      if (s.kind === "truck" && s.label?.toLowerCase().includes("outbound")) {
        // The outbound trailer pulls away from the building when a simulated truck departs.
        const home = model.position.clone();
        const out = new THREE.Vector3(home.x, 0, home.z).normalize().multiplyScalar(60);
        departure.truck = model;
        departure.home.copy(home);
        departure.away.copy(home).add(out);
      }
      model.traverse((o) => { if (o.userData.belt) belts.push(o.userData.belt); });
      if (s.kind === "rack") {  // inventory overlays: a fill-level tint and a selection outline
        const tint = new THREE.Mesh(
          new THREE.BoxGeometry(s.w + 0.3, s.h + 0.3, s.d + 0.3),
          new THREE.MeshBasicMaterial({ transparent: true, opacity: 0.55, depthWrite: false }),
        );
        tint.position.copy(toWorld(s.x, s.y, s.h / 2));
        tint.visible = false;
        scene.add(tint);
        heat[index] = tint;
        const edge = new THREE.LineSegments(
          new THREE.EdgesGeometry(new THREE.BoxGeometry(s.w + 0.6, s.h + 0.6, s.d + 0.6)),
          new THREE.LineBasicMaterial({ color: LIME }),
        );
        edge.position.copy(tint.position);
        edge.visible = false;
        scene.add(edge);
        outline[index] = edge;
      }
      if (s.label) {
        const l = label(s.label, "structure-label");
        l.position.copy(toWorld(s.x, s.y, s.h + 2));
        scene.add(l);
      }
    });

    // Floor workers walk fixed loops. They are scenery: not observed, and not part of the routing.
    const workers = (map.workers ?? []).map((w) => {
      const points = w.path.map(([x, y]) => toWorld(x, y, 0));
      const lengths = points.map((p, i) => p.distanceTo(points[(i + 1) % points.length]));
      const figure = buildWorker();
      solid(figure);
      scene.add(figure);
      return { figure, points, lengths, total: lengths.reduce((a, b) => a + b, 0), speed: w.speed };
    });

    // Click a structure to select it (a drag is an orbit, not a click).
    const raycaster = new THREE.Raycaster();
    let downAt: [number, number] | null = null;
    const onDown = (e: PointerEvent) => { downAt = [e.clientX, e.clientY]; };
    const onUp = (e: PointerEvent) => {
      if (!downAt || Math.hypot(e.clientX - downAt[0], e.clientY - downAt[1]) > 4) return;
      const rect = renderer.domElement.getBoundingClientRect();
      const point = new THREE.Vector2(((e.clientX - rect.left) / rect.width) * 2 - 1, -((e.clientY - rect.top) / rect.height) * 2 + 1);
      raycaster.setFromCamera(point, camera);
      let hit: THREE.Object3D | null = raycaster.intersectObjects(models, true)[0]?.object ?? null;
      while (hit && hit.userData.structureIndex === undefined) hit = hit.parent;
      selectRef.current(hit ? (hit.userData.structureIndex as number) : null);
    };
    renderer.domElement.addEventListener("pointerdown", onDown);
    renderer.domElement.addEventListener("pointerup", onUp);

    // Observed zones: hazard-tape outline on the floor, plus a volume that takes the state colour
    const zones: Handles["zones"] = {};
    const tape = hazardTexture();
    textures.push(tape);
    for (const z of map.zones) {
      const xs = z.polygon.map((p) => p[0]), ys = z.polygon.map((p) => p[1]);
      const x0 = Math.min(...xs), y0 = Math.min(...ys);
      const w = Math.max(...xs) - x0, h = Math.max(...ys) - y0;
      const centre = toWorld(x0 + w / 2, y0 + h / 2);
      for (const [len, across, dx, dz] of [[w, false, 0, -h / 2], [w, false, 0, h / 2], [h, true, -w / 2, 0], [h, true, w / 2, 0]] as const) {
        const texture = tape.clone();
        texture.repeat.set(len / 1.6, 1);
        texture.needsUpdate = true;
        textures.push(texture);
        flat(len + 0.6, 0.6, new THREE.MeshStandardMaterial({ map: texture, roughness: 0.7 }),
          centre.clone().add(new THREE.Vector3(dx, 0.06, dz)), across ? Math.PI / 2 : 0);
      }
      const mesh = new THREE.Mesh(
        new THREE.BoxGeometry(w, 2.2, h),
        new THREE.MeshStandardMaterial({ transparent: true, depthWrite: false }),
      );
      mesh.position.copy(centre).setY(1.15);
      scene.add(mesh);
      const l = label(z.label, "zone-label");
      l.position.copy(centre).setY(6);
      scene.add(l);
      zones[z.id] = { mesh, label: l, name: z.label };
    }

    const route = new THREE.Group();
    scene.add(route);
    const { group: vehicle, beacon } = buildVehicle();
    solid(vehicle);
    scene.add(vehicle);
    const vehicleLabel = label("Vehicle (SIMULATED)", "vehicle-label");
    vehicle.add(vehicleLabel);
    vehicleLabel.position.set(0, 5.4, 0);

    handles.current = {
      zones, route, vehicle, beacon, vehicleLabel, target: new THREE.Vector3(), placed: false, toWorld,
      scene, fleet: {}, heat, outline, lanes, departure, clock: new THREE.Clock(),
    };

    const frameView = () => {
      // Far enough to see the whole floor at this aspect ratio.
      const distance = Math.max(140, 250 / camera.aspect);
      camera.position.copy(controls.target).addScaledVector(VIEW_DIRECTION, distance);
      controls.update();
    };
    const resize = () => {
      const { clientWidth: w, clientHeight: h } = host;
      if (!w || !h) return;
      renderer.setSize(w, h);
      labels.setSize(w, h);
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      if (!userMoved) frameView();
    };
    const resetView = () => { userMoved = false; frameView(); };
    renderer.domElement.addEventListener("dblclick", resetView);
    const observer = new ResizeObserver(resize);
    observer.observe(host);
    resize();

    let frame = 0;
    const clock = handles.current.clock;
    // Glide towards the server position and point along the direction of travel.
    const follow = (group: THREE.Group, target: THREE.Vector3) => {
      const dx = target.x - group.position.x, dz = target.z - group.position.z;
      if (dx * dx + dz * dz > 0.01) group.rotation.y = -Math.atan2(dz, dx);
      group.position.lerp(target, 0.18);
    };
    const animate = () => {
      frame = requestAnimationFrame(animate);
      const h = handles.current!;
      const dt = Math.min(clock.getDelta(), 0.1);
      if (h.placed) follow(h.vehicle, h.target);
      for (const v of Object.values(h.fleet)) follow(v.group, v.target);
      const elapsed = clock.elapsedTime;
      for (const [index, w] of workers.entries()) {
        let along = (elapsed * w.speed + index * 7) % w.total;
        let i = 0;
        while (along > w.lengths[i]) { along -= w.lengths[i]; i++; }
        const a = w.points[i], b = w.points[(i + 1) % w.points.length];
        w.figure.position.lerpVectors(a, b, along / w.lengths[i]);
        w.figure.rotation.y = -Math.atan2(b.z - a.z, b.x - a.x);
      }
      if (h.departure.truck && h.departure.started >= 0) {
        // 3 s pulling away, 2 s gone, then the next trailer backs in over 3 s.
        const t = elapsed - h.departure.started;
        const k = t < 3 ? t / 3 : t < 5 ? 1 : Math.max(0, 1 - (t - 5) / 3);
        h.departure.truck.position.lerpVectors(h.departure.home, h.departure.away, k * k);
        if (t >= 8) h.departure.started = -1;
      }
      for (const belt of belts) {
        for (const parcel of belt.parcels) {
          parcel.position.x += 2.2 * dt;
          if (parcel.position.x > belt.half) parcel.position.x = -belt.half;
        }
      }
      controls.update();
      renderer.render(scene, camera);
      labels.render(scene, camera);
    };
    animate();

    return () => {
      cancelAnimationFrame(frame);
      observer.disconnect();
      controls.dispose();
      renderer.domElement.removeEventListener("pointerdown", onDown);
      renderer.domElement.removeEventListener("pointerup", onUp);
      scene.traverse((o) => (o as THREE.Mesh).geometry?.dispose());
      textures.forEach((t) => t.dispose());
      renderer.dispose();
      host.replaceChildren();
      handles.current = null;
    };
  }, [map]);

  useEffect(() => {
    const h = handles.current;
    // While the use case is switching, the state can briefly describe a map that is not drawn yet.
    if (!h || !state || state.map_id !== map.id) return;
    const nodeById = Object.fromEntries(map.nodes.map((n) => [n.id, n]));

    for (const [id, zone] of Object.entries(state.zones)) {
      const handle = h.zones[id];
      if (!handle) continue;
      const style = ZONE_STYLE[zone.state];
      const material = handle.mesh.material as THREE.MeshStandardMaterial;
      material.color.setHex(style.color);
      material.opacity = style.opacity;
      const source = state.mode === "SYNTHETIC" ? "SYNTHETIC" : "OBSERVED";
      handle.label.element.textContent = `${handle.name} · ${zone.state} (${source})`;
      handle.label.element.className = `zone-label zone-${zone.state}`;
    }

    const v = state.vehicle;
    h.target.copy(h.toWorld(v.x, v.y, 0.04));
    if (!h.placed || v.status === "IDLE") {
      h.vehicle.position.copy(h.target);
      h.placed = true;
    }
    const paused = v.status.startsWith("PAUSED") || v.status === "WAITING_BLOCKED";
    h.beacon.emissive.setHex(paused ? AMBER : LIME);
    h.vehicleLabel.element.textContent = paused ? "Vehicle paused (SIMULATED)" : "Vehicle (SIMULATED)";
    h.vehicleLabel.element.className = paused ? "vehicle-label paused" : "vehicle-label";

    // Extra simulated vehicles appear and disappear with the fleet toggle.
    const live = new Set(state.fleet.vehicles.map((f) => f.id));
    for (const [id, item] of Object.entries(h.fleet)) {
      if (!live.has(id)) { h.scene.remove(item.group); delete h.fleet[id]; }
    }
    for (const f of state.fleet.vehicles) {
      let item = h.fleet[f.id];
      const target = h.toWorld(f.x, f.y, 0.04);
      if (!item) {
        const built = buildFleetVehicle(f.kind);
        built.group.traverse((o) => { if ((o as THREE.Mesh).isMesh) { o.castShadow = true; o.receiveShadow = true; } });
        built.group.position.copy(target);
        const tag = label(`${f.id} ${f.kind}`, "vehicle-label fleet");
        tag.position.set(0, f.kind === "amr" ? 3.2 : 5.4, 0);
        built.group.add(tag);
        h.scene.add(built.group);
        item = h.fleet[f.id] = { group: built.group, beacon: built.beacon, target: target.clone() };
      }
      if (f.status === "IDLE") item.group.position.copy(target);
      item.target.copy(target);
      item.beacon.emissive.setHex(f.status.startsWith("PAUSED") ? AMBER : LIME);
    }

    // A new departure count starts the outbound trailer's pull-away.
    if (h.departure.seen >= 0 && state.ops.trucks_departed > h.departure.seen) h.departure.started = h.clock.elapsedTime;
    h.departure.seen = state.ops.trucks_departed;

    for (const child of [...h.route.children]) {
      h.route.remove(child);
      (child as THREE.Mesh).geometry.dispose();
      ((child as THREE.Mesh).material as THREE.Material).dispose();
    }
    const points = [h.toWorld(v.x, v.y, 0.1), ...v.route.map((id) => h.toWorld(nodeById[id].x, nodeById[id].y, 0.1))];
    for (let i = 0; i + 1 < points.length; i++) {
      const a = points[i], b = points[i + 1];
      const length = a.distanceTo(b);
      if (length < 0.05) continue;
      const seg = new THREE.Mesh(
        new THREE.BoxGeometry(length + 1.1, 0.12, 1.1),
        new THREE.MeshStandardMaterial({ color: LIME, emissive: LIME, emissiveIntensity: 0.9 }),
      );
      seg.position.copy(a).add(b).multiplyScalar(0.5);
      seg.rotation.y = -Math.atan2(b.z - a.z, b.x - a.x);
      h.route.add(seg);
    }
  }, [state, map]);

  useEffect(() => {
    const h = handles.current;
    if (!h) return;
    const fillByIndex = new Map(racks.map((r) => [r.structure_index, r.fill]));
    for (const [key, tint] of Object.entries(h.heat)) {
      const index = Number(key), fill = fillByIndex.get(index);
      tint.visible = heatmap && fill !== undefined;
      if (fill !== undefined) (tint.material as THREE.MeshBasicMaterial).color.copy(fillColor(fill));
      h.outline[index].visible = selected === index;
    }
  }, [racks, heatmap, selected, map]);

  const traffic = state?.ops.traffic;
  useEffect(() => {
    const h = handles.current;
    if (!h) return;
    for (const [key, material] of Object.entries(h.lanes)) {
      const value = trafficHeat ? traffic?.[key] ?? 0 : 0;
      material.color.setHex(LANE_GREY);
      if (value > 0) material.color.lerp(new THREE.Color(LIME), 0.15 + 0.75 * value);  // busier lanes are more lime; red stays reserved for BLOCKED
    }
  }, [traffic, trafficHeat, map]);

  return <div className="scene" ref={hostRef} title="Drag to orbit, scroll to zoom, double-click to reset the view" />;
}
