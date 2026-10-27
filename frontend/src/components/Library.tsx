import { useCallback, useEffect, useMemo, useState } from "react";
import {
  api, formatSize, kindForFile, uploadImage, type Category, type Engine, type ImageInfo, type Template,
} from "../api";
import { DEVICE_ICONS, DeviceIcon, ICON_LABELS, Icon } from "../icons";
import { Dialog } from "./Overlays";

const KIND_LABEL: Record<string, string> = { qemu: "QEMU (QCOW2)", iol: "Cisco IOL", docker: "Docker" };
const CATEGORY_LABEL: Record<Category, string> = {
  router: "Router", switch: "Switch", security: "Seguridad", "end-device": "Equipo final", other: "Otro",
};
const ENGINE_LABEL: Record<Engine, string> = {
  qemu: "QEMU (imagen QCOW2)", iol: "Cisco IOL", docker: "Docker (contenedor)", switch: "Switch integrado",
};

type Upload = { name: string; progress: number; error?: string };

export function Library({ templates, onChanged, onClose, notify }: {
  templates: Template[];
  onChanged: () => void;
  onClose: () => void;
  notify: (msg: string, error?: boolean) => void;
}) {
  const [tab, setTab] = useState<"images" | "templates">("images");
  const [images, setImages] = useState<ImageInfo[]>([]);
  const [editing, setEditing] = useState<Partial<Template> | null>(null);

  const loadImages = useCallback(() => api.images().then(setImages).catch((e) => notify(e.message, true)), [notify]);
  useEffect(() => { loadImages(); }, [loadImages]);

  return (
    <Dialog title="Imágenes y plantillas" onClose={onClose} wide>
      <div className="tabs" role="tablist">
        <button role="tab" aria-selected={tab === "images"} onClick={() => { setTab("images"); setEditing(null); }}>
          Imágenes
        </button>
        <button role="tab" aria-selected={tab === "templates"} onClick={() => setTab("templates")}>
          Plantillas
        </button>
      </div>
      <div className="body" style={{ paddingTop: 16 }}>
        {tab === "images" ? (
          <Images images={images} reload={loadImages} notify={notify}
            onCreateTemplate={(img) => {
              setTab("templates");
              setEditing(templateFromImage(img));
            }} />
        ) : editing ? (
          <TemplateForm initial={editing} images={images} isNew={!templates.some((t) => t.id === editing.id)}
            onCancel={() => setEditing(null)}
            onSaved={() => { setEditing(null); onChanged(); }} notify={notify} />
        ) : (
          <Templates templates={templates} onEdit={setEditing} onChanged={onChanged} notify={notify} />
        )}
      </div>
    </Dialog>
  );
}

// ---------------------------------------------------------------- images

