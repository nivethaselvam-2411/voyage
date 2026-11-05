import React from 'react';
import type { MetricType } from '../types';

interface TypeTagProps {
  type?: MetricType | string;
  size?: 'sm' | 'md';
}

export const TypeTag: React.FC<TypeTagProps> = ({ type = 'MEASURED', size = 'sm' }) => {
  const isSimulated = type.toUpperCase() === 'SIMULATED';
  const label = isSimulated ? 'SIMULATED' : 'MEASURED';

  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        padding: size === 'sm' ? '1px 5px' : '2px 7px',
        fontSize: size === 'sm' ? '10px' : '11px',
        fontFamily: 'var(--font-sans)',
        fontWeight: 600,
        letterSpacing: '0.04em',
        textTransform: 'uppercase',
        border: '1px solid #BCC8D4',
        borderRadius: 'var(--radius-sm)',
        backgroundColor: isSimulated ? '#FDF5E6' : '#EEF4FA',
        color: 'var(--color-ink-muted)',
        lineHeight: 1.2,
        userSelect: 'none'
      }}
      title={isSimulated ? 'Simulated counterfactual model output' : 'Empirically measured telemetry baseline'}
    >
      {label}
    </span>
  );
};

