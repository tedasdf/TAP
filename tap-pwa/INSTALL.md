# TAP PWA — Installation Instructions

## Files delivered

```
public/
  manifest.json                  ← Web app manifest
  sw.js                          ← Service worker
  icons/
    icon-72x72.png
    icon-96x96.png
    icon-128x128.png
    icon-144x144.png
    icon-152x152.png
    icon-192x192.png
    icon-192x192-maskable.png    ← Android adaptive icon
    icon-384x384.png
    icon-512x512.png
    apple-touch-icon.png         ← iOS home screen icon

src/app/
  layout.tsx                     ← Replace your existing layout.tsx

src/components/
  ServiceWorkerRegistration.tsx  ← New component
  InstallPrompt.tsx              ← New component

next.config.ts                   ← Replace your existing next.config.ts
```

---

## Steps

### 1. Copy icons

```bash
cp -r icons/ frontend/public/icons/
cp manifest.json frontend/public/manifest.json
cp sw.js frontend/public/sw.js
```

### 2. Replace layout.tsx

```bash
cp layout.tsx frontend/src/app/layout.tsx
```

### 3. Add the two new components

```bash
cp ServiceWorkerRegistration.tsx frontend/src/components/ServiceWorkerRegistration.tsx
cp InstallPrompt.tsx frontend/src/components/InstallPrompt.tsx
```

### 4. Replace next.config.ts

```bash
cp next.config.ts frontend/next.config.ts
```

### 5. Rebuild and deploy

```bash
cd frontend
npm run build
```

---

## Installing on your phone

### iOS (Safari)
1. Open TAP in Safari
2. Tap the **Share** button (box with arrow)
3. Scroll down → **Add to Home Screen**
4. Tap **Add**

The install banner in the app will show these instructions automatically on first visit.

### Android (Chrome)
1. Open TAP in Chrome
2. Tap the **⋮** menu → **Add to Home Screen**
   — or tap the **Install** banner that appears at the bottom of the screen

---

## What you get

- **Standalone mode** — no browser chrome, looks like a native app
- **Offline shell** — app loads even when your phone has no signal (API calls will fail gracefully, but the UI opens)
- **App shortcuts** — long-press the icon to jump directly to Runs, New Run, or Templates
- **Cached API responses** — last-known data shown while reconnecting
- **Theme color** — status bar matches TAP teal on both iOS and Android

---

## Notes

- The service worker caches API responses from port 8000. If you change your backend URL, update `sw.js` line: `url.port === '8000'`
- The install prompt won't show again once dismissed. To reset: `localStorage.removeItem('tap-install-dismissed')` in the browser console.
- iOS does not support the native install prompt — the banner shows manual instructions instead.
