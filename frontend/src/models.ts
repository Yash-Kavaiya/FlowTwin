// Facility models built from primitives and canvas textures, so the demo needs no downloaded assets.
// Every builder returns a group whose footprint is w (x) by d (z), standing on y = 0, centred on the origin.
import * as THREE from "three";

export const LIME = 0xbfd732;
export const AMBER = 0xf5a524;

function rng(seed: number) {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

const std = (color: number, roughness = 0.8, metalness = 0.05) =>
  new THREE.MeshStandardMaterial({ color, roughness, metalness });

const MAT = {
  steelBlue: std(0x1f5aa8, 0.5, 0.4),
  beam: std(0xe8751a, 0.55, 0.3),
  deck: std(0x8d949c, 0.7, 0.3),
  metal: std(0x9aa3ad, 0.4, 0.7),
  dark: std(0x23262a, 0.7, 0.2),
  rubber: std(0x121314, 0.95, 0),
  wood: std(0xb08a57, 0.9, 0),
  white: std(0xf1f3f4, 0.6, 0.1),
  wall: std(0x24282d, 0.9, 0),
  machine: std(0xc9d1d9, 0.45, 0.35),
  machineDark: std(0x3b4652, 0.6, 0.3),
  lime: std(LIME, 0.5, 0.1),
  yellow: std(0xf2c81a, 0.7, 0),
  glass: new THREE.MeshStandardMaterial({ color: 0x9fd3ff, roughness: 0.1, metalness: 0.2, transparent: true, opacity: 0.55 }),
  screen: new THREE.MeshStandardMaterial({ color: 0x0b2a12, emissive: 0x39d353, emissiveIntensity: 0.9 }),
};
const CARDBOARD = [0xc49a6c, 0xb5895a, 0xd1aa7c, 0xa97c50].map((c) => std(c, 0.95, 0));

function box(w: number, h: number, d: number, material: THREE.Material, x = 0, y = 0, z = 0): THREE.Mesh {
  const mesh = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), material);
  mesh.position.set(x, y + h / 2, z);
  return mesh;
}

function wheel(radius: number, width: number, x: number, z: number): THREE.Mesh {
  const mesh = new THREE.Mesh(new THREE.CylinderGeometry(radius, radius, width, 18), MAT.rubber);
  mesh.rotation.x = Math.PI / 2;
  mesh.position.set(x, radius, z);
  return mesh;
}

/** Stack of cartons filling roughly w by d up to height h. */
function cartons(group: THREE.Group, rand: () => number, w: number, d: number, h: number, x: number, y: number, z: number) {
  let cursor = -w / 2;
  while (cursor < w / 2 - 0.6) {
    const bw = Math.min(0.9 + rand() * 1.3, w / 2 - cursor);
    const bh = h * (0.45 + rand() * 0.5);
    const bd = d * (0.6 + rand() * 0.3);
    if (rand() > 0.14) {
      group.add(box(bw - 0.12, bh, bd, CARDBOARD[Math.floor(rand() * CARDBOARD.length)], x + cursor + bw / 2, y, z));
    }
    cursor += bw;
  }
}

function rack(w: number, d: number, h: number, seed: number): THREE.Group {
  const g = new THREE.Group();
  const rand = rng(seed);
  const bays = Math.max(1, Math.round(w / 9));
  for (let i = 0; i <= bays; i++) {
    const x = -w / 2 + (w * i) / bays;
    for (const z of [-d / 2 + 0.15, d / 2 - 0.15]) g.add(box(0.3, h, 0.3, MAT.steelBlue, x, 0, z));
    g.add(box(0.12, 0.12, d - 0.3, MAT.steelBlue, x, h * 0.5, 0));
  }
  const levels = Math.max(2, Math.round(h / 2.4));
  for (let level = 0; level < levels; level++) {
    const y = 0.25 + (level * (h - 0.6)) / levels;
    for (const z of [-d / 2 + 0.15, d / 2 - 0.15]) g.add(box(w, 0.22, 0.18, MAT.beam, 0, y, z));
    g.add(box(w - 0.3, 0.06, d - 0.4, MAT.deck, 0, y + 0.22, 0));
    for (let bay = 0; bay < bays; bay++) {
      const bayWidth = w / bays - 0.5;
      cartons(g, rand, bayWidth, d - 0.6, (h - 0.6) / levels - 0.5, -w / 2 + (w * (bay + 0.5)) / bays, y + 0.28, 0);
    }
  }
  return g;
}

