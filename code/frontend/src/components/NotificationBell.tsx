import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { apiGet, apiPost } from "../lib/api";
import { BellIcon } from "./Icons";

export interface NotificationItem {
  notification_id: number;
  kind: string;
  title: string;
  body: string | null;
  link: string | null;
  created_at: string;
  read: boolean;
}

interface NotificationList {
  unread: number;
  items: NotificationItem[];
}

const POLL_MS = 60_000;

function ago(iso: string): string {
  const minutes = Math.floor((Date.now() - new Date(iso).getTime()) / 60_000);
  if (minutes < 1) return "Just now";
  if (minutes < 60) return `${minutes} min ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours} h ago`;
  const days = Math.floor(hours / 24);
  return days === 1 ? "Yesterday" : `${days} days ago`;
}

/** The bell in the top bar: unread count, and a list that opens on click. */
export function NotificationBell() {
  const [data, setData] = useState<NotificationList>({ unread: 0, items: [] });
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();

  const load = useCallback(() => {
    apiGet<NotificationList>("/api/notifications")
      .then((d) => {
        if (d && Array.isArray(d.items)) setData(d);
      })
      .catch(() => undefined);
  }, []);

  useEffect(() => {
    load();
    const timer = setInterval(load, POLL_MS);
    return () => clearInterval(timer);
  }, [load]);

  // Close when clicking outside or pressing Escape.
  useEffect(() => {
    if (!open) return;
    const onClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    document.addEventListener("mousedown", onClick);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onClick);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  const openItem = async (n: NotificationItem) => {
    if (!n.read) {
      setData((d) => ({
        unread: Math.max(0, d.unread - 1),
        items: d.items.map((x) => (x.notification_id === n.notification_id ? { ...x, read: true } : x)),
      }));
      apiPost(`/api/notifications/${n.notification_id}/read`).catch(() => undefined);
    }
    setOpen(false);
    if (n.link) navigate(n.link);
  };

  const readAll = () => {
    setData((d) => ({ unread: 0, items: d.items.map((x) => ({ ...x, read: true })) }));
    apiPost("/api/notifications/read-all").catch(() => undefined);
  };

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        onClick={() => {
          setOpen((o) => !o);
          if (!open) load();
        }}
        aria-label={data.unread ? `Notifications, ${data.unread} unread` : "Notifications"}
        aria-expanded={open}
        className="relative rounded-full p-2 text-ink-soft transition hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-night-700"
      >
        <BellIcon className="h-5 w-5" />
        {data.unread > 0 && (
          <span className="absolute -right-0.5 -top-0.5 flex h-[18px] min-w-[18px] items-center justify-center rounded-full bg-pop-500 px-1 text-[10px] font-bold text-white ring-2 ring-paper dark:ring-night">
            {data.unread > 9 ? "9+" : data.unread}
          </span>
        )}
      </button>

      {open && (
        <div
          role="dialog"
          aria-label="Notifications"
          className="rise absolute right-0 z-30 mt-2 w-[22rem] max-w-[calc(100vw-2rem)] overflow-hidden rounded-xl border border-slate-200 bg-white shadow-xl dark:border-night-600 dark:bg-night-800"
        >
          <div className="flex items-center justify-between border-b border-slate-200 px-4 py-3 dark:border-night-600">
            <p className="font-semibold">Notifications</p>
            {data.unread > 0 && (
              <button onClick={readAll} className="text-xs font-semibold text-brand-700 hover:underline dark:text-brand-300">
                Mark all as read
              </button>
            )}
          </div>
          {data.items.length === 0 ? (
            <p className="muted px-4 py-8 text-center text-sm">You're all caught up. New activity shows up here.</p>
          ) : (
            <ul className="max-h-96 overflow-y-auto">
              {data.items.map((n) => (
                <li key={n.notification_id}>
                  <button
                    onClick={() => openItem(n)}
                    className={`flex w-full gap-3 border-b border-slate-100 px-4 py-3 text-left transition last:border-0 hover:bg-slate-50 dark:border-night-700 dark:hover:bg-night-700 ${
                      n.read ? "" : "bg-brand-600/[0.04]"
                    }`}
                  >
                    <span
                      className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${n.read ? "bg-transparent" : "bg-brand-600"}`}
                      aria-hidden="true"
                    />
                    <span className="min-w-0">
                      <span className={`block text-sm ${n.read ? "font-medium" : "font-semibold"}`}>{n.title}</span>
                      {n.body && <span className="muted mt-0.5 block text-xs leading-relaxed">{n.body}</span>}
                      <span className="muted mt-1 block text-[11px]">{ago(n.created_at)}</span>
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
