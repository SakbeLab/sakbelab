import { useEffect, useRef, useState, type ReactNode } from "react";
import type { LabNode } from "../api";
import { Icon } from "../icons";

// ---------------------------------------------------------------- floating menu

export interface MenuItem {
  label: string;
  icon?: string;
  onClick?: () => void;
  disabled?: boolean;
  danger?: boolean;
  separator?: boolean;
}

export function Menu({ x, y, title, items, onClose, children }: {
  x: number;
  y: number;
  title?: string;
  items?: MenuItem[];
  onClose: () => void;
  children?: ReactNode;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const [pos, setPos] = useState({ x, y });
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const r = el.getBoundingClientRect();
    setPos({
      x: Math.min(x, window.innerWidth - r.width - 8),
      y: Math.min(y, window.innerHeight - r.height - 8),
    });
  }, [x, y]);
  useEffect(() => {
    const away = (e: MouseEvent) => !ref.current?.contains(e.target as Node) && onClose();
    const esc = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("mousedown", away);
    window.addEventListener("keydown", esc);
    return () => {
      window.removeEventListener("mousedown", away);
      window.removeEventListener("keydown", esc);
    };
  }, [onClose]);

  return (
    <div ref={ref} className="menu" role="menu" style={{ left: pos.x, top: pos.y }}
      onContextMenu={(e) => e.preventDefault()}>
      {title && <div className="menu-title">{title}</div>}
      {items?.map((it, i) =>
        it.separator ? <hr key={i} /> : (
          <button key={i} role="menuitem" disabled={it.disabled} className={it.danger ? "danger" : ""}
            onClick={() => { onClose(); it.onClick?.(); }}>
            {it.icon && <Icon name={it.icon} size={16} />}
            {it.label}
          </button>
        ),
      )}
      {children}
    </div>
  );
}

// ---------------------------------------------------------------- interface picker

export function InterfacePicker({ x, y, node, onPick, onClose }: {
  x: number;
  y: number;
  node: LabNode;
  onPick: (iface: string) => void;
  onClose: () => void;
}) {
  const used = new Set(node.used_interfaces);
  return (
    <Menu x={x} y={y} title={`Interfaz de ${node.name}`} onClose={onClose}>
      <div className="iface-list">
        {node.interfaces.map((iface) => (
          <button key={iface} disabled={used.has(iface)} onClick={() => { onClose(); onPick(iface); }}>
            {iface}
            {used.has(iface) && <small>en uso</small>}
          </button>
        ))}
      </div>
    </Menu>
  );
}

// ---------------------------------------------------------------- dialog shell

export function Dialog({ title, onClose, children, footer, wide }: {
  title: string;
  onClose: () => void;
  children: ReactNode;
  footer?: ReactNode;
  wide?: boolean;
}) {
  useEffect(() => {
    const esc = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", esc);
    return () => window.removeEventListener("keydown", esc);
  }, [onClose]);
  return (
    <div className="backdrop" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div className={`dialog ${wide ? "wide" : ""}`} role="dialog" aria-modal="true" aria-label={title}>
        <header>
          <h3>{title}</h3>
          <button onClick={onClose} aria-label="Cerrar"><Icon name="close" /></button>
        </header>
        {children}
        {footer && <footer>{footer}</footer>}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------- node settings

export function NodeDialog({ node, onSave, onClose }: {
  node: LabNode;
  onSave: (patch: Partial<LabNode>) => Promise<void>;
  onClose: () => void;
}) {
  const running = node.state === "running";
  const [name, setName] = useState(node.name);
  const [ram, setRam] = useState(node.ram?.toString() ?? "");
  const [cpus, setCpus] = useState(node.cpus?.toString() ?? "");
  const [config, setConfig] = useState(node.config ?? "");
  const [busy, setBusy] = useState(false);
  const isSwitch = !node.has_console;

  const submit = async () => {
    setBusy(true);
    const patch: Partial<LabNode> = { config: config || null };
    if (name !== node.name) patch.name = name;
    patch.ram = ram ? Number(ram) : null;
    patch.cpus = cpus ? Number(cpus) : null;
    try {
      await onSave(patch);
      onClose();
    } finally {
      setBusy(false);
    }
  };

  return (
    <Dialog title={`Configurar ${node.name}`} onClose={onClose}
      footer={<>
        <button className="btn" onClick={onClose}>Cancelar</button>
        <button className="btn primary" onClick={submit} disabled={busy || !name}>Guardar cambios</button>
      </>}>
      <div className="body">
        {running && (
          <p className="notice">El nodo está encendido. Los cambios de RAM, CPU y configuración inicial se
            aplican la próxima vez que lo enciendas. Para renombrarlo, apagalo primero.</p>
        )}
        <label className="field">
          <span>Nombre</span>
          <input value={name} disabled={running} onChange={(e) => setName(e.target.value)} />
        </label>
        {!isSwitch && (
          <>
            <div className="row">
              <label className="field">
                <span>RAM (MB)</span>
                <input type="number" min={32} step={32} value={ram} placeholder="Según la plantilla"
                  onChange={(e) => setRam(e.target.value)} />
              </label>
              <label className="field">
                <span>vCPU</span>
                <input type="number" min={1} max={16} value={cpus} placeholder="Según la plantilla"
                  onChange={(e) => setCpus(e.target.value)} />
              </label>
            </div>
            <label className="field">
              <span>Configuración inicial</span>
              <textarea value={config} spellCheck={false} onChange={(e) => setConfig(e.target.value)}
                placeholder={"hostname R1\ninterface eth1\n ip address 10.0.0.1/30"} />
              <span className="help">Se aplica al encender el nodo. Usá "Guardar configuraciones" en la barra
                superior para traer aquí la configuración actual de los equipos encendidos.</span>
            </label>
          </>
        )}
        <label className="field">
          <span>Plantilla</span>
          <input value={node.template_name} disabled />
        </label>
      </div>
    </Dialog>
  );
}
