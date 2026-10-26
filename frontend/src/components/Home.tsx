import { useEffect, useRef, useState } from "react";
import { api, type LabSummary } from "../api";
import { Icon } from "../icons";

// Start screen: open, create or import a lab.
export function Home({ onOpen, notify }: { onOpen: (name: string) => void; notify: (m: string, e?: boolean) => void }) {
  const [labs, setLabs] = useState<LabSummary[] | null>(null);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const file = useRef<HTMLInputElement>(null);

  const load = () => api.labs().then(setLabs).catch((e) => notify(e.message, true));
  useEffect(() => { load(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const create = async (e: React.FormEvent) => {
    e.preventDefault();
    const clean = name.trim().toLowerCase().replace(/\s+/g, "-");
    try {
      await api.createLab(clean, description.trim());
      onOpen(clean);
    } catch (err) {
      notify((err as Error).message, true);
    }
  };

  const importFile = async (f: File) => {
    try {
      const lab = await api.importYaml(await f.text());
      notify(`Lab ${lab.name} importado.`);
      onOpen(lab.name);
    } catch (err) {
      notify((err as Error).message, true);
    }
  };

  return (
    <main className="home">
      <div className="home-inner">
        <h1><b>Sakbe</b><span>Lab</span></h1>
        <p className="lead">
          Armá tu red arrastrando routers, switches y equipos al lienzo, conectalos y abrí sus consolas desde el navegador.
        </p>

        <h2>Tus labs</h2>
        <div className="lab-rows">
          {labs === null && <div className="empty">Cargando…</div>}
          {labs?.length === 0 && <div className="empty">Todavía no hay labs. Creá el primero aquí abajo.</div>}
          {labs?.map((l) => (
            <div key={l.name} className="lab-row" role="button" tabIndex={0}
              onClick={() => onOpen(l.name)} onKeyDown={(e) => e.key === "Enter" && onOpen(l.name)}>
              <div>
                <div>{l.name}</div>
                {l.description && <div className="desc">{l.description}</div>}
              </div>
              <small>{l.nodes} equipos, {l.running} encendidos</small>
              <button title={`Eliminar ${l.name}`} onClick={async (e) => {
                e.stopPropagation();
                if (!confirm(`¿Eliminar el lab "${l.name}"? Se apagan sus equipos y se borra su definición.`)) return;
                try { await api.deleteLab(l.name); load(); } catch (err) { notify((err as Error).message, true); }
              }}><Icon name="trash" size={16} /></button>
            </div>
          ))}
        </div>

        <h2>Nuevo lab</h2>
        <form onSubmit={create}>
          <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Nombre, por ejemplo ospf-area0"
            pattern="[A-Za-z0-9][A-Za-z0-9 _\-]{0,31}" required aria-label="Nombre del lab" />
          <input value={description} onChange={(e) => setDescription(e.target.value)}
            placeholder="Descripción (opcional)" aria-label="Descripción" />
          <button className="btn primary" type="submit"><Icon name="plus" size={16} /> Crear lab</button>
        </form>

        <h2>Importar</h2>
        <button className="btn" onClick={() => file.current?.click()}>
          <Icon name="upload" size={16} /> Importar lab desde YAML
        </button>
        <input ref={file} type="file" accept=".yml,.yaml" hidden
          onChange={(e) => e.target.files?.[0] && importFile(e.target.files[0])} />
      </div>
    </main>
  );
}
