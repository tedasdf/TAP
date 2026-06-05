"use client";

import { useEffect } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

async function getVapidKey(): Promise<string | null> {
  try {
    const res = await fetch(`${API_BASE}/push/vapid-public-key`);
    if (!res.ok) return null;
    const data = await res.json();
    return data.public_key ?? null;
  } catch {
    return null;
  }
}

function urlBase64ToUint8Array(base64String: string): Uint8Array {
  const padding = "=".repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, "+").replace(/_/g, "/");
  const raw = atob(base64);
  return Uint8Array.from([...raw].map((c) => c.charCodeAt(0)));
}

async function subscribe(registration: ServiceWorkerRegistration): Promise<void> {
  const vapidKey = await getVapidKey();
  if (!vapidKey) return;

  const existing = await registration.pushManager.getSubscription();
  const sub =
    existing ??
    (await registration.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: urlBase64ToUint8Array(vapidKey).buffer as ArrayBuffer,
    }));

  const json = sub.toJSON();
  const keys = json.keys as { p256dh: string; auth: string } | undefined;
  if (!json.endpoint || !keys?.p256dh || !keys?.auth) return;

  await fetch(`${API_BASE}/push/subscribe`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      endpoint: json.endpoint,
      p256dh: keys.p256dh,
      auth: keys.auth,
    }),
  });
}

function isIOS() {
  return /iPhone|iPad|iPod/.test(navigator.userAgent);
}

export function PushNotificationSetup() {
  useEffect(() => {
    if (!("serviceWorker" in navigator) || !("PushManager" in window)) return;
    // iOS requires a user gesture — the NotificationBell handles it there
    if (isIOS()) return;

    Notification.requestPermission().then((permission) => {
      if (permission !== "granted") return;
      navigator.serviceWorker.ready.then(subscribe).catch(console.error);
    });
  }, []);

  return null;
}

export async function requestPushPermission(): Promise<boolean> {
  if (!("serviceWorker" in navigator) || !("PushManager" in window)) return false;
  const permission = await Notification.requestPermission();
  if (permission !== "granted") return false;
  const reg = await navigator.serviceWorker.ready;
  await subscribe(reg);
  return true;
}
