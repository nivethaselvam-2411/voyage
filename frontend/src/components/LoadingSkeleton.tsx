import React from 'react';

interface LoadingSkeletonProps {
  rows?: number;
  height?: number;
}

export const LoadingSkeleton: React.FC<LoadingSkeletonProps> = ({ rows = 4, height = 48 }) => {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', width: '100%' }}>
      {Array.from({ length: rows }).map((_, idx) => (
        <div
          key={idx}
          style={{
            height: `${height}px`,
            backgroundColor: '#DFE7EE',
            border: 'var(--border-hairline)',
            borderRadius: 'var(--radius-sm)',
            opacity: 0.7
          }}
        />
      ))}
    </div>
  );
};

