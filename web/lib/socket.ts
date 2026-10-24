"use client";

/**
 * Role-aware client for the visit channel.
 *
 * @implements CDR-001: Visit WebSocket event contract
 * @contract ws:/ws/visit
 * @see openspec/tdr/cdr/cdr-001-visit-websocket-events.md
 */

import { useCallback, useEffect, useRef, useState } from "react";
import type { Envelope, Role } from "./contracts";

export const SERVER_PORT = process.env.NEXT_PUBLIC_SERVER_PORT ?? "8000";

/** The server runs on the same host as the page, so a TV on the LAN reaches the laptop. */
export function serverHttpUrl(): string {
  if (typeof window === "undefined") return `http://localhost:${SERVER_PORT}`;
  return `${window.location.protocol}//${window.location.hostname}:${SERVER_PORT}`;
}

function serverWsUrl(role: Role): string {
  const proto = window.location.protocol === "https:" ? "wss" : "ws";
  return `${proto}://${window.location.hostname}:${SERVER_PORT}/ws/visit?role=${role}`;
}

export type ConnectionState = "connecting" | "open" | "closed";

/**
 * Connects with a role and hands every event to onEvent. A seq gap means an event was
 * missed, so the client reconnects and the server's on-connect visit.state resyncs it.
 */
export function useVisitSocket(role: Role, onEvent: (event: Envelope) => void) {
  const [state, setState] = useState<ConnectionState>("connecting");
  const wsRef = useRef<WebSocket | null>(null);
  const handlerRef = useRef(onEvent);
  handlerRef.current = onEvent;

  useEffect(() => {
    let stopped = false;
    let retry: ReturnType<typeof setTimeout> | undefined;

    const connect = () => {
      setState("connecting");
      const ws = new WebSocket(serverWsUrl(role));
      wsRef.current = ws;
      let lastSeq = 0;
      ws.onopen = () => setState("open");
      ws.onmessage = (message) => {
        const event = JSON.parse(message.data) as Envelope;
        if (lastSeq && event.seq !== lastSeq + 1) {
          ws.close(); // resync through a fresh visit.state
          return;
        }
        lastSeq = event.seq;
        handlerRef.current(event);
      };
      ws.onclose = () => {
        setState("closed");
        if (!stopped) retry = setTimeout(connect, 1000);
      };
    };
    connect();
    return () => {
      stopped = true;
      clearTimeout(retry);
      wsRef.current?.close();
    };
  }, [role]);

  const send = useCallback((type: string, payload: unknown) => {
    const ws = wsRef.current;
    if (ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify({ type, payload }));
  }, []);

  return { state, send };
}
