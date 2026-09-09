#!/usr/bin/env node
// Check the rendered centerline paths independently of the routing planner's
// crossing list. No browser, WebGL, screenshot or private scene state is needed.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import { fileURLToPath } from 'node:url';
import * as THREE from 'three';
import { prepareWireRouting, buildWireTubeGeometry } from '../src/lib/layout3d-scene.js';

const input = process.argv[2] || fileURLToPath(new URL('../public/layouts/5f1-3d.json', import.meta.url));
const data = JSON.parse(fs.readFileSync(input, 'utf8'));
const EPS = 1e-5;
const minimumGap = 0.08; // Greater than the combined conductor radii (<=0.066).
const distance = (a, b) => Math.hypot(a[0] - b[0], a[1] - b[1]);
const near = (a, b) => distance(a, b) < EPS;
const endpoint = (connection, p) => near(connection.points[0], p) || near(connection.points.at(-1), p);
const close = (actual, expected, message) => assert.ok(Math.abs(actual - expected) < EPS, `${message}: ${actual} != ${expected}`);

function segmentFraction(a, b, p) {
  const squared = (b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2;
  if (squared < EPS ** 2) return near(a, p) ? 0 : null;
  const t = ((p[0] - a[0]) * (b[0] - a[0]) + (p[1] - a[1]) * (b[1] - a[1])) / squared;
  if (t < -EPS || t > 1 + EPS) return null;
  const projected = [a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])];
  return near(projected, p) ? Math.max(0, Math.min(1, t)) : null;
}

// Intersect implicit line equations, then check finite-segment containment.
function intersection(a, b, c, d) {
  const a1 = a[1] - b[1], b1 = b[0] - a[0], c1 = a[0] * b[1] - b[0] * a[1];
  const a2 = c[1] - d[1], b2 = d[0] - c[0], c2 = c[0] * d[1] - d[0] * c[1];
  const determinant = a1 * b2 - a2 * b1;
  if (Math.abs(determinant) < 1e-8) return null;
  const p = [(b1 * c2 - b2 * c1) / determinant, (c1 * a2 - c2 * a1) / determinant];
  return segmentFraction(a, b, p) !== null && segmentFraction(c, d, p) !== null ? p : null;
}

function heightsAt(path, p) {
  const heights = [];
  for (let i = 1; i < path.length; i++) {
    const t = segmentFraction(path[i - 1].point, path[i].point, p);
    if (t !== null) heights.push(path[i - 1].height * (1 - t) + path[i].height * t);
  }
  assert.ok(heights.length, `Rendered route no longer passes source point ${p}`);
  return heights;
}

function intendedJunction(a, b, p) {
  if (endpoint(a, p) && endpoint(b, p)) return true;
  for (const [bus, wire] of [[a, b], [b, a]]) {
    if (bus.kind !== 'bus') continue;
    if (near(wire.points[0], p) && wire.fromOwner == null) return true;
    if (near(wire.points.at(-1), p) && wire.toOwner == null) return true;
  }
  return false;
}

function crossingPoints(connections) {
  const found = new Map();
  for (let i = 0; i < connections.length; i++) {
    const a = connections[i];
    for (let j = i + 1; j < connections.length; j++) {
      const b = connections[j];
      for (let ai = 1; ai < a.points.length; ai++) for (let bi = 1; bi < b.points.length; bi++) {
        const p = intersection(a.points[ai - 1], a.points[ai], b.points[bi - 1], b.points[bi]);
        if (!p || intendedJunction(a, b, p)) continue;
        found.set(`${a.id}|${b.id}|${p.map(n => n.toFixed(5))}`, { a, b, p });
      }
    }
  }
  return [...found.values()];
}

