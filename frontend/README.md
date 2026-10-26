# Editor web de SakbeLab

React + TypeScript, con React Flow (`@xyflow/react`) para el lienzo y xterm.js para las consolas.

- `src/components/Editor.tsx`: lienzo, barra de herramientas, menús y consolas.
- `src/components/DevicePanel.tsx`: categorías y paleta de dispositivos (arrastrar y soltar).
- `src/components/Library.tsx`: imágenes y plantillas.
- `src/icons.tsx`: íconos de equipos y de la barra.

## Desarrollo

```bash
npm install
npm run dev        # http://localhost:5173, con la API en http://127.0.0.1:8080
npm run build      # genera la app dentro de backend/sakbe/web
```

El resultado de `npm run build` se versiona dentro del paquete de Python, así la OVA no necesita Node para funcionar.
Después de cambiar el frontend, ejecutá `npm run build` y subí también los archivos generados.
