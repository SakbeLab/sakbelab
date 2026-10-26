import type { Category, Template } from "../api";
import { DeviceIcon, Icon } from "../icons";

export type Filter = Category | "all";

const CATEGORIES: { id: Filter; label: string; icon: string }[] = [
  { id: "router", label: "Routers", icon: "router" },
  { id: "switch", label: "Switches", icon: "switch" },
  { id: "security", label: "Seguridad", icon: "firewall" },
  { id: "end-device", label: "Equipos finales", icon: "pc" },
  { id: "all", label: "Todos los dispositivos", icon: "" },
];

export const DRAG_TYPE = "application/x-sakbe-template";

export function CategoryRail({ filter, onFilter, linking, onLinking }: {
  filter: Filter;
  onFilter: (f: Filter) => void;
  linking: boolean;
  onLinking: () => void;
}) {
  return (
    <nav className="rail" aria-label="Categorías de dispositivos">
      {CATEGORIES.map((c) => (
        <button key={c.id} title={c.label} aria-label={c.label} aria-pressed={filter === c.id}
          onClick={() => onFilter(c.id)}>
          {c.icon ? <DeviceIcon icon={c.icon} size={30} /> : <span style={{ color: "#e8eef5" }}><Icon name="list" size={22} /></span>}
        </button>
      ))}
      <button className="rail-link" title="Agregar enlace (L)" aria-label="Agregar enlace"
        aria-pressed={linking} onClick={onLinking}>
        <Icon name="link" size={24} />
      </button>
    </nav>
  );
}

export function DevicePanel({ templates, filter, onManage }: {
  templates: Template[];
  filter: Filter;
  onManage: () => void;
}) {
  const shown = templates
    .filter((t) => filter === "all" || t.category === filter)
    .sort((a, b) => Number(b.available) - Number(a.available) || a.name.localeCompare(b.name));
  const title = CATEGORIES.find((c) => c.id === filter)?.label ?? "Dispositivos";

  return (
    <aside className="devices" aria-label="Dispositivos">
      <h2>{title}</h2>
      <p className="hint">Arrastrá un dispositivo al lienzo.</p>
      <div className="device-list">
        {shown.length === 0 && <p className="hint">No hay plantillas en esta categoría.</p>}
        {shown.map((t) => (
          <div key={t.id} className={`device ${t.available ? "" : "off"}`} draggable={t.available}
            title={t.available ? `${t.name}: arrastralo al lienzo` : t.unavailable_reason}
            onDragStart={(e) => {
              e.dataTransfer.setData(DRAG_TYPE, t.id);
              e.dataTransfer.effectAllowed = "copy";
            }}>
            <DeviceIcon icon={t.icon} size={34} muted={!t.available} />
            <div>
              <div className="name">{t.name}</div>
              <div className="meta">{t.available ? t.vendor || t.engine : "Próximamente"}</div>
            </div>
          </div>
        ))}
      </div>
      <button className="manage" onClick={onManage}>
        <Icon name="library" size={16} /> Imágenes y plantillas
      </button>
    </aside>
  );
}
