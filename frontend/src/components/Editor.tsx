import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  Background, BackgroundVariant, Controls, MiniMap, ReactFlow, useNodesState, useReactFlow,
  type Edge, type Node, type NodeChange,
} from "@xyflow/react";
import { api, type Lab, type LabNode, type Template } from "../api";
import { Icon } from "../icons";
import { ConsoleDock, type ConsoleTab } from "./ConsoleDock";
import { CategoryRail, DevicePanel, DRAG_TYPE, type Filter } from "./DevicePanel";
import {
  DeviceNode, LinkEdge, NoteNode, type DeviceFlowNode, type LinkFlowEdge, type NoteFlowNode,
} from "./FlowParts";
import { InterfacePicker, Menu, NodeDialog, type MenuItem } from "./Overlays";

const nodeTypes = { device: DeviceNode, note: NoteNode };
const edgeTypes = { link: LinkEdge };
const POLL_MS = 3000;

type MenuState =
  | { kind: "node"; x: number; y: number; node: LabNode }
  | { kind: "link"; x: number; y: number; id: string; label: string }
  | { kind: "note"; x: number; y: number; id: string; locked: boolean }
  | { kind: "pane"; x: number; y: number; fx: number; fy: number }
  | null;

type Pending = { node: string; iface: string } | null;

const STATE_TEXT = { running: "todo encendido", stopped: "apagado", partial: "parcialmente encendido" };

