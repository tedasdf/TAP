"use client";

import { useEffect, useState } from "react";

interface BeforeInstallPromptEvent extends Event {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
}

export function InstallPrompt() {
  const [promptEvent, setPromptEvent] =
    useState<BeforeInstallPromptEvent | null>(null);
  const [visible, setVisible] = useState(false);
  const [isIos, setIsIos] = useState(false);
  const [isStandalone, setIsStandalone] = useState(false);

  useEffect(() => {
    // Already installed
    const standalone =
      window.matchMedia("(display-mode: standalone)").matches ||
      ("standalone" in window.navigator &&
        (window.navigator as { standalone?: boolean }).standalone === true);

    if (standalone) {
      setIsStandalone(true);
      return;
    }

    // Dismissed before
    const dismissed = localStorage.getItem("tap-install-dismissed");
    if (dismissed) return;

    // iOS detection (no beforeinstallprompt on iOS)
    const ios =
      /iphone|ipad|ipod/i.test(navigator.userAgent) &&
      !(window as { MSStream?: unknown }).MSStream;

    if (ios) {
      setIsIos(true);
      // Show iOS instructions after a short delay
      setTimeout(() => setVisible(true), 3000);
      return;
    }

    // Android / Chrome — capture the native prompt
    const handler = (e: Event) => {
      e.preventDefault();
      setPromptEvent(e as BeforeInstallPromptEvent);
      setTimeout(() => setVisible(true), 3000);
    };

    window.addEventListener("beforeinstallprompt", handler);
    return () => window.removeEventListener("beforeinstallprompt", handler);
  }, []);

  const handleInstall = async () => {
    if (!promptEvent) return;
    await promptEvent.prompt();
    const { outcome } = await promptEvent.userChoice;
    if (outcome === "accepted") {
      setVisible(false);
    }
    setPromptEvent(null);
  };

  const handleDismiss = () => {
    setVisible(false);
    localStorage.setItem("tap-install-dismissed", "1");
  };

  if (isStandalone || !visible) return null;

  return (
    <div
      style={{
        position: "fixed",
        bottom: "calc(env(safe-area-inset-bottom, 0px) + 80px)",
        left: 16,
        right: 16,
        zIndex: 9999,
        background: "#1D9E75",
        borderRadius: 16,
        padding: "14px 16px",
        display: "flex",
        alignItems: "flex-start",
        gap: 12,
        boxShadow: "0 4px 24px rgba(0,0,0,0.18)",
        animation: "tap-slide-up 0.25s ease",
      }}
    >
      <style>{`
        @keyframes tap-slide-up {
          from { transform: translateY(20px); opacity: 0; }
          to   { transform: translateY(0);   opacity: 1; }
        }
      `}</style>

      {/* Icon */}
      <div
        style={{
          width: 40,
          height: 40,
          borderRadius: 10,
          background: "#0F6E56",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          flexShrink: 0,
          fontSize: 15,
          fontWeight: 700,
          color: "white",
          letterSpacing: 0.5,
        }}
      >
        TAP
      </div>

      {/* Text */}
      <div style={{ flex: 1, minWidth: 0 }}>
        <div
          style={{
            fontSize: 14,
            fontWeight: 600,
            color: "white",
            marginBottom: 2,
          }}
        >
          Add TAP to Home Screen
        </div>
        <div style={{ fontSize: 12, color: "rgba(255,255,255,0.8)", lineHeight: 1.4 }}>
          {isIos
            ? 'Tap the share button below, then "Add to Home Screen"'
            : "Install for quick access to your runs"}
        </div>
      </div>

      {/* Actions */}
      <div style={{ display: "flex", gap: 8, flexShrink: 0, alignItems: "center" }}>
        {!isIos && (
          <button
            onClick={handleInstall}
            style={{
              background: "white",
              color: "#0F6E56",
              border: "none",
              borderRadius: 8,
              padding: "7px 14px",
              fontSize: 13,
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            Install
          </button>
        )}
        <button
          onClick={handleDismiss}
          style={{
            background: "transparent",
            border: "none",
            color: "rgba(255,255,255,0.7)",
            fontSize: 20,
            cursor: "pointer",
            padding: "4px 6px",
            lineHeight: 1,
          }}
          aria-label="Dismiss"
        >
          ×
        </button>
      </div>
    </div>
  );
}
