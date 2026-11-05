export interface ZoneDefinition {
  id: 'control-room' | 'depots' | 'fleet' | 'scorecard' | 'dataset';
  title: string;
  subtitle: string;
  position: [number, number, number];
  color: string;
  radius: number;
}

export const ZONES: ZoneDefinition[] = [
  {
    id: 'control-room',
    title: 'Control room',
    subtitle: 'Ranked alert queue & lead time',
    position: [0, 0, -45],
    color: '#E8692A',
    radius: 8.5
  },
  {
    id: 'depots',
    title: 'Depot yard',
    subtitle: 'Fleet rebalancing simulator',
    position: [55, 0, 10],
    color: '#2563EB',
    radius: 8.5
  },
  {
    id: 'fleet',
    title: 'Fleet corridors',
    subtitle: 'Full network corridor table',
    position: [-50, 0, 35],
    color: '#2E7D32',
    radius: 8.5
  },
  {
    id: 'scorecard',
    title: 'Scorecard',
    subtitle: 'Validation & operational limits',
    position: [15, 0, 65],
    color: '#1F2630',
    radius: 8.5
  },
  {
    id: 'dataset',
    title: "Judge dataset",
    subtitle: 'Theme 4 telemetry & stops',
    position: [-25, 0, -25],
    color: '#D97706',
    radius: 8.5
  }
];

// Elevation calculation for terrain and physics clamping
export function getTerrainHeight(x: number, z: number): number {
  // Distance from center
  const dist = Math.sqrt(x * x + z * z);
  if (dist > 180) return 0;

  // Road & zone safety: keep central path relatively flat
  const dCenter = Math.sqrt(x * x + z * z);
  const dControl = Math.sqrt(x * x + (z + 45) * (z + 45));
  const dDepot = Math.sqrt((x - 55) * (x - 55) + (z - 10) * (z - 10));
  const dFleet = Math.sqrt((x + 50) * (x + 50) + (z - 35) * (z - 35));
  const dScorecard = Math.sqrt((x - 15) * (x - 15) + (z - 65) * (z - 65));
  const dDataset = Math.sqrt((x + 25) * (x + 25) + (z + 25) * (z + 25));

  const minZoneDist = Math.min(dCenter, dControl, dDepot, dFleet, dScorecard, dDataset);

  // Gentle low-poly undulating hills on outer perimeter
  const wave1 = Math.sin(x * 0.04) * Math.cos(z * 0.04) * 3.5;
  const wave2 = Math.sin(x * 0.08 + z * 0.06) * 1.5;
  const rawHeight = Math.max(0, wave1 + wave2);

  // Flatten when near road or zones
  const flattenFactor = Math.min(1, Math.max(0, (minZoneDist - 16) / 24));
  return rawHeight * flattenFactor;
}

