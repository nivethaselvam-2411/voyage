import React from 'react';
import { getDcrStatus } from '../utils/dcr';

interface DcrBadgeProps {
  dcr: number;
  showLabel?: boolean;
  prefix?: string;
}

export const DcrBadge: React.FC<DcrBadgeProps> = ({ dcr, showLabel = false, prefix }) => {
  const status = getDcrStatus(dcr);
  const formattedValue = typeof dcr === 'number' && !Number.isNaN(dcr) ? dcr.toFixed(2) : 'n/a';

  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '4px',
        padding: '2px 6px',
        fontSize: '12px',
        fontFamily: 'var(--font-mono)',
        fontWeight: 600,
        color: status.color,
        backgroundColor: status.bg,
        border: `1px solid ${status.border}`,
        borderRadius: 'var(--radius-sm)',
        lineHeight: 1.2
      }}
      title={`Demand-to-capacity ratio: ${formattedValue} (${status.label})`}
    >
      {prefix && <span style={{ fontWeight: 400, color: 'var(--color-ink-muted)' }}>{prefix}</span>}
      <span>{formattedValue}</span>
      {showLabel && (
        <span
          style={{
            fontSize: '11px',
            fontFamily: 'var(--font-sans)',
            fontWeight: 500,
            color: status.color,
            marginLeft: '2px'
          }}
        >
          {status.label}
        </span>
      )}
    </span>
  );
};
