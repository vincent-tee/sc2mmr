/**
 * AnimatedNumber - counts up/down to a target value instead of snapping,
 * so ratings/percentages feel alive as teams are adjusted.
 */
import React, { useEffect, useRef, useState } from 'react';

interface AnimatedNumberProps {
  value: number;
  decimals?: number;
  duration?: number;
  suffix?: string;
  prefix?: string;
  format?: (n: number) => string;
}

const prefersReducedMotion = (): boolean =>
  typeof window !== 'undefined' &&
  window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;

const AnimatedNumber: React.FC<AnimatedNumberProps> = ({
  value,
  decimals = 0,
  duration = 500,
  suffix = '',
  prefix = '',
  format,
}) => {
  const [display, setDisplay] = useState(value);
  const displayRef = useRef(value);
  const rafRef = useRef<number | undefined>(undefined);

  useEffect(() => {
    const from = displayRef.current;
    const to = value;

    if (Math.abs(from - to) < 10 ** -(decimals + 2) || prefersReducedMotion()) {
      setDisplay(to);
      displayRef.current = to;
      return;
    }

    const start = performance.now();
    const step = (now: number): void => {
      const t = Math.min(1, (now - start) / duration);
      const eased = 1 - Math.pow(1 - t, 3);
      const next = from + (to - from) * eased;
      setDisplay(next);
      displayRef.current = next;
      if (t < 1) {
        rafRef.current = requestAnimationFrame(step);
      }
    };
    rafRef.current = requestAnimationFrame(step);

    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value, duration, decimals]);

  return (
    <>
      {prefix}
      {format ? format(display) : display.toFixed(decimals)}
      {suffix}
    </>
  );
};

export default React.memo(AnimatedNumber);
