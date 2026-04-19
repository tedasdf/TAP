import { BottomNav } from "@/components/navigation/bottom-nav";

export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-black text-white">
      <div className="mx-auto w-full max-w-3xl px-4 py-6 pb-24">{children}</div>
      <BottomNav />
    </div>
  );
}