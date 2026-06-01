import { BottomNav } from "@/components/navigation/bottom-nav";
import { NotificationBell } from "@/components/layout/NotificationBell";

export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-black text-white">
      <header className="sticky top-0 z-40 border-b border-zinc-800 bg-black/95 backdrop-blur">
        <div className="mx-auto flex max-w-3xl items-center justify-between px-4 py-3">
          <span className="text-sm font-semibold tracking-wide text-zinc-300">TAP</span>
          <NotificationBell />
        </div>
      </header>

      <div className="mx-auto w-full max-w-3xl px-4 py-6 pb-24">
        {children}
      </div>

      <BottomNav />
    </div>
  );
}