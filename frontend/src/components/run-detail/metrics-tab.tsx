import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

type MetricsPoint = {
  step: number;
  trainingLoss?: number | null;
  validationLoss?: number | null;
  learningRate?: number | null;
};

type MetricsTabProps = {
  data: MetricsPoint[];
};

function ChartCard({
  title,
  data,
  dataKey,
}: {
  title: string;
  data: MetricsPoint[];
  dataKey: "trainingLoss" | "validationLoss" | "learningRate";
}) {
  const chartData = data.filter((point) => typeof point[dataKey] === "number");

  return (
    <div className="rounded-2xl border border-zinc-800 bg-zinc-900/70 p-4">
      <h3 className="text-sm font-semibold text-white">{title}</h3>
      {chartData.length < 2 ? (
        <div className="mt-4 flex h-56 items-center justify-center rounded-xl border border-dashed border-zinc-800 text-center text-sm text-zinc-500">
          Not enough real metric history yet.
        </div>
      ) : (
        <div className="mt-4 h-56">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData}>
              <CartesianGrid stroke="#27272a" strokeDasharray="3 3" />
              <XAxis dataKey="step" stroke="#71717a" fontSize={12} />
              <YAxis stroke="#71717a" fontSize={12} />
              <Tooltip
                contentStyle={{
                  background: "#09090b",
                  border: "1px solid #27272a",
                  borderRadius: 12,
                  color: "#fff",
                }}
              />
              <Line type="monotone" dataKey={dataKey} stroke="#fafafa" dot={false} strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}

export function MetricsTab({ data }: MetricsTabProps) {
  return (
    <div className="space-y-4">
      <div className="rounded-2xl border border-emerald-500/20 bg-emerald-500/10 p-4 text-sm text-emerald-100">
        Charts below use real metric history from TAP. No synthetic chart points are generated.
      </div>
      <ChartCard title="Training Loss" data={data} dataKey="trainingLoss" />
      <ChartCard title="Validation Loss" data={data} dataKey="validationLoss" />
      <ChartCard title="Learning Rate" data={data} dataKey="learningRate" />
    </div>
  );
}
