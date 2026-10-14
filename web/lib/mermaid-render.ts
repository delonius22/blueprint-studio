// Renders Mermaid source to SVG in the browser; loaded on demand because mermaid is large.
export type MermaidRenderer = (id: string, source: string) => Promise<string>;

export const renderMermaid: MermaidRenderer = async (id, source) => {
  const { default: mermaid } = await import("mermaid");
  const dark = window.matchMedia?.("(prefers-color-scheme: dark)").matches ?? false;
  mermaid.initialize({ startOnLoad: false, securityLevel: "strict", theme: dark ? "dark" : "default" });
  const { svg } = await mermaid.render(id, source);
  return svg;
};
