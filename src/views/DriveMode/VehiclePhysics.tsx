import React, { useRef } from 'react';
import { useFrame, useThree } from '@react-three/fiber';
import * as THREE from 'three';
import { BusModel } from './BusModel';
import { getTerrainHeight, ZONES } from './constants';
import type { ControlsState } from './useKeyboardControls';

interface VehiclePhysicsProps {
  controls: ControlsState;
  onZoneChange: (zoneId: string | null) => void;
  onSpeedChange?: (speedKmh: number) => void;
  autoDriveTarget: [number, number, number] | null;
  onAutoDriveArrived: () => void;
}

export const VehiclePhysics: React.FC<VehiclePhysicsProps> = ({
  controls,
  onZoneChange,
  onSpeedChange,
  autoDriveTarget,
  onAutoDriveArrived
}) => {
  const busGroupRef = useRef<THREE.Group>(null);
  const { camera } = useThree();

  // Physics state
  const state = useRef({
    position: new THREE.Vector3(0, 0, -30),
    rotationY: 0, // Facing along Z
    speed: 0,
    maxForwardSpeed: 16.0,
    maxReverseSpeed: -6.0,
    acceleration: 20.0,
    braking: 28.0,
    drag: 7.0,
    turnRate: 1.85,
    cameraOffset: new THREE.Vector3(0, 5.0, -11.0),
    cameraLookOffset: new THREE.Vector3(0, 1.4, 4.0),
    currentZone: null as string | null
  });

  // Reusable vectors for performance
  const tempVec = useRef(new THREE.Vector3());
  const cameraTarget = useRef(new THREE.Vector3());
  const cameraPos = useRef(new THREE.Vector3());

  useFrame((_, delta) => {
    if (!busGroupRef.current) return;

    // Clamp delta to prevent huge jumps on tab switch
    const dt = Math.min(delta, 0.1);
    const p = state.current;

    // Handle Auto-Drive Mode
    if (autoDriveTarget) {
      const targetVec = tempVec.current.set(autoDriveTarget[0], 0, autoDriveTarget[2]);
      const currentPos2D = new THREE.Vector2(p.position.x, p.position.z);
      const targetPos2D = new THREE.Vector2(targetVec.x, targetVec.z);
      const distance = currentPos2D.distanceTo(targetPos2D);

      if (distance < 3.0) {
        // Arrived at target
        p.speed = THREE.MathUtils.lerp(p.speed, 0, dt * 6.0);
        onAutoDriveArrived();
      } else {
        // Calculate desired heading towards target
        const dx = targetPos2D.x - currentPos2D.x;
        const dy = targetPos2D.y - currentPos2D.y;
        // In 3D space: forward is +sin(rotY) on X, +cos(rotY) on Z
        const targetAngle = Math.atan2(dx, dy);

        // Normalize angle difference between -PI and PI
        let angleDiff = targetAngle - p.rotationY;
        while (angleDiff > Math.PI) angleDiff -= Math.PI * 2;
        while (angleDiff < -Math.PI) angleDiff += Math.PI * 2;

        p.rotationY += Math.sign(angleDiff) * Math.min(Math.abs(angleDiff), p.turnRate * 1.5 * dt);

        // Cruise speed
        const desiredSpeed = Math.min(12.0, distance * 1.5);
        p.speed = THREE.MathUtils.lerp(p.speed, desiredSpeed, dt * 3.0);
      }
    } else {
      // Manual Driving Physics
      // 1. Acceleration & Braking
      if (controls.forward) {
        p.speed += p.acceleration * dt;
        if (p.speed > p.maxForwardSpeed) p.speed = p.maxForwardSpeed;
      } else if (controls.backward) {
        if (p.speed > 0.5) {
          p.speed -= p.braking * dt;
        } else {
          p.speed -= p.acceleration * dt;
          if (p.speed < p.maxReverseSpeed) p.speed = p.maxReverseSpeed;
        }
      } else {
        // Natural friction / drag
        if (p.speed > 0) {
          p.speed = Math.max(0, p.speed - p.drag * dt);
        } else if (p.speed < 0) {
          p.speed = Math.min(0, p.speed + p.drag * dt);
        }
      }

      // 2. Steering (scales with speed and direction)
      if (Math.abs(p.speed) > 0.1) {
        const speedFactor = Math.min(1, Math.abs(p.speed) / 5.0);
        const directionSign = p.speed >= 0 ? 1 : -1;

        if (controls.left) {
          p.rotationY += p.turnRate * dt * speedFactor * directionSign;
        }
        if (controls.right) {
          p.rotationY -= p.turnRate * dt * speedFactor * directionSign;
        }
      }
    }

    // 3. Move bus forward along heading
    const moveX = Math.sin(p.rotationY) * p.speed * dt;
    const moveZ = Math.cos(p.rotationY) * p.speed * dt;

    p.position.x += moveX;
    p.position.z += moveZ;

    // Bounds clamp (stay within 160 units of center)
    const distanceFromCenter = Math.sqrt(p.position.x * p.position.x + p.position.z * p.position.z);
    if (distanceFromCenter > 160) {
      const angle = Math.atan2(p.position.z, p.position.x);
      p.position.x = Math.cos(angle) * 160;
      p.position.z = Math.sin(angle) * 160;
      p.speed = 0;
    }

    // 4. Ground clamping: bus stays on terrain height
    const groundHeight = getTerrainHeight(p.position.x, p.position.z);
    p.position.y = groundHeight;

    // Update 3D bus mesh transform
    busGroupRef.current.position.copy(p.position);
    busGroupRef.current.rotation.y = p.rotationY;

    // 5. Chase Camera
    // Compute desired camera position behind the bus based on heading
    const behindX = p.position.x - Math.sin(p.rotationY) * 10.5;
    const behindZ = p.position.z - Math.cos(p.rotationY) * 10.5;
    const behindY = Math.max(groundHeight + 4.5, getTerrainHeight(behindX, behindZ) + 4.0);

    cameraPos.current.set(behindX, behindY, behindZ);
    // Smooth lerp for camera
    camera.position.lerp(cameraPos.current, Math.min(1, dt * 4.5));

    // Camera look target (front of bus)
    const lookX = p.position.x + Math.sin(p.rotationY) * 4.0;
    const lookZ = p.position.z + Math.cos(p.rotationY) * 4.0;
    const lookY = p.position.y + 1.2;
    cameraTarget.current.set(lookX, lookY, lookZ);
    camera.lookAt(cameraTarget.current);

    // 6. Zone Proximity Detection
    let insideZoneId: string | null = null;
    for (const zone of ZONES) {
      const dx = p.position.x - zone.position[0];
      const dz = p.position.z - zone.position[2];
      const dist = Math.sqrt(dx * dx + dz * dz);

      if (dist <= zone.radius) {
        insideZoneId = zone.id;
        break;
      }
    }

    if (insideZoneId !== p.currentZone) {
      p.currentZone = insideZoneId;
      onZoneChange(insideZoneId);
    }

    // Speedometer output (approx km/h)
    if (onSpeedChange) {
      onSpeedChange(Math.round(Math.abs(p.speed) * 3.6));
    }
  });

  return (
    <group ref={busGroupRef}>
      <BusModel headlightsOn={true} />
    </group>
  );
};
