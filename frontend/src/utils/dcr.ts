export interface DcrStatusInfo {
  color: string;
  bg: string;
  border: string;
  label: string;
}

export function getDcrStatus(dcr: number): DcrStatusInfo {
  if (dcr <= 0.40) {
    return {
      color: 'var(--dcr-blue)',
      bg: 'var(--dcr-blue-bg)',
      border: 'rgba(37, 99, 235, 0.4)',
      label: 'Surplus (donor)'
    };
  }
  if (dcr <= 0.85) {
    return {
      color: 'var(--dcr-green)',
      bg: 'var(--dcr-green-bg)',
      border: 'rgba(46, 125, 50, 0.4)',
      label: 'Balanced'
    };
  }
  if (dcr <= 1.00) {
    return {
      color: 'var(--dcr-amber)',
      bg: 'var(--dcr-amber-bg)',
      border: 'rgba(217, 119, 6, 0.4)',
      label: 'Near capacity'
    };
  }
  return {
    color: 'var(--dcr-red)',
    bg: 'var(--dcr-red-bg)',
    border: 'rgba(197, 48, 48, 0.4)',
    label: 'Over capacity'
  };
}

