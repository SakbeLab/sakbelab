// SakbeLab icon set. Device glyphs are original flat drawings in the blue
// network-diagram style; toolbar icons are simple 1.6px line icons.

import type { ReactElement } from "react";

const BLUE = "#1F6FD1";
const BLUE_DARK = "#1658A8";
const WHITE = "#FFFFFF";

type DeviceProps = { size?: number; muted?: boolean };

function arrow(x1: number, y1: number, x2: number, y2: number, key: string) {
  const ang = Math.atan2(y2 - y1, x2 - x1);
  const h = 6;
  const p1 = [x2 - h * Math.cos(ang - 0.6), y2 - h * Math.sin(ang - 0.6)];
  const p2 = [x2 - h * Math.cos(ang + 0.6), y2 - h * Math.sin(ang + 0.6)];
  return (
    <g key={key}>
      <line x1={x1} y1={y1} x2={x2} y2={y2} stroke={WHITE} strokeWidth={3} strokeLinecap="round" />
      <path d={`M${p1[0]},${p1[1]} L${x2},${y2} L${p2[0]},${p2[1]}`} fill="none" stroke={WHITE}
        strokeWidth={3} strokeLinecap="round" strokeLinejoin="round" />
    </g>
  );
}

const DEVICES: Record<string, (fill: string, dark: string) => ReactElement> = {
  router: (fill, dark) => (
    <>
      <ellipse cx={32} cy={40} rx={27} ry={14} fill={dark} />
      <rect x={5} y={26} width={54} height={14} fill={dark} />
      <ellipse cx={32} cy={26} rx={27} ry={14} fill={fill} />
      {arrow(32, 26, 32, 15, "n")}
      {arrow(32, 26, 32, 37, "s")}
      {arrow(32, 26, 15, 26, "w")}
      {arrow(32, 26, 49, 26, "e")}
    </>
  ),
  switch: (fill, dark) => (
    <>
      <path d="M8 22 L20 12 H58 L46 22 Z" fill={fill} />
      <rect x={8} y={22} width={38} height={22} fill={fill} />
      <path d="M46 22 L58 12 V34 L46 44 Z" fill={dark} />
      {arrow(13, 29, 41, 29, "r")}
      {arrow(41, 37, 13, 37, "l")}
    </>
  ),
  l3switch: (fill, dark) => (
    <>
      <path d="M8 22 L20 12 H58 L46 22 Z" fill={fill} />
      <rect x={8} y={22} width={38} height={24} fill={fill} />
      <path d="M46 22 L58 12 V36 L46 46 Z" fill={dark} />
      {arrow(13, 29, 41, 29, "r")}
      {arrow(41, 38, 13, 38, "l")}
      <circle cx={33} cy={17} r={4} fill={WHITE} />
    </>
  ),
  firewall: (fill, dark) => (
    <>
      <rect x={8} y={12} width={48} height={36} rx={3} fill={fill} />
      <rect x={8} y={44} width={48} height={6} rx={2} fill={dark} />
      {[20, 32].map((y) => (
        <line key={y} x1={8} y1={y} x2={56} y2={y} stroke={WHITE} strokeWidth={2} />
      ))}
      {[[20, 12, 20], [44, 12, 20], [32, 20, 32], [20, 32, 44], [44, 32, 44]].map(([x, a, b], i) => (
        <line key={i} x1={x} y1={a} x2={x} y2={b} stroke={WHITE} strokeWidth={2} />
      ))}
    </>
  ),
  pc: (fill, dark) => (
    <>
      <rect x={10} y={10} width={44} height={30} rx={3} fill={fill} />
      <rect x={15} y={15} width={34} height={20} rx={1} fill={WHITE} opacity={0.9} />
      <rect x={28} y={40} width={8} height={6} fill={dark} />
      <rect x={18} y={46} width={28} height={5} rx={2} fill={dark} />
    </>
  ),
  server: (fill, dark) => (
    <>
      <rect x={18} y={8} width={28} height={46} rx={3} fill={fill} />
      <rect x={46} y={10} width={4} height={42} rx={1} fill={dark} />
      {[16, 26, 36].map((y) => (
        <g key={y}>
          <rect x={22} y={y} width={20} height={5} rx={1} fill={WHITE} opacity={0.9} />
        </g>
      ))}
      <circle cx={32} cy={48} r={2.5} fill={WHITE} />
    </>
  ),
  cloud: (fill) => (
    <path d="M18 46 a10 10 0 0 1 0-20 a14 14 0 0 1 26-6 a11 11 0 0 1 4 22 Z" fill={fill} />
  ),
  hub: (fill, dark) => (
    <>
      <rect x={8} y={22} width={48} height={16} rx={3} fill={fill} />
      <rect x={8} y={36} width={48} height={6} rx={2} fill={dark} />
      {[16, 26, 36, 46].map((x) => <rect key={x} x={x - 3} y={27} width={6} height={5} fill={WHITE} />)}
    </>
  ),
  unknown: (fill) => (
    <>
      <rect x={10} y={10} width={44} height={44} rx={8} fill={fill} />
      <text x={32} y={40} textAnchor="middle" fontSize={26} fontWeight={600} fill={WHITE}>?</text>
    </>
  ),
};

