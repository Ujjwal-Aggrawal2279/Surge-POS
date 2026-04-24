import { io, Socket } from "socket.io-client";
import type { QueryClient } from "@tanstack/react-query";

type SurgeInvalidateEvent = { type: "items" | "stock"; warehouse?: string };

declare global {
  interface Window {
    frappe?: {
      realtime?: {
        on: (event: string, cb: (data: unknown) => void) => void;
        off: (event: string, cb: (data: unknown) => void) => void;
      };
    };
  }
}

let _socket: Socket | null = null;

function getSocketUrl(): string {
  const cfg = window.SURGE_CONFIG;
  const port = cfg?.socketio_port ?? 9000;
  const siteName = cfg?.site_name ?? window.location.hostname;
  // In bench dev, socketio runs on a separate port; in prod it's proxied through nginx on same origin.
  const origin = window.location.protocol + "//" + window.location.hostname + ":" + port;
  return `${origin}/${siteName}`;
}

export function initRealtime(): Socket {
  if (_socket) return _socket;

  _socket = io(getSocketUrl(), {
    withCredentials: true,   // sends session cookie so Frappe middleware identifies the user
    reconnectionAttempts: Infinity,
    reconnectionDelay: 1000,
    reconnectionDelayMax: 10_000,
    transports: ["websocket", "polling"],
  });

  _socket.on("connect_error", (err) => {
    console.warn("[Surge realtime] connect error:", err.message);
  });

  // Expose as window.frappe.realtime so existing components can use the same API
  if (!window.frappe) window.frappe = {};
  window.frappe.realtime = {
    on: (event, cb) => { _socket!.on(event, cb); },
    off: (event, cb) => { _socket!.off(event, cb); },
  };

  return _socket;
}

const JITTER_MS = 1500;

export function subscribeToSurgeEvents(queryClient: QueryClient): () => void {
  const socket = initRealtime();

  const cb = (data: unknown) => {
    const ev = data as SurgeInvalidateEvent;
    const delay = Math.random() * JITTER_MS;
    setTimeout(() => {
      if (ev.type === "items") {
        queryClient.invalidateQueries({ queryKey: ["items"] });
        queryClient.invalidateQueries({ queryKey: ["item-prices"] });
      }
      if (ev.type === "stock") {
        queryClient.invalidateQueries({ queryKey: ["stock"] });
      }
    }, delay);
  };

  socket.on("surge:invalidate", cb);
  return () => socket.off("surge:invalidate", cb);
}
