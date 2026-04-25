'use client';

import { useEffect, useState } from 'react';
import { AlertTriangle, X } from 'lucide-react';

interface Alert {
  id: string;
  message: string;
  timestamp: Date;
}

export default function AlertBanner() {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    const wsUrl = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000';
    let ws: WebSocket;
    let retryTimer: ReturnType<typeof setTimeout>;

    const connect = () => {
      ws = new WebSocket(`${wsUrl}/ws/alerts`);

      ws.onopen = () => setConnected(true);

      ws.onmessage = (e) => {
        try {
          const data = JSON.parse(e.data);
          const items: Alert[] = Array.isArray(data)
            ? data.map((d: { product?: string; sku?: string; quantity?: number }, i: number) => ({
                id: `${Date.now()}-${i}`,
                message: `Low stock: ${d.product || d.sku} — ${d.quantity} units remaining`,
                timestamp: new Date(),
              }))
            : [{ id: `${Date.now()}`, message: e.data, timestamp: new Date() }];
          setAlerts((prev) => [...items, ...prev].slice(0, 5));
        } catch {
          setAlerts((prev) =>
            [{ id: `${Date.now()}`, message: e.data, timestamp: new Date() }, ...prev].slice(0, 5)
          );
        }
      };

      ws.onclose = () => {
        setConnected(false);
        retryTimer = setTimeout(connect, 5000);
      };

      ws.onerror = () => ws.close();
    };

    connect();
    return () => {
      clearTimeout(retryTimer);
      ws?.close();
    };
  }, []);

  const dismiss = (id: string) => setAlerts((prev) => prev.filter((a) => a.id !== id));

  if (alerts.length === 0) return null;

  return (
    <div className="space-y-2 mb-4">
      {!connected && (
        <div className="text-xs text-gray-400 px-1">WebSocket reconnecting...</div>
      )}
      {alerts.map((a) => (
        <div
          key={a.id}
          className="flex items-start gap-3 bg-red-50 border border-red-200 rounded-lg px-4 py-3"
        >
          <AlertTriangle className="w-4 h-4 text-red-500 mt-0.5 shrink-0" />
          <div className="flex-1 text-sm text-red-700">{a.message}</div>
          <button onClick={() => dismiss(a.id)} className="text-red-400 hover:text-red-600">
            <X className="w-4 h-4" />
          </button>
        </div>
      ))}
    </div>
  );
}
