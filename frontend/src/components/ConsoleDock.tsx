import { useRef } from "react";
import { Icon } from "../icons";
import { Terminal } from "./Terminal";
import { VncConsole } from "./VncConsole";

export interface ConsoleTab {
  key: string;
  lab: string;
  node: string;
  kind: "serial" | "vnc";
}

interface Props {
  tabs: ConsoleTab[];
  active: string | null;
  height: number;
  onHeight: (h: number) => void;
  onSelect: (key: string) => void;
  onClose: (key: string) => void;
  onCloseAll: () => void;
}

// Bottom dock with one tab per open console, like the GNS3 console panel.
export function ConsoleDock({ tabs, active, height, onHeight, onSelect, onClose, onCloseAll }: Props) {
  const start = useRef<{ y: number; h: number } | null>(null);
  if (!tabs.length) return null;

  const onGrip = (e: React.PointerEvent) => {
    start.current = { y: e.clientY, h: height };
    (e.target as HTMLElement).setPointerCapture(e.pointerId);
  };
  const onMove = (e: React.PointerEvent) => {
    if (!start.current) return;
    const h = start.current.h + (start.current.y - e.clientY);
    onHeight(Math.max(140, Math.min(window.innerHeight - 160, h)));
  };

  const popout = (t: ConsoleTab) => {
    window.open(`/console/${encodeURIComponent(t.lab)}/${encodeURIComponent(t.node)}${t.kind === "vnc" ? "?vnc=1" : ""}`, `console-${t.key}`,
      "width=900,height=560");
    onClose(t.key);
  };

  return (
    <section className="dock" style={{ height }} aria-label="Consolas">
      <div className="dock-grip" onPointerDown={onGrip} onPointerMove={onMove}
        onPointerUp={() => (start.current = null)} title="Arrastrá para cambiar la altura" />
      <div className="dock-tabs" role="tablist">
        {tabs.map((t) => (
          <div key={t.key} role="tab" aria-selected={t.key === active}
            className={`dock-tab ${t.key === active ? "active" : ""}`} onClick={() => onSelect(t.key)}>
            <Icon name="terminal" size={15} />
            {t.node}
            <button title="Abrir en otra ventana" onClick={(e) => { e.stopPropagation(); popout(t); }}>
              <Icon name="popout" size={14} />
            </button>
            <button title="Cerrar consola" onClick={(e) => { e.stopPropagation(); onClose(t.key); }}>
              <Icon name="close" size={14} />
            </button>
          </div>
        ))}
        <div className="dock-actions">
          <button className="tool" onClick={onCloseAll} title="Cerrar todas las consolas">
            <span className="label">Cerrar todas</span>
          </button>
        </div>
      </div>
      <div className="dock-body">
        {tabs.map((t) => (
          <div key={t.key} className={`term-pane ${t.key === active ? "active" : ""}`}>
            {t.kind === "vnc"
              ? <VncConsole lab={t.lab} node={t.node} active={t.key === active} />
              : <Terminal lab={t.lab} node={t.node} active={t.key === active} />}
          </div>
        ))}
      </div>
    </section>
  );
}
