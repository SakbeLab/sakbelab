import { useEffect, useRef, useState } from "react";
import RFB from "@novnc/novnc/lib/rfb";
import { Icon } from "../icons";

function vncUrl(lab: string, node: string): string {
  const proto = location.protocol === "https:" ? "wss" : "ws";
  const enc = encodeURIComponent;
  return `${proto}://${location.host}/api/v1/labs/${enc(lab)}/nodes/${enc(node)}/vnc`;
}

// Graphical console (VNC) for QEMU nodes, drawn with noVNC.
export function VncConsole({ lab, node, active }: { lab: string; node: string; active: boolean }) {
  const host = useRef<HTMLDivElement>(null);
  const rfbRef = useRef<RFB | null>(null);
  const [status, setStatus] = useState("Conectando…");

  useEffect(() => {
    const rfb = new RFB(host.current!, vncUrl(lab, node), { wsProtocols: ["binary"], shared: true });
    rfb.scaleViewport = true;
    rfb.background = "#0b1524";
    rfb.focusOnClick = true;
    rfb.addEventListener("connect", () => setStatus(""));
    rfb.addEventListener("disconnect", () => setStatus("Desconectado: cerrá la pestaña y abrí la consola de nuevo."));
    rfbRef.current = rfb;
    return () => rfb.disconnect();
  }, [lab, node]);

  useEffect(() => {
    if (active) rfbRef.current?.focus();
  }, [active]);

  return (
    <div style={{ position: "relative", width: "100%", height: "100%" }}>
      <div ref={host} style={{ width: "100%", height: "100%" }} />
      {status && <div className="vnc-status">{status}</div>}
      <button className="vnc-cad" title="Enviar Ctrl+Alt+Supr" onClick={() => rfbRef.current?.sendCtrlAltDel()}>
        <Icon name="settings" size={14} /> Ctrl+Alt+Supr
      </button>
    </div>
  );
}
