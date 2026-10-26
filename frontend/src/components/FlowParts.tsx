import { memo, useEffect, useRef, useState } from "react";
import {
  BaseEdge, EdgeLabelRenderer, Handle, Position, type Edge, type EdgeProps, type Node, type NodeProps,
} from "@xyflow/react";
import type { LabNode, LabNote } from "../api";
import { DeviceIcon, Icon } from "../icons";

// ---------------------------------------------------------------- device node

export type DeviceNodeData = { node: LabNode };
export type DeviceFlowNode = Node<DeviceNodeData, "device">;

export const DeviceNode = memo(({ data }: NodeProps<DeviceFlowNode>) => {
  const n = data.node;
  return (
    <div className="dev-node" title={`${n.name} · ${n.template_name}`}>
      <div className="glyph">
        <DeviceIcon icon={n.icon} size={56} muted={n.state !== "running"} />
        {n.locked && <span className="lock"><Icon name="lock" size={14} /></span>}
      </div>
      <span className="label">{n.name}</span>
      <Handle type="source" position={Position.Top} className="center-handle" isConnectable={false} />
      <Handle type="target" position={Position.Top} className="center-handle" isConnectable={false} />
    </div>
  );
});

// ---------------------------------------------------------------- note node

export type NoteNodeData = { note: LabNote; onSave: (id: string, text: string) => void };
export type NoteFlowNode = Node<NoteNodeData, "note">;

export const NoteNode = memo(({ data }: NodeProps<NoteFlowNode>) => {
  const [editing, setEditing] = useState(!data.note.text);
  const [text, setText] = useState(data.note.text);
  const ref = useRef<HTMLTextAreaElement>(null);
  useEffect(() => setText(data.note.text), [data.note.text]);
  useEffect(() => { if (editing) ref.current?.focus(); }, [editing]);

  const finish = () => {
    setEditing(false);
    if (text !== data.note.text) data.onSave(data.note.id, text);
  };
  return (
    <div className="note-node" onDoubleClick={() => !data.note.locked && setEditing(true)}>
      {editing ? (
        <textarea ref={ref} className="nodrag" value={text} placeholder="Escribí una nota"
          onChange={(e) => setText(e.target.value)} onBlur={finish}
          onKeyDown={(e) => { if (e.key === "Escape") { setText(data.note.text); setEditing(false); } }} />
      ) : (
        text || <span style={{ opacity: 0.5 }}>Nota vacía</span>
      )}
    </div>
  );
});

// ---------------------------------------------------------------- link edge

export type LinkEdgeData = { aIface: string; bIface: string; aUp: boolean; bUp: boolean; showIfaces: boolean };
export type LinkFlowEdge = Edge<LinkEdgeData, "link">;

const GREEN = "#2bb08f";
const RED = "#d64545";

export function LinkEdge({ id, sourceX, sourceY, targetX, targetY, data, selected }: EdgeProps<LinkFlowEdge>) {
  const dx = targetX - sourceX;
  const dy = targetY - sourceY;
  const len = Math.max(Math.hypot(dx, dy), 1);
  const ux = dx / len;
  const uy = dy / len;
  const at = (d: number, fromTarget = false) =>
    fromTarget ? [targetX - ux * d, targetY - uy * d] : [sourceX + ux * d, sourceY + uy * d];
  const [d1x, d1y] = at(46);
  const [d2x, d2y] = at(46, true);
  const [l1x, l1y] = at(Math.min(78, len / 2 - 10));
  const [l2x, l2y] = at(Math.min(78, len / 2 - 10), true);
  const path = `M${sourceX},${sourceY} L${targetX},${targetY}`;
  return (
    <>
      <BaseEdge id={id} path={path} interactionWidth={14}
        style={{ stroke: selected ? "#1f6fd1" : "#2c3e55", strokeWidth: selected ? 3 : 2 }} />
      {len > 110 && (
        <>
          <circle cx={d1x} cy={d1y} r={4.5} fill={data?.aUp ? GREEN : RED} />
          <circle cx={d2x} cy={d2y} r={4.5} fill={data?.bUp ? GREEN : RED} />
        </>
      )}
      {data?.showIfaces && len > 150 && (
        <EdgeLabelRenderer>
          <span className="link-label" style={{ transform: `translate(-50%,-50%) translate(${l1x}px,${l1y}px)` }}>
            {data.aIface}
          </span>
          <span className="link-label" style={{ transform: `translate(-50%,-50%) translate(${l2x}px,${l2y}px)` }}>
            {data.bIface}
          </span>
        </EdgeLabelRenderer>
      )}
    </>
  );
}
