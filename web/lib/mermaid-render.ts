// Renders Mermaid source to SVG in the browser; loaded on demand because mermaid is large.
// Diagrams sit on a white plate in every theme, like a printed blueprint, so they keep
// Mermaid's light theme and need no re-render when the theme changes.
export type MermaidRenderer = (id: string, source: string) => Promise<string>;

export const renderMermaid: MermaidRenderer = async (id, source) => {
  const { default: mermaid } = await import("mermaid");
  mermaid.initialize({ startOnLoad: false, securityLevel: "strict", theme: "default" });
  const { svg } = await mermaid.render(id, source);
  return svg;
};