export const DEVICE_ICONS = ["router", "switch", "l3switch", "firewall", "pc", "server", "cloud", "hub"];

export const ICON_LABELS: Record<string, string> = {
  router: "Router",
  switch: "Switch",
  l3switch: "Switch L3",
  firewall: "Firewall",
  pc: "PC",
  server: "Servidor",
  cloud: "Nube",
  hub: "Hub",
};

export function DeviceIcon({ icon, size = 48, muted = false }: DeviceProps & { icon: string }) {
  const draw = DEVICES[icon] ?? DEVICES.unknown;
  const fill = muted ? "#9AA7B8" : BLUE;
  const dark = muted ? "#7C8A9C" : BLUE_DARK;
  return (
    <svg width={size} height={size} viewBox="0 0 64 60" aria-hidden="true">
      {draw(fill, dark)}
    </svg>
  );
}

const LINE: Record<string, ReactElement> = {
  play: <path d="M7 5l12 7-12 7z" />,
  stop: <rect x="6" y="6" width="12" height="12" rx="1.5" />,
  reload: <path d="M19 8a8 8 0 1 0 1 6M19 3v5h-5" />,
  save: <path d="M5 4h11l3 3v13H5zM8 4v5h7V4M8 20v-6h8v6" />,
  link: <path d="M4 18c4 0 4-12 8-12s4 12 8 12" />,
  note: <path d="M5 4h14v11l-5 5H5zM14 20v-5h5" />,
  lock: <path d="M6 11h12v9H6zM8.5 11V8a3.5 3.5 0 0 1 7 0v3" />,
  unlock: <path d="M6 11h12v9H6zM8.5 11V8a3.5 3.5 0 0 1 6.8-1.2" />,
  fit: <path d="M4 9V4h5M15 4h5v5M20 15v5h-5M9 20H4v-5" />,
  download: <path d="M12 4v11M7 10l5 5 5-5M5 20h14" />,
  upload: <path d="M12 16V5M7 10l5-5 5 5M5 20h14" />,
  library: <path d="M4 5h5v14H4zM10 5h5v14h-5zM16 6l4 1-3 13-4-1z" />,
  plus: <path d="M12 5v14M5 12h14" />,
  trash: <path d="M5 7h14M10 7V4h4v3M7 7l1 13h8l1-13" />,
  terminal: <path d="M4 5h16v14H4zM7 10l3 2-3 2M12 15h5" />,
  settings: <path d="M12 9a3 3 0 1 0 0 6 3 3 0 0 0 0-6zM12 3v3M12 18v3M3 12h3M18 12h3M5.6 5.6l2.1 2.1M16.3 16.3l2.1 2.1M5.6 18.4l2.1-2.1M16.3 7.7l2.1-2.1" />,
  tag: <path d="M4 4h8l8 8-8 8-8-8zM8.5 8.5h.01" />,
  close: <path d="M6 6l12 12M18 6L6 18" />,
  popout: <path d="M14 4h6v6M20 4l-9 9M18 14v6H4V6h6" />,
  edit: <path d="M5 19h4L19 9l-4-4L5 15zM13 7l4 4" />,
  list: <path d="M8 6h12M8 12h12M8 18h12M4 6h.01M4 12h.01M4 18h.01" />,
  back: <path d="M15 5l-7 7 7 7" />,
  file: <path d="M6 3h8l4 4v14H6zM14 3v4h4" />,
};

export function Icon({ name, size = 18 }: { name: keyof typeof LINE | string; size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor"
      strokeWidth={1.6} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      {LINE[name] ?? null}
    </svg>
  );
}
