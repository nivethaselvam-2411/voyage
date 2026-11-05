import React, { useEffect } from 'react';
import { X, ExternalLink } from 'lucide-react';
import { Link } from 'react-router-dom';
import { ControlRoomView } from '../ControlRoomView';
import { DepotsView } from '../DepotsView';
import { FleetView } from '../FleetView';
import { ScorecardView } from '../ScorecardView';
import { DatasetView } from '../DatasetView';

interface SlideOverPanelProps {
  zoneId: string | null;
  isOpen: boolean;
  onClose: () => void;
}

export const SlideOverPanel: React.FC<SlideOverPanelProps> = ({
  zoneId,
  isOpen,
  onClose
}) => {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen || !zoneId) return null;

  const renderContent = () => {
    switch (zoneId) {
      case 'control-room':
        return <ControlRoomView isPanel={true} />;
      case 'depots':
        return <DepotsView isPanel={true} />;
      case 'fleet':
        return <FleetView isPanel={true} />;
      case 'scorecard':
        return <ScorecardView isPanel={true} />;
      case 'dataset':
        return <DatasetView isPanel={true} />;
      default:
        return null;
    }
  };

  const getFullRoute = () => {
    switch (zoneId) {
      case 'control-room':
        return '/control-room';
      case 'depots':
        return '/depots';
      case 'fleet':
        return '/fleet';
      case 'scorecard':
        return '/scorecard';
      case 'dataset':
        return '/dataset';
      default:
        return '/control-room';
    }
  };

  const getTitle = () => {
    switch (zoneId) {
      case 'control-room':
        return 'Control room alert console';
      case 'depots':
        return 'Depot rebalance simulator';
      case 'fleet':
        return 'Fleet corridor telemetry';
      case 'scorecard':
        return 'Model validation scorecard';
      case 'dataset':
        return "Judge's problem dataset & telemetry explorer";
      default:
        return 'Operational console';
    }
  };

  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        right: 0,
        bottom: 0,
        width: '100%',
        maxWidth: '840px',
        backgroundColor: 'var(--color-page)',
        borderLeft: '1px solid var(--border-dark)',
        zIndex: 100,
        display: 'flex',
        flexDirection: 'column',
        boxShadow: '-4px 0 24px rgba(31, 38, 48, 0.14)',
        animation: 'slideInRight 240ms cubic-bezier(0.16, 1, 0.3, 1)'
      }}
      role="dialog"
      aria-modal="true"
      aria-label={getTitle()}
    >
      {/* Panel Top Bar */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '12px 20px',
          backgroundColor: 'var(--color-panel)',
          borderBottom: 'var(--border-panel)'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <span
            style={{
              fontFamily: 'var(--font-serif)',
              fontSize: '18px',
              color: 'var(--color-ink)'
            }}
          >
            {getTitle()}
          </span>
          <span
            style={{
              fontSize: '11px',
              fontFamily: 'var(--font-mono)',
              color: 'var(--color-ink-muted)',
              backgroundColor: 'var(--color-panel-contrast)',
              padding: '1px 6px',
              borderRadius: 'var(--radius-sm)'
            }}
          >
            Zone inspection
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Link
            to={getFullRoute()}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '4px',
              padding: '5px 10px',
              fontSize: '12px',
              color: 'var(--color-ink-muted)',
              textDecoration: 'none',
              backgroundColor: '#FFFFFF',
              border: 'var(--border-hairline)',
              borderRadius: 'var(--radius-sm)'
            }}
            title="Open in full screen"
          >
            <ExternalLink size={12} />
            <span>Full screen</span>
          </Link>

          <button
            type="button"
            onClick={onClose}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '4px',
              padding: '5px 10px',
              fontSize: '12px',
              backgroundColor: 'var(--color-ink)',
              color: '#FFFFFF',
              border: 'none',
              borderRadius: 'var(--radius-sm)'
            }}
            title="Close panel (Esc)"
          >
            <X size={14} />
            <span>Close (Esc)</span>
          </button>
        </div>
      </div>

      {/* Scrollable Panel View Content */}
      <div
        style={{
          flex: 1,
          overflowY: 'auto',
          backgroundColor: 'var(--color-page)'
        }}
      >
        {renderContent()}
      </div>

      <style>{`
        @keyframes slideInRight {
          from { transform: translateX(100%); }
          to { transform: translateX(0); }
        }
      `}</style>
    </div>
  );
};

