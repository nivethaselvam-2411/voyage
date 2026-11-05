import { useState, useEffect } from 'react';

export interface ControlsState {
  forward: boolean;
  backward: boolean;
  left: boolean;
  right: boolean;
}

export function useKeyboardControls(
  onEnter?: () => void,
  onEscape?: () => void,
  enabled: boolean = true
) {
  const [controls, setControls] = useState<ControlsState>({
    forward: false,
    backward: false,
    left: false,
    right: false
  });

  useEffect(() => {
    if (!enabled) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      // Don't capture keys if typing in an input
      if (
        e.target instanceof HTMLInputElement ||
        e.target instanceof HTMLTextAreaElement ||
        e.target instanceof HTMLSelectElement
      ) {
        return;
      }

      if (e.key === 'Enter') {
        onEnter?.();
        return;
      }

      if (e.key === 'Escape') {
        onEscape?.();
        return;
      }

      switch (e.code) {
        case 'KeyW':
        case 'ArrowUp':
          setControls((c) => ({ ...c, forward: true }));
          break;
        case 'KeyS':
        case 'ArrowDown':
          setControls((c) => ({ ...c, backward: true }));
          break;
        case 'KeyA':
        case 'ArrowLeft':
          setControls((c) => ({ ...c, left: true }));
          break;
        case 'KeyD':
        case 'ArrowRight':
          setControls((c) => ({ ...c, right: true }));
          break;
      }
    };

    const handleKeyUp = (e: KeyboardEvent) => {
      switch (e.code) {
        case 'KeyW':
        case 'ArrowUp':
          setControls((c) => ({ ...c, forward: false }));
          break;
        case 'KeyS':
        case 'ArrowDown':
          setControls((c) => ({ ...c, backward: false }));
          break;
        case 'KeyA':
        case 'ArrowLeft':
          setControls((c) => ({ ...c, left: false }));
          break;
        case 'KeyD':
        case 'ArrowRight':
          setControls((c) => ({ ...c, right: false }));
          break;
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    window.addEventListener('keyup', handleKeyUp);

    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      window.removeEventListener('keyup', handleKeyUp);
    };
  }, [enabled, onEnter, onEscape]);

  return controls;
}