function pallet(w: number, d: number, h: number, seed: number): THREE.Group {
  const g = new THREE.Group();
  const rand = rng(seed);
  for (let i = 0; i < 5; i++) g.add(box(w, 0.12, d / 7, MAT.wood, 0, 0.28, -d / 2 + (d * (i + 0.5)) / 5));
  for (const z of [-d / 2 + 0.3, 0, d / 2 - 0.3]) g.add(box(w, 0.28, 0.3, MAT.wood, 0, 0, z));
  const layers = Math.max(1, Math.round(h / 1.1));
  for (let layer = 0; layer < layers; layer++) {
    cartons(g, rand, w - 0.3, d - 0.4, (h - 0.4) / layers, 0, 0.4 + (layer * (h - 0.4)) / layers, 0);
  }
  return g;
}

function bench(w: number, d: number, h: number, seed: number): THREE.Group {
  const g = new THREE.Group();
  const rand = rng(seed);
  g.add(box(w, 0.2, d, MAT.deck, 0, h - 0.2, 0));
  for (const x of [-w / 2 + 0.25, w / 2 - 0.25]) {
    for (const z of [-d / 2 + 0.25, d / 2 - 0.25]) g.add(box(0.2, h - 0.2, 0.2, MAT.dark, x, 0, z));
  }
  for (let i = 0; i < 3; i++) {
    g.add(box(0.9 + rand(), 0.6 + rand() * 0.5, 0.9 + rand(), CARDBOARD[i % 4], (rand() - 0.5) * (w - 1.5), h, (rand() - 0.5) * (d - 1.5)));
  }
  return g;
}

/** Dock wall with roller doors along its long side. */
function dock(w: number, d: number, h: number): THREE.Group {
  const g = new THREE.Group();
  const alongZ = d > w;
  const length = alongZ ? d : w, depth = alongZ ? w : d;
  const inner = new THREE.Group();
  inner.add(box(length, h, depth, MAT.wall));
  const doors = Math.max(1, Math.round(length / 9));
  for (let i = 0; i < doors; i++) {
    const x = -length / 2 + (length * (i + 0.5)) / doors;
    const doorWidth = Math.min(6, length / doors - 1.5);
    inner.add(box(doorWidth, h * 0.72, depth + 0.1, MAT.deck, x, 0, 0));
    for (let s = 1; s < 6; s++) inner.add(box(doorWidth, 0.06, depth + 0.16, MAT.dark, x, (h * 0.72 * s) / 6, 0));
    inner.add(box(doorWidth + 0.6, 0.35, depth + 0.2, MAT.lime, x, h * 0.72, 0));
    for (const side of [-1, 1]) inner.add(box(0.35, 1.1, depth + 0.5, MAT.yellow, x + (side * (doorWidth + 0.5)) / 2, 0, 0));
  }
  if (alongZ) inner.rotation.y = Math.PI / 2;
  g.add(inner);
  return g;
}

function truck(w: number, d: number, h: number): THREE.Group {
  const g = new THREE.Group();
  const alongZ = d > w;
  const length = alongZ ? d : w, width = alongZ ? w : d;
  const inner = new THREE.Group();
  const trailer = length * 0.74, cab = length * 0.2;
  inner.add(box(trailer, h * 0.72, width * 0.94, MAT.white, -length / 2 + trailer / 2, 1.3, 0));
  for (const z of [-1, 1]) {
    inner.add(box(trailer * 0.96, 0.5, 0.06, MAT.lime, -length / 2 + trailer / 2, 1.3 + h * 0.3, (z * width * 0.94) / 2));
  }
  inner.add(box(trailer, 0.3, width * 0.7, MAT.dark, -length / 2 + trailer / 2, 1.0, 0));
  const cabX = length / 2 - cab / 2;
  inner.add(box(cab, h * 0.55, width * 0.9, MAT.machineDark, cabX, 0.9, 0));
  inner.add(box(cab * 0.5, h * 0.22, width * 0.84, MAT.glass, cabX + cab * 0.28, 0.9 + h * 0.3, 0));
  for (const x of [-length / 2 + 1.2, -length / 2 + 2.9, cabX]) {
    for (const z of [-1, 1]) inner.add(wheel(0.9, 0.6, x, (z * width) / 2 - z * 0.3));
  }
  if (alongZ) inner.rotation.y = Math.PI / 2;
  g.add(inner);
  return g;
}

