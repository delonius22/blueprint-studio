"use client";

// One diagram panel (SPECS S11.3): rendered Mermaid plus its source.
import { useEffect, useId, useState } from "react";
import { type MermaidRenderer, renderMermaid } from "../../lib/mermaid-render";
import styles from "./Canvas.module.css";

type Props = {
  title: string;
  source: string;
  // What the image shows, for screen readers; the source below lists every element.
  description: string;
  // Shown instead of the image while there is nothing to draw.
  empty?: string | null;
  render?: MermaidRenderer;
};

export function DiagramPanel({ title, source, description, empty = null, render = renderMermaid }: Props) {
  const [svg, setSvg] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const domId = `diagram-${useId().replace(/[^A-Za-z0-9]/g, "")}`;

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

  return (
    <section className={`${styles.panel} ${styles.wide}`} aria-labelledby={`${domId}-title`}>
      <h3 id={`${domId}-title`}>{title}</h3>
      {empty ? (
        <p className={styles.empty}>{empty}</p>
      ) : error ? (
        <p role="alert">{error}</p>
      ) : (
        <div
          className={styles.diagram}
          role="img"
          aria-label={`${description}; the Mermaid source below lists every element.`}
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
