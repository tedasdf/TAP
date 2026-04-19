type EmptyStateProps = {
  title: string;
  description?: string;
};

export function EmptyState({ title, description }: EmptyStateProps) {
  return (
    <div className="rounded-2xl border border-zinc-800 bg-zinc-900/60 p-4 text-center">
      <p className="text-sm font-medium text-white">{title}</p>
      {description ? <p className="mt-1 text-sm text-zinc-400">{description}</p> : null}
    </div>
  );
}