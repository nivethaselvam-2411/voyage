import React, { useMemo, useRef, useLayoutEffect } from 'react';
import * as THREE from 'three';
import { getTerrainHeight } from './constants';

export const Terrain: React.FC = () => {
  // 1. Procedural Low-Poly Terrain Mesh
  const { geometry } = useMemo(() => {
    const size = 380;
    const segments = 64;
    const geom = new THREE.PlaneGeometry(size, size, segments, segments);
    geom.rotateX(-Math.PI / 2);

    const pos = geom.attributes.position;
    const colArray = new Float32Array(pos.count * 3);

    // Color palette: soft dry grassland / pale pasture matching sky #E8EFF5
    const baseGreen = new THREE.Color('#9EB3A8');
    const hillGreen = new THREE.Color('#8DA396');
    const pathSand = new THREE.Color('#D8DEC8');

    for (let i = 0; i < pos.count; i++) {
      const x = pos.getX(i);
      const z = pos.getZ(i);
      const y = getTerrainHeight(x, z);
      pos.setY(i, y);

      // Color based on height and zone proximity
      const dCenter = Math.sqrt(x * x + z * z);
      const factor = Math.min(1, y / 5.0);
      const c = new THREE.Color().copy(baseGreen).lerp(hillGreen, factor);
      if (dCenter < 30) {
        c.lerp(pathSand, 0.35);
      }

      colArray[i * 3] = c.r;
      colArray[i * 3 + 1] = c.g;
      colArray[i * 3 + 2] = c.b;
    }

    geom.setAttribute('color', new THREE.BufferAttribute(colArray, 3));
    geom.computeVertexNormals();

    return { geometry: geom, colors: colArray };
  }, []);

  // 2. Winding Road Spline Curve
  const { roadGeometry, lineGeometry } = useMemo(() => {
    const points = [
      new THREE.Vector3(0, 0.05, -55),
      new THREE.Vector3(0, 0.05, -45), // Control room
      new THREE.Vector3(25, 0.05, -25),
      new THREE.Vector3(45, 0.05, -5),
      new THREE.Vector3(55, 0.05, 10), // Depot yard
      new THREE.Vector3(40, 0.05, 35),
      new THREE.Vector3(15, 0.05, 65), // Scorecard
      new THREE.Vector3(-20, 0.05, 55),
      new THREE.Vector3(-50, 0.05, 35), // Fleet
      new THREE.Vector3(-40, 0.05, 5),
      new THREE.Vector3(-25, 0.05, -20),
      new THREE.Vector3(0, 0.05, -45) // Loop back
    ];

    const curve = new THREE.CatmullRomCurve3(points, true);
    const divisions = 240;
    const curvePoints = curve.getPoints(divisions);

    // Create a flat ribbon geometry for the asphalt road
    const roadWidth = 6.0;
    const roadPositions: number[] = [];
    const roadIndices: number[] = [];

    for (let i = 0; i <= divisions; i++) {
      const pt = curvePoints[i % divisions];
      const nextPt = curvePoints[(i + 1) % divisions];
      const dir = new THREE.Vector3().subVectors(nextPt, pt).normalize();
      const normal = new THREE.Vector3(-dir.z, 0, dir.x).normalize();

      const y = getTerrainHeight(pt.x, pt.z) + 0.06;

      const pLeft = new THREE.Vector3().copy(pt).addScaledVector(normal, roadWidth / 2);
      pLeft.y = y;
      const pRight = new THREE.Vector3().copy(pt).addScaledVector(normal, -roadWidth / 2);
      pRight.y = y;

      roadPositions.push(pLeft.x, pLeft.y, pLeft.z);
      roadPositions.push(pRight.x, pRight.y, pRight.z);

      if (i < divisions) {
        const base = i * 2;
        roadIndices.push(base, base + 1, base + 2);
        roadIndices.push(base + 1, base + 3, base + 2);
      }
    }

    const roadGeom = new THREE.BufferGeometry();
    roadGeom.setAttribute('position', new THREE.Float32BufferAttribute(roadPositions, 3));
    roadGeom.setIndex(roadIndices);
    roadGeom.computeVertexNormals();

    // Dashed center line strips
    const linePositions: number[] = [];
    const lineIndices: number[] = [];
    let lineIdx = 0;

    for (let i = 0; i < divisions; i += 2) {
      const pt = curvePoints[i];
      const nextPt = curvePoints[(i + 1) % divisions];
      const mid = new THREE.Vector3().addVectors(pt, nextPt).multiplyScalar(0.5);
      const dir = new THREE.Vector3().subVectors(nextPt, pt).normalize();
      const normal = new THREE.Vector3(-dir.z, 0, dir.x).normalize();

      const y = getTerrainHeight(mid.x, mid.z) + 0.09;
      const len = 1.6;
      const w = 0.22;

      const p1 = new THREE.Vector3().copy(mid).addScaledVector(dir, -len / 2).addScaledVector(normal, -w / 2);
      p1.y = y;
      const p2 = new THREE.Vector3().copy(mid).addScaledVector(dir, -len / 2).addScaledVector(normal, w / 2);
      p2.y = y;
      const p3 = new THREE.Vector3().copy(mid).addScaledVector(dir, len / 2).addScaledVector(normal, -w / 2);
      p3.y = y;
      const p4 = new THREE.Vector3().copy(mid).addScaledVector(dir, len / 2).addScaledVector(normal, w / 2);
      p4.y = y;

      const b = lineIdx * 4;
      linePositions.push(p1.x, p1.y, p1.z, p2.x, p2.y, p2.z, p3.x, p3.y, p3.z, p4.x, p4.y, p4.z);
      lineIndices.push(b, b + 1, b + 2, b + 1, b + 3, b + 2);
      lineIdx++;
    }

    const lineGeom = new THREE.BufferGeometry();
    lineGeom.setAttribute('position', new THREE.Float32BufferAttribute(linePositions, 3));
    lineGeom.setIndex(lineIndices);
    lineGeom.computeVertexNormals();

    return { roadGeometry: roadGeom, lineGeometry: lineGeom };
  }, []);

  // 3. Instanced Trees (cones + cylinders)
  const treeCount = 90;
  const treeFoliageRef = useRef<THREE.InstancedMesh>(null);
  const treeTrunkRef = useRef<THREE.InstancedMesh>(null);

  useLayoutEffect(() => {
    if (!treeFoliageRef.current || !treeTrunkRef.current) return;

    const dummy = new THREE.Object3D();
    const pseudoRandom = (i: number) => ((Math.sin(i * 12.9898 + 78.233) * 43758.5453) % 1 + 1) % 1;

    let placed = 0;
    for (let i = 0; i < 300 && placed < treeCount; i++) {
      const angle = pseudoRandom(i * 3 + 1) * Math.PI * 2;
      const radius = 25 + pseudoRandom(i * 3 + 2) * 110;
      const x = Math.cos(angle) * radius;
      const z = Math.sin(angle) * radius;

      // Keep trees off road & zones
      const dControl = Math.sqrt(x * x + (z + 45) * (z + 45));
      const dDepot = Math.sqrt((x - 55) * (x - 55) + (z - 10) * (z - 10));
      const dFleet = Math.sqrt((x + 50) * (x + 50) + (z - 35) * (z - 35));
      const dScorecard = Math.sqrt((x - 15) * (x - 15) + (z - 65) * (z - 65));

      if (dControl < 12 || dDepot < 12 || dFleet < 12 || dScorecard < 12) continue;

      const y = getTerrainHeight(x, z);
      const scale = 0.8 + pseudoRandom(i * 3 + 3) * 0.6;

      // Trunk
      dummy.position.set(x, y + 0.6 * scale, z);
      dummy.scale.set(scale, scale, scale);
      dummy.rotation.set(0, pseudoRandom(i * 5) * Math.PI, 0);
      dummy.updateMatrix();
      treeTrunkRef.current.setMatrixAt(placed, dummy.matrix);

      // Foliage
      dummy.position.set(x, y + 2.2 * scale, z);
      dummy.scale.set(scale, scale, scale);
      dummy.updateMatrix();
      treeFoliageRef.current.setMatrixAt(placed, dummy.matrix);

      placed++;
    }

    treeFoliageRef.current.instanceMatrix.needsUpdate = true;
    treeTrunkRef.current.instanceMatrix.needsUpdate = true;
  }, [treeCount]);

  // 4. Instanced Modern Flat-Roof Houses
  const houseCount = 28;
  const houseRef = useRef<THREE.InstancedMesh>(null);

  useLayoutEffect(() => {
    if (!houseRef.current) return;

    const dummy = new THREE.Object3D();
    const houseCoords = [
      // Near Control Room cluster
      { x: -18, z: -55, ry: 0.3 },
      { x: 18, z: -58, ry: -0.4 },
      { x: -25, z: -40, ry: 0.8 },
      // Near Depot Yard cluster
      { x: 72, z: 5, ry: 0.1 },
      { x: 68, z: 22, ry: -0.6 },
      { x: 45, z: -18, ry: 0.5 },
      // Near Fleet cluster
      { x: -68, z: 28, ry: -0.2 },
      { x: -62, z: 46, ry: 0.4 },
      { x: -42, z: 50, ry: -0.7 },
      // Near Scorecard cluster
      { x: 30, z: 75, ry: 0.2 },
      { x: 2, z: 78, ry: -0.3 },
      { x: -8, z: 62, ry: 0.5 },
      // Suburban perimeter clusters
      { x: 35, z: -42, ry: 0.9 },
      { x: -48, z: -20, ry: -0.5 },
      { x: 50, z: 50, ry: 0.4 },
      { x: -30, z: -62, ry: 0.1 },
      { x: 80, z: -10, ry: -0.3 },
      { x: -75, z: 12, ry: 0.6 },
      { x: 42, z: 72, ry: -0.4 },
      { x: -55, z: 60, ry: 0.8 },
      { x: 60, z: -35, ry: 0.2 },
      { x: -65, z: -38, ry: -0.6 },
      { x: 10, z: -70, ry: 0.3 },
      { x: -10, z: -72, ry: -0.2 },
      { x: 75, z: 32, ry: 0.7 },
      { x: -72, z: -15, ry: -0.4 },
      { x: 25, z: 85, ry: 0.5 },
      { x: -25, z: 75, ry: -0.8 }
    ];

    houseCoords.forEach((coord, i) => {
      const y = getTerrainHeight(coord.x, coord.z);
      dummy.position.set(coord.x, y + 1.4, coord.z);
      dummy.rotation.set(0, coord.ry, 0);
      dummy.scale.set(3.2, 2.8, 3.8);
      dummy.updateMatrix();
      houseRef.current!.setMatrixAt(i, dummy.matrix);
    });

    houseRef.current.instanceMatrix.needsUpdate = true;
  }, []);

  return (
    <group>
      {/* Terrain Base */}
      <mesh geometry={geometry}>
        <meshLambertMaterial vertexColors flatShading />
      </mesh>

      {/* Winding Road Surface */}
      <mesh geometry={roadGeometry}>
        <meshLambertMaterial color="#3C444D" polygonOffset polygonOffsetFactor={-1} />
      </mesh>

      {/* Road Dashed Center Line */}
      <mesh geometry={lineGeometry}>
        <meshBasicMaterial color="#E8EEF5" polygonOffset polygonOffsetFactor={-2} />
      </mesh>

      {/* Trees: Trunks */}
      <instancedMesh ref={treeTrunkRef} args={[undefined, undefined, treeCount]}>
        <cylinderGeometry args={[0.15, 0.22, 1.2, 5]} />
        <meshLambertMaterial color="#544339" flatShading />
      </instancedMesh>

      {/* Trees: Foliage (Low-poly Cones) */}
      <instancedMesh ref={treeFoliageRef} args={[undefined, undefined, treeCount]}>
        <coneGeometry args={[1.3, 2.4, 5]} />
        <meshLambertMaterial color="#4A6E4F" flatShading />
      </instancedMesh>

      {/* Modern Flat-Roof Houses */}
      <instancedMesh ref={houseRef} args={[undefined, undefined, houseCount]}>
        <boxGeometry args={[1, 1, 1]} />
        <meshLambertMaterial color="#F4ECD8" flatShading />
      </instancedMesh>
    </group>
  );
};
