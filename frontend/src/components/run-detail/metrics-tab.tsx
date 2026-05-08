
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
  trainingLoss: number | null;
  validationLoss: number | null;
  learningRate: number | null;
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
  return (
    <div className="rounded-2xl border border-zinc-800 bg-zinc-900/70 p-4">
      <h3 className="text-sm font-semibold text-white">{title}</h3>
      <div className="mt-4 h-56">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data}>
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
    </div>
  );
}

export function MetricsTab({ data }: MetricsTabProps) {
  return (
    <div className="space-y-4">
      <ChartCard title="Training Loss" data={data} dataKey="trainingLoss" />
      <ChartCard title="Validation Loss" data={data} dataKey="validationLoss" />
      <ChartCard title="Learning Rate" data={data} dataKey="learningRate" />
    </div>
  );
}