function conveyor(w: number, d: number, h: number, seed: number): THREE.Group {
  const g = new THREE.Group();
  const rand = rng(seed);
  const alongZ = d > w;
  const length = alongZ ? d : w, width = alongZ ? w : d;
  const inner = new THREE.Group();
  inner.add(box(length, 0.18, width - 0.3, MAT.rubber, 0, h - 0.18, 0));
  for (const z of [-1, 1]) inner.add(box(length, 0.45, 0.14, MAT.lime, 0, h - 0.3, (z * (width - 0.14)) / 2));
  const legs = Math.max(2, Math.round(length / 5));
  for (let i = 0; i <= legs; i++) {
    const x = -length / 2 + 0.3 + ((length - 0.6) * i) / legs;
    for (const z of [-1, 1]) inner.add(box(0.18, h - 0.3, 0.18, MAT.metal, x, 0, (z * (width - 0.4)) / 2));
  }
  for (let x = -length / 2 + 0.6; x < length / 2; x += 1.1) {
    const roller = new THREE.Mesh(new THREE.CylinderGeometry(0.12, 0.12, width - 0.4, 10), MAT.metal);
    roller.rotation.x = Math.PI / 2;
    roller.position.set(x, h - 0.02, 0);
    inner.add(roller);
  }
  const parcels: THREE.Mesh[] = [];
  for (let x = -length / 2 + 2; x < length / 2 - 1; x += 3.2 + rand() * 2.5) {
    const s = 0.8 + rand() * 0.6;
    const parcel = box(s * 1.2, s * 0.8, Math.min(s, width - 0.6), CARDBOARD[Math.floor(rand() * 4)], x, h, 0);
    parcels.push(parcel);
    inner.add(parcel);
  }
  inner.userData.belt = { parcels, half: length / 2 - 0.8 };  // the scene moves these along the belt
  if (alongZ) inner.rotation.y = Math.PI / 2;
  g.add(inner);
  return g;
}

function cage(w: number, d: number, h: number, seed: number): THREE.Group {
  const g = new THREE.Group();
  const rand = rng(seed);
  const cells = 2, cw = w / cells - 0.4, cd = d / cells - 0.4;
  for (let i = 0; i < cells; i++) {
    for (let j = 0; j < cells; j++) {
      const x = -w / 2 + (w * (i + 0.5)) / cells, z = -d / 2 + (d * (j + 0.5)) / cells;
      g.add(box(cw, 0.15, cd, MAT.metal, x, 0.3, z));
      const frame = new THREE.LineSegments(
        new THREE.EdgesGeometry(new THREE.BoxGeometry(cw, h - 0.3, cd)),
        new THREE.LineBasicMaterial({ color: 0xb8c0c8 }),
      );
      frame.position.set(x, 0.3 + (h - 0.3) / 2, z);
      g.add(frame);
      for (const level of [0.4, 0.7]) g.add(box(cw, 0.05, 0.05, MAT.metal, x, 0.3 + (h - 0.3) * level, z + cd / 2));
      const fill = (h - 0.6) * (0.35 + rand() * 0.6);
      g.add(box(cw * 0.8, fill, cd * 0.8, CARDBOARD[Math.floor(rand() * 4)], x, 0.45, z));
      for (const sx of [-1, 1]) g.add(wheel(0.22, 0.15, x + (sx * cw) / 2.4, z));
    }
  }
  return g;
}

