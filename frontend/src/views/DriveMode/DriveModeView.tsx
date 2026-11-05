import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { DriveScene } from './DriveScene';
import { SlideOverPanel } from './SlideOverPanel';
import { VirtualJoystick } from './VirtualJoystick';
import { useKeyboardControls, type ControlsState } from './useKeyboardControls';
import { ZONES } from './constants';
import { fetchControlRoomAlerts } from '../../services/api';
import { DriveSceneErrorBoundary } from '../../components/DriveSceneErrorBoundary';
import {
  ArrowRight,
  Gauge,
  Navigation,
  LayoutDashboard,
  ChevronRight
} from 'lucide-react';

export const DriveModeView: React.FC = () => {
  const navigate = useNavigate();

  // State
  const [started, setStarted] = useState<boolean>(false);
  const [currentZoneId, setCurrentZoneId] = useState<string | null>(null);
  const [panelZoneId, setPanelZoneId] = useState<string | null>(null);
  const [speedKmh, setSpeedKmh] = useState<number>(0);
  const [alertCount, setAlertCount] = useState<number>(0);
  const [autoDriveTarget, setAutoDriveTarget] = useState<[number, number, number] | null>(null);
  const [touchControls, setTouchControls] = useState<ControlsState>({
    forward: false,
    backward: false,
    left: false,
    right: false
  });
  const [isTouchDevice, setIsTouchDevice] = useState<boolean>(false);
  const [webGlSupported, setWebGlSupported] = useState<boolean>(true);

  // Fallback checks: WebGL and prefers-reduced-motion
  useEffect(() => {
    // 1. Detect touch device
    const hasTouch = 'ontouchstart' in window || navigator.maxTouchPoints > 0;
    setIsTouchDevice(hasTouch);

    // 2. Check prefers-reduced-motion
    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (prefersReducedMotion) {
      console.info('Prefers reduced motion detected: routing to classic dashboard');
      navigate('/control-room', { replace: true });
      return;
    }

    // 3. Check WebGL support
    try {
      const canvas = document.createElement('canvas');
      const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
      if (!gl) {
        setWebGlSupported(false);
      }
    } catch {
      setWebGlSupported(false);
    }

    // Fetch alert count for badge
    fetchControlRoomAlerts()
      .then((alerts) => setAlertCount(alerts.length))
      .catch(() => setAlertCount(0));
  }, [navigate]);

  // Open active zone panel
  const handleOpenPanel = useCallback(() => {
    if (currentZoneId) {
      setPanelZoneId(currentZoneId);
    }
  }, [currentZoneId]);

  const handleClosePanel = useCallback(() => {
    setPanelZoneId(null);
  }, []);

  // Keyboard controls
  const keyboardControls = useKeyboardControls(
    handleOpenPanel,
    handleClosePanel,
    started && panelZoneId === null
  );

  // Merge keyboard and touch controls
  const activeControls = useMemo<ControlsState>(() => {
    return {
      forward: keyboardControls.forward || touchControls.forward,
      backward: keyboardControls.backward || touchControls.backward,
      left: keyboardControls.left || touchControls.left,
      right: keyboardControls.right || touchControls.right
    };
  }, [keyboardControls, touchControls]);

  // Handle "Take me there" selection
  const handleTakeMeThere = (zoneId: string) => {
    const zone = ZONES.find((z) => z.id === zoneId);
    if (zone) {
      setAutoDriveTarget(zone.position);
    }
  };

  const handleAutoDriveArrived = useCallback(() => {
    setAutoDriveTarget(null);
  }, []);

  // Get active zone details
  const activeZone = useMemo(() => {
    if (!currentZoneId) return null;
    return ZONES.find((z) => z.id === currentZoneId) || null;
  }, [currentZoneId]);

  // WebGL Fallback screen
  if (!webGlSupported) {
    return (
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          minHeight: '100vh',
          backgroundColor: 'var(--color-page)',
          padding: '24px',
          textAlign: 'center'
        }}
      >
        <div
          style={{
            maxWidth: '500px',
            backgroundColor: 'var(--color-panel)',
            border: 'var(--border-panel)',
            padding: '32px'
          }}
        >
          <h1 style={{ fontSize: '24px', marginBottom: '12px' }}>Drive mode unavailable</h1>
          <p style={{ fontSize: '13px', color: 'var(--color-ink-muted)', marginBottom: '20px' }}>
            Hardware accelerated WebGL is not available on this browser or device. You can explore all operational tools using the classic control-room dashboard.
          </p>
          <button
            type="button"
            onClick={() => navigate('/control-room')}
            style={{
              padding: '10px 20px',
              backgroundColor: 'var(--color-accent-orange)',
              color: '#FFFFFF',
              border: 'none',
              fontWeight: 600
            }}
          >
            Go to classic dashboard
          </button>
        </div>
      </div>
    );
  }

  return (
    <div
      style={{
        position: 'relative',
        width: '100vw',
        height: '100vh',
        overflow: 'hidden',
        backgroundColor: '#E8EFF5'
      }}
    >
      {/* 3D WebGL Canvas — wrapped in ErrorBoundary so a WebGL crash doesn't blank the whole app */}
      <DriveSceneErrorBoundary>
        <DriveScene
          controls={activeControls}
          onZoneChange={setCurrentZoneId}
          onSpeedChange={setSpeedKmh}
          alertCount={alertCount}
          currentZoneId={currentZoneId}
          autoDriveTarget={autoDriveTarget}
          onAutoDriveArrived={handleAutoDriveArrived}
        />
      </DriveSceneErrorBoundary>

      {/* Start Driving Overlay */}
      {!started && (
        <div
          style={{
            position: 'absolute',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: 'rgba(232, 239, 245, 0.88)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '24px',
            zIndex: 60,
            backdropFilter: 'none' // Strict design rule: no glassmorphism
          }}
          role="dialog"
          aria-label="Welcome to Marina Sentinel Drive Mode"
        >
          <div
            style={{
              maxWidth: '540px',
              width: '100%',
              backgroundColor: 'var(--color-panel)',
              border: '1px solid var(--color-ink)',
              padding: '36px 32px',
              display: 'flex',
              flexDirection: 'column',
              gap: '16px'
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span
                style={{
                  fontFamily: 'var(--font-mono)',
                  fontSize: '11px',
                  fontWeight: 700,
                  color: 'var(--color-accent-orange)',
                  textTransform: 'uppercase',
                  letterSpacing: '0.04em'
                }}
              >
                Chennai MTC Control-Room Copilot
              </span>
            </div>

            <h1
              style={{
                fontFamily: 'var(--font-serif)',
                fontSize: '32px',
                color: 'var(--color-ink)',
                lineHeight: 1.15
              }}
            >
              Drive through Chennai's bus network
            </h1>

            <p
              style={{
                fontFamily: 'var(--font-sans)',
                fontSize: '15px',
                color: 'var(--color-ink-muted)',
                lineHeight: 1.45
              }}
            >
              See the problem an hour before it happens. Navigate an interactive 3D procedural simulation of the corridor network, or open the operational dashboard directly.
            </p>

            <div
              style={{
                borderTop: '1px solid var(--border-panel)',
                paddingTop: '16px',
                display: 'flex',
                flexDirection: 'column',
                gap: '8px',
                fontSize: '12px',
                color: 'var(--color-ink-muted)'
              }}
            >
              <div><strong>Controls:</strong> WASD or Arrow keys to steer &amp; accelerate.</div>
              <div><strong>Stops:</strong> Enter dashed zones to inspect live corridor alerts and rebalance pairs.</div>
            </div>

            <div
              style={{
                display: 'flex',
                flexWrap: 'wrap',
                gap: '12px',
                marginTop: '12px',
                paddingTop: '16px',
                borderTop: '1px solid var(--border-panel)'
              }}
            >
              <button
                type="button"
                onClick={() => setStarted(true)}
                style={{
                  padding: '10px 20px',
                  backgroundColor: 'var(--color-accent-orange)',
                  color: '#FFFFFF',
                  border: 'none',
                  fontWeight: 600,
                  fontSize: '14px',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '8px'
                }}
              >
                <span>Start driving</span>
                <ChevronRight size={16} />
              </button>

              <button
                type="button"
                onClick={() => navigate('/control-room')}
                style={{
                  padding: '10px 18px',
                  backgroundColor: '#FFFFFF',
                  color: 'var(--color-ink)',
                  border: 'var(--border-hairline)',
                  fontSize: '14px',
                  fontWeight: 500,
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '8px'
                }}
              >
                <span>Explore without driving</span>
                <ArrowRight size={14} />
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Top HUD: Brand & Mode Switch */}
      <div
        style={{
          position: 'absolute',
          top: '16px',
          left: '16px',
          right: '16px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          pointerEvents: 'none',
          zIndex: 40
        }}
      >
        {/* Left: Brand Pill */}
        <div
          style={{
            pointerEvents: 'auto',
            backgroundColor: 'var(--color-panel)',
            border: 'var(--border-panel)',
            padding: '8px 14px',
            display: 'flex',
            alignItems: 'center',
            gap: '12px'
          }}
        >
          <span style={{ fontFamily: 'var(--font-serif)', fontSize: '18px', color: 'var(--color-ink)' }}>
            Marina Sentinel
          </span>
          <span style={{ fontSize: '11px', fontFamily: 'var(--font-mono)', color: 'var(--color-accent-orange)', fontWeight: 600 }}>
            Drive Mode
          </span>
          <span style={{ fontSize: '12px', color: 'var(--color-ink-muted)', borderLeft: '1px solid var(--border-panel)', paddingLeft: '8px' }}>
            Chennai MTC
          </span>
        </div>

        {/* Right: Take me there Menu & Classic Dashboard Link */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', pointerEvents: 'auto' }}>
          {/* "Take me there" Dropdown Menu */}
          <div
            style={{
              backgroundColor: 'var(--color-panel)',
              border: 'var(--border-panel)',
              padding: '4px 8px',
              display: 'flex',
              alignItems: 'center',
              gap: '6px'
            }}
          >
            <Navigation size={13} style={{ color: 'var(--color-ink-muted)' }} />
            <label htmlFor="take-me-there" style={{ fontSize: '11px', color: 'var(--color-ink-muted)' }}>
              Take me there:
            </label>
            <select
              id="take-me-there"
              defaultValue=""
              onChange={(e) => {
                if (e.target.value) {
                  handleTakeMeThere(e.target.value);
                  e.target.value = '';
                }
              }}
              style={{ fontSize: '12px', padding: '3px 8px' }}
              aria-label="Auto-drive to zone"
            >
              <option value="" disabled>
                Select destination...
              </option>
              {ZONES.map((zone) => (
                <option key={zone.id} value={zone.id}>
                  {zone.title}
                </option>
              ))}
            </select>
          </div>

          <button
            type="button"
            onClick={() => navigate('/control-room')}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              padding: '6px 12px',
              backgroundColor: '#FFFFFF',
              border: 'var(--border-hairline)',
              color: 'var(--color-ink)',
              fontSize: '12px',
              fontWeight: 500
            }}
            title="Open classic dashboard"
          >
            <LayoutDashboard size={13} />
            <span>Classic dashboard</span>
          </button>
        </div>
      </div>

      {/* Auto-drive Active Notification Banner */}
      {autoDriveTarget && (
        <div
          style={{
            position: 'absolute',
            top: '70px',
            left: '50%',
            transform: 'translateX(-50%)',
            backgroundColor: 'var(--color-ink)',
            color: '#FFFFFF',
            padding: '6px 14px',
            fontSize: '12px',
            fontFamily: 'var(--font-mono)',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            zIndex: 45
          }}
        >
          <Navigation size={13} style={{ color: 'var(--color-accent-orange)' }} />
          <span>Auto-driving to destination... Steering in progress</span>
        </div>
      )}

      {/* Stopping Inside Ring Prompt Banner */}
      {activeZone && panelZoneId === null && (
        <div
          style={{
            position: 'absolute',
            bottom: isTouchDevice ? '140px' : '36px',
            left: '50%',
            transform: 'translateX(-50%)',
            backgroundColor: 'var(--color-panel)',
            border: '2px solid var(--color-ink)',
            padding: '12px 20px',
            display: 'flex',
            alignItems: 'center',
            gap: '16px',
            zIndex: 50,
            animation: 'fadeIn 200ms ease'
          }}
        >
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontFamily: 'var(--font-serif)', fontSize: '16px', fontWeight: 600 }}>
                {activeZone.title}
              </span>
              <span
                style={{
                  fontSize: '11px',
                  fontFamily: 'var(--font-mono)',
                  color: 'var(--color-accent-orange)',
                  fontWeight: 700
                }}
              >
                Inside zone
              </span>
            </div>
            <div style={{ fontSize: '12px', color: 'var(--color-ink-muted)' }}>
              {activeZone.subtitle}
            </div>
          </div>

          <button
            type="button"
            onClick={handleOpenPanel}
            style={{
              padding: '8px 16px',
              backgroundColor: 'var(--color-accent-orange)',
              color: '#FFFFFF',
              border: 'none',
              fontWeight: 600,
              fontSize: '13px',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px'
            }}
          >
            <span>Press Enter to open</span>
            <ChevronRight size={14} />
          </button>
        </div>
      )}

      {/* Bottom HUD: Speedometer & Controls Helper */}
      <div
        style={{
          position: 'absolute',
          bottom: '20px',
          right: '20px',
          display: 'flex',
          alignItems: 'center',
          gap: '12px',
          pointerEvents: 'none',
          zIndex: 40
        }}
      >
        <div
          style={{
            backgroundColor: 'var(--color-panel)',
            border: 'var(--border-panel)',
            padding: '6px 12px',
            display: 'flex',
            alignItems: 'baseline',
            gap: '4px',
            fontFamily: 'var(--font-mono)'
          }}
        >
          <Gauge size={13} style={{ color: 'var(--color-ink-muted)', marginRight: '2px' }} />
          <span style={{ fontSize: '16px', fontWeight: 700, color: 'var(--color-ink)' }}>
            {speedKmh}
          </span>
          <span style={{ fontSize: '10px', color: 'var(--color-ink-muted)' }}>km/h</span>
        </div>

        <div
          style={{
            backgroundColor: 'var(--color-panel)',
            border: 'var(--border-panel)',
            padding: '6px 10px',
            fontSize: '11px',
            color: 'var(--color-ink-muted)',
            fontFamily: 'var(--font-mono)'
          }}
        >
          WASD / Arrows to drive
        </div>
      </div>

      {/* Virtual Touch Joystick for touch devices */}
      {isTouchDevice && started && panelZoneId === null && (
        <VirtualJoystick onControlsChange={setTouchControls} />
      )}

      {/* Slide-over Side Panel Rendering the Exact Same Classic Screen */}
      <SlideOverPanel
        zoneId={panelZoneId}
        isOpen={panelZoneId !== null}
        onClose={handleClosePanel}
      />
    </div>
  );
};
