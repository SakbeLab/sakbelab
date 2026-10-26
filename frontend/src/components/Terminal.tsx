import { useEffect, useRef } from "react";
import { Terminal as XTerm } from "@xterm/xterm";
import { FitAddon } from "@xterm/addon-fit";
import { consoleUrl } from "../api";

// One live console: an xterm.js terminal connected to the node over WebSocket.
export function Terminal({ lab, node, active }: { lab: string; node: string; active: boolean }) {
  const host = useRef<HTMLDivElement>(null);
  const fitRef = useRef<FitAddon | null>(null);
  const termRef = useRef<XTerm | null>(null);

  useEffect(() => {
    const term = new XTerm({
      cursorBlink: true,
      fontSize: 14,
      scrollback: 10000,
      fontFamily: '"IBM Plex Mono", ui-monospace, Menlo, Consolas, monospace',
      theme: { background: "#0b1524", foreground: "#e8eef5", cursor: "#2bb08f", selectionBackground: "#23364f" },
    });
    const fit = new FitAddon();
    term.loadAddon(fit);
    term.open(host.current!);
    termRef.current = term;
    fitRef.current = fit;

    let closed = false;
    const ws = new WebSocket(consoleUrl(lab, node));
    const sendSize = () => {
      if (ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify({ t: "r", c: term.cols, r: term.rows }));
    };
    ws.onopen = () => {
      try { fit.fit(); } catch { /* hidden pane */ }
      sendSize();
    };
    ws.onmessage = (e) => term.write(e.data);
    ws.onclose = () => {
      if (!closed) term.write("\r\n\x1b[90m[desconectado: cerrá la pestaña y abrí la consola de nuevo]\x1b[0m\r\n");
    };
    const data = term.onData((d) => ws.readyState === WebSocket.OPEN && ws.send(JSON.stringify({ t: "i", d })));
    const resize = term.onResize(sendSize);
    const observer = new ResizeObserver(() => {
      try { fit.fit(); } catch { /* hidden pane */ }
    });
    observer.observe(host.current!);

    return () => {
      closed = true;
      observer.disconnect();
      data.dispose();
      resize.dispose();
      ws.close();
      term.dispose();
    };
  }, [lab, node]);

  useEffect(() => {
    if (!active) return;
    requestAnimationFrame(() => {
      try { fitRef.current?.fit(); } catch { /* not visible yet */ }
      termRef.current?.focus();
    });
  }, [active]);

  return <div ref={host} style={{ width: "100%", height: "100%" }} />;
}