function Images({ images, reload, notify, onCreateTemplate }: {
  images: ImageInfo[];
  reload: () => void;
  notify: (msg: string, error?: boolean) => void;
  onCreateTemplate: (img: ImageInfo) => void;
}) {
  const [over, setOver] = useState(false);
  const [uploads, setUploads] = useState<Upload[]>([]);

  const send = async (files: FileList | File[]) => {
    for (const file of Array.from(files)) {
      const kind = kindForFile(file.name);
      if (!kind) {
        notify(`${file.name}: formato no reconocido. Use .qcow2, .img, .vmdk, .iso, .bin o .tar`, true);
        continue;
      }
      setUploads((u) => [...u, { name: file.name, progress: 0 }]);
      const set = (patch: Partial<Upload>) =>
        setUploads((u) => u.map((x) => (x.name === file.name ? { ...x, ...patch } : x)));
      try {
        await uploadImage(kind, file, (p) => set({ progress: p }));
        notify(`${file.name} cargada.`);
        setUploads((u) => u.filter((x) => x.name !== file.name));
        reload();
      } catch (e) {
        set({ error: (e as Error).message });
      }
    }
  };

  return (
    <>
      <label className={`dropzone ${over ? "over" : ""}`}
        onDragOver={(e) => { e.preventDefault(); setOver(true); }}
        onDragLeave={() => setOver(false)}
        onDrop={(e) => { e.preventDefault(); setOver(false); send(e.dataTransfer.files); }}>
        <Icon name="upload" size={26} />
        <div><strong>Arrastrá tus imágenes aquí</strong> o hacé clic para elegirlas</div>
        <div style={{ fontSize: 12.5, marginTop: 4 }}>
          QCOW2, IMG, VMDK o ISO para QEMU; .bin para Cisco IOL; .tar (docker save) para contenedores
        </div>
        <input type="file" multiple hidden onChange={(e) => e.target.files && send(e.target.files)} />
      </label>
      {uploads.map((u) => (
        <div key={u.name} style={{ marginBottom: 10 }}>
          <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13 }}>
            <span>{u.name}</span>
            <span>{u.error ? "" : `${Math.round(u.progress * 100)} %`}</span>
          </div>
          {u.error ? <div className="notice" style={{ marginTop: 4 }}>{u.error}</div> : (
            <div className="progress"><div style={{ width: `${u.progress * 100}%` }} /></div>
          )}
        </div>
      ))}
      <p className="notice info">
        SakbeLab no descarga imágenes de fabricantes: cargá las tuyas, con su licencia. Para archivos muy grandes
        también podés copiarlos por SCP a <code>/opt/sakbe/images/qemu/</code> o <code>/opt/sakbe/images/iol/</code>.
      </p>
      {images.length === 0 ? (
        <p style={{ color: "var(--ink-soft)" }}>Todavía no cargaste imágenes.</p>
      ) : (
        <table className="list">
          <thead><tr><th>Imagen</th><th>Tipo</th><th>Tamaño</th><th>SHA256</th><th /></tr></thead>
          <tbody>
            {images.map((img) => (
              <tr key={img.kind + img.name}>
                <td>{img.reference ?? img.name}</td>
                <td>{KIND_LABEL[img.kind]}</td>
                <td>{formatSize(img.size)}</td>
                <td className="mono" title={img.sha256 ?? ""}>{img.sha256 ? `${img.sha256.slice(0, 12)}…` : "sin calcular"}</td>
                <td style={{ textAlign: "right", whiteSpace: "nowrap" }}>
                  <button className="btn" style={{ padding: "4px 10px" }} onClick={() => onCreateTemplate(img)}>
                    Crear plantilla
                  </button>
                  <button className="icon-btn" title="Eliminar imagen" onClick={async () => {
                    if (!confirm(`¿Eliminar ${img.name}?`)) return;
                    try { await api.deleteImage(img.kind, img.name); reload(); }
                    catch (e) { notify((e as Error).message, true); }
                  }}><Icon name="trash" size={16} /></button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </>
  );
}

function slug(text: string) {
  return text.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "")
    .replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 48) || "plantilla";
}

// Known images get the settings their vendor (and GNS3) recommend.
function presetFor(fileName: string): Partial<Template> | null {
  const n = fileName.toLowerCase();
  if (/^vios[_-]?l2/.test(n)) {
    return {
      name: "Cisco vIOS-L2", vendor: "Cisco", category: "switch", icon: "l3switch", name_prefix: "SW",
      defaults: { ram: 1024, cpus: 1 },
      interfaces: { count: 16, naming: "Gi{slot}/{port}", start: 0, ports_per_slot: 4 },
      config: { nic: "e1000", disk_interface: "virtio", config: "ios-disk" },
    };
  }
  if (/^vios/.test(n)) {
    return {
      name: "Cisco vIOS", vendor: "Cisco", category: "router", icon: "router", name_prefix: "R",
      defaults: { ram: 1024, cpus: 1 },
      interfaces: { count: 8, naming: "Gi0/{index}", start: 0, ports_per_slot: 4 },
      config: { nic: "e1000", disk_interface: "virtio", config: "ios-disk" },
    };
  }
  if (/fortios|fgt|fortigate/.test(n)) {
    return {
      name: "FortiGate VM", vendor: "Fortinet", category: "security", icon: "firewall", name_prefix: "FW",
      defaults: { ram: 2048, cpus: 1 },
      interfaces: { count: 10, naming: "port{index}", start: 1, ports_per_slot: 4 },
      config: { nic: "virtio-net-pci", disk_interface: "virtio", extra_disks: [30] },
    };
  }
  return null;
}

function templateFromImage(img: ImageInfo): Partial<Template> {
  const preset = img.kind === "qemu" ? presetFor(img.name) : null;
  if (preset) {
    const base = img.name.replace(/\.(qcow2|img|vmdk|iso)$/i, "");
    return { id: slug(base), engine: "qemu", image: img.name, ...preset };
  }
  const base = (img.reference ?? img.name).replace(/\.(qcow2|img|vmdk|iso|bin|iol)$/i, "");
  const engine: Engine = img.kind;
  return {
    id: slug(base),
    name: base,
    vendor: "",
    engine,
    category: engine === "iol" ? "router" : "router",
    icon: "router",
    name_prefix: "R",
    image: img.reference ?? img.name,
    defaults: { ram: engine === "qemu" ? 1024 : 512, cpus: 1 },
    interfaces: engine === "iol"
      ? { count: 4, naming: "Ethernet{slot}/{port}", start: 0, ports_per_slot: 4 }
      : { count: 4, naming: engine === "docker" ? "eth{index}" : "Gi{index}", start: engine === "docker" ? 1 : 0, ports_per_slot: 4 },
  };
}

// ---------------------------------------------------------------- templates list

function Templates({ templates, onEdit, onChanged, notify }: {
  templates: Template[];
  onEdit: (t: Partial<Template>) => void;
  onChanged: () => void;
  notify: (msg: string, error?: boolean) => void;
}) {
  const sorted = [...templates].sort((a, b) => a.category.localeCompare(b.category) || a.name.localeCompare(b.name));
  return (
    <>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
        <span style={{ color: "var(--ink-soft)", fontSize: 13 }}>
          Una plantilla define cómo se crea cada equipo: imagen, recursos e interfaces.
        </span>
        <button className="btn primary" onClick={() => onEdit({
          id: "", name: "", engine: "qemu", category: "router", icon: "router", name_prefix: "R",
          defaults: { ram: 1024, cpus: 1 }, interfaces: { count: 4, naming: "Gi{index}", start: 0, ports_per_slot: 4 },
        })}><Icon name="plus" size={16} /> Nueva plantilla</button>
      </div>
      <table className="list">
        <thead><tr><th /><th>Plantilla</th><th>Categoría</th><th>Motor</th><th>Interfaces</th><th /></tr></thead>
        <tbody>
          {sorted.map((t) => (
            <tr key={t.id}>
              <td style={{ width: 40 }}><DeviceIcon icon={t.icon} size={30} muted={!t.available} /></td>
              <td>
                <div>{t.name}</div>
                <div style={{ fontSize: 12, color: "var(--ink-soft)" }}>
                  {[t.vendor, t.image].filter(Boolean).join(", ")}
                </div>
                {!t.available && <div style={{ fontSize: 12, color: "var(--amber)" }}>{t.unavailable_reason}</div>}
              </td>
              <td>{CATEGORY_LABEL[t.category]}</td>
              <td>{ENGINE_LABEL[t.engine]}</td>
              <td className="mono">{t.interface_names.length} ({t.interface_names[0]}…)</td>
              <td style={{ textAlign: "right", whiteSpace: "nowrap" }}>
                <button className="icon-btn" title="Editar" onClick={() => onEdit(t)}><Icon name="edit" size={16} /></button>
                <button className="icon-btn" title="Eliminar" onClick={async () => {
                  if (!confirm(`¿Eliminar la plantilla ${t.name}?`)) return;
                  try { await api.deleteTemplate(t.id); onChanged(); }
                  catch (e) { notify((e as Error).message, true); }
                }}><Icon name="trash" size={16} /></button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </>
  );
}

// ---------------------------------------------------------------- template form

function previewNames(i: Template["interfaces"]): string[] {
  const out: string[] = [];
  for (let n = i.start; n < i.start + Math.min(i.count, 64); n++) {
    const slot = Math.floor((n - i.start) / (i.ports_per_slot || 1));
    const port = (n - i.start) % (i.ports_per_slot || 1);
    out.push(i.naming.replace("{index}", String(n)).replace("{slot}", String(slot)).replace("{port}", String(port)));
  }
  return out;
}

function TemplateForm({ initial, images, isNew, onCancel, onSaved, notify }: {
  initial: Partial<Template>;
  images: ImageInfo[];
  isNew: boolean;
  onCancel: () => void;
  onSaved: () => void;
  notify: (msg: string, error?: boolean) => void;
}) {
  const [t, setT] = useState<Partial<Template>>(() => ({
    console: { type: "exec", command: ["/bin/sh"] },
    config: {},
    ...initial,
    defaults: { ...initial.defaults },
    interfaces: { count: 4, naming: "eth{index}", start: 0, ports_per_slot: 4, ...initial.interfaces },
  }));
  const [docker, setDocker] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const set = (patch: Partial<Template>) => setT((cur) => ({ ...cur, ...patch }));
  const iface = t.interfaces!;
  const names = useMemo(() => previewNames(iface), [iface]);

  useEffect(() => {
    if (t.engine === "docker") api.localDockerImages().then(setDocker).catch(() => setDocker([]));
  }, [t.engine]);

  const imageOptions = t.engine === "docker"
    ? docker
    : images.filter((i) => i.kind === t.engine).map((i) => i.name);

  const save = async () => {
    setBusy(true);
    try {
      const body = { ...t, id: isNew ? slug(t.id || t.name || "") : t.id };
      await api.saveTemplate(body, isNew);
      notify(`Plantilla ${t.name} guardada.`);
      onSaved();
    } catch (e) {
      notify((e as Error).message, true);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div>
      <div className="row">
        <label className="field">
          <span>Nombre</span>
          <input value={t.name ?? ""} placeholder="FortiGate 7.2" onChange={(e) => set({ name: e.target.value })} />
        </label>
        <label className="field">
          <span>Fabricante</span>
          <input value={t.vendor ?? ""} placeholder="Fortinet" onChange={(e) => set({ vendor: e.target.value })} />
        </label>
        <label className="field">
          <span>Categoría</span>
          <select value={t.category} onChange={(e) => set({ category: e.target.value as Category })}>
            {Object.entries(CATEGORY_LABEL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>
        </label>
      </div>
      <div className="field">
        <span>Ícono</span>
        <div className="icon-pick">
          {DEVICE_ICONS.map((ic) => (
            <button key={ic} type="button" aria-pressed={t.icon === ic} onClick={() => set({ icon: ic })}>
              <DeviceIcon icon={ic} size={34} />{ICON_LABELS[ic]}
            </button>
          ))}
        </div>
      </div>
      <div className="row">
        <label className="field">
          <span>Motor</span>
          <select value={t.engine} disabled={!isNew} onChange={(e) => set({ engine: e.target.value as Engine, image: null })}>
            {(["qemu", "iol", "docker"] as Engine[]).map((k) => <option key={k} value={k}>{ENGINE_LABEL[k]}</option>)}
            {t.engine === "switch" && <option value="switch">{ENGINE_LABEL.switch}</option>}
          </select>
        </label>
        {t.engine !== "switch" && (
          <label className="field">
            <span>Imagen</span>
            <select value={t.image ?? ""} onChange={(e) => set({ image: e.target.value || null })}>
              <option value="">Elegí una imagen</option>
              {t.image && !imageOptions.includes(t.image) && <option value={t.image}>{t.image}</option>}
              {imageOptions.map((n) => <option key={n} value={n}>{n}</option>)}
            </select>
          </label>
        )}
        <label className="field">
          <span>Prefijo del nombre</span>
          <input value={t.name_prefix ?? ""} placeholder="FW" onChange={(e) => set({ name_prefix: e.target.value })} />
          <span className="help">Los equipos se llamarán {t.name_prefix || "N"}1, {t.name_prefix || "N"}2…</span>
        </label>
      </div>
      {t.engine === "qemu" && (
        <fieldset className="group">
        <legend>Opciones de QEMU</legend>
        <div className="row">
          <label className="field">
            <span>Tarjeta de red</span>
            <select value={(t.config?.nic as string) ?? "virtio-net-pci"}
              onChange={(e) => set({ config: { ...t.config, nic: e.target.value } })}>
              <option value="virtio-net-pci">virtio (recomendada)</option>
              <option value="e1000">e1000 (Intel, compatible)</option>
              <option value="e1000e">e1000e</option>
              <option value="vmxnet3">vmxnet3 (VMware)</option>
              <option value="rtl8139">rtl8139</option>
            </select>
          </label>
          <label className="field">
            <span>Disco</span>
            <select value={(t.config?.disk_interface as string) ?? "virtio"}
              onChange={(e) => set({ config: { ...t.config, disk_interface: e.target.value } })}>
              <option value="virtio">virtio (recomendado)</option>
              <option value="ide">IDE (compatible)</option>
              <option value="scsi">SCSI</option>
            </select>
          </label>
          <label className="field">
            <span>Consola</span>
            <select value={(t.config?.display as string) ?? "serial"}
              onChange={(e) => set({ config: { ...t.config, display: e.target.value === "serial" ? undefined : e.target.value } })}>
              <option value="serial">Serial (texto, routers y firewalls)</option>
              <option value="vnc">Gráfica (VNC, equipos con escritorio)</option>
            </select>
          </label>
          <label className="field">
            <span>Configuración inicial</span>
            <select value={(t.config?.config as string) ?? ""}
              onChange={(e) => set({ config: { ...t.config, config: e.target.value || undefined } })}>
              <option value="">Por consola (sin disco)</option>
              <option value="ios-disk">Disco de configuración Cisco (vIOS, vIOS-L2)</option>
              <option value="cloud-init">cloud-init (VyOS, equipos modernos)</option>
            </select>
          </label>
          <label className="field">
            <span>Procesador</span>
            <select value={(t.config?.cpu as string) ?? ""}
              onChange={(e) => set({ config: { ...t.config, cpu: e.target.value || undefined } })}>
              <option value="">Automático (el del servidor)</option>
              <option value="kvm64">kvm64 (genérico, compatible)</option>
              <option value="qemu64">qemu64 (genérico)</option>
              <option value="Nehalem">Nehalem (Intel antiguo)</option>
            </select>
            <span className="help">Si un equipo arranca muy lento o se traba, probá kvm64.</span>
          </label>
          <label className="field">
            <span>Discos adicionales (GB)</span>
            <input value={((t.config?.extra_disks as number[]) ?? []).join(", ")} placeholder="30"
              onChange={(e) => {
                const sizes = e.target.value.split(/[ ,]+/).map(Number).filter((n) => n > 0);
                set({ config: { ...t.config, extra_disks: sizes.length ? sizes : undefined } });
              }} />
            <span className="help">Discos vacíos, por ejemplo 30 para FortiGate.</span>
          </label>
        </div>
        </fieldset>
      )}
      {t.engine !== "switch" && (
        <div className="row compact">
          <label className="field">
            <span>RAM (MB)</span>
            <input type="number" min={32} step={32} value={t.defaults?.ram ?? ""}
              onChange={(e) => set({ defaults: { ...t.defaults, ram: Number(e.target.value) || undefined } })} />
          </label>
          <label className="field">
            <span>vCPU</span>
            <input type="number" min={1} max={16} value={t.defaults?.cpus ?? ""}
              onChange={(e) => set({ defaults: { ...t.defaults, cpus: Number(e.target.value) || undefined } })} />
          </label>
        </div>
      )}
      <div className="row">
        <label className="field">
          <span>Cantidad de interfaces</span>
          <input type="number" min={1} max={64} value={iface.count}
            onChange={(e) => set({ interfaces: { ...iface, count: Number(e.target.value) || 1 } })} />
        </label>
        <label className="field">
          <span>Nombre de interfaz</span>
          <input value={iface.naming} onChange={(e) => set({ interfaces: { ...iface, naming: e.target.value } })} />
          <span className="help">Usá {"{index}"}, o {"{slot}"} y {"{port}"}.</span>
        </label>
        <label className="field">
          <span>Primer número</span>
          <input type="number" min={0} value={iface.start}
            onChange={(e) => set({ interfaces: { ...iface, start: Number(e.target.value) || 0 } })} />
        </label>
      </div>
      <div className="field">
        <span>Interfaces resultantes</span>
        <div className="chips">{names.map((n) => <span key={n}>{n}</span>)}</div>
      </div>
      {t.engine === "docker" && (
        <label className="field">
          <span>Comando de consola</span>
          <input value={(t.console?.command ?? []).join(" ")}
            onChange={(e) => set({ console: { type: "exec", command: e.target.value.split(" ").filter(Boolean) } })} />
        </label>
      )}
      <div style={{ display: "flex", justifyContent: "flex-end", gap: 8, marginTop: 8 }}>
        <button className="btn" onClick={onCancel}>Volver</button>
        <button className="btn primary" onClick={save} disabled={busy || !t.name || (t.engine !== "switch" && !t.image)}>
          {isNew ? "Crear plantilla" : "Guardar plantilla"}
        </button>
      </div>
    </div>
  );
}
