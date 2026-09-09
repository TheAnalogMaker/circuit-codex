import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

// The source layout has drawing coordinates, not physical dimensions. Only its
// x/y coordinates and endpoint identities carry authority here. Body dimensions,
// materials and the vertical separation below are illustrative presentation.
const SCALE = 1 / 40;
const UP = new THREE.Vector3(0, 1, 0);
const LAYERS = ['board', 'components', 'hardware', 'wiring', 'heaters', 'labels'];
const BAND_COLORS = [0x211b17, 0x653d27, 0xa94b38, 0xd27d31, 0xe1b947,
  0x4e7454, 0x42688c, 0x796084, 0x92928a, 0xebe5d7];

function visibleInTree(object) {
  for (let node = object; node; node = node.parent) if (!node.visible) return false;
  return true;
}

function resistorBands(value) {
  const match = String(value || '').replaceAll(',', '').match(/([\d.]+)\s*([kKmM]?)/);
  if (!match) return null;
  const resistance = Number(match[1]) * ({ k: 1e3, K: 1e3, M: 1e6, m: 1e6 }[match[2]] || 1);
  if (!(resistance > 0)) return null;
  const exponent = Math.floor(Math.log10(resistance)) - 1;
  const digits = Math.round(resistance / (10 ** exponent));
  if (digits < 10 || digits > 99 || exponent < 0 || exponent > 9) return null;
  // Three value bands only: no invented tolerance band.
  return [BAND_COLORS[Math.floor(digits / 10)], BAND_COLORS[digits % 10], BAND_COLORS[exponent]];
}

/**
 * Compute illustrative overpasses at source-path crossings. This pure planner
 * is exported so endpoint/crossing regressions can run without a WebGL context.
 * Source x/y positions and electrical identities remain unchanged. Only height
 * is added; an intersection in a drawing is never treated as a new junction.
 */
