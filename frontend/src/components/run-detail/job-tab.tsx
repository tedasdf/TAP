type JobTabProps = {
  job: {
    jobId: string;
    queueState: string;
    executionState: string;
    nodeInfo?: string;
    startTime?: string;
    endTime?: string;
    exitStatus?: string;
    logPath?: string;
    errorLogPath?: string;
  };
};

export function JobTab({ job }: JobTabProps) {
  const rows = [
    { label: "Job ID", value: job.jobId },
    { label: "Queue State", value: job.queueState },
    { label: "Execution State", value: job.executionState },
    { label: "Node", value: job.nodeInfo ?? "—" },
    { label: "Start Time", value: job.startTime ?? "—" },
    { label: "End Time", value: job.endTime ?? "—" },
    { label: "Exit Status", value: job.exitStatus ?? "—" },
    { label: "Log Path", value: job.logPath ?? "—" },
    { label: "Error Log Path", value: job.errorLogPath ?? "—" },
  ];

  return (
    <div className="rounded-2xl border border-zinc-800 bg-zinc-900/70 p-4">
      <div className="space-y-4 text-sm">
        {rows.map((row) => (
          <div key={row.label} className="flex justify-between gap-4">
            <span className="text-zinc-500">{row.label}</span>
            <span className="max-w-[60%] text-right text-zinc-200 break-words">{row.value}</span>
          </div>
        ))}
      </div>
    </div>
  );
}