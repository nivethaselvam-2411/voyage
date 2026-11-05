import React from 'react';
import { Radio } from 'lucide-react';

export const FooterPill: React.FC = () => {
  return (
    <footer
      style={{
        marginTop: 'auto',
        padding: '16px 24px',
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center'
      }}
    >
      <div
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: '8px',
          padding: '6px 14px',
          backgroundColor: 'var(--color-panel)',
          border: 'var(--border-panel)',
          borderRadius: 'var(--radius-sm)',
          fontSize: '12px',
          fontFamily: 'var(--font-mono)',
          color: 'var(--color-ink-muted)'
        }}
      >
        <Radio size={13} style={{ color: 'var(--color-accent-orange)', strokeWidth: 2 }} />
        <span>Telemetry: ETM ticket replay | Engine: 60-minute ex-ante XGBoost</span>
      </div>
    </footer>
  );
};