export function prepareWireRouting(connections) {
  const EPSILON = 1e-6;
  const CLEARANCE = 0.15; // World-space centerline gap; wire diameter is 0.05.
  const records = connections.filter(c => Array.isArray(c.points) && c.points.length > 1)
    .map((connection, index) => {
      const distances = [0];
      const segments = [];
      for (let i = 1; i < connection.points.length; i++) {
        const a = connection.points[i - 1];
        const b = connection.points[i];
        const length = Math.hypot(b[0] - a[0], b[1] - a[1]);
        if (length > EPSILON) segments.push({ a, b, length, start: distances[i - 1],
          minX: Math.min(a[0], b[0]), maxX: Math.max(a[0], b[0]),
          minY: Math.min(a[1], b[1]), maxY: Math.max(a[1], b[1]) });
        distances.push(distances[i - 1] + length);
      }
      return { connection, index, distances, segments, total: distances.at(-1) };
    }).filter(record => record.total > EPSILON)
    // The bare ground bus stays below crossing insulated leads.
    .sort((a, b) => Number(a.connection.kind !== 'bus') - Number(b.connection.kind !== 'bus') || a.index - b.index);
  const byId = new Map(records.map(record => [record.connection.id, record]));
  const crossings = [];
  const seen = new Set();
  const end = (record, distance) => distance < EPSILON || record.total - distance < EPSILON;
  function addCrossing(a, da, b, db, preferredUpper = null) {
    const aEnd = end(a, da);
    const bEnd = end(b, db);
    // Common endpoints are the source's intentional connection points. A wire
    // explicitly terminating at a board-bus anchor also intentionally meets it.
    if (aEnd && bEnd) return;
    const anchorAt = (record, d) => d < EPSILON ? record.connection.fromOwner == null : record.connection.toOwner == null;
    if (a.connection.kind === 'bus' && bEnd && anchorAt(b, db)) return;
    if (b.connection.kind === 'bus' && aEnd && anchorAt(a, da)) return;
    let lower = a, upper = b, lowerDistance = da, upperDistance = db;
    // A terminal cannot be lifted away from its source component. If only one
    // path ends here, the continuing path supplies the bridge instead.
    if (bEnd || (preferredUpper === a && !aEnd)) { lower = b; upper = a; lowerDistance = db; upperDistance = da; }
    const key = `${lower.connection.id}:${lowerDistance.toFixed(5)}|${upper.connection.id}:${upperDistance.toFixed(5)}`;
    if (seen.has(key)) return;
    seen.add(key);
    crossings.push({ lowerId: lower.connection.id, upperId: upper.connection.id, lowerDistance, upperDistance });
  }
  const cross = (ax, ay, bx, by) => ax * by - ay * bx;
  for (let i = 0; i < records.length; i++) {
    const a = records[i];
    for (let j = i + 1; j < records.length; j++) {
      const b = records[j];
      for (const sa of a.segments) for (const sb of b.segments) {
        if (sa.maxX < sb.minX - EPSILON || sb.maxX < sa.minX - EPSILON
          || sa.maxY < sb.minY - EPSILON || sb.maxY < sa.minY - EPSILON) continue;
        const rx = sa.b[0] - sa.a[0], ry = sa.b[1] - sa.a[1];
        const sx = sb.b[0] - sb.a[0], sy = sb.b[1] - sb.a[1];
        const qx = sb.a[0] - sa.a[0], qy = sb.a[1] - sa.a[1];
        const denominator = cross(rx, ry, sx, sy);
        if (Math.abs(denominator) > EPSILON) {
          const t = cross(qx, qy, sx, sy) / denominator;
          const u = cross(qx, qy, rx, ry) / denominator;
          if (t >= -EPSILON && t <= 1 + EPSILON && u >= -EPSILON && u <= 1 + EPSILON) {
            addCrossing(a, sa.start + Math.max(0, Math.min(1, t)) * sa.length,
              b, sb.start + Math.max(0, Math.min(1, u)) * sb.length);
          }
        } else if (Math.abs(cross(qx, qy, rx, ry)) < EPSILON) {
          // Collinear drawing sections need separation too, not only X-shaped
          // crossings. Dense plateau constraints cover the overlapping interval.
          const rr = rx * rx + ry * ry;
          const t0 = (qx * rx + qy * ry) / rr;
          const t1 = t0 + (sx * rx + sy * ry) / rr;
          const low = Math.max(0, Math.min(t0, t1));
          const high = Math.min(1, Math.max(t0, t1));
          if (high < low - EPSILON) continue;
          const aTouchesEnd = end(a, sa.start + low * sa.length) || end(a, sa.start + high * sa.length);
          const bDistances = [low, high].map(t => {
            const x = sa.a[0] + t * rx, y = sa.a[1] + t * ry;
            return sb.start + ((x - sb.a[0]) * sx + (y - sb.a[1]) * sy) / sb.length;
          });
          const bTouchesEnd = bDistances.some(d => end(b, d));
          // Keep a single over/under ordering over an overlapping interval.
          // The longer path bridges over a contained path's fixed endpoints.
          const preferredUpper = bTouchesEnd && !aTouchesEnd ? a : b;
          const steps = Math.max(1, Math.ceil((high - low) * sa.length / 2));
          for (let n = 0; n <= steps; n++) {
            const t = low + (high - low) * n / steps;
            const x = sa.a[0] + t * rx, y = sa.a[1] + t * ry;
            const u = ((x - sb.a[0]) * sx + (y - sb.a[1]) * sy) / (sb.length ** 2);
            addCrossing(a, sa.start + t * sa.length, b, sb.start + Math.max(0, Math.min(1, u)) * sb.length, preferredUpper);
          }
        }
      }
    }
  }
  const perUpper = new Map(records.map(record => [record.connection.id, []]));
  for (const crossing of crossings) perUpper.get(crossing.upperId).push(crossing);
  return {
    crossings,
    route(liftForOwner = () => 0) {
      const bridges = new Map(records.map(record => [record.connection.id, []]));
      function base(record, distance) {
        const t = distance / record.total;
        return 0.19 + liftForOwner(record.connection.fromOwner) * (1 - t) + liftForOwner(record.connection.toOwner) * t;
      }
      function bridgeWeight(bridge, distance) {
        const delta = distance - bridge.at;
        const span = delta < 0 ? bridge.left : bridge.right;
        const plateau = Math.min(2.5, span * 0.35);
        if (Math.abs(delta) <= plateau) return 1;
        return Math.max(0, (span - Math.abs(delta)) / (span - plateau));
      }
      function heightAt(id, distance) {
        const record = byId.get(id);
        let added = 0;
        if (!end(record, distance)) {
          for (const bridge of bridges.get(id)) added = Math.max(added, bridge.height * bridgeWeight(bridge, distance));
        }
        return base(record, distance) + added;
      }
      let converged = false;
      for (let pass = 0; pass < 40; pass++) {
        let adjusted = false;
        for (const record of records) {
          for (const crossing of perUpper.get(record.connection.id)) {
            const at = crossing.upperDistance;
            const lowerHeight = heightAt(crossing.lowerId, crossing.lowerDistance);
            if (heightAt(record.connection.id, at) - lowerHeight >= CLEARANCE - EPSILON) continue;
            const needed = Math.max(0, lowerHeight + CLEARANCE - base(record, at));
            const existing = bridges.get(record.connection.id).find(bridge => Math.abs(bridge.at - at) < EPSILON);
            if (existing) existing.height = Math.max(existing.height, needed);
            else bridges.get(record.connection.id).push({ at, height: needed,
              left: Math.min(9, at), right: Math.min(9, record.total - at) });
            adjusted = true;
          }
        }
        if (!adjusted) { converged = true; break; }
      }
      // Some hypothetical collinear routes cannot be separated with upward
      // bridges and fixed endpoints. Refuse that scene instead of drawing a
      // false junction or silently inventing a new x/y route.
      if (!converged) throw new Error('The source wiring needs a reviewed 3D crossing route before it can be displayed.');
      const paths = new Map();
      for (const record of records) {
        const samples = new Set(record.distances);
        for (const segment of record.segments) {
          const count = Math.max(1, Math.ceil(segment.length / 4));
          for (let n = 1; n < count; n++) samples.add(segment.start + segment.length * n / count);
        }
        for (const bridge of bridges.get(record.connection.id)) {
          for (const offset of [-bridge.left, -Math.min(2.5, bridge.left * 0.35), 0,
            Math.min(2.5, bridge.right * 0.35), bridge.right]) samples.add(bridge.at + offset);
        }
        let segmentIndex = 0;
        const points = [...samples].sort((a, b) => a - b).map(distance => {
          while (segmentIndex < record.segments.length - 1
            && distance > record.segments[segmentIndex].start + record.segments[segmentIndex].length) segmentIndex++;
          const segment = record.segments[segmentIndex];
          const t = Math.max(0, Math.min(1, (distance - segment.start) / segment.length));
          return { point: [segment.a[0] + (segment.b[0] - segment.a[0]) * t,
            segment.a[1] + (segment.b[1] - segment.a[1]) * t], height: heightAt(record.connection.id, distance) };
        });
        paths.set(record.connection.id, points);
      }
      return { paths, heightAt };
    },
  };
}