export function Editor({ labName, templates, onExit, onLibrary, notify }: {
  labName: string;
  templates: Template[];
  onExit: () => void;
  onLibrary: () => void;
  notify: (msg: string, error?: boolean) => void;
}) {
  const [lab, setLab] = useState<Lab | null>(null);
  const [filter, setFilter] = useState<Filter>("router");
  const [linking, setLinking] = useState(false);
  const [pending, setPending] = useState<Pending>(null);
  const [picker, setPicker] = useState<{ x: number; y: number; node: LabNode } | null>(null);
  const [menu, setMenu] = useState<MenuState>(null);
  const [editNode, setEditNode] = useState<LabNode | null>(null);
  const [showIfaces, setShowIfaces] = useState(true);
  const [summaryOpen, setSummaryOpen] = useState(true);
  const [consoles, setConsoles] = useState<ConsoleTab[]>([]);
  const [activeConsole, setActiveConsole] = useState<string | null>(null);
  const [dockHeight, setDockHeight] = useState(280);
  const [busy, setBusy] = useState<string | null>(null);
  const dragging = useRef(false);
  const fitted = useRef(false);
  const flow = useReactFlow();
  const [nodes, setNodes, onNodesChangeBase] = useNodesState<Node>([]);

  // ------------------------------------------------------------ data

  const refresh = useCallback(async () => {
    try {
      const next = await api.lab(labName);
      if (!dragging.current) setLab(next);
    } catch (e) {
      notify((e as Error).message, true);
    }
  }, [labName, notify]);

  useEffect(() => {
    refresh();
    const t = setInterval(refresh, POLL_MS);
    return () => clearInterval(t);
  }, [refresh]);

  const run = useCallback(async (label: string | null, action: () => Promise<Lab | null | void>) => {
    if (label) setBusy(label);
    try {
      const result = await action();
      if (result && "nodes" in result) {
        setLab(result);
        result.errors?.forEach((e) => notify(e, true));
      } else {
        await refresh();
      }
    } catch (e) {
      notify((e as Error).message, true);
      await refresh();
    } finally {
      if (label) setBusy(null);
    }
  }, [notify, refresh]);

  const saveNote = useCallback((id: string, text: string) => {
    run(null, () => api.patchNote(labName, id, { text }));
  }, [labName, run]);

  // ------------------------------------------------------------ lab -> flow

  useEffect(() => {
    if (!lab) return;
    setNodes((prev) => {
      const selected = new Set(prev.filter((n) => n.selected).map((n) => n.id));
      const devices: DeviceFlowNode[] = lab.nodes.map((n) => ({
        id: `n:${n.name}`,
        type: "device",
        position: { x: n.x, y: n.y },
        data: { node: n },
        draggable: !n.locked,
        selected: selected.has(`n:${n.name}`),
      }));
      const notes: NoteFlowNode[] = lab.notes.map((n) => ({
        id: `note:${n.id}`,
        type: "note",
        position: { x: n.x, y: n.y },
        data: { note: n, onSave: saveNote },
        draggable: !n.locked,
        selected: selected.has(`note:${n.id}`),
        zIndex: -1,
      }));
      return [...notes, ...devices];
    });
    if (!fitted.current && lab.nodes.length) {
      fitted.current = true;
      requestAnimationFrame(() => flow.fitView({ padding: 0.3, maxZoom: 1.2 }));
    }
  }, [lab, setNodes, saveNote, flow]);

  const edges: Edge[] = useMemo(() => (lab?.links ?? []).map((l): LinkFlowEdge => {
    const [a, aIface] = l.a.split(":");
    const [b, bIface] = l.b.split(":");
    return {
      id: l.id,
      source: `n:${a}`,
      target: `n:${b}`,
      type: "link",
      data: { aIface, bIface, aUp: l.a_up, bUp: l.b_up, showIfaces },
    };
  }), [lab, showIfaces]);

  // ------------------------------------------------------------ canvas events

  const onNodesChange = useCallback((changes: NodeChange[]) => {
    onNodesChangeBase(changes.filter((c) => c.type !== "remove"));
  }, [onNodesChangeBase]);

  const onNodeDragStart = () => { dragging.current = true; };
  const onNodeDragStop = useCallback((_: unknown, __: Node, moved: Node[]) => {
    dragging.current = false;
    for (const n of moved) {
      const x = Math.round(n.position.x);
      const y = Math.round(n.position.y);
      if (n.id.startsWith("n:")) run(null, () => api.patchNode(labName, n.id.slice(2), { x, y }));
      else run(null, () => api.patchNote(labName, n.id.slice(5), { x, y }));
    }
  }, [labName, run]);

  const deviceOf = (n: Node) => (n.type === "device" ? (n as DeviceFlowNode).data.node : null);

  const onNodeClick = (e: React.MouseEvent, n: Node) => {
    const dev = deviceOf(n);
    if (!linking || !dev) return;
    if (pending && pending.node === dev.name) return;
    setPicker({ x: e.clientX, y: e.clientY, node: dev });
  };

  const pickInterface = (iface: string) => {
    if (!picker) return;
    const here = { node: picker.node.name, iface };
    if (!pending) {
      setPending(here);
      return;
    }
    const a = `${pending.node}:${pending.iface}`;
    const b = `${here.node}:${here.iface}`;
    setPending(null);
    run(null, () => api.addLink(labName, a, b));
  };

  const stopLinking = () => {
    setLinking(false);
    setPending(null);
    setPicker(null);
  };

  const openConsole = useCallback((node: LabNode) => {
    if (!node.has_console) return;
    if (node.state !== "running") {
      notify(`Encendé ${node.name} para abrir su consola.`, true);
      return;
    }
    const key = `${labName}/${node.name}`;
    setConsoles((tabs) => (tabs.some((t) => t.key === key) ? tabs : [...tabs, { key, lab: labName, node: node.name }]));
    setActiveConsole(key);
  }, [labName, notify]);

  const closeConsole = (key: string) => {
    setConsoles((tabs) => {
      const rest = tabs.filter((t) => t.key !== key);
      if (activeConsole === key) setActiveConsole(rest.at(-1)?.key ?? null);
      return rest;
    });
  };

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    const id = e.dataTransfer.getData(DRAG_TYPE);
    if (!id) return;
    const p = flow.screenToFlowPosition({ x: e.clientX, y: e.clientY });
    run(null, () => api.addNode(labName, id, Math.round(p.x - 32), Math.round(p.y - 28)));
  };

  const deleteSelected = useCallback(() => {
    const selectedNodes = nodes.filter((n) => n.selected);
    const selectedEdges = flow.getEdges().filter((e) => e.selected);
    if (!selectedNodes.length && !selectedEdges.length) return;
    const locked = selectedNodes.filter((n) => !n.draggable);
    if (locked.length) notify("Los elementos bloqueados no se eliminan. Desbloquealos primero.", true);
    const deletable = selectedNodes.filter((n) => n.draggable);
    if (deletable.some((n) => n.id.startsWith("n:"))
      && !confirm(`¿Eliminar ${deletable.length} elemento(s)? Los equipos se apagan y se pierden sus enlaces.`)) return;
    run(null, async () => {
      let last: Lab | null = null;
      for (const e of selectedEdges) last = await api.deleteLink(labName, e.id);
      for (const n of deletable) {
        last = n.id.startsWith("n:")
          ? await api.deleteNode(labName, n.id.slice(2))
          : await api.deleteNote(labName, n.id.slice(5));
      }
      return last;
    });
  }, [nodes, flow, labName, notify, run]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const typing = (e.target as HTMLElement).closest("input, textarea, select, .xterm");
      if (typing) return;
      if (e.key === "Escape") stopLinking();
      if (e.key === "Delete" || e.key === "Backspace") deleteSelected();
      if (e.key.toLowerCase() === "l" && !e.ctrlKey && !e.metaKey) {
        setLinking((v) => !v);
        setPending(null);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [deleteSelected]);

  const addNoteAt = (x: number, y: number) => run(null, () => api.addNote(labName, "", Math.round(x), Math.round(y)));
  const addNoteCentered = () => {
    const box = document.querySelector(".canvas")!.getBoundingClientRect();
    const p = flow.screenToFlowPosition({ x: box.left + box.width / 2, y: box.top + box.height / 2 });
    addNoteAt(p.x - 70, p.y - 20);
  };

  // ------------------------------------------------------------ menus

  const nodeMenu = (n: LabNode): MenuItem[] => {
    const on = n.state === "running";
    const switchLike = !n.has_console;
    return [
      { label: "Encender", icon: "play", disabled: on, onClick: () => run(null, () => api.nodeAction(labName, n.name, "start")) },
      { label: "Apagar", icon: "stop", disabled: !on, onClick: () => run(null, () => api.nodeAction(labName, n.name, "stop")) },
      { label: "Reiniciar", icon: "reload", disabled: !on, onClick: () => run(null, () => api.nodeAction(labName, n.name, "reload")) },
      { separator: true, label: "" },
      { label: "Consola", icon: "terminal", disabled: !on || switchLike, onClick: () => openConsole(n) },
      { label: "Configurar…", icon: "settings", onClick: () => setEditNode(n) },
      {
        label: n.locked ? "Desbloquear" : "Bloquear", icon: n.locked ? "unlock" : "lock",
        onClick: () => run(null, () => api.patchNode(labName, n.name, { locked: !n.locked })),
      },
      { separator: true, label: "" },
      {
        label: "Eliminar", icon: "trash", danger: true, disabled: n.locked,
        onClick: () => confirm(`¿Eliminar ${n.name}? Se apaga y se pierden sus enlaces.`)
          && run(null, () => api.deleteNode(labName, n.name)),
      },
    ];
  };

  // ------------------------------------------------------------ render

  const allLocked = !!lab && [...lab.nodes, ...lab.notes].length > 0
    && [...lab.nodes, ...lab.notes].every((n) => n.locked);
  const anyRunning = lab?.nodes.some((n) => n.state === "running");
  const anyStopped = lab?.nodes.some((n) => n.state !== "running");

  return (
    <div className="app" style={{ gridTemplateRows: `48px 1fr ${consoles.length ? `${dockHeight}px` : "0px"}` }}>
      <header className="topbar">
        <div className="brand"><b>Sakbe</b><span>Lab</span></div>
        <button className="lab-switch" onClick={onExit} title="Volver a tus labs">
          <Icon name="back" size={15} />
          <strong>{labName}</strong>
          {lab && <span className="lab-state">{STATE_TEXT[lab.state]}</span>}
        </button>
        <button className="tool go" disabled={!anyStopped || !!busy} title="Encender todos los equipos"
          onClick={() => run("start", () => api.labAction(labName, "start"))}>
          <Icon name="play" /><span className="label">{busy === "start" ? "Encendiendo…" : "Encender todo"}</span>
        </button>
        <button className="tool halt" disabled={!anyRunning || !!busy} title="Apagar todos los equipos"
          onClick={() => run("stop", async () => { setConsoles([]); return api.labAction(labName, "stop"); })}>
          <Icon name="stop" /><span className="label">{busy === "stop" ? "Apagando…" : "Apagar todo"}</span>
        </button>
        <button className="tool" disabled={!anyRunning} title="Guardar en el lab la configuración actual de los equipos encendidos"
          onClick={() => run(null, async () => {
            const r = await api.saveConfigs(labName);
            notify(r.saved.length ? `Configuración guardada: ${r.saved.join(", ")}.` : "Ningún equipo tiene configuración para guardar.");
          })}>
          <Icon name="save" /><span className="label optional">Guardar configuraciones</span>
        </button>
        <span className="sep" />
        <button className="tool" aria-pressed={linking} title="Agregar enlace (L)"
          onClick={() => (linking ? stopLinking() : setLinking(true))}>
          <Icon name="link" /><span className="label">Enlace</span>
        </button>
        <button className="tool" title="Agregar una nota de texto" onClick={addNoteCentered}>
          <Icon name="note" /><span className="label optional">Nota</span>
        </button>
        <button className="tool" aria-pressed={showIfaces} title="Mostrar los nombres de interfaz en los enlaces"
          onClick={() => setShowIfaces((v) => !v)}>
          <Icon name="tag" /><span className="label optional">Interfaces</span>
        </button>
        <button className="tool" title={allLocked ? "Desbloquear todos los elementos" : "Bloquear todos los elementos"}
          onClick={() => run(null, () => api.lockAll(labName, !allLocked))}>
          <Icon name={allLocked ? "unlock" : "lock"} />
          <span className="label optional">{allLocked ? "Desbloquear todo" : "Bloquear todo"}</span>
        </button>
        <button className="tool" title="Ajustar la vista a la topología" onClick={() => flow.fitView({ padding: 0.3, maxZoom: 1.2 })}>
          <Icon name="fit" />
        </button>
        <div className="spacer" />
        <a className="tool" href={`/api/v1/labs/${encodeURIComponent(labName)}/yaml`} title="Descargar el lab en YAML">
          <Icon name="download" /><span className="label optional">Exportar</span>
        </a>
        <button className="tool" onClick={onLibrary} title="Imágenes y plantillas">
          <Icon name="library" /><span className="label optional">Imágenes y plantillas</span>
        </button>
      </header>

      <div className="workspace">
        <CategoryRail filter={filter} onFilter={setFilter} linking={linking}
          onLinking={() => (linking ? stopLinking() : setLinking(true))} />
        <DevicePanel templates={templates} filter={filter} onManage={onLibrary} />

        <div className={`canvas ${linking ? "linking" : ""}`}
          onDragOver={(e) => { e.preventDefault(); e.dataTransfer.dropEffect = "copy"; }} onDrop={onDrop}>
          {linking && (
            <div className="canvas-banner" role="status">
              {pending
                ? <>Desde {pending.node} {pending.iface}: elegí el otro equipo</>
                : <>Modo enlace: hacé clic en el primer equipo</>}
              <button onClick={stopLinking}>Terminar</button>
            </div>
          )}
          {lab && lab.nodes.length === 0 && lab.notes.length === 0 && (
            <div className="canvas-empty"><div>
              <strong>Lienzo vacío</strong>
              Arrastrá un router o un switch desde el panel izquierdo para empezar.
            </div></div>
          )}
          <ReactFlow
            nodes={nodes}
            edges={edges}
            nodeTypes={nodeTypes}
            edgeTypes={edgeTypes}
            onNodesChange={onNodesChange}
            onNodeDragStart={onNodeDragStart}
            onNodeDragStop={onNodeDragStop}
            onNodeClick={onNodeClick}
            onNodeDoubleClick={(_, n) => { const d = deviceOf(n); if (d && !linking) openConsole(d); }}
            onNodeContextMenu={(e, n) => {
              e.preventDefault();
              const d = deviceOf(n);
              if (d) setMenu({ kind: "node", x: e.clientX, y: e.clientY, node: d });
              else if (n.type === "note") {
                const note = (n as NoteFlowNode).data.note;
                setMenu({ kind: "note", x: e.clientX, y: e.clientY, id: note.id, locked: note.locked });
              }
            }}
            onEdgeContextMenu={(e, edge) => {
              e.preventDefault();
              const l = lab?.links.find((x) => x.id === edge.id);
              setMenu({ kind: "link", x: e.clientX, y: e.clientY, id: edge.id, label: l ? `${l.a} ↔ ${l.b}` : "" });
            }}
            onPaneContextMenu={(e) => {
              e.preventDefault();
              const p = flow.screenToFlowPosition({ x: e.clientX, y: e.clientY });
              setMenu({ kind: "pane", x: e.clientX, y: e.clientY, fx: p.x, fy: p.y });
            }}
            onPaneClick={() => { setMenu(null); setPicker(null); }}
            deleteKeyCode={null}
            nodesConnectable={false}
            snapToGrid
            snapGrid={[10, 10]}
            minZoom={0.2}
            maxZoom={3}
            proOptions={{ hideAttribution: true }}
          >
            <Background variant={BackgroundVariant.Dots} gap={20} size={1.4} color="#c3ccd4" />
            <Controls showInteractive={false} position="bottom-left" />
            <MiniMap pannable zoomable position="bottom-right" nodeColor={(n) => (n.type === "note" ? "#f3e7a6" : "#1f6fd1")}
              maskColor="rgba(15,27,45,0.08)" style={{ width: 160, height: 110 }} />
          </ReactFlow>
        </div>

        <aside className={`summary ${summaryOpen ? "" : "collapsed"}`} aria-label="Resumen de la topología">
          <header>
            {summaryOpen && <span>Topología</span>}
            <button onClick={() => setSummaryOpen((v) => !v)} title={summaryOpen ? "Ocultar resumen" : "Mostrar resumen"}>
              <Icon name={summaryOpen ? "close" : "list"} size={16} />
            </button>
          </header>
          {summaryOpen && (
            <ul>
              {lab?.nodes.map((n) => (
                <li key={n.name} title="Doble clic para abrir la consola"
                  onClick={() => {
                    flow.setCenter(n.x + 32, n.y + 28, { zoom: Math.max(flow.getZoom(), 1), duration: 300 });
                  }}
                  onDoubleClick={() => openConsole(n)}
                  onContextMenu={(e) => { e.preventDefault(); setMenu({ kind: "node", x: e.clientX, y: e.clientY, node: n }); }}>
                  <span className={`dot ${n.state === "running" ? "running" : ""}`} />
                  <span>{n.name}</span>
                  <small>{n.template_name}</small>
                </li>
              ))}
              {lab && lab.nodes.length === 0 && <li style={{ cursor: "default" }}><span /><small>Sin equipos</small></li>}
            </ul>
          )}
        </aside>
      </div>

      <ConsoleDock tabs={consoles} active={activeConsole} height={dockHeight} onHeight={setDockHeight}
        onSelect={setActiveConsole} onClose={closeConsole} onCloseAll={() => { setConsoles([]); setActiveConsole(null); }} />

      {menu?.kind === "node" && (
        <Menu x={menu.x} y={menu.y} title={`${menu.node.name} (${menu.node.template_name})`}
          items={nodeMenu(menu.node)} onClose={() => setMenu(null)} />
      )}
      {menu?.kind === "link" && (
        <Menu x={menu.x} y={menu.y} title={menu.label} onClose={() => setMenu(null)} items={[
          { label: "Eliminar enlace", icon: "trash", danger: true, onClick: () => run(null, () => api.deleteLink(labName, menu.id)) },
        ]} />
      )}
      {menu?.kind === "note" && (
        <Menu x={menu.x} y={menu.y} title="Nota" onClose={() => setMenu(null)} items={[
          {
            label: menu.locked ? "Desbloquear" : "Bloquear", icon: menu.locked ? "unlock" : "lock",
            onClick: () => run(null, () => api.patchNote(labName, menu.id, { locked: !menu.locked })),
          },
          { label: "Eliminar nota", icon: "trash", danger: true, disabled: menu.locked, onClick: () => run(null, () => api.deleteNote(labName, menu.id)) },
        ]} />
      )}
      {menu?.kind === "pane" && (
        <Menu x={menu.x} y={menu.y} onClose={() => setMenu(null)} items={[
          { label: "Agregar nota aquí", icon: "note", onClick: () => addNoteAt(menu.fx, menu.fy) },
          { label: "Encender todo", icon: "play", disabled: !anyStopped, onClick: () => run("start", () => api.labAction(labName, "start")) },
          { label: "Apagar todo", icon: "stop", disabled: !anyRunning, onClick: () => run("stop", () => api.labAction(labName, "stop")) },
          { label: "Ajustar vista", icon: "fit", onClick: () => flow.fitView({ padding: 0.3, maxZoom: 1.2 }) },
        ]} />
      )}
      {picker && (
        <InterfacePicker x={picker.x} y={picker.y} node={picker.node} onPick={pickInterface}
          onClose={() => setPicker(null)} />
      )}
      {editNode && (
        <NodeDialog node={editNode} onClose={() => setEditNode(null)}
          onSave={async (patch) => {
            const updated = await api.patchNode(labName, editNode.name, patch).catch((e) => {
              notify((e as Error).message, true);
              throw e;
            });
            setLab(updated);
            notify(`${patch.name ?? editNode.name} actualizado.`);
          }} />
      )}
    </div>
  );
}