function machine(w: number, d: number, h: number, seed: number): THREE.Group {
  const g = new THREE.Group();
  const rand = rng(seed);
  const bw = w * 0.72, bd = d * 0.66;
  g.add(box(bw, 0.6, bd, MAT.machineDark, 0, 0, 0));
  g.add(box(bw * 0.96, h * 0.62, bd * 0.94, MAT.machine, 0, 0.6, 0));
  g.add(box(bw * 0.5, h * 0.3, bd * 0.05, MAT.glass, -bw * 0.12, 0.6 + h * 0.2, bd * 0.47 + 0.02));
  g.add(box(bw * 0.6, h * 0.22, bd * 0.6, MAT.machineDark, bw * 0.1, 0.6 + h * 0.62, -bd * 0.1));
  g.add(box(bw * 0.9, 0.3, 0.08, MAT.lime, 0, 0.6 + h * 0.5, bd * 0.47 + 0.03));
  // operator panel and signal tower
  g.add(box(0.9, 1.8, 0.5, MAT.machineDark, bw * 0.36, 0, bd / 2 + 0.7));
  g.add(box(0.75, 0.6, 0.06, MAT.screen, bw * 0.36, 1.1, bd / 2 + 0.96));
  const pole = new THREE.Mesh(new THREE.CylinderGeometry(0.07, 0.07, 1.4, 8), MAT.metal);
  pole.position.set(bw * 0.4, 0.6 + h * 0.62 + 0.7, bd * 0.3);
  g.add(pole);
  const lamp = new THREE.Mesh(
    new THREE.CylinderGeometry(0.18, 0.18, 0.5, 12),
    new THREE.MeshStandardMaterial({ color: 0x1b5e20, emissive: rand() > 0.3 ? 0x39d353 : AMBER, emissiveIntensity: 1.2 }),
  );
  lamp.position.set(bw * 0.4, 0.6 + h * 0.62 + 1.5, bd * 0.3);
  g.add(lamp);
  // safety fence around the cell
  for (const [x, z] of [[-1, -1], [1, -1], [1, 1], [-1, 1]] as const) {
    g.add(box(0.14, 1.6, 0.14, MAT.yellow, (x * w) / 2 - x * 0.1, 0, (z * d) / 2 - z * 0.1));
  }
  for (const y of [0.55, 1.5]) {
    g.add(box(w - 0.2, 0.06, 0.06, MAT.yellow, 0, y, -d / 2 + 0.1));
    for (const x of [-1, 1]) g.add(box(0.06, 0.06, d - 0.2, MAT.yellow, (x * w) / 2 - x * 0.1, y, 0));
  }
  return g;
}

/** Vehicle charging bay: cabinet with a status light, cable post and a painted parking pad. */
function charger(w: number, d: number, h: number): THREE.Group {
  const g = new THREE.Group();
  g.add(box(w, 0.05, d, MAT.lime, 0, 0, 0));
  g.add(box(w - 0.5, 0.06, d - 0.5, MAT.dark, 0, 0, 0));
  g.add(box(1.4, h, 1.0, MAT.machineDark, -w / 2 + 0.9, 0, -d / 2 + 0.7));
  g.add(box(0.9, 0.5, 0.06, MAT.screen, -w / 2 + 0.9, h * 0.6, -d / 2 + 1.23));
  g.add(box(0.2, h * 0.7, 0.2, MAT.yellow, w / 2 - 0.5, 0, -d / 2 + 0.5));
  return g;
}

/** Glazed supervisor office on a raised plinth. */
function office(w: number, d: number, h: number): THREE.Group {
  const g = new THREE.Group();
  g.add(box(w, 0.5, d, MAT.machineDark, 0, 0, 0));
  g.add(box(w - 0.4, h - 1.1, d - 0.4, MAT.glass, 0, 0.5, 0));
  g.add(box(w, 0.6, d, MAT.wall, 0, h - 0.6, 0));
  g.add(box(w + 0.1, 0.25, d + 0.1, MAT.lime, 0, h - 0.85, 0));
  for (const x of [-1, 1]) for (const z of [-1, 1]) g.add(box(0.3, h - 0.5, 0.3, MAT.dark, (x * (w - 0.3)) / 2, 0.5, (z * (d - 0.3)) / 2));
  g.add(box(w * 0.5, 1.0, d * 0.35, MAT.deck, 0, 0.5, 0));
  return g;
}

const BUILDERS: Record<string, (w: number, d: number, h: number, seed: number) => THREE.Group> = {
  rack, pallet, bench, dock, truck, conveyor, cage, machine, charger, office,
};

