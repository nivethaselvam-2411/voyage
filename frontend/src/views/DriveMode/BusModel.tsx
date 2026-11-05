import React from 'react';

interface BusModelProps {
  headlightsOn?: boolean;
}

export const BusModel: React.FC<BusModelProps> = ({ headlightsOn = true }) => {
  return (
    <group>
      {/* 1. Main Chassis & Lower Body */}
      <mesh position={[0, 0.7, 0]}>
        <boxGeometry args={[1.7, 0.7, 4.4]} />
        <meshLambertMaterial color="#D95A1E" flatShading />
      </mesh>

      {/* 2. Main Bus Body (Orange #E8692A) */}
      <mesh position={[0, 1.25, 0]}>
        <boxGeometry args={[1.7, 0.75, 4.4]} />
        <meshLambertMaterial color="#E8692A" flatShading />
      </mesh>

      {/* 3. Window Band & Roof (Cream #F4ECD8) */}
      <mesh position={[0, 1.72, 0]}>
        <boxGeometry args={[1.68, 0.42, 4.36]} />
        <meshLambertMaterial color="#F4ECD8" flatShading />
      </mesh>

      {/* 4. Roof Top */}
      <mesh position={[0, 1.96, 0]}>
        <boxGeometry args={[1.62, 0.12, 4.2]} />
        <meshLambertMaterial color="#EAE0C7" flatShading />
      </mesh>

      {/* 5. Roof AC Unit / Vents */}
      <mesh position={[0, 2.06, 0.2]}>
        <boxGeometry args={[1.1, 0.16, 1.6]} />
        <meshLambertMaterial color="#FFFFFF" flatShading />
      </mesh>

      {/* 6. Front Windshield (Dark ink / glass) */}
      <mesh position={[0, 1.65, 2.21]}>
        <boxGeometry args={[1.5, 0.5, 0.04]} />
        <meshLambertMaterial color="#1F2630" flatShading />
      </mesh>

      {/* 7. Rear Window */}
      <mesh position={[0, 1.65, -2.21]}>
        <boxGeometry args={[1.4, 0.45, 0.04]} />
        <meshLambertMaterial color="#1F2630" flatShading />
      </mesh>

      {/* 8. Side Windows (Left & Right) */}
      {/* Left side windows */}
      {[-1.2, -0.4, 0.4, 1.2].map((z, idx) => (
        <mesh key={`win-l-${idx}`} position={[-0.86, 1.65, z]}>
          <boxGeometry args={[0.04, 0.42, 0.65]} />
          <meshLambertMaterial color="#1F2630" flatShading />
        </mesh>
      ))}

      {/* Right side windows */}
      {[-1.2, -0.4, 0.4, 1.2].map((z, idx) => (
        <mesh key={`win-r-${idx}`} position={[0.86, 1.65, z]}>
          <boxGeometry args={[0.04, 0.42, 0.65]} />
          <meshLambertMaterial color="#1F2630" flatShading />
        </mesh>
      ))}

      {/* 9. Front Headlights */}
      <mesh position={[-0.6, 0.85, 2.22]}>
        <boxGeometry args={[0.26, 0.16, 0.05]} />
        <meshBasicMaterial color={headlightsOn ? '#FFF8D6' : '#C4D0DB'} />
      </mesh>
      <mesh position={[0.6, 0.85, 2.22]}>
        <boxGeometry args={[0.26, 0.16, 0.05]} />
        <meshBasicMaterial color={headlightsOn ? '#FFF8D6' : '#C4D0DB'} />
      </mesh>

      {/* 10. Front Route Display Board (MTC Marina Sentinel) */}
      <mesh position={[0, 1.95, 2.15]}>
        <boxGeometry args={[1.2, 0.18, 0.05]} />
        <meshBasicMaterial color="#1F2630" />
      </mesh>

      {/* 11. Wheels (4 low-poly cylinders) */}
      {/* Front Left */}
      <mesh position={[-0.85, 0.35, 1.3]} rotation={[0, 0, Math.PI / 2]}>
        <cylinderGeometry args={[0.35, 0.35, 0.28, 12]} />
        <meshLambertMaterial color="#1A1F26" flatShading />
      </mesh>
      {/* Front Right */}
      <mesh position={[0.85, 0.35, 1.3]} rotation={[0, 0, Math.PI / 2]}>
        <cylinderGeometry args={[0.35, 0.35, 0.28, 12]} />
        <meshLambertMaterial color="#1A1F26" flatShading />
      </mesh>
      {/* Rear Left */}
      <mesh position={[-0.85, 0.35, -1.3]} rotation={[0, 0, Math.PI / 2]}>
        <cylinderGeometry args={[0.35, 0.35, 0.28, 12]} />
        <meshLambertMaterial color="#1A1F26" flatShading />
      </mesh>
      {/* Rear Right */}
      <mesh position={[0.85, 0.35, -1.3]} rotation={[0, 0, Math.PI / 2]}>
        <cylinderGeometry args={[0.35, 0.35, 0.28, 12]} />
        <meshLambertMaterial color="#1A1F26" flatShading />
      </mesh>
    </group>
  );
};
