import { useEffect, useRef, useState } from "react";
import DateTimeWheelPicker from "./DateTimeWheelPicker";

function pad(n: number): string {
  return String(n).padStart(2, "0");
}

function toLocalValue(date: Date): string {
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

function parseLocalValue(value: string): Date {
  if (!value) {
    const now = new Date();
    now.setSeconds(0, 0);
    return now;
  }
  const [datePart, timePart] = value.split("T");
  const [y, m, d] = datePart.split("-").map(Number);
  const [h, min] = (timePart || "00:00").split(":").map(Number);
  return new Date(y, m - 1, d, h, min);
}

export default function DateTimeField({
  value,
  onChange,
  placeholder = "Select date & time",
}: {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
}) {
  const [open, setOpen] = useState(false);
  const [draft, setDraft] = useState<Date>(() => parseLocalValue(value));
  const wrapRef = useRef<HTMLDivElement>(null);
  const popoverRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (open) setDraft(parseLocalValue(value));
  }, [open, value]);

  useEffect(() => {
    if (!open) return;
    const popover = popoverRef.current;
    const trigger = wrapRef.current;
    if (!popover || !trigger) return;

    const triggerRect = trigger.getBoundingClientRect();
    const popoverWidth = popover.offsetWidth;
    const margin = 8;

    let left = triggerRect.width / 2 - popoverWidth / 2;
    const absoluteLeft = triggerRect.left + left;

    if (absoluteLeft < margin) {
      left += margin - absoluteLeft;
    } else if (absoluteLeft + popoverWidth > window.innerWidth - margin) {
      left -= absoluteLeft + popoverWidth - (window.innerWidth - margin);
    }

    popover.style.left = `${left}px`;
    popover.style.visibility = "visible";
  }, [open]);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    if (open) document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [open]);

  const displayLabel = value
    ? parseLocalValue(value).toLocaleString(undefined, {
        month: "short",
        day: "numeric",
        year: "numeric",
        hour: "numeric",
        minute: "2-digit",
      })
    : placeholder;

  function handleDone() {
    onChange(toLocalValue(draft));
    setOpen(false);
  }

  return (
    <div className="datetime-field" ref={wrapRef}>
      <button type="button" className={`datetime-trigger ${value ? "" : "datetime-trigger-empty"}`} onClick={() => setOpen((o) => !o)}>
        {displayLabel}
      </button>
      {open && (
        <div className="datetime-popover" ref={popoverRef}>
          <DateTimeWheelPicker value={draft} onChange={setDraft} />
          <div className="datetime-popover-actions">
            <button type="button" className="btn-secondary datetime-cancel" onClick={() => setOpen(false)}>
              Cancel
            </button>
            <button type="button" className="datetime-done" onClick={handleDone}>
              Done
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
