// Thin client for the SakbeLab REST API. The editor never touches the host directly.

export type Category = "router" | "switch" | "security" | "end-device" | "other";
export type Engine = "docker" | "switch" | "iol" | "qemu";

export interface Template {
  id: string;
  name: string;
  vendor: string;
  engine: Engine;
  category: Category;
  image: string | null;
  icon: string;
  name_prefix: string;
  defaults: { ram?: number; cpus?: number };
  interfaces: { count: number; naming: string; start: number; ports_per_slot: number };
  console: { type: string; command: string[] };
  config: Record<string, unknown>;
  interface_names: string[];
  available: boolean;
  unavailable_reason: string;
}

export type NodeState = "running" | "stopped" | "absent";

export interface LabNode {
  name: string;
  template: string;
  image: string | null;
  ram: number | null;
  cpus: number | null;
  config: string | null;
  x: number;
  y: number;
  locked: boolean;
  state: NodeState;
  icon: string;
  category: Category;
  template_name: string;
  interfaces: string[];
  used_interfaces: string[];
  has_console: boolean;
  engine: Engine | null;
  console_kind: "serial" | "vnc" | "none";
}

export interface LabLink {
  id: string;
  a: string;
  b: string;
  a_up: boolean;
  b_up: boolean;
}

export interface LabNote {
  id: string;
  text: string;
  x: number;
  y: number;
  locked: boolean;
}

export interface Lab {
  name: string;
  description: string;
  state: "running" | "stopped" | "partial";
  nodes: LabNode[];
  links: LabLink[];
  notes: LabNote[];
  errors?: string[];
}

export interface LabSummary {
  name: string;
  description: string;
  nodes: number;
  running: number;
}

export interface ImageInfo {
  kind: "qemu" | "iol" | "docker";
  name: string;
  size: number | null;
  sha256: string | null;
  reference: string | null;
  refs?: string[];
}

const BASE = "/api/v1";

