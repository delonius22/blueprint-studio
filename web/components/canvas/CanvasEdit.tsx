"use client";

// Gives canvas panels a way to write edits (SPECS S11.3); absent where the canvas is read-only.
import { createContext, useContext } from "react";
import type { Counters } from "../../lib/editing";
import type { Design } from "../../lib/state";

export type CanvasEditor = {
  design: Design;
  counters: Counters;
  disabled: boolean;
  save: (design: Design, counters: Counters) => void;
};

export const CanvasEditContext = createContext<CanvasEditor | null>(null);

export function useCanvasEditor(): CanvasEditor | null {
  return useContext(CanvasEditContext);
}
