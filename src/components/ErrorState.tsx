import React from 'react';
import { AlertCircle, RefreshCw } from 'lucide-react';

interface ErrorStateProps {
  message?: string;
  onRetry?: () => void;
  title?: string;
}

export const ErrorState: React.FC<ErrorStateProps> = ({
  title = 'Failed to load telemetry data',
  message = 'The service encountered an issue reading from the backend. You can retry the request.',
  onRetry
}) => {
  return (
    <div
      style={{
        padding: '32px 24px',
        backgroundColor: 'var(--color-panel)',
        border: 'var(--border-panel)',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        textAlign: 'center',
        gap: '12px',
        maxWidth: '520px',
        margin: '24px auto'
      }}
      role="alert"
    >
      <div
        style={{
          width: '36px',
          height: '36px',
          borderRadius: 'var(--radius-sm)',
          backgroundColor: '#FEE2E2',
          border: '1px solid #FECACA',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: 'var(--dcr-red)'
        }}
      >
        <AlertCircle size={20} strokeWidth={2} />
      </div>

      <h3
        style={{
          fontFamily: 'var(--font-serif)',
          fontSize: '18px',
          color: 'var(--color-ink)'
        }}
      >
        {title}
      </h3>

      <p
        style={{
          fontSize: '13px',
          color: 'var(--color-ink-muted)',
          maxWidth: '440px',
          lineHeight: 1.5
        }}
      >
        {message}
      </p>

      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          style={{
            marginTop: '8px',
            display: 'inline-flex',
            alignItems: 'center',
            gap: '6px',
            padding: '8px 16px',
            backgroundColor: 'var(--color-ink)',
            color: '#FFFFFF',
            border: 'none',
            fontWeight: 500
          }}
        >
          <RefreshCw size={14} />
          Retry request
        </button>
      )}
    </div>
  );
};

