import React from 'react';
import { Canvas } from '@react-three/fiber';
import { Terrain } from './Terrain';
import { ZoneRings } from './ZoneRings';
import { VehiclePhysics } from './VehiclePhysics';
import type { ControlsState } from './useKeyboardControls';

interface DriveSceneProps {
  controls: ControlsState;
  onZoneChange: (zoneId: string | null) => void;
  onSpeedChange: (speedKmh: number) => void;
  alertCount: number;
  currentZoneId: string | null;
  autoDriveTarget: [number, number, number] | null;
  onAutoDriveArrived: () => void;
}

export const DriveScene: React.FC<DriveSceneProps> = ({
  controls,
  onZoneChange,
  onSpeedChange,
  alertCount,
  currentZoneId,
  autoDriveTarget,
  onAutoDriveArrived
}) => {
  return (
    <Canvas
      dpr={[1, 1.5]} // capped at 1.5 for performance
      gl={{ antialias: true, powerPreference: 'high-performance' }}
      camera={{ position: [0, 8, -42], fov: 50, near: 0.1, far: 350 }}
      style={{
        position: 'absolute',
        top: 0,
        left: 0,
        width: '100%',
        height: '100%',
        backgroundColor: '#E8EFF5'
      }}
    >
      {/* Soft atmospheric fog matching pale sky #E8EFF5 */}
      <color attach="background" args={['#E8EFF5']} />
      <fog attach="fog" args={['#E8EFF5', 70, 260]} />

      {/* Balanced lighting: One directional sun + soft ambient */}
      <ambientLight intensity={0.7} color="#F4ECD8" />
      <directionalLight
        position={[60, 90, 40]}
        intensity={0.9}
        color="#FFFFFF"
        castShadow={false} // Avoid heavy shadows for 60fps target
      />
      <hemisphereLight args={['#E8EFF5', '#D8DEC8', 0.4]} />

      {/* Procedural Low-Poly Terrain, Winding Road, and Instanced Houses/Trees */}
      <Terrain />

      {/* Dashed Ring Zones with Floating Labels */}
      <ZoneRings alertCount={alertCount} currentZoneId={currentZoneId} />

      {/* Arcade Physics & Chase Camera Bus */}
      <VehiclePhysics
        controls={controls}
        onZoneChange={onZoneChange}
        onSpeedChange={onSpeedChange}
        autoDriveTarget={autoDriveTarget}
        onAutoDriveArrived={onAutoDriveArrived}
      />
    </Canvas>
  );
};

