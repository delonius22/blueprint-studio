"use client";

// The architecture diagram panel (SPECS S11.3): rendered Mermaid plus its source.
import { useEffect, useId, useMemo, useState } from "react";
import { designToMermaid } from "../../lib/mermaid";
import { type MermaidRenderer, renderMermaid } from "../../lib/mermaid-render";
import type { Design } from "../../lib/state";
import styles from "./Canvas.module.css";

type Props = { design: Pick<Design, "components" | "flows">; render?: MermaidRenderer };

export function DiagramPanel({ design, render = renderMermaid }: Props) {
  const source = useMemo(() => designToMermaid(design), [design]);
  const [svg, setSvg] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const domId = `diagram-${useId().replace(/[^A-Za-z0-9]/g, "")}`;
  const empty = design.components.length === 0;

  useEffect(() => {
    if (empty) return;
    let cancelled = false;
    render(domId, source)
      .then((output) => {
        if (!cancelled) {
          setSvg(output);
          setError(null);
        }
      })
      .catch((caught: unknown) => {
        if (!cancelled) setError(caught instanceof Error ? caught.message : "The diagram could not be drawn.");
      });
    return () => {
      cancelled = true;
    };
  }, [domId, empty, render, source]);

  const flows = design.flows.length;
  return (
    <section className={`${styles.panel} ${styles.wide}`} aria-labelledby={`${domId}-title`}>
      <h3 id={`${domId}-title`}>Architecture diagram</h3>
      {empty ? (
        <p className={styles.empty}>Nothing to draw yet: the diagram appears once components are recorded.</p>
      ) : error ? (
        <p role="alert">{error}</p>
      ) : (
        <div
          className={styles.diagram}
          role="img"
          aria-label={`Architecture diagram of ${design.components.length} components and ${flows} flows; the Mermaid source below lists every element.`}
          // Mermaid's strict security level sanitises the SVG it returns.
          dangerouslySetInnerHTML={{ __html: svg ?? "" }}
        />
      )}
      <details className={styles.source}>
        <summary>Mermaid source</summary>
        <pre>
          <code>{source}</code>
        </pre>
      </details>
    </section>
  );
}
