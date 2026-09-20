import { Inter } from 'next/font/google';
import AgentChat from '@/components/AgentChat';
import s from '@/components/agentUi.module.css';

const inter = Inter({ subsets: ['latin'], weight: ['400', '500', '600'], display: 'swap' });

// 24 radial rays around the mark, starting at 12 o'clock.
const RAYS = Array.from({ length: 24 }, (_, i) => {
  const a = -Math.PI / 2 + (i * 2 * Math.PI) / 24;
  return {
    x1: (26 + Math.cos(a) * 10.4).toFixed(2),
    y1: (26 + Math.sin(a) * 10.4).toFixed(2),
    x2: (26 + Math.cos(a) * 22.6).toFixed(2),
    y2: (26 + Math.sin(a) * 22.6).toFixed(2),
  };
});

export default function AgentPage() {
  return (
    <div className={`${s.root} ${inter.className}`}>
      <header className={`${s.header} ${s.enter}`}>
        <svg className={s.logo} viewBox="0 0 52 52" aria-hidden="true">
          <g stroke="#a770ad" strokeWidth="1.4" strokeLinecap="round">
            {RAYS.map((r, i) => (
              <line key={i} x1={r.x1} y1={r.y1} x2={r.x2} y2={r.y2} />
            ))}
          </g>
          <circle cx="26" cy="26" r="7.4" fill="#5f0264" />
        </svg>

        <div>
          <h1 className={s.headerTitle}>AI Agent</h1>
          <p className={s.headerSub}>Intelligent Retail System</p>
        </div>
      </header>

      <AgentChat />
    </div>
  );
}
