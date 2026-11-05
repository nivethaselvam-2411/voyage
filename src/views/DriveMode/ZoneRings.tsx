import React from 'react';
import { Html } from '@react-three/drei';
import * as THREE from 'three';
import { ZONES, getTerrainHeight } from './constants';

interface ZoneRingsProps {
  alertCount?: number;
  currentZoneId?: string | null;
}

export const ZoneRings: React.FC<ZoneRingsProps> = ({ alertCount = 0, currentZoneId }) => {
  return (
    <group>
      {ZONES.map((zone) => {
        const [x, , z] = zone.position;
        const groundY = getTerrainHeight(x, z);
        const isActive = currentZoneId === zone.id;

        return (
          <group key={zone.id} position={[x, groundY, z]}>
            {/* Ground Ring Geometry (Dashed Ring Effect) */}
            <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.08, 0]}>
              <ringGeometry args={[zone.radius - 0.4, zone.radius, 48]} />
              <meshBasicMaterial
                color={zone.color}
                side={THREE.DoubleSide}
                wireframe={true}
                transparent
                opacity={isActive ? 0.9 : 0.6}
              />
            </mesh>

            {/* Inner subtle flat ground disc */}
            <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.05, 0]}>
              <circleGeometry args={[zone.radius - 0.5, 32]} />
              <meshBasicMaterial
                color={zone.color}
                side={THREE.DoubleSide}
                transparent
                opacity={isActive ? 0.16 : 0.06}
              />
            </mesh>

            {/* Architectural Landmark per Zone */}
            {zone.id === 'control-room' && (
              <group position={[0, 0, 0]}>
                {/* Comms Tower / Signal Mast */}
                <mesh position={[0, 4.5, 0]}>
                  <cylinderGeometry args={[0.1, 0.35, 9, 6]} />
                  <meshLambertMaterial color="#8896A6" flatShading />
                </mesh>
                <mesh position={[0, 8.8, 0]}>
                  <sphereGeometry args={[0.4, 8, 8]} />
                  <meshBasicMaterial color="#E8692A" />
                </mesh>
              </group>
            )}

            {zone.id === 'depots' && (
              <group position={[0, 0, 0]}>
                {/* Depot Canopy / Bay Shelter */}
                <mesh position={[0, 2.2, 0]}>
                  <boxGeometry args={[7, 0.3, 5]} />
                  <meshLambertMaterial color="#F4ECD8" flatShading />
                </mesh>
                <mesh position={[-3, 1.1, -2]}>
                  <cylinderGeometry args={[0.12, 0.12, 2.2, 6]} />
                  <meshLambertMaterial color="#5A6472" />
                </mesh>
                <mesh position={[3, 1.1, -2]}>
                  <cylinderGeometry args={[0.12, 0.12, 2.2, 6]} />
                  <meshLambertMaterial color="#5A6472" />
                </mesh>
              </group>
            )}

            {zone.id === 'fleet' && (
              <group position={[0, 0, 0]}>
                {/* Corridor Terminal Board */}
                <mesh position={[0, 2.2, 0]}>
                  <boxGeometry args={[4.5, 2.0, 0.2]} />
                  <meshLambertMaterial color="#1F2630" flatShading />
                </mesh>
                <mesh position={[0, 0.6, 0]}>
                  <cylinderGeometry args={[0.12, 0.12, 1.2, 6]} />
                  <meshLambertMaterial color="#5A6472" />
                </mesh>
              </group>
            )}

            {zone.id === 'scorecard' && (
              <group position={[0, 0, 0]}>
                {/* Calibration Obelisk */}
                <mesh position={[0, 2.6, 0]}>
                  <boxGeometry args={[1.2, 5.2, 1.2]} />
                  <meshLambertMaterial color="#EAE0C7" flatShading />
                </mesh>
              </group>
            )}

            {zone.id === 'dataset' && (
              <group position={[0, 0, 0]}>
                {/* Data Telemetry Hub Monolith */}
                <mesh position={[0, 2.0, 0]}>
                  <boxGeometry args={[2.0, 4.0, 2.0]} />
                  <meshLambertMaterial color="#F4ECD8" flatShading />
                </mesh>
                <mesh position={[0, 4.2, 0]}>
                  <cylinderGeometry args={[0.08, 0.08, 1.5, 6]} />
                  <meshLambertMaterial color="#D97706" />
                </mesh>
              </group>
            )}

            {/* Floating Label using Drei Html */}
            <Html
              position={[0, zone.id === 'control-room' ? 9.8 : 5.2, 0]}
              center
              distanceFactor={32}
              style={{ pointerEvents: 'none', userSelect: 'none' }}
            >
              <div
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  gap: '4px',
                  backgroundColor: 'rgba(244, 236, 216, 0.95)',
                  border: `1.5px solid ${zone.color}`,
                  padding: '6px 12px',
                  borderRadius: '2px',
                  minWidth: '140px',
                  textAlign: 'center',
                  boxShadow: 'none'
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <span
                    style={{
                      fontFamily: 'Georgia, serif',
                      fontSize: '14px',
                      fontWeight: 600,
                      color: '#1F2630',
                      whiteSpace: 'nowrap'
                    }}
                  >
                    {zone.title}
                  </span>

                  {/* Badge over Control Room showing active alert count */}
                  {zone.id === 'control-room' && alertCount > 0 && (
                    <span
                      style={{
                        backgroundColor: '#C53030',
                        color: '#FFFFFF',
                        fontSize: '11px',
                        fontFamily: 'monospace',
                        fontWeight: 700,
                        padding: '1px 6px',
                        borderRadius: '2px'
                      }}
                      title={`${alertCount} pending operational alerts`}
                    >
                      {alertCount} alerts
                    </span>
                  )}

                  {zone.id === 'dataset' && (
                    <span
                      style={{
                        backgroundColor: '#D97706',
                        color: '#FFFFFF',
                        fontSize: '10px',
                        fontFamily: 'monospace',
                        fontWeight: 700,
                        padding: '1px 5px',
                        borderRadius: '2px'
                      }}
                    >
                      Theme 4
                    </span>
                  )}
                </div>

                <span
                  style={{
                    fontSize: '11px',
                    fontFamily: 'Inter, sans-serif',
                    color: '#5A6472',
                    whiteSpace: 'nowrap'
                  }}
                >
                  {zone.subtitle}
                </span>

                {isActive && (
                  <span
                    style={{
                      marginTop: '2px',
                      fontSize: '10px',
                      fontFamily: 'monospace',
                      fontWeight: 700,
                      color: '#E8692A',
                      backgroundColor: '#FFFFFF',
                      padding: '1px 6px',
                      borderRadius: '2px',
                      border: '1px solid #E8692A'
                    }}
                  >
                    Inside zone
                  </span>
                )}
              </div>
            </Html>
          </group>
        );
      })}
    </group>
  );
};
