import React, { useEffect, useState, useRef } from 'react';
import { TypeTag } from './TypeTag';
import type { MetricType } from '../types';

interface KpiCardProps {
  label: string;
  value: number | string;
  type?: MetricType | string;
  definition?: string;
  unit?: string;
  secondaryLabel?: string;
  secondaryValue?: string | number;
}

export const KpiCard: React.FC<KpiCardProps> = ({
  label,
  value,
  type = 'MEASURED',
  definition,
  unit,
  secondaryLabel,
  secondaryValue
}) => {
  const [displayValue, setDisplayValue] = useState<string | number>(value);
  const frameRef = useRef<number | null>(null);

  useEffect(() => {
    if (typeof value !== 'number') {
      return;
    }

    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (prefersReducedMotion) {
      return;
    }

    const duration = 750;
    const start = performance.now();
    const isDecimal = value % 1 !== 0;

    const animate = (now: number) => {
      const elapsed = now - start;
      const progress = Math.min(elapsed / duration, 1);
      // easeOutQuad
      const eased = 1 - (1 - progress) * (1 - progress);
      const current = value * eased;

      setDisplayValue(isDecimal ? Number(current.toFixed(1)) : Math.round(current));

      if (progress < 1) {
        frameRef.current = requestAnimationFrame(animate);
      } else {
        setDisplayValue(value);
      }
    };

    frameRef.current = requestAnimationFrame(animate);
    return () => {
      if (frameRef.current !== null) {
        cancelAnimationFrame(frameRef.current);
      }
    };
  }, [value]);

  return (
    <div
      style={{
        backgroundColor: 'var(--color-panel)',
        border: 'var(--border-panel)',
        padding: '16px 20px',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
        minHeight: '124px',
        position: 'relative'
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '8px', marginBottom: '8px' }}>
        <span
          style={{
            fontSize: '12px',
            fontFamily: 'var(--font-sans)',
            fontWeight: 500,
            color: 'var(--color-ink-muted)',
            lineHeight: 1.3
          }}
        >
          {label}
        </span>
        <TypeTag type={type} size="sm" />
      </div>

      <div>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: '4px' }}>
          <h2
            style={{
              fontFamily: 'var(--font-serif)',
              fontSize: '32px',
              fontWeight: 400,
              color: 'var(--color-ink)',
              lineHeight: 1,
              letterSpacing: '-0.02em'
            }}
          >
            {displayValue}
          </h2>
          {unit && (
            <span
              style={{
                fontFamily: 'var(--font-sans)',
                fontSize: '14px',
                fontWeight: 500,
                color: 'var(--color-ink-muted)'
              }}
            >
              {unit}
            </span>
          )}
        </div>

        {secondaryLabel && secondaryValue !== undefined && (
          <div
            style={{
              marginTop: '4px',
              fontSize: '12px',
              fontFamily: 'var(--font-mono)',
              color: 'var(--color-ink-muted)'
            }}
          >
            {secondaryLabel}: <span style={{ color: 'var(--color-ink)', fontWeight: 600 }}>{secondaryValue}</span>
          </div>
        )}
      </div>

      {definition && (
        <p
          style={{
            marginTop: '8px',
            fontSize: '11px',
            fontFamily: 'var(--font-sans)',
            color: 'var(--color-ink-muted)',
            lineHeight: 1.3,
            borderTop: '1px solid var(--border-panel)',
            paddingTop: '6px'
          }}
        >
          {definition}
        </p>
      )}
    </div>
  );
};