export function buildStructure(s: { kind: string; x: number; y: number; w: number; d: number; h: number }): THREE.Group {
  const seed = Math.round(s.x * 131 + s.y * 17 + s.w * 7);
  return (BUILDERS[s.kind] ?? ((w, d, h) => new THREE.Group().add(box(w, h, d, MAT.machineDark))))(s.w, s.d, s.h, seed);
}

/** Tugger-style delivery vehicle in fleet colours. The beacon colour is the status signal. */
export function buildVehicle(body: THREE.Material = MAT.lime): { group: THREE.Group; beacon: THREE.MeshStandardMaterial } {
  const group = new THREE.Group();
  group.add(box(4.4, 0.7, 2.6, MAT.dark, 0, 0.35, 0));
  group.add(box(2.0, 1.3, 2.4, body, -0.9, 1.05, 0));
  group.add(box(0.5, 2.6, 2.2, MAT.dark, 0.35, 1.05, 0));
  for (const z of [-0.8, 0.8]) group.add(box(0.14, 3.2, 0.14, MAT.metal, 0.7, 0.4, z));
  group.add(box(0.16, 0.16, 1.9, MAT.metal, 0.7, 3.5, 0));
  for (const z of [-0.6, 0.6]) group.add(box(1.8, 0.1, 0.3, MAT.metal, 1.6, 0.45, z));
  group.add(box(1.4, 1.1, 1.6, CARDBOARD[0], 1.75, 0.55, 0));
  group.add(box(1.5, 0.08, 2.2, MAT.dark, -0.9, 3.1, 0));
  for (const x of [-1.8, 0]) for (const z of [-1.0, 1.0]) group.add(box(0.1, 0.8, 0.1, MAT.dark, x, 2.35, z));
  for (const x of [-1.5, 1.2]) for (const z of [-1.25, 1.25]) group.add(wheel(0.5, 0.35, x, z));
  const beacon = new THREE.MeshStandardMaterial({ color: 0xffffff, emissive: LIME, emissiveIntensity: 1.6 });
  const lamp = new THREE.Mesh(new THREE.CylinderGeometry(0.22, 0.22, 0.35, 12), beacon);
  lamp.position.set(-0.9, 3.35, 0);
  group.add(lamp);
  return { group, beacon };
}

/** Low autonomous mobile robot carrying one tote. */
export function buildAmr(): { group: THREE.Group; beacon: THREE.MeshStandardMaterial } {
  const group = new THREE.Group();
  group.add(box(3.0, 0.7, 2.2, MAT.white, 0, 0.3, 0));
  group.add(box(3.1, 0.18, 2.3, MAT.lime, 0, 0.62, 0));
  group.add(box(2.2, 0.12, 1.7, MAT.dark, 0, 1.0, 0));
  group.add(box(1.6, 0.9, 1.3, CARDBOARD[1], 0, 1.12, 0));
  for (const x of [-1.0, 1.0]) for (const z of [-1.0, 1.0]) group.add(wheel(0.3, 0.25, x, z));
  const beacon = new THREE.MeshStandardMaterial({ color: 0xffffff, emissive: LIME, emissiveIntensity: 1.6 });
  const lamp = new THREE.Mesh(new THREE.BoxGeometry(0.25, 0.25, 1.9), beacon);
  lamp.position.set(1.45, 0.75, 0);
  group.add(lamp);
  return { group, beacon };
}

/** Vehicle for a fleet kind: tugger (white), forklift (orange) or AMR. */
export function buildFleetVehicle(kind: string): { group: THREE.Group; beacon: THREE.MeshStandardMaterial } {
  if (kind === "amr") return buildAmr();
  return buildVehicle(kind === "forklift" ? MAT.beam : MAT.white);
}

/** Floor worker in a hi-vis vest and hard hat. Scenery only. */
export function buildWorker(): THREE.Group {
  const group = new THREE.Group();
  const legs = new THREE.Mesh(new THREE.CylinderGeometry(0.42, 0.36, 1.5, 10), MAT.machineDark);
  legs.position.y = 0.75;
  const torso = new THREE.Mesh(new THREE.CylinderGeometry(0.5, 0.46, 1.3, 10), MAT.lime);
  torso.position.y = 2.15;
  const head = new THREE.Mesh(new THREE.SphereGeometry(0.36, 12, 10), std(0xd9a37a, 0.8, 0));
  head.position.y = 3.15;
  const hat = new THREE.Mesh(new THREE.SphereGeometry(0.4, 12, 8, 0, Math.PI * 2, 0, Math.PI / 2), MAT.yellow);
  hat.position.y = 3.25;
  group.add(legs, torso, head, hat);
  return group;
}

