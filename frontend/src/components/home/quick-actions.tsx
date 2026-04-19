import Link from "next/link";
import { Bell, Plus, RefreshCw } from "lucide-react";
import { SectionTitle } from "@/components/shared/section-title";

export function QuickActions() {
  const actions = [
    {
      label: "Create Run",
      description: "Launch a new experiment",
      href: "/runs/new",
      icon: Plus,
    },
    {
      label: "Alerts",
      description: "Check notifications",
      href: "/alerts",
      icon: Bell,
    },
    {
      label: "System",
      description: "View system status",
      href: "/system",
      icon: RefreshCw,
    },
  ];

  return (
    <section>
      <SectionTitle title="Quick Actions" />
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        {actions.map((action) => {
          const Icon = action.icon;
          return (
            <Link
              key={action.label}
              href={action.href}
              className="rounded-2xl border border-zinc-800 bg-zinc-900/70 p-4 transition hover:border-zinc-700"
            >
              <Icon className="h-5 w-5 text-zinc-300" />
              <h3 className="mt-3 text-sm font-semibold text-white">{action.label}</h3>
              <p className="mt-1 text-sm text-zinc-400">{action.description}</p>
            </Link>
          );
        })}
      </div>
    </section>
  );
}