function check(connections, liftForOwner, label) {
  const original = JSON.stringify(connections);
  const routing = prepareWireRouting(connections).route(liftForOwner);
  const crossings = crossingPoints(connections);
  let smallest = Infinity;
  let vertices = 0;
  let triangles = 0;
  for (const connection of connections) {
    const path = routing.paths.get(connection.id);
    assert.ok(path?.length >= 2, `${label}: missing route ${connection.id}`);
    assert.ok(near(path[0].point, connection.points[0]), `${connection.id}: moved source endpoint`);
    assert.ok(near(path.at(-1).point, connection.points.at(-1)), `${connection.id}: moved target endpoint`);
    close(path[0].height, 0.19 + liftForOwner(connection.fromOwner), `${connection.id}: source height`);
    close(path.at(-1).height, 0.19 + liftForOwner(connection.toOwner), `${connection.id}: target height`);
    for (const sample of path) {
      assert.ok(Number.isFinite(sample.height), `${connection.id}: non-finite height`);
      assert.ok(connection.points.slice(1).some((p, i) => segmentFraction(connection.points[i], p, sample.point) !== null),
        `${connection.id}: moved x/y off source path`);
    }
    for (const p of connection.points) heightsAt(path, p); // Every original bend survives.
    const points = path.map(sample => new THREE.Vector3(sample.point[0] / 40, sample.height, sample.point[1] / 40));
    const geometry = buildWireTubeGeometry(points, connection.kind === 'bus' ? 0.033 : 0.025);
    assert.ok(geometry, `${connection.id}: missing tube geometry`);
    const positions = geometry.getAttribute('position');
    vertices += positions.count;
    triangles += geometry.index.count / 3;
    const centers = [];
    for (let ring = 0; ring < positions.count / 7; ring++) {
      const center = new THREE.Vector3();
      // Six sides plus a repeated seam vertex: average the six unique corners.
      for (let side = 0; side < 6; side++) center.add(new THREE.Vector3().fromBufferAttribute(positions, ring * 7 + side));
      center.multiplyScalar(1 / 6);
      assert.ok(Number.isFinite(center.lengthSq()), `${connection.id}: non-finite tube ring`);
      centers.push(center);
    }
    assert.ok(centers[0].distanceTo(points[0]) < EPS, `${connection.id}: mesh source detached`);
    assert.ok(centers.at(-1).distanceTo(points.at(-1)) < EPS, `${connection.id}: mesh target detached`);
    // Every planned bridge apex and source bend must be an actual tube ring;
    // arc-length resampling previously could skip short bridge details.
    for (const p of points) assert.ok(centers.some(center => center.distanceTo(p) < EPS * 2), `${connection.id}: mesh skipped a routing knot`);
    geometry.dispose();
  }
  for (const { a, b, p } of crossings) {
    const ah = heightsAt(routing.paths.get(a.id), p), bh = heightsAt(routing.paths.get(b.id), p);
    const gap = Math.min(...ah.flatMap(ha => bh.map(hb => Math.abs(ha - hb))));
    smallest = Math.min(smallest, gap);
    assert.ok(gap >= minimumGap, `${label}: ${a.id} intersects ${b.id} at ${p}; gap=${gap}`);
  }
  // Ground-bus endpoints deliberately remain touching at every explosion state.
  for (const bus of connections.filter(c => c.kind === 'bus')) {
    for (const wire of connections.filter(c => c.kind !== 'bus')) {
      for (const [index, owner] of [[0, wire.fromOwner], [wire.points.length - 1, wire.toOwner]]) {
        const p = wire.points[index];
        if (owner != null || !bus.points.slice(1).some((b, i) => segmentFraction(bus.points[i], b, p) !== null)) continue;
        const endHeight = index === 0 ? routing.paths.get(wire.id)[0].height : routing.paths.get(wire.id).at(-1).height;
        assert.ok(heightsAt(routing.paths.get(bus.id), p).some(height => Math.abs(height - endHeight) < EPS), `${wire.id}: detached ground junction`);
      }
    }
  }
  assert.ok(triangles <= 100000, `${label}: wire triangle budget exceeded (${triangles})`);
  assert.equal(JSON.stringify(connections), original, `${label}: mutated source data`);
  console.log(`${label}: ${connections.length} routes, ${crossings.length} independently found crossings, minimum gap ${smallest.toFixed(3)}; ${vertices} vertices/${triangles} triangles; endpoints and bus junctions intact`);
  return routing;
}

const owners = new Map(data.components.map(c => [c.id, c.mount]));
for (const amount of [0, 0.5, 1]) {
  const routes = check(data.connections, id => owners.has(id) ? amount * (owners.get(id) === 'board' ? 1.8 : 3.25) : 0, `5F1 explode ${amount}`);
  // The original reported failure: distinct PT secondary leads must not join.
  const red1 = data.connections.find(c => c.from === 'PT.red1' && c.to === 'V3.pin4');
  const red2 = data.connections.find(c => c.from === 'PT.red2' && c.to === 'V3.pin6');
  assert.ok(red1 && red2, 'Missing PT regression leads');
  const ptCross = crossingPoints([red1, red2]).find(({ p }) => distance(p, [210.735, 306.549]) < 0.01);
  assert.ok(ptCross, 'Missing known PT crossing');
  const gap = Math.abs(heightsAt(routes.paths.get(red1.id), ptCross.p)[0] - heightsAt(routes.paths.get(red2.id), ptCross.p)[0]);
  assert.ok(gap >= minimumGap, `PT red leads touch at explode=${amount}`);
}

// A heater-category path must receive the same treatment, even when the pilot
// export omits its unverified heater layer. Collinear overlap is sampled too.
const fixtures = [
  { id: 'bus', kind: 'bus', points: [[0, 0], [40, 0]], fromOwner: null, toOwner: null },
  { id: 'ground', kind: 'wire', points: [[10, -20], [10, 0]], fromOwner: 'raised', toOwner: null },
  { id: 'crossing', kind: 'wire', points: [[20, -20], [20, 20]], fromOwner: 'raised', toOwner: 'raised' },
  { id: 'heater', kind: 'heater', points: [[0, 10], [40, 10]], fromOwner: 'base', toOwner: 'base' },
  { id: 'overlap', kind: 'wire', points: [[4, 10], [36, 10]], fromOwner: 'base', toOwner: 'base' },
];
for (const amount of [0, 0.5, 1]) {
  const routes = check(fixtures, id => id === 'raised' ? amount * 3.25 : 0, `fixture explode ${amount}`);
  for (let x = 4.5; x < 36; x += 0.5) {
    const first = heightsAt(routes.paths.get('heater'), [x, 10])[0];
    const second = heightsAt(routes.paths.get('overlap'), [x, 10])[0];
    assert.ok(Math.abs(first - second) >= minimumGap, `Overlapping paths touch at ${x}, explode=${amount}`);
  }
}
console.log('3D geometry regression passed.');
