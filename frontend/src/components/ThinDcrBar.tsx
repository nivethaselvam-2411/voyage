import React from 'react';
import { getDcrStatus } from '../utils/dcr';

interface ThinDcrBarProps {
  dcr: number;
  height?: number;
  width?: string | number;
  showMarker?: boolean;
}

export const ThinDcrBar: React.FC<ThinDcrBarProps> = ({
  dcr,
  height = 8,
  width = '100%',
  showMarker = true
}) => {
  const status = getDcrStatus(dcr);
  // Scale from 0 to 1.8 max
  const maxDcr = 1.8;
  const pct = Math.min(Math.max((dcr / maxDcr) * 100, 2), 100);
  const thresholdPct = (1.0 / maxDcr) * 100; // ~55.5%

  return (
    <div style={{ width, display: 'flex', flexDirection: 'column', gap: '3px' }}>
      <div
        style={{
          position: 'relative',
          width: '100%',
          height: `${height}px`,
          backgroundColor: '#DFE7EE',
          borderRadius: 'var(--radius-sm)',
          overflow: 'hidden',
          border: '1px solid #C9D5E0'
        }}
        title={`DCR: ${dcr.toFixed(2)}`}
      >
        {/* Fill bar */}
        <div
          style={{
            position: 'absolute',
            left: 0,
            top: 0,
            bottom: 0,
            width: `${pct}%`,
            backgroundColor: status.color,
            transition: 'width var(--transition-speed) ease'
          }}
        />

        {/* 1.0 Over Capacity Marker */}
        {showMarker && (
          <div
            style={{
              position: 'absolute',
              left: `${thresholdPct}%`,
              top: 0,
              bottom: 0,
              width: '1.5px',
              backgroundColor: 'var(--color-ink)',
              zIndex: 2
            }}
            title="1.0 capacity threshold"
          />
        )}
      </div>

      {showMarker && (
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            fontSize: '10px',
            color: 'var(--color-ink-muted)',
            fontFamily: 'var(--font-mono)',
            lineHeight: 1
          }}
        >
          <span>0</span>
          <span style={{ position: 'relative', left: `calc(${thresholdPct}% - 40%)`, color: 'var(--color-ink)' }}>
            1.0 cap
          </span>
          <span>1.8+</span>
        </div>
      )}
    </div>
  );
};