function canvasTexture(width: number, height: number, draw: (ctx: CanvasRenderingContext2D) => void): THREE.CanvasTexture {
  const canvas = document.createElement("canvas");
  canvas.width = width;
  canvas.height = height;
  draw(canvas.getContext("2d")!);
  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  texture.anisotropy = 4;
  return texture;
}

/** Sealed concrete: speckle, a few stains and saw-cut joints. */
export function floorTexture(): THREE.CanvasTexture {
  const rand = rng(7);
  const texture = canvasTexture(1024, 1024, (ctx) => {
    ctx.fillStyle = "#3a3e43";
    ctx.fillRect(0, 0, 1024, 1024);
    for (let i = 0; i < 26000; i++) {
      const shade = 48 + Math.floor(rand() * 36);
      ctx.fillStyle = `rgba(${shade},${shade + 2},${shade + 5},0.5)`;
      ctx.fillRect(rand() * 1024, rand() * 1024, 1 + rand() * 2, 1 + rand() * 2);
    }
    for (let i = 0; i < 14; i++) {
      const x = rand() * 1024, y = rand() * 1024, r = 40 + rand() * 110;
      const stain = ctx.createRadialGradient(x, y, 0, x, y, r);
      stain.addColorStop(0, "rgba(20,22,24,0.22)");
      stain.addColorStop(1, "rgba(20,22,24,0)");
      ctx.fillStyle = stain;
      ctx.fillRect(x - r, y - r, r * 2, r * 2);
    }
    ctx.strokeStyle = "rgba(15,16,18,0.55)";
    ctx.lineWidth = 2;
    for (let p = 0; p <= 1024; p += 256) {
      ctx.beginPath(); ctx.moveTo(p, 0); ctx.lineTo(p, 1024); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(0, p); ctx.lineTo(1024, p); ctx.stroke();
    }
  });
  texture.wrapS = texture.wrapT = THREE.RepeatWrapping;
  return texture;
}

/** Wall sign in the fleet colours: wordmark plus the site name. */
export function signTexture(brand: string, site: string): THREE.CanvasTexture {
  return canvasTexture(1024, 256, (ctx) => {
    ctx.fillStyle = "#0a0a0a";
    ctx.fillRect(0, 0, 1024, 256);
    ctx.fillStyle = "#bfd732";
    ctx.fillRect(0, 232, 1024, 24);
    ctx.font = "800 120px Heebo, 'Segoe UI', Arial, sans-serif";
    ctx.textBaseline = "middle";
    const half = Math.ceil(brand.length / 2);
    ctx.fillStyle = "#ffffff";
    ctx.fillText(brand.slice(0, half), 48, 100);
    ctx.fillStyle = "#bfd732";
    ctx.fillText(brand.slice(half), 48 + ctx.measureText(brand.slice(0, half)).width, 100);
    ctx.font = "500 44px Heebo, 'Segoe UI', Arial, sans-serif";
    ctx.fillStyle = "#c8c8c8";
    ctx.fillText(site.toUpperCase(), 52, 190);
  });
}

/** Yellow and black hazard tape. */
export function hazardTexture(): THREE.CanvasTexture {
  const texture = canvasTexture(64, 64, (ctx) => {
    ctx.fillStyle = "#f2c81a";
    ctx.fillRect(0, 0, 64, 64);
    ctx.fillStyle = "#151515";
    ctx.beginPath();
    ctx.moveTo(0, 64); ctx.lineTo(32, 64); ctx.lineTo(64, 32); ctx.lineTo(64, 0); ctx.closePath();
    ctx.moveTo(0, 32); ctx.lineTo(0, 0); ctx.lineTo(32, 0); ctx.closePath();
    ctx.fill();
  });
  texture.wrapS = texture.wrapT = THREE.RepeatWrapping;
  return texture;
}

export const materials = MAT;
export { box };
