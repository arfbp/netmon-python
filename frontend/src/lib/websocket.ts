import { env } from "./env";

export type ConnectionStatus = "connecting" | "connected" | "disconnected";

interface WSMessage {
  type: string;
  payload: unknown;
  timestamp: string;
}

type MessageHandler = (payload: unknown) => void;
type StatusHandler = (status: ConnectionStatus) => void;

/**
 * Thin WebSocket wrapper: connects to `/ws`, dispatches inbound
 * messages to subscribers by `type` (matching the backend's WSMessage
 * envelope — see backend/app/websocket/schemas.py), and reconnects
 * automatically with capped exponential backoff on any unexpected
 * close. A clean `disconnect()` call is not retried.
 */
export class MonitoringSocket {
  private socket: WebSocket | null = null;
  private handlers = new Map<string, Set<MessageHandler>>();
  private statusHandlers = new Set<StatusHandler>();
  private reconnectAttempt = 0;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private disconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private intentionallyClosed = false;

  private clearReconnectTimer(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
  }

  connect(): void {
    if (this.disconnectTimer) {
      clearTimeout(this.disconnectTimer);
      this.disconnectTimer = null;
    }
    this.clearReconnectTimer();
    this.intentionallyClosed = false;

    if (this.socket && this.socket.readyState <= WebSocket.OPEN) {
      return;
    }

    this.open();
  }

  disconnect(): void {
    this.intentionallyClosed = true;
    this.clearReconnectTimer();
    if (this.disconnectTimer) clearTimeout(this.disconnectTimer);
    this.disconnectTimer = setTimeout(() => {
      this.socket?.close();
      this.disconnectTimer = null;
    }, 250);
  }

  on(type: string, handler: MessageHandler): () => void {
    if (!this.handlers.has(type)) this.handlers.set(type, new Set());
    this.handlers.get(type)!.add(handler);
    return () => this.handlers.get(type)?.delete(handler);
  }

  onStatusChange(handler: StatusHandler): () => void {
    this.statusHandlers.add(handler);
    return () => this.statusHandlers.delete(handler);
  }

  private open(): void {
    this.setStatus("connecting");
    const url = `${env.wsBaseUrl}/ws`;
    const socket = new WebSocket(url);
    this.socket = socket;

    socket.onopen = () => {
      this.reconnectAttempt = 0;
      this.clearReconnectTimer();
      this.setStatus("connected");
    };

    socket.onmessage = (event: MessageEvent<string>) => {
      let message: WSMessage;
      try {
        message = JSON.parse(event.data);
      } catch {
        return; // malformed frame — ignore rather than crash the UI
      }
      const handlers = this.handlers.get(message.type);
      if (handlers) {
        for (const handler of handlers) handler(message.payload);
      }
    };

    socket.onclose = () => {
      if (this.socket === socket) {
        this.socket = null;
      }
      this.setStatus("disconnected");
      if (!this.intentionallyClosed) this.scheduleReconnect();
    };

    socket.onerror = () => {
      socket.close();
    };
  }

  private scheduleReconnect(): void {
    // Capped exponential backoff: 1s, 2s, 4s, ... up to 30s — fast
    // enough to feel responsive after a brief network blip, bounded
    // enough not to hammer the server during a real outage.
    const delayMs = Math.min(1000 * 2 ** this.reconnectAttempt, 30_000);
    this.reconnectAttempt += 1;
    this.reconnectTimer = setTimeout(() => this.open(), delayMs);
  }

  private setStatus(status: ConnectionStatus): void {
    for (const handler of this.statusHandlers) handler(status);
  }
}

export const monitoringSocket = new MonitoringSocket();
