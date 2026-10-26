import { useCallback, useEffect, useState } from "react";
import { ReactFlowProvider } from "@xyflow/react";
import { api, type Template } from "./api";
import { Editor } from "./components/Editor";
import { Home } from "./components/Home";
import { Library } from "./components/Library";
import { Terminal } from "./components/Terminal";

type Toast = { id: number; text: string; error: boolean };

function labFromHash(): string | null {
  const m = location.hash.match(/^#\/lab\/([^/]+)$/);
  return m ? decodeURIComponent(m[1]) : null;
}

export default function App() {
  const consoleMatch = location.pathname.match(/^\/console\/([^/]+)\/([^/]+)$/);
  if (consoleMatch) {
    const [, lab, node] = consoleMatch.map(decodeURIComponent);
    document.title = `${node} · ${lab}`;
    return <div className="console-page"><Terminal lab={lab} node={node} active /></div>;
  }
  return <Main />;
}

function Main() {
  const [labName, setLabName] = useState<string | null>(labFromHash);
  const [templates, setTemplates] = useState<Template[]>([]);
  const [library, setLibrary] = useState(false);
  const [toasts, setToasts] = useState<Toast[]>([]);

  const notify = useCallback((text: string, error = false) => {
    const id = Date.now() + Math.random();
    setToasts((t) => [...t.slice(-3), { id, text, error }]);
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), error ? 7000 : 3500);
  }, []);

  const loadTemplates = useCallback(() => {
    api.templates().then(setTemplates).catch((e) => notify(e.message, true));
  }, [notify]);
  useEffect(() => { loadTemplates(); }, [loadTemplates]);

  useEffect(() => {
    const onHash = () => setLabName(labFromHash());
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  useEffect(() => {
    document.title = labName ? `${labName} · SakbeLab` : "SakbeLab";
  }, [labName]);

  const open = (name: string | null) => {
    location.hash = name ? `#/lab/${encodeURIComponent(name)}` : "";
    setLabName(name);
  };

  return (
    <>
      {labName ? (
        <ReactFlowProvider key={labName}>
          <Editor labName={labName} templates={templates} onExit={() => open(null)}
            onLibrary={() => setLibrary(true)} notify={notify} />
        </ReactFlowProvider>
      ) : (
        <Home onOpen={open} notify={notify} />
      )}
      {library && (
        <Library templates={templates} onChanged={loadTemplates} onClose={() => setLibrary(false)} notify={notify} />
      )}
      <div className="toasts" aria-live="polite">
        {toasts.map((t) => <div key={t.id} className={`toast ${t.error ? "error" : ""}`}>{t.text}</div>)}
      </div>
    </>
  );
}
