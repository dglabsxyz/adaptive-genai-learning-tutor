import React from 'react';

/**
 * Skeleton loading placeholder — theme-aware shimmer effect.
 */
export default function Skeleton({ width = '100%', height = '16px', rounded = 'var(--r-sm)', className = '' }) {
  return (
    <div
      className={`skeleton ${className}`}
      style={{ width, height, borderRadius: rounded }}
    />
  );
}