async function call<T>(method: string, path: string, body?: unknown, text = false): Promise<T> {
  const init: RequestInit = { method, headers: {} };
  if (body !== undefined) {
    init.body = text ? String(body) : JSON.stringify(body);
    (init.headers as Record<string, string>)["Content-Type"] = text ? "text/plain" : "application/json";
  }
  const res = await fetch(BASE + path, init);
  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`;
    try {
      const j = await res.json();
      if (typeof j.detail === "string") detail = j.detail;
      else if (Array.isArray(j.detail)) detail = j.detail.map((d: { msg: string }) => d.msg).join("; ");
    } catch {
      /* keep status text */
    }
    throw new Error(detail);
  }
  return (res.status === 204 ? null : await res.json()) as T;
}

const enc = encodeURIComponent;

export const api = {
  health: () => call<{ version: string; kvm: boolean; qemu: boolean }>("GET", "/health"),
  templates: () => call<Template[]>("GET", "/templates"),
  saveTemplate: (t: Partial<Template>, isNew: boolean) =>
    isNew ? call<Template>("POST", "/templates", t) : call<Template>("PUT", `/templates/${enc(t.id!)}`, t),
  deleteTemplate: (id: string) => call<null>("DELETE", `/templates/${enc(id)}`),

  labs: () => call<LabSummary[]>("GET", "/labs"),
  lab: (name: string) => call<Lab>("GET", `/labs/${enc(name)}`),
  createLab: (name: string, description: string) => call<Lab>("POST", "/labs", { name, description }),
  importYaml: (text: string) => call<Lab>("POST", "/labs/yaml", text, true),
  importLab: async (file: File, name?: string): Promise<Lab & { warnings: string[] }> => {
    const q = name ? `?name=${enc(name)}` : "";
    const res = await fetch(`${BASE}/labs/import${q}`, { method: "POST", body: file });
    const body = await res.json().catch(() => ({}));
    if (!res.ok) {
      const err = new Error(typeof body.detail === "string" ? body.detail : `Error ${res.status}`);
      (err as Error & { status?: number }).status = res.status;
      throw err;
    }
    return body;
  },
  deleteLab: (name: string) => call<null>("DELETE", `/labs/${enc(name)}`),
  labAction: (name: string, action: "start" | "stop") => call<Lab>("POST", `/labs/${enc(name)}/${action}`),
  saveConfigs: (name: string) => call<{ saved: string[] }>("POST", `/labs/${enc(name)}/save`),
  lockAll: (name: string, locked: boolean) => call<Lab>("POST", `/labs/${enc(name)}/lock`, { locked }),

  addNode: (lab: string, template: string, x: number, y: number) =>
    call<Lab>("POST", `/labs/${enc(lab)}/nodes`, { template, x, y }),
  patchNode: (lab: string, node: string, patch: Partial<LabNode>) =>
    call<Lab>("PATCH", `/labs/${enc(lab)}/nodes/${enc(node)}`, patch),
  deleteNode: (lab: string, node: string) => call<Lab>("DELETE", `/labs/${enc(lab)}/nodes/${enc(node)}`),
  nodeAction: (lab: string, node: string, action: "start" | "stop" | "reload") =>
    call<Lab>("POST", `/labs/${enc(lab)}/nodes/${enc(node)}/${action}`),

  addLink: (lab: string, a: string, b: string) => call<Lab>("POST", `/labs/${enc(lab)}/links`, { a, b }),
  deleteLink: (lab: string, id: string) => call<Lab>("DELETE", `/labs/${enc(lab)}/links/${enc(id)}`),

  addNote: (lab: string, text: string, x: number, y: number) =>
    call<Lab>("POST", `/labs/${enc(lab)}/notes`, { text, x, y }),
  patchNote: (lab: string, id: string, patch: Partial<LabNote>) =>
    call<Lab>("PATCH", `/labs/${enc(lab)}/notes/${enc(id)}`, patch),
  deleteNote: (lab: string, id: string) => call<Lab>("DELETE", `/labs/${enc(lab)}/notes/${enc(id)}`),

  images: () => call<ImageInfo[]>("GET", "/images"),
  localDockerImages: () => call<string[]>("GET", "/images/docker-local"),
  deleteImage: (kind: string, name: string) => call<null>("DELETE", `/images/${kind}/${enc(name)}`),
};

export function uploadImage(
  kind: string,
  file: File,
  onProgress: (fraction: number) => void,
): Promise<ImageInfo> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("PUT", `${BASE}/images/${kind}/${enc(file.name)}`);
    xhr.upload.onprogress = (e) => e.lengthComputable && onProgress(e.loaded / e.total);
    xhr.onload = () => {
      let body: { detail?: string } | ImageInfo = {} as ImageInfo;
      try {
        body = JSON.parse(xhr.responseText);
      } catch {
        /* empty */
      }
      if (xhr.status >= 200 && xhr.status < 300) resolve(body as ImageInfo);
      else reject(new Error((body as { detail?: string }).detail || `Error ${xhr.status}`));
    };
    xhr.onerror = () => reject(new Error("Se cortó la conexión durante la subida."));
    xhr.send(file);
  });
}

export function consoleUrl(lab: string, node: string): string {
  const proto = location.protocol === "https:" ? "wss" : "ws";
  return `${proto}://${location.host}${BASE}/labs/${enc(lab)}/nodes/${enc(node)}/console`;
}

export function kindForFile(name: string): "qemu" | "iol" | "docker" | null {
  const n = name.toLowerCase();
  if (/\.(qcow2|img|vmdk|iso)$/.test(n)) return "qemu";
  if (/\.(tar|tar\.gz|tgz)$/.test(n)) return "docker";
  if (/\.(bin|iol)$/.test(n) || !n.includes(".")) return "iol";
  return null;
}

export function formatSize(bytes: number | null): string {
  if (bytes == null) return "";
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  if (bytes < 1024 ** 3) return `${(bytes / 1024 ** 2).toFixed(1)} MB`;
  return `${(bytes / 1024 ** 3).toFixed(2)} GB`;
}
