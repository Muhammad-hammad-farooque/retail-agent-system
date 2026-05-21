'use client';

import { useEffect, useState } from 'react';
import { AlertTriangle, X, PackageX } from 'lucide-react';

interface StockItem {
  id: number;
  name: string;
  quantity: number;
  reorder_level: number;
}

interface ParsedAlert {
  fingerprint: string;
  type: string;
  count: number;
  items: StockItem[];
  timestamp: Date;
}

function formatTimestamp(date: Date): string {
  const now = new Date();
  const isToday =
    date.getDate() === now.getDate() &&
    date.getMonth() === now.getMonth() &&
    date.getFullYear() === now.getFullYear();

  const timeStr = date.toLocaleTimeString('en-US', {
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
  });

  if (isToday) return `Today at ${timeStr}`;

  const yesterday = new Date(now);
  yesterday.setDate(now.getDate() - 1);
  const isYesterday =
    date.getDate() === yesterday.getDate() &&
    date.getMonth() === yesterday.getMonth() &&
    date.getFullYear() === yesterday.getFullYear();

  if (isYesterday) return `Yesterday at ${timeStr}`;

  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) + ` at ${timeStr}`;
}

function makeFingerprint(type: string, items: StockItem[]): string {
  const ids = items.map((i) => i.id).sort().join(',');
  return `${type}:${ids}`;
}

export default function AlertBanner() {
  const [alerts, setAlerts] = useState<ParsedAlert[]>([]);
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
          if (data.type === 'LOW_STOCK' && Array.isArray(data.items)) {
            const fp = makeFingerprint(data.type, data.items);
            setAlerts((prev) => {
              const exists = prev.find((a) => a.fingerprint === fp);
              if (exists) {
                // Same items — just refresh the timestamp, don't duplicate
                return prev.map((a) =>
                  a.fingerprint === fp ? { ...a, timestamp: new Date() } : a
                );
              }
              const newAlert: ParsedAlert = {
                fingerprint: fp,
                type: data.type,
                count: data.count ?? data.items.length,
                items: data.items,
                timestamp: new Date(),
              };
              return [newAlert, ...prev].slice(0, 10);
            });
          }
        } catch {
          // silently ignore malformed messages
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

  const dismiss = (fp: string) =>
    setAlerts((prev) => prev.filter((a) => a.fingerprint !== fp));

  const clearAll = () => setAlerts([]);

  if (alerts.length === 0) return null;

  return (
    <div className="mb-6 space-y-3">
      {/* Header row */}
      <div className="flex items-center justify-between px-1">
        <span className="text-xs font-semibold uppercase tracking-wide text-red-500">
          Stock Alerts
        </span>
        <button
          onClick={clearAll}
          className="text-xs text-gray-400 hover:text-gray-600 transition-colors"
        >
          Clear All
        </button>
      </div>

      {!connected && (
        <div className="text-xs text-gray-400 px-1">WebSocket reconnecting…</div>
      )}

      {alerts.map((alert) => (
        <div
          key={alert.fingerprint}
          className="bg-red-50 border border-red-200 rounded-xl overflow-hidden"
        >
          {/* Card header */}
          <div className="flex items-start gap-3 px-4 pt-4 pb-3">
            <div className="w-8 h-8 rounded-full bg-red-100 flex items-center justify-center shrink-0 mt-0.5">
              <AlertTriangle className="w-4 h-4 text-red-500" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-semibold text-red-800">Low Stock Alert</p>
              <p className="text-xs text-red-500 mt-0.5">
                {alert.count} {alert.count === 1 ? 'item' : 'items'} below reorder level
              </p>
            </div>
            <div className="flex items-center gap-3 shrink-0">
              <span className="text-xs text-red-400">{formatTimestamp(alert.timestamp)}</span>
              <button
                onClick={() => dismiss(alert.fingerprint)}
                className="text-red-300 hover:text-red-500 transition-colors"
                aria-label="Dismiss"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Items table */}
          <div className="border-t border-red-100 mx-4 mb-4">
            <div className="mt-3 space-y-1.5">
              {alert.items.map((item) => (
                <div
                  key={item.id}
                  className="flex items-center justify-between gap-2 text-xs"
                >
                  <div className="flex items-center gap-1.5 min-w-0">
                    <PackageX className="w-3.5 h-3.5 text-red-400 shrink-0" />
                    <span className="text-red-800 font-medium truncate">{item.name}</span>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <span className="text-red-400">
                      Reorder: {item.reorder_level}
                    </span>
                    <span
                      className={`px-2 py-0.5 rounded-full font-semibold ${
                        item.quantity === 0
                          ? 'bg-red-600 text-white'
                          : 'bg-red-100 text-red-700'
                      }`}
                    >
                      {item.quantity} left
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
