import React, { useRef, useState } from 'react';
import type { ControlsState } from './useKeyboardControls';

interface VirtualJoystickProps {
  onControlsChange: (controls: ControlsState) => void;
}

export const VirtualJoystick: React.FC<VirtualJoystickProps> = ({ onControlsChange }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [active, setActive] = useState(false);
  const [knobPos, setKnobPos] = useState({ x: 0, y: 0 });

  const radius = 45;

  const handleTouch = (clientX: number, clientY: number) => {
    if (!containerRef.current) return;
    const rect = containerRef.current.getBoundingClientRect();
    const centerX = rect.left + rect.width / 2;
    const centerY = rect.top + rect.height / 2;

    const dx = clientX - centerX;
    const dy = clientY - centerY;
    const dist = Math.sqrt(dx * dx + dy * dy);

    const clampedDist = Math.min(dist, radius);
    const angle = Math.atan2(dy, dx);

    const x = Math.cos(angle) * clampedDist;
    const y = Math.sin(angle) * clampedDist;

    setKnobPos({ x, y });

    // Thresholds
    const threshold = 15;
    const forward = y < -threshold;
    const backward = y > threshold;
    const left = x < -threshold;
    const right = x > threshold;

    onControlsChange({ forward, backward, left, right });
  };

  const handleTouchStart = (e: React.TouchEvent) => {
    setActive(true);
    const touch = e.touches[0];
    handleTouch(touch.clientX, touch.clientY);
  };

  const handleTouchMove = (e: React.TouchEvent) => {
    if (!active) return;
    const touch = e.touches[0];
    handleTouch(touch.clientX, touch.clientY);
  };

  const handleTouchEnd = () => {
    setActive(false);
    setKnobPos({ x: 0, y: 0 });
    onControlsChange({ forward: false, backward: false, left: false, right: false });
  };

  return (
    <div
      ref={containerRef}
      onTouchStart={handleTouchStart}
      onTouchMove={handleTouchMove}
      onTouchEnd={handleTouchEnd}
      onTouchCancel={handleTouchEnd}
      style={{
        position: 'absolute',
        bottom: '24px',
        left: '24px',
        width: '110px',
        height: '110px',
        borderRadius: '50%',
        backgroundColor: 'rgba(244, 236, 216, 0.85)',
        border: '2px solid rgba(31, 38, 48, 0.3)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        touchAction: 'none',
        zIndex: 40,
        userSelect: 'none'
      }}
      aria-label="Touch driving joystick"
    >
      <div
        style={{
          width: '44px',
          height: '44px',
          borderRadius: '50%',
          backgroundColor: 'var(--color-accent-orange)',
          border: '2px solid #FFFFFF',
          transform: `translate(${knobPos.x}px, ${knobPos.y}px)`,
          transition: active ? 'none' : 'transform 150ms ease-out',
          boxShadow: 'none'
        }}
      />
    </div>
  );
};