// TubeGeometry normally resamples a CurvePath by length, wasting vertices on
// straight leads and potentially skipping a narrow bridge apex. This curve
// makes each exported bend/bridge knot an exact tube ring instead.
export function buildWireTubeGeometry(inputPoints, radius = 0.025) {
  const points = inputPoints.filter((p, i) => i === 0 || p.distanceToSquared(inputPoints[i - 1]) > 1e-10);
  if (points.length < 2) return null;
  class KnotCurve extends THREE.Curve {
    getPoint(t, target = new THREE.Vector3()) {
      const position = Math.max(0, Math.min(1, t)) * (points.length - 1);
      const index = Math.min(points.length - 2, Math.floor(position));
      return target.copy(points[index]).lerp(points[index + 1], position - index);
    }
    getPointAt(t, target) { return this.getPoint(t, target); }
    getTangentAt(t, target = new THREE.Vector3()) {
      const index = Math.max(0, Math.min(points.length - 1, Math.round(t * (points.length - 1))));
      if (index === 0) return target.copy(points[1]).sub(points[0]).normalize();
      if (index === points.length - 1) return target.copy(points[index]).sub(points[index - 1]).normalize();
      const incoming = points[index].clone().sub(points[index - 1]).normalize();
      const outgoing = points[index + 1].clone().sub(points[index]).normalize();
      target.copy(incoming).add(outgoing);
      return target.lengthSq() < 1e-10 ? target.copy(outgoing) : target.normalize();
    }
  }
  return new THREE.TubeGeometry(new KnotCurve(), points.length - 1, radius, 6, false);
}

/**
 * Create an on-demand 3D view of the exported layout. onSelect receives the
 * original component object or null. No data is modified by this renderer.
 */
