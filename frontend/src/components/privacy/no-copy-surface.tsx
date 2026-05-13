"use client";

import { useEffect, useRef } from "react";

type NoCopySurfaceProps = {
  children: React.ReactNode;
  className?: string;
};

export function NoCopySurface({ children, className = "" }: NoCopySurfaceProps) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const node = ref.current;
    if (!node) return;

    const prevent = (event: Event) => {
      event.preventDefault();
      event.stopPropagation();
    };

    const preventCopyShortcut = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null;
      if (target?.closest("input, textarea, select, [contenteditable='true']")) return;
      const key = event.key.toLowerCase();
      if ((event.ctrlKey || event.metaKey) && ["c", "x", "s", "p", "a"].includes(key)) {
        event.preventDefault();
        event.stopPropagation();
      }
    };

    node.addEventListener("copy", prevent);
    node.addEventListener("cut", prevent);
    node.addEventListener("dragstart", prevent);
    node.addEventListener("contextmenu", prevent);
    node.addEventListener("keydown", preventCopyShortcut, true);

    return () => {
      node.removeEventListener("copy", prevent);
      node.removeEventListener("cut", prevent);
      node.removeEventListener("dragstart", prevent);
      node.removeEventListener("contextmenu", prevent);
      node.removeEventListener("keydown", preventCopyShortcut, true);
    };
  }, []);

  return (
    <div
      ref={ref}
      className={`select-none ${className}`}
      style={{ WebkitUserSelect: "none", userSelect: "none", WebkitTouchCallout: "none" }}
      onContextMenu={(event) => event.preventDefault()}
      onCopy={(event) => event.preventDefault()}
      onCut={(event) => event.preventDefault()}
      onDragStart={(event) => event.preventDefault()}
    >
      {children}
    </div>
  );
}
