import { useEffect, useRef } from "react";

const ITEM_HEIGHT = 40;
const VISIBLE_ITEMS = 5;

export default function WheelColumn({
  options,
  index,
  onChange,
}: {
  options: string[];
  index: number;
  onChange: (index: number) => void;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const scrollTimeout = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    const node = ref.current;
    if (!node) return;
    const targetTop = index * ITEM_HEIGHT;
    if (Math.abs(node.scrollTop - targetTop) > 1) {
      node.scrollTop = targetTop;
    }
  }, [index]);

  function handleScroll() {
    if (scrollTimeout.current) clearTimeout(scrollTimeout.current);
    scrollTimeout.current = setTimeout(() => {
      const node = ref.current;
      if (!node) return;
      const nearest = Math.round(node.scrollTop / ITEM_HEIGHT);
      const clamped = Math.max(0, Math.min(options.length - 1, nearest));
      if (clamped !== index) {
        onChange(clamped);
      } else if (Math.abs(node.scrollTop - clamped * ITEM_HEIGHT) > 1) {
        node.scrollTop = clamped * ITEM_HEIGHT;
      }
    }, 120);
  }

  return (
    <div className="wheel-column-wrap">
      <div className="wheel-column" ref={ref} onScroll={handleScroll} style={{ height: ITEM_HEIGHT * VISIBLE_ITEMS }}>
        <div style={{ height: ITEM_HEIGHT * Math.floor(VISIBLE_ITEMS / 2) }} />
        {options.map((opt, i) => (
          <div
            key={opt + i}
            className={`wheel-item ${i === index ? "wheel-item-active" : ""}`}
            style={{ height: ITEM_HEIGHT }}
            onClick={() => onChange(i)}
          >
            {opt}
          </div>
        ))}
        <div style={{ height: ITEM_HEIGHT * Math.floor(VISIBLE_ITEMS / 2) }} />
      </div>
      <div className="wheel-highlight" style={{ height: ITEM_HEIGHT }} aria-hidden="true" />
    </div>
  );
}