export function createLayoutScene(container, data, { onSelect = () => {}, onError = () => {} } = {}) {
  if (!container || !data?.board || !Array.isArray(data.components)) {
    throw new Error('The 3D layout data is incomplete.');
  }

  let disposed = false;
  let contextLost = false;
  let frame = 0;
  let explode = 0;
  let explodeDirty = false;
  let selectedId = null;
  let hoveredId = null;
  let pointerStart = null;
  const materialCache = new Map();
  const ownedGeometries = new Set();
  const ownedTextures = new Set();
  const componentRecords = new Map();
  const labels = [];
  const wires = [];
  const pickables = [];
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x1d1a15);
  const layers = Object.fromEntries(LAYERS.map(name => {
    const group = new THREE.Group();
    group.name = name;
    scene.add(group);
    return [name, group];
  }));
  layers.labels.visible = false;

  const centerX = data.board.x + data.board.width / 2;
  const centerZ = data.board.y + data.board.height / 2;
  const point = (xy, height = 0) => new THREE.Vector3(
    (xy[0] - centerX) * SCALE, height, (xy[1] - centerZ) * SCALE,
  );
  const trackGeometry = geometry => (ownedGeometries.add(geometry), geometry);
  function material(color, { metalness = 0, roughness = 0.66, ...options } = {}) {
    const key = JSON.stringify([color, metalness, roughness, options]);
    if (!materialCache.has(key)) {
      materialCache.set(key, new THREE.MeshStandardMaterial({ color, metalness, roughness, ...options }));
    }
    return materialCache.get(key);
  }
  function mesh(parent, geometry, mat, position) {
    const object = new THREE.Mesh(trackGeometry(geometry), mat);
    if (position) object.position.copy(position);
    object.castShadow = true;
    object.receiveShadow = true;
    parent.add(object);
    return object;
  }
  function cylinder(parent, radius, height, mat, position, topRadius = radius, segments = 24) {
    return mesh(parent, new THREE.CylinderGeometry(topRadius, radius, height, segments), mat, position);
  }
  function rod(parent, from, to, radius, mat) {
    const delta = to.clone().sub(from);
    if (delta.lengthSq() < 1e-10) return null;
    const object = cylinder(parent, radius, delta.length(), mat, from.clone().add(to).multiplyScalar(0.5), radius, 10);
    object.quaternion.setFromUnitVectors(UP, delta.normalize());
    return object;
  }
  const metal = material(0xb9b4a2, { metalness: 0.88, roughness: 0.35 });
  const solder = material(0x9eaaa5, { metalness: 0.78, roughness: 0.28 });
  const darkMetal = material(0x454b46, { metalness: 0.65, roughness: 0.45 });
  const brass = material(0xa88b53, { metalness: 0.72, roughness: 0.4 });
  const black = material(0x242a28, { roughness: 0.46 });

  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false, powerPreference: 'low-power' });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.45;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFShadowMap;
  const canvas = renderer.domElement;
  canvas.style.cssText = 'display:block;width:100%;height:100%;touch-action:none;';
  canvas.tabIndex = 0;
  canvas.setAttribute('aria-label', `${data.id.toUpperCase()} interactive 3D layout. Drag to orbit, use two fingers to pan or zoom. Use the component list for keyboard selection.`);
  container.appendChild(canvas);

  const camera = new THREE.PerspectiveCamera(38, 1, 0.05, 500);
  const controls = new OrbitControls(camera, canvas);
  controls.enableDamping = false;
  controls.autoRotate = false;
  controls.enablePan = true;
  controls.screenSpacePanning = true;
  controls.minPolarAngle = 0.01;
  controls.maxPolarAngle = Math.PI - 0.01;
  controls.zoomSpeed = 0.8;
  controls.rotateSpeed = 0.65;

  const hemisphere = new THREE.HemisphereLight(0xe8f0e8, 0x554027, 2.2);
  scene.add(hemisphere);
  const key = new THREE.DirectionalLight(0xffedd0, 3.3);
  key.position.set(-7, 18, 10);
  key.castShadow = true;
  key.shadow.mapSize.set(2048, 2048);
  key.shadow.normalBias = 0.035;
  key.shadow.bias = -0.0002;
  scene.add(key);
  const fill = new THREE.DirectionalLight(0xc6dbef, 1.4);
  fill.position.set(7, 6, -8);
  scene.add(fill);
  const below = new THREE.DirectionalLight(0xb8c3b7, 2.0);
  below.position.set(0, -8, 3);
  scene.add(below);

  // A pierced board, rather than dark circles painted over a solid slab, allows
  // underside inspection. Every hole comes from the source eyelet inventory.
  const boardWidth = data.board.width * SCALE;
  const boardDepth = data.board.height * SCALE;
  const boardShape = new THREE.Shape();
  boardShape.moveTo(-boardWidth / 2, -boardDepth / 2);
  boardShape.lineTo(boardWidth / 2, -boardDepth / 2);
  boardShape.lineTo(boardWidth / 2, boardDepth / 2);
  boardShape.lineTo(-boardWidth / 2, boardDepth / 2);
  boardShape.closePath();
  const eyeletPoints = new Map();
  for (const eyelet of data.eyelets || []) {
    const p = point(eyelet.point);
    const key = `${p.x.toFixed(6)},${p.z.toFixed(6)}`;
    if (eyeletPoints.has(key)) continue;
    eyeletPoints.set(key, p);
    if (Math.abs(p.x) < boardWidth / 2 - 0.12 && Math.abs(p.z) < boardDepth / 2 - 0.12) {
      const hole = new THREE.Path();
      hole.absarc(p.x, -p.z, 0.08, 0, Math.PI * 2, true);
      boardShape.holes.push(hole);
    }
  }
  const board = mesh(layers.board, new THREE.ExtrudeGeometry(boardShape, {
    depth: 0.15, bevelEnabled: true, bevelSize: 0.022, bevelThickness: 0.015,
    bevelSegments: 1, steps: 1, curveSegments: 10,
  }), material(0x714a2e, { roughness: 0.92 }));
  board.rotation.x = -Math.PI / 2;
  for (const p of eyeletPoints.values()) {
    for (const height of [0.175, -0.02]) {
      const ring = mesh(layers.board, new THREE.TorusGeometry(0.105, 0.027, 8, 16), brass, new THREE.Vector3(p.x, height, p.z));
      ring.rotation.x = Math.PI / 2;
    }
    mesh(layers.board, new THREE.CylinderGeometry(0.08, 0.08, 0.16, 12, 1, true), metal, new THREE.Vector3(p.x, 0.075, p.z));
  }

  function labelSprite(text, owner, y) {
    const labelCanvas = document.createElement('canvas');
    const ctx = labelCanvas.getContext('2d');
    if (!ctx) return;
    const message = String(text).slice(0, 52);
    ctx.font = '500 28px ui-monospace, SFMono-Regular, Menlo, monospace';
    const width = Math.ceil(ctx.measureText(message).width) + 28;
    labelCanvas.width = Math.min(1024, Math.max(110, width));
    labelCanvas.height = 56;
    ctx.fillStyle = 'rgba(22, 30, 27, 0.91)';
    ctx.beginPath();
    ctx.roundRect(0, 0, labelCanvas.width, 56, 10);
    ctx.fill();
    ctx.strokeStyle = 'rgba(190, 169, 118, 0.55)';
    ctx.lineWidth = 2;
    ctx.stroke();
    ctx.fillStyle = '#f0e7ce';
    ctx.font = '500 28px ui-monospace, SFMono-Regular, Menlo, monospace';
    ctx.textBaseline = 'middle';
    ctx.fillText(message, 14, 29);
    const texture = new THREE.CanvasTexture(labelCanvas);
    texture.colorSpace = THREE.SRGBColorSpace;
    ownedTextures.add(texture);
    const mat = new THREE.SpriteMaterial({ map: texture, depthTest: true,
      depthWrite: false, transparent: true, sizeAttenuation: false });
    const sprite = new THREE.Sprite(mat);
    sprite.position.copy(point(owner.center, y));
    sprite.userData.componentId = owner.id;
    layers.labels.add(sprite);
    labels.push({ sprite, owner, baseHeight: y, mat, aspect: labelCanvas.width / 56 });
    pickables.push(sprite);
  }

  function axialPart(group, component) {
    const rawA = component.a || component.terminals?.[0]?.point;
    const rawB = component.b || component.terminals?.[1]?.point;
    if (!rawA || !rawB) return;
    const a = point(rawA).sub(point(component.center));
    const b = point(rawB).sub(point(component.center));
    const axis = b.clone().sub(a).normalize();
    const span = a.distanceTo(b);
    const category = component.category;
    const isResistor = category === 'res' || category === 'resistor';
    const isElectrolytic = category === 'electro' || category === 'electrolytic';
    const bodyLength = Math.min(span * 0.66, isElectrolytic ? 1.8 : isResistor ? 0.82 : 1.16);
    const radius = isElectrolytic ? 0.235 : isResistor ? 0.108 : 0.15;
    const height = isElectrolytic ? 0.44 : 0.33;
    const middle = a.clone().add(b).multiplyScalar(0.5).setY(height);
    const body = new THREE.Group();
    body.position.copy(middle);
    body.quaternion.setFromUnitVectors(UP, axis);
    group.add(body);
    const bodyMat = isResistor ? material(0xb59868) : isElectrolytic ? material(0xb7aa83, { roughness: 0.7 }) : material(0x995d36, { roughness: 0.52 });
    cylinder(body, radius, bodyLength, bodyMat, new THREE.Vector3());
    if (isResistor) {
      const colors = resistorBands(component.value);
      colors?.forEach((color, index) => cylinder(body, radius + 0.003, 0.058, material(color), new THREE.Vector3(0, bodyLength * (-0.27 + index * 0.18), 0)));
    } else {
      for (const sign of [-1, 1]) cylinder(body, radius * 0.83, 0.035, isElectrolytic ? metal : material(0x493b2a), new THREE.Vector3(0, sign * bodyLength / 2, 0));
      // Neutral casing detail: do not invent polarity when the export has none.
      cylinder(body, radius + 0.004, 0.033, material(isElectrolytic ? 0x6f755f : 0xc09765), new THREE.Vector3(0, -bodyLength * 0.33, 0));
    }
    const half = axis.clone().multiplyScalar(bodyLength / 2);
    const leadA = middle.clone().sub(half);
    const leadB = middle.clone().add(half);
    a.y = b.y = 0.19;
    rod(group, a, leadA, 0.026, metal);
    rod(group, leadB, b, 0.026, metal);
    for (const terminal of [a, b]) {
      const dot = mesh(group, new THREE.SphereGeometry(0.074, 12, 8), solder, terminal);
      dot.scale.y = 0.55;
    }
  }

  function tube(group, component) {
    const small = /12[A-Z]|ECC/i.test(component.label || component.value || '');
    const radius = small ? 0.32 : 0.43;
    const height = small ? 1.48 : 2.08;
    cylinder(group, radius + 0.15, 0.18, material(0x38342d), new THREE.Vector3(0, 0.17, 0));
    cylinder(group, radius + 0.1, 0.06, brass, new THREE.Vector3(0, 0.29, 0));
    const profile = [new THREE.Vector2(radius * 0.86, 0.31), new THREE.Vector2(radius, 0.43),
      new THREE.Vector2(radius, height - 0.25), new THREE.Vector2(radius * 0.91, height - 0.08),
      new THREE.Vector2(radius * 0.55, height + 0.04), new THREE.Vector2(0, height + 0.07)];
    const glass = new THREE.MeshPhysicalMaterial({ color: 0xd8e8dc, metalness: 0.04, roughness: 0.13,
      transparent: true, opacity: 0.19, depthWrite: false, side: THREE.DoubleSide });
    materialCache.set(`glass-${component.id}`, glass);
    const envelope = mesh(group, new THREE.LatheGeometry(profile, 28), glass);
    envelope.castShadow = false;
    cylinder(group, radius * 0.59, height * 0.58, darkMetal, new THREE.Vector3(0, height * 0.56, 0));
    for (const y of [0.49, height - 0.22]) cylinder(group, radius * 0.84, 0.035, material(0xa8a699, { roughness: 0.7 }), new THREE.Vector3(0, y, 0));
    cylinder(group, radius * 0.7, 0.035, metal, new THREE.Vector3(0, height - 0.08, 0));
    // Unlit internals: the reference layout does not claim an energized state.
    for (const x of [-0.085, 0.085]) rod(group, new THREE.Vector3(x, 0.29, 0), new THREE.Vector3(x, height - 0.2, 0), 0.013, material(0x956c47, { metalness: 0.5 }));
    return height + 0.36;
  }

  function transformer(group) {
    const core = mesh(group, new THREE.BoxGeometry(1.28, 1.12, 0.93), darkMetal, new THREE.Vector3(0, 0.74, 0));
    for (let i = 0; i < 9; i++) {
      mesh(group, new THREE.BoxGeometry(1.32, 0.018, 0.97), material(i % 2 ? 0x575b50 : 0x383e37, { metalness: 0.6 }), new THREE.Vector3(0, 0.24 + i * 0.122, 0));
    }
    for (const x of [-0.69, 0.69]) mesh(group, new THREE.BoxGeometry(0.18, 0.99, 0.87), material(0x585747, { metalness: 0.65 }), new THREE.Vector3(x, 0.76, 0));
    mesh(group, new THREE.BoxGeometry(1.8, 0.08, 1.07), darkMetal, new THREE.Vector3(0, 0.16, 0));
    for (const x of [-0.78, 0.78]) for (const z of [-0.36, 0.36]) {
      cylinder(group, 0.065, 0.05, metal, new THREE.Vector3(x, 0.225, z), 0.065, 6);
    }
    return core.position.y + 1;
  }

  function hardware(group, component) {
    if (component.kind === 'tube') return tube(group, component);
    if (component.kind === 'xfmr') return transformer(group);
    if (component.kind === 'pot') {
      cylinder(group, 0.4, 0.28, brass, new THREE.Vector3(0, 0.28, 0));
      cylinder(group, 0.29, 0.08, black, new THREE.Vector3(0, 0.12, 0));
      cylinder(group, 0.11, 0.42, metal, new THREE.Vector3(0, 0.58, 0));
      cylinder(group, 0.13, 0.05, brass, new THREE.Vector3(0, 0.47, 0), 0.13, 6);
      return 1.08;
    }
    if (component.kind === 'jack') {
      cylinder(group, 0.245, 0.3, metal, new THREE.Vector3(0, 0.31, 0));
      cylinder(group, 0.29, 0.07, brass, new THREE.Vector3(0, 0.19, 0), 0.29, 6);
      cylinder(group, 0.145, 0.02, black, new THREE.Vector3(0, 0.47, 0));
      const ring = mesh(group, new THREE.TorusGeometry(0.2, 0.036, 8, 20), metal, new THREE.Vector3(0, 0.47, 0));
      ring.rotation.x = Math.PI / 2;
      return 0.8;
    }
    if (component.category === 'lamp') {
      cylinder(group, 0.255, 0.3, brass, new THREE.Vector3(0, 0.29, 0));
      const jewel = mesh(group, new THREE.SphereGeometry(0.21, 16, 10, 0, Math.PI * 2, 0, Math.PI / 2), material(0x844031, { roughness: 0.27 }), new THREE.Vector3(0, 0.43, 0));
      jewel.scale.y = 0.6;
      return 0.84;
    }
    axialPart(group, component);
    return 0.83;
  }

  for (const component of data.components) {
    const group = new THREE.Group();
    group.position.copy(point(component.center));
    group.userData.componentId = component.id;
    const layer = component.mount === 'board' ? 'components' : 'hardware';
    layers[layer].add(group);
    let labelHeight;
    if (component.mount === 'board') { axialPart(group, component); labelHeight = 0.8; }
    else labelHeight = hardware(group, component);
    // Terminal markers are positioned from exported coordinates, including each
    // actual tube pin and transformer lead. No mechanical proxy defines a net.
    for (const terminal of component.terminals || []) {
      const pos = point(terminal.point, 0.19).sub(point(component.center));
      if (component.mount !== 'board') cylinder(group, 0.052, 0.04, solder, pos, 0.052, 10);
    }
    group.traverse(object => {
      object.userData.componentId = component.id;
      if (object.isMesh) pickables.push(object);
    });
    componentRecords.set(component.id, { component, group, layer });
    labelSprite(component.ref || component.label || component.id, component, labelHeight);
  }

  function ownerLift(id) {
    const record = componentRecords.get(id);
    return record ? explode * (record.component.mount === 'board' ? 1.8 : 3.25) : 0;
  }
  const wireRouting = prepareWireRouting(data.connections || []);
  let wireRoutes = wireRouting.route(ownerLift);
  function buildWireGeometry(connection) {
    const route = wireRoutes.paths.get(connection.id);
    if (!route) return null;
    const points = route.map(sample => point(sample.point, sample.height));
    // Each polyline remains a separate conductor. Heater strands are expanded
    // by the exporter, not guessed or electrically duplicated in this view.
    return buildWireTubeGeometry(points, connection.kind === 'bus' ? 0.033 : 0.025);
  }
  for (const connection of data.connections || []) {
    if (!Array.isArray(connection.points) || connection.points.length < 2) continue;
    const geometry = buildWireGeometry(connection);
    if (!geometry) continue;
    const color = connection.color || (connection.kind === 'heater' ? '#51865a' : connection.kind === 'bus' ? '#ad9870' : '#b6a17b');
    const mat = material(color, { metalness: connection.kind === 'bus' ? 0.72 : 0.08, roughness: 0.65 });
    const lit = material(color, { metalness: connection.kind === 'bus' ? 0.72 : 0.08,
      roughness: 0.3, emissive: color, emissiveIntensity: 0.95 });
    const dimmed = material(new THREE.Color(color).multiplyScalar(0.12), {
      metalness: 0.08, roughness: 0.8,
    });
    const object = mesh(layers[connection.kind === 'heater' ? 'heaters' : 'wiring'], geometry, mat);
    object.name = connection.id;
    object.userData.connectionId = connection.id;
    object.castShadow = false;
    wires.push({ object, connection, baseMaterial: mat, highlightMaterial: lit, dimmedMaterial: dimmed });
  }

  const selection = new THREE.Box3Helper(new THREE.Box3(), 0xd8b268);
  selection.material.depthTest = false;
  selection.material.transparent = true;
  selection.material.opacity = 0.8;
  selection.renderOrder = 10;
  selection.visible = false;
  scene.add(selection);

  // Bounds include the actual long harness paths, not only the board rectangle.
  const allPoints = [point([data.board.x, data.board.y]), point([data.board.x + data.board.width, data.board.y + data.board.height])];
  for (const component of data.components) {
    allPoints.push(point(component.center));
    for (const terminal of component.terminals || []) allPoints.push(point(terminal.point));
  }
  for (const connection of data.connections || []) for (const p of connection.points || []) allPoints.push(point(p));
  const bounds = new THREE.Box3().setFromPoints(allPoints);
  bounds.expandByScalar(1.1);
  const focus = bounds.getCenter(new THREE.Vector3());
  focus.y = 0.6;
  const size = bounds.getSize(new THREE.Vector3());
  const longest = Math.max(size.x, size.z, 8);
  camera.far = longest * 30;
  controls.minDistance = 1.6;
  controls.maxDistance = longest * 6;
  Object.assign(key.shadow.camera, { left: -longest, right: longest, top: longest, bottom: -longest, near: 0.5, far: longest * 5 });
  key.position.set(-longest * 0.35, longest, longest * 0.55);
  key.shadow.camera.updateProjectionMatrix();

  function updateSelection() {
    const record = componentRecords.get(selectedId);
    selection.visible = !!record && visibleInTree(record.group);
    if (selection.visible) {
      record.group.updateWorldMatrix(true, true);
      selection.box.setFromObject(record.group).expandByScalar(0.11);
    }
  }
  function updateLeadHighlight() {
    for (const wire of wires) {
      const attached = selectedId && (wire.connection.fromOwner === selectedId || wire.connection.toOwner === selectedId);
      wire.object.material = attached ? wire.highlightMaterial
        : selectedId ? wire.dimmedMaterial : wire.baseMaterial;
    }
  }
  function updateLabelVisibility() {
    for (const item of labels) {
      const record = componentRecords.get(item.owner.id);
      item.sprite.visible = !!record && layers[record.layer].visible;
      item.sprite.material.opacity = selectedId && item.owner.id !== selectedId ? 0.65 : 1;
    }
  }
  function render() {
    frame = 0;
    if (disposed || contextLost || !container.clientWidth || !container.clientHeight) return;
    try {
      if (explodeDirty) updateExplode();
      updateSelection();
      renderer.render(scene, camera);
    } catch (error) {
      contextLost = true;
      onError(error instanceof Error ? error : new Error(String(error)));
    }
  }
  function requestRender() {
    if (!disposed && !contextLost && !frame) frame = requestAnimationFrame(render);
  }
  controls.addEventListener('change', requestRender);

  function resize() {
    if (disposed) return;
    const width = container.clientWidth;
    const height = container.clientHeight;
    if (!width || !height) return;
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    renderer.setSize(width, height, false);
    const nextAspect = width / height;
    // Retain the user's orbit and horizontal framing when the viewport narrows.
    // This also prevents a desktop overview from clipping on phone rotation.
    if (camera.aspect > 0 && camera.position.lengthSq() > 0 && nextAspect !== camera.aspect) {
      const offset = camera.position.clone().sub(controls.target);
      offset.multiplyScalar(camera.aspect / nextAspect);
      const distance = THREE.MathUtils.clamp(offset.length(), controls.minDistance, controls.maxDistance);
      camera.position.copy(controls.target).add(offset.setLength(distance));
      controls.update();
    }
    camera.aspect = nextAspect;
    camera.updateProjectionMatrix();
    // Screen-sized labels remain readable at the fitted overview; changing
    // camera distance must not shrink reference designators to a few pixels.
    const labelHeight = 24 * 2 * Math.tan(THREE.MathUtils.degToRad(camera.fov / 2)) / height;
    for (const label of labels) label.sprite.scale.set(labelHeight * label.aspect, labelHeight, 1);
    requestRender();
  }
  function setView(view = 'perspective') {
    if (disposed) return;
    resize();
    const halfFov = THREE.MathUtils.degToRad(camera.fov / 2);
    const widthDistance = size.x / (2 * Math.tan(halfFov) * Math.max(camera.aspect, 0.3));
    const depthDistance = size.z / (2 * Math.tan(halfFov));
    const distance = Math.max(widthDistance, depthDistance, longest * 0.85) * 1.18;
    controls.target.copy(focus);
    controls.target.y += explode * 1.3;
    const direction = view === 'top' ? new THREE.Vector3(0, 1, 0.001)
      : view === 'bottom' ? new THREE.Vector3(0, -1, 0.001)
        : new THREE.Vector3(0.1, 0.9, 0.96).normalize();
    camera.position.copy(controls.target).addScaledVector(direction, distance);
    camera.up.set(0, 1, 0);
    controls.update();
    requestRender();
  }
  function updateExplode() {
    explodeDirty = false;
    wireRoutes = wireRouting.route(ownerLift);
    for (const [id, record] of componentRecords) record.group.position.y = ownerLift(id);
    for (const item of labels) item.sprite.position.y = item.baseHeight + ownerLift(item.owner.id);
    for (const wire of wires) {
      const geometry = buildWireGeometry(wire.connection);
      if (!geometry) continue;
      ownedGeometries.delete(wire.object.geometry);
      wire.object.geometry.dispose();
      wire.object.geometry = trackGeometry(geometry);
    }
  }
  function setExplode(value) {
    if (disposed) return;
    const next = THREE.MathUtils.clamp(Number(value) || 0, 0, 1);
    if (next === explode) return;
    explode = next;
    explodeDirty = true;
    requestRender();
  }
  function selectComponent(id) {
    if (disposed) return;
    const record = componentRecords.get(id);
    selectedId = record ? id : null;
    updateLeadHighlight();
    updateLabelVisibility();
    requestRender();
    onSelect(record?.component || null);
  }
  function setLayer(name, visible) {
    if (disposed || !layers[name]) return;
    layers[name].visible = !!visible;
    const selected = componentRecords.get(selectedId);
    if (!visible && selected?.layer === name) selectComponent(null);
    updateLabelVisibility();
    requestRender();
  }
  const raycaster = new THREE.Raycaster();
  const pointer = new THREE.Vector2();
  function hitAt(event) {
    const rect = canvas.getBoundingClientRect();
    pointer.set((event.clientX - rect.left) / rect.width * 2 - 1, -(event.clientY - rect.top) / rect.height * 2 + 1);
    scene.updateMatrixWorld(true);
    raycaster.setFromCamera(pointer, camera);
    const targets = pickables.filter(visibleInTree);
    // A visible board occludes parts behind it, including from the underside.
    if (visibleInTree(board)) targets.push(board);
    const hits = raycaster.intersectObjects(targets, false);
    return hits[0]?.object.userData.componentId || null;
  }
  function pointerDown(event) {
    if (!event.isPrimary || event.button !== 0) { pointerStart = null; return; }
    pointerStart = { x: event.clientX, y: event.clientY, id: event.pointerId };
  }
  function pointerMove(event) {
    if (event.pointerType === 'touch' || event.buttons) return;
    const id = hitAt(event);
    if (id !== hoveredId) {
      hoveredId = id;
      canvas.style.cursor = id ? 'pointer' : 'grab';
    }
  }
  function pointerUp(event) {
    if (!pointerStart || event.pointerId !== pointerStart.id) return;
    const moved = Math.hypot(event.clientX - pointerStart.x, event.clientY - pointerStart.y);
    pointerStart = null;
    if (moved < 6) selectComponent(hitAt(event));
  }
  function pointerCancel() { pointerStart = null; }
  function contextLoss(event) {
    event.preventDefault();
    contextLost = true;
    if (frame) cancelAnimationFrame(frame);
    frame = 0;
    onError(new Error('The 3D graphics context was lost. Reload the viewer to continue.'));
  }
  canvas.addEventListener('pointerdown', pointerDown);
  canvas.addEventListener('pointermove', pointerMove);
  canvas.addEventListener('pointerup', pointerUp);
  canvas.addEventListener('pointercancel', pointerCancel);
  canvas.addEventListener('webglcontextlost', contextLoss);
  const resizeObserver = new ResizeObserver(resize);
  resizeObserver.observe(container);
  window.addEventListener('resize', resize);
  resize();
  setView('perspective');

  return {
    canvas,
    setLayer, setExplode, selectComponent, setView, resize,
    rotate(azimuthRadians, elevationRadians) {
      if (disposed) return;
      controls.rotateLeft(Number(azimuthRadians) || 0);
      controls.rotateUp(Number(elevationRadians) || 0);
      controls.update();
      requestRender();
    },
    zoom(factor) {
      if (disposed || !(Number(factor) > 0)) return;
      // A factor above one moves closer; below one moves farther away.
      controls.dollyIn(1 / THREE.MathUtils.clamp(Number(factor), 0.2, 5));
      controls.update();
      requestRender();
    },
    reset() {
      if (disposed) return;
      setExplode(0);
      selectComponent(null);
      setView('perspective');
    },
    dispose() {
      if (disposed) return;
      disposed = true;
      if (frame) cancelAnimationFrame(frame);
      resizeObserver.disconnect();
      window.removeEventListener('resize', resize);
      controls.removeEventListener('change', requestRender);
      controls.dispose();
      canvas.removeEventListener('pointerdown', pointerDown);
      canvas.removeEventListener('pointermove', pointerMove);
      canvas.removeEventListener('pointerup', pointerUp);
      canvas.removeEventListener('pointercancel', pointerCancel);
      canvas.removeEventListener('webglcontextlost', contextLoss);
      for (const geometry of ownedGeometries) geometry.dispose();
      for (const mat of materialCache.values()) mat.dispose();
      for (const texture of ownedTextures) texture.dispose();
      for (const label of labels) label.mat.dispose();
      selection.geometry.dispose();
      selection.material.dispose();
      key.shadow.dispose();
      renderer.dispose();
      renderer.forceContextLoss();
      canvas.remove();
      scene.clear();
      for (const group of Object.values(layers)) group.clear();
      componentRecords.clear();
      materialCache.clear();
      ownedTextures.clear();
      ownedGeometries.clear();
      pickables.length = 0;
      labels.length = 0;
      wires.length = 0;
    },
  };
}
