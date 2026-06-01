import { useEffect, useMemo, useState } from "react";
import {
  getNotifications,
  markAllNotificationsRead,
  markNotificationRead,
} from "@/lib/api/notifications";
import { requestPushPermission } from "@/components/PushNotificationSetup";
import type { ApiNotification } from "@/lib/types/api";

export function NotificationBell() {
  const [notifications, setNotifications] = useState<ApiNotification[]>([]);
  const [open, setOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pushPermission, setPushPermission] = useState<NotificationPermission | null>(null);

  useEffect(() => {
    if ("Notification" in window) setPushPermission(Notification.permission);
  }, []);

  const unreadCount = useMemo(
    () => notifications.filter((item) => item.read_state === 0).length,
    [notifications],
  );

  async function handleMarkRead(notification: ApiNotification) {
    if (notification.read_state === 0) {
      const updated = await markNotificationRead(notification.notification_id);

      setNotifications((current) =>
        current.map((item) =>
          item.notification_id === updated.notification_id ? updated : item,
        ),
      );
    }

    if (notification.run_id) {
        window.location.assign(`/runs/${notification.run_id}`);    
    }
  }

  async function handleEnablePush() {
    const granted = await requestPushPermission();
    setPushPermission(granted ? "granted" : "denied");
  }

  async function handleMarkAllRead() {
    await markAllNotificationsRead();

    setNotifications((current) =>
      current.map((item) => ({
        ...item,
        read_state: 1,
      })),
    );
  }

  useEffect(() => {
    let isActive = true;

    void getNotifications()
        .then((data) => {
            if (isActive) {
                setNotifications(data);
            }
            })
            .catch(() => {
            if (isActive) {
                setError("Could not load notifications");
            }
        });

        return () => {
            isActive = false;
        };
    }, []);

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        className="relative rounded-lg border border-zinc-700 px-3 py-2 text-sm hover:bg-zinc-800"
      >
        🔔

        {unreadCount > 0 && (
          <span className="absolute -right-2 -top-2 rounded-full bg-red-500 px-2 py-0.5 text-xs text-white">
            {unreadCount}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 z-50 mt-2 w-96 rounded-xl border border-zinc-700 bg-zinc-950 p-3 shadow-xl">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-sm font-semibold">Notifications</h2>

            <button
              type="button"
              onClick={handleMarkAllRead}
              className="text-xs text-zinc-400 hover:text-zinc-100"
            >
              Mark all read
            </button>
          </div>

          {pushPermission !== "granted" && "Notification" in window && (
            <button
              type="button"
              onClick={handleEnablePush}
              className="mb-3 w-full rounded-lg border border-zinc-600 py-2 text-xs text-zinc-300 hover:bg-zinc-800"
            >
              Enable push notifications
            </button>
          )}

          {error && <p className="text-sm text-red-400">{error}</p>}

          {!error && notifications.length === 0 && (
            <p className="text-sm text-zinc-400">No notifications yet.</p>
          )}

          <div className="max-h-96 space-y-2 overflow-y-auto">
            {notifications.map((notification) => (
              <button
                key={notification.notification_id}
                type="button"
                onClick={() => handleMarkRead(notification)}
                className={`w-full rounded-lg border p-3 text-left text-sm ${
                  notification.read_state === 0
                    ? "border-zinc-500 bg-zinc-900"
                    : "border-zinc-800 bg-zinc-950"
                }`}
              >
                <div className="flex items-center justify-between gap-3">
                  <span className="font-medium">{notification.title}</span>
                  <span className="text-xs text-zinc-500">
                    {notification.event_type}
                  </span>
                </div>

                <p className="mt-1 text-zinc-400">{notification.message}</p>

                <p className="mt-2 text-xs text-zinc-500">
                  {new Date(notification.timestamp).toLocaleString()}
                </p>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}