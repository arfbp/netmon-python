import { useMemo } from "react";
import ReactECharts from "echarts-for-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { CHART_COLORS } from "@/lib/colors";
import type { TargetState } from "@/store/pingStore";

export function PingChart({ targets }: { targets: TargetState[] }) {
  const option = useMemo(() => {
    const series = targets.map((target, index) => ({
      name: target.target,
      type: "line" as const,
      showSymbol: false,
      smooth: true,
      lineStyle: { width: 2, color: CHART_COLORS.series[index % CHART_COLORS.series.length] },
      itemStyle: { color: CHART_COLORS.series[index % CHART_COLORS.series.length] },
      data: target.history.map((point) => [point.t, point.v]),
      connectNulls: false,
    }));

    return {
      backgroundColor: "transparent",
      textStyle: { color: CHART_COLORS.textMuted, fontFamily: "inherit" },
      grid: { left: 48, right: 16, top: 32, bottom: 32 },
      legend: {
        data: targets.map((t) => t.target),
        textStyle: { color: CHART_COLORS.textMuted, fontSize: 11 },
        top: 0,
      },
      xAxis: {
        type: "time",
        axisLine: { lineStyle: { color: CHART_COLORS.border } },
        axisLabel: { color: CHART_COLORS.textMuted, fontSize: 10 },
        splitLine: { show: false },
      },
      yAxis: {
        type: "value",
        name: "ms",
        nameTextStyle: { color: CHART_COLORS.textMuted },
        axisLine: { show: false },
        axisLabel: { color: CHART_COLORS.textMuted, fontSize: 10 },
        splitLine: { lineStyle: { color: CHART_COLORS.border, type: "dashed" } },
      },
      tooltip: {
        trigger: "axis" as const,
        backgroundColor: CHART_COLORS.surface,
        borderColor: CHART_COLORS.border,
        textStyle: { color: "#E7EAF2" },
        valueFormatter: (value: unknown) =>
          value === null || value === undefined ? "timeout" : `${Number(value).toFixed(1)} ms`,
      },
      series,
    };
  }, [targets]);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Live latency</CardTitle>
      </CardHeader>
      <CardContent>
        {targets.length === 0 ? (
          <div className="flex h-64 items-center justify-center text-sm text-content-muted">
            Waiting for the first ping results…
          </div>
        ) : (
          <ReactECharts option={option} style={{ height: 280 }} notMerge={false} lazyUpdate />
        )}
      </CardContent>
    </Card>
  );
}
