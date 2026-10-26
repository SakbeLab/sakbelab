import { createRoot } from "react-dom/client";
import App from "./App";
import "./styles.css";

// No StrictMode: its double mount would open every node console twice.
createRoot(document.getElementById("root")!).render(<App />);
