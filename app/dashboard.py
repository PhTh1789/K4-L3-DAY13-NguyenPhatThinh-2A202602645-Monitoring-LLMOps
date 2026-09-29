from __future__ import annotations

import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .logging_config import LOG_PATH


def _calculate_percentile(values: list[int | float], p: float) -> float:
    if not values:
        return 0.0
    sorted_vals = sorted(values)
    idx = max(0, min(len(sorted_vals) - 1, math.ceil((p / 100.0) * len(sorted_vals)) - 1))
    return float(sorted_vals[idx])


def get_dashboard_metrics(time_window_minutes: int = 60) -> dict[str, Any]:
    log_file = Path(LOG_PATH)
    if not log_file.exists():
        return {}

    now = datetime.now(timezone.utc)
    records: list[dict[str, Any]] = []

    for line in log_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
            ts_str = rec.get("ts")
            if ts_str:
                ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                # Filter within time window
                if (now - ts).total_seconds() <= time_window_minutes * 60:
                    records.append(rec)
        except Exception:
            continue

    latencies: list[int] = []
    ttfts: list[int] = []
    costs: list[float] = []
    tokens_in_list: list[int] = []
    tokens_out_list: list[int] = []
    qualities: list[float] = []
    request_received_count = 0
    request_failed_count = 0
    error_types: dict[str, int] = {}
    tool_successes = 0
    tool_total = 0

    timestamps_min: dict[str, dict[str, Any]] = {}

    for r in records:
        event = r.get("event")
        ts_str = r.get("ts", "")[:16]  # group by YYYY-MM-DDTHH:MM
        if ts_str not in timestamps_min:
            timestamps_min[ts_str] = {"req": 0, "cost": 0.0, "tokens": 0}

        if event == "request_received":
            request_received_count += 1
            timestamps_min[ts_str]["req"] += 1

        elif event == "response_sent":
            lat = r.get("latency_ms")
            if lat is not None:
                latencies.append(lat)
            ttft = r.get("ttft_ms")
            if ttft is not None:
                ttfts.append(ttft)
            c = r.get("cost_usd")
            if c is not None:
                costs.append(c)
                timestamps_min[ts_str]["cost"] += c
            tin = r.get("tokens_in")
            if tin is not None:
                tokens_in_list.append(tin)
                timestamps_min[ts_str]["tokens"] += tin
            tout = r.get("tokens_out")
            if tout is not None:
                tokens_out_list.append(tout)
                timestamps_min[ts_str]["tokens"] += tout
            q = r.get("quality_score")
            if q is not None:
                qualities.append(q)
            if "tool_success" in r and r.get("tool_name") == "retrieval":
                tool_total += 1
                if r["tool_success"]:
                    tool_successes += 1

        elif event == "request_failed":
            request_failed_count += 1
            err = r.get("error_type", "UnknownError")
            error_types[err] = error_types.get(err, 0) + 1
            if r.get("tool_name") == "retrieval":
                tool_total += 1

    p50 = _calculate_percentile(latencies, 50)
    p95 = _calculate_percentile(latencies, 95)
    p99 = _calculate_percentile(latencies, 99)
    ttft_p95 = _calculate_percentile(ttfts, 95)
    error_rate_pct = round((request_failed_count / max(1, request_received_count)) * 100, 2)
    tool_success_rate_pct = round((tool_successes / max(1, tool_total)) * 100, 2)
    total_cost = round(sum(costs), 4)
    tokens_in_total = sum(tokens_in_list)
    tokens_out_total = sum(tokens_out_list)
    quality_avg = round(sum(qualities) / max(1, len(qualities)), 2)

    # Sort minute timeline
    sorted_minutes = sorted(timestamps_min.keys())
    minute_labels = [m[-5:] for m in sorted_minutes]  # HH:MM
    traffic_series = [timestamps_min[m]["req"] for m in sorted_minutes]
    cost_series = [round(timestamps_min[m]["cost"], 4) for m in sorted_minutes]

    return {
        "p50": p50,
        "p95": p95,
        "p99": p99,
        "ttft_p95": ttft_p95,
        "traffic_count": request_received_count,
        "traffic_rate_per_min": round(request_received_count / max(1, len(sorted_minutes)), 1),
        "error_rate_pct": error_rate_pct,
        "tool_success_rate_pct": tool_success_rate_pct,
        "error_breakdown": error_types,
        "total_cost_usd": total_cost,
        "tokens_in_total": tokens_in_total,
        "tokens_out_total": tokens_out_total,
        "quality_avg": quality_avg,
        "minute_labels": minute_labels or ["Now"],
        "traffic_series": traffic_series or [0],
        "cost_series": cost_series or [0.0],
    }


def render_dashboard_html() -> str:
    data = get_dashboard_metrics()
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta http-equiv="refresh" content="30">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>K4-L3A Day 13 Monitoring & LLMOps Dashboard</title>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <style>
    :root {{
      --bg: #0f172a;
      --card-bg: #1e293b;
      --border: #334155;
      --text: #f8fafc;
      --text-muted: #94a3b8;
      --primary: #38bdf8;
      --accent: #818cf8;
      --success: #34d399;
      --warning: #fbbf24;
      --danger: #f87171;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      background: var(--bg);
      color: var(--text);
      padding: 24px;
      line-height: 1.5;
    }}
    header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 24px;
      padding-bottom: 16px;
      border-bottom: 1px solid var(--border);
    }}
    h1 {{ font-size: 24px; font-weight: 700; color: var(--text); }}
    .badge {{
      display: inline-block;
      padding: 4px 12px;
      border-radius: 9999px;
      font-size: 12px;
      font-weight: 600;
      background: rgba(56, 189, 248, 0.15);
      color: var(--primary);
      border: 1px solid var(--primary);
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(360px, 1fr));
      gap: 20px;
    }}
    .panel {{
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 20px;
      display: flex;
      flex-direction: column;
      position: relative;
    }}
    .panel-header {{
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 16px;
    }}
    .panel-title {{
      font-size: 15px;
      font-weight: 600;
      color: var(--text);
    }}
    .panel-unit {{
      font-size: 11px;
      color: var(--text-muted);
      text-transform: uppercase;
    }}
    .threshold-badge {{
      font-size: 11px;
      font-weight: 500;
      color: var(--warning);
      background: rgba(251, 191, 36, 0.1);
      padding: 2px 8px;
      border-radius: 4px;
      border: 1px solid rgba(251, 191, 36, 0.3);
    }}
    .metrics-row {{
      display: flex;
      gap: 16px;
      margin-bottom: 12px;
    }}
    .stat {{
      flex: 1;
      background: rgba(15, 23, 42, 0.6);
      padding: 12px;
      border-radius: 8px;
      border: 1px solid var(--border);
    }}
    .stat-label {{
      font-size: 11px;
      color: var(--text-muted);
      margin-bottom: 4px;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }}
    .stat-value {{
      font-size: 20px;
      font-weight: 700;
      color: var(--text);
    }}
    .chart-container {{
      height: 180px;
      margin-top: auto;
    }}
  </style>
</head>
<body>
  <header>
    <div>
      <h1>K4-L3A Day 13 Monitoring & LLMOps Dashboard</h1>
      <p style="color: var(--text-muted); font-size: 13px; margin-top: 4px;">
        Source: <code>data/logs.jsonl</code> &bull; Time Range: <strong>60 minutes</strong> &bull; Refresh: <strong>30s</strong>
      </p>
    </div>
    <div>
      <span class="badge">SLO Target: 99.5%</span>
    </div>
  </header>

  <div class="grid">
    <!-- Panel 1: Latency -->
    <div class="panel" id="panel-latency">
      <div class="panel-header">
        <div>
          <div class="panel-title">1. Latency percentiles and TTFT</div>
          <div class="panel-unit">Unit: ms</div>
        </div>
        <div class="threshold-badge">SLO Threshold: P95 &le; 3000 ms</div>
      </div>
      <div class="metrics-row">
        <div class="stat"><div class="stat-label">P50 Latency</div><div class="stat-value">{data.get('p50', 0):.0f} <span style="font-size: 12px;">ms</span></div></div>
        <div class="stat"><div class="stat-label">P95 Latency</div><div class="stat-value" style="color: {'var(--danger)' if data.get('p95', 0) > 3000 else 'var(--success)'};">{data.get('p95', 0):.0f} <span style="font-size: 12px;">ms</span></div></div>
        <div class="stat"><div class="stat-label">P99 Latency</div><div class="stat-value">{data.get('p99', 0):.0f} <span style="font-size: 12px;">ms</span></div></div>
        <div class="stat"><div class="stat-label">TTFT P95</div><div class="stat-value">{data.get('ttft_p95', 0):.0f} <span style="font-size: 12px;">ms</span></div></div>
      </div>
      <div class="chart-container">
        <canvas id="latencyChart"></canvas>
      </div>
    </div>

    <!-- Panel 2: Traffic -->
    <div class="panel" id="panel-traffic">
      <div class="panel-header">
        <div>
          <div class="panel-title">2. Request traffic</div>
          <div class="panel-unit">Unit: requests / min</div>
        </div>
        <div class="threshold-badge">Threshold: Rate &ge; 1 req/min</div>
      </div>
      <div class="metrics-row">
        <div class="stat"><div class="stat-label">Total Requests</div><div class="stat-value">{data.get('traffic_count', 0)}</div></div>
        <div class="stat"><div class="stat-label">Rate / Min</div><div class="stat-value">{data.get('traffic_rate_per_min', 0)}</div></div>
      </div>
      <div class="chart-container">
        <canvas id="trafficChart"></canvas>
      </div>
    </div>

    <!-- Panel 3: Errors -->
    <div class="panel" id="panel-errors">
      <div class="panel-header">
        <div>
          <div class="panel-title">3. Error rate and retrieval success</div>
          <div class="panel-unit">Unit: percent (%)</div>
        </div>
        <div class="threshold-badge">Threshold: Error &le; 2.0%</div>
      </div>
      <div class="metrics-row">
        <div class="stat"><div class="stat-label">Error Rate</div><div class="stat-value" style="color: {'var(--danger)' if data.get('error_rate_pct', 0) > 2.0 else 'var(--success)'};">{data.get('error_rate_pct', 0)}%</div></div>
        <div class="stat"><div class="stat-label">Retrieval Success</div><div class="stat-value" style="color: var(--success);">{data.get('tool_success_rate_pct', 100)}%</div></div>
      </div>
      <div class="chart-container">
        <canvas id="errorChart"></canvas>
      </div>
    </div>

    <!-- Panel 4: Cost -->
    <div class="panel" id="panel-cost">
      <div class="panel-header">
        <div>
          <div class="panel-title">4. Cost over time</div>
          <div class="panel-unit">Unit: USD ($)</div>
        </div>
        <div class="threshold-badge">Budget Threshold: Total &le; $2.5</div>
      </div>
      <div class="metrics-row">
        <div class="stat"><div class="stat-label">Total Cost</div><div class="stat-value">${data.get('total_cost_usd', 0):.4f}</div></div>
        <div class="stat"><div class="stat-label">Budget Remaining</div><div class="stat-value">${max(0, 2.5 - data.get('total_cost_usd', 0)):.4f}</div></div>
      </div>
      <div class="chart-container">
        <canvas id="costChart"></canvas>
      </div>
    </div>

    <!-- Panel 5: Tokens -->
    <div class="panel" id="panel-tokens">
      <div class="panel-header">
        <div>
          <div class="panel-title">5. Input and output tokens</div>
          <div class="panel-unit">Unit: tokens</div>
        </div>
        <div class="threshold-badge">Threshold: Sum &le; 50,000</div>
      </div>
      <div class="metrics-row">
        <div class="stat"><div class="stat-label">Input Tokens</div><div class="stat-value">{data.get('tokens_in_total', 0):,}</div></div>
        <div class="stat"><div class="stat-label">Output Tokens</div><div class="stat-value">{data.get('tokens_out_total', 0):,}</div></div>
        <div class="stat"><div class="stat-label">Total Tokens</div><div class="stat-value">{data.get('tokens_in_total', 0) + data.get('tokens_out_total', 0):,}</div></div>
      </div>
      <div class="chart-container">
        <canvas id="tokensChart"></canvas>
      </div>
    </div>

    <!-- Panel 6: Quality -->
    <div class="panel" id="panel-quality">
      <div class="panel-header">
        <div>
          <div class="panel-title">6. Quality proxy</div>
          <div class="panel-unit">Unit: score (0.0 to 1.0)</div>
        </div>
        <div class="threshold-badge">Threshold: Mean &ge; 0.75</div>
      </div>
      <div class="metrics-row">
        <div class="stat"><div class="stat-label">Mean Quality Score</div><div class="stat-value" style="color: {'var(--success)' if data.get('quality_avg', 0) >= 0.75 else 'var(--danger)'};">{data.get('quality_avg', 0):.2f} / 1.0</div></div>
      </div>
      <div class="chart-container">
        <canvas id="qualityChart"></canvas>
      </div>
    </div>
  </div>

  <script>
    const labels = {json.dumps(data.get('minute_labels', []))};
    const trafficData = {json.dumps(data.get('traffic_series', []))};
    const costData = {json.dumps(data.get('cost_series', []))};

    // 1. Latency Bar Chart
    new Chart(document.getElementById('latencyChart'), {{
      type: 'bar',
      data: {{
        labels: ['P50', 'P95', 'P99', 'TTFT P95'],
        datasets: [{{
          label: 'Latency (ms)',
          data: [{data.get('p50', 0)}, {data.get('p95', 0)}, {data.get('p99', 0)}, {data.get('ttft_p95', 0)}],
          backgroundColor: ['#38bdf8', '#818cf8', '#f87171', '#34d399']
        }}]
      }},
      options: {{
        responsive: true,
        maintainAspectRatio: false,
        plugins: {{ legend: {{ display: false }} }},
        scales: {{ y: {{ beginAtZero: true, grid: {{ color: '#334155' }} }} }}
      }}
    }});

    // 2. Traffic Line Chart
    new Chart(document.getElementById('trafficChart'), {{
      type: 'line',
      data: {{
        labels: labels,
        datasets: [{{
          label: 'Requests',
          data: trafficData,
          borderColor: '#38bdf8',
          backgroundColor: 'rgba(56, 189, 248, 0.1)',
          fill: true,
          tension: 0.3
        }}]
      }},
      options: {{
        responsive: true,
        maintainAspectRatio: false,
        plugins: {{ legend: {{ display: false }} }},
        scales: {{ y: {{ beginAtZero: true, grid: {{ color: '#334155' }} }} }}
      }}
    }});

    // 3. Error Doughnut Chart
    new Chart(document.getElementById('errorChart'), {{
      type: 'doughnut',
      data: {{
        labels: ['Successful Requests', 'Failed Requests'],
        datasets: [{{
          data: [{max(0, 100 - data.get('error_rate_pct', 0))}, {data.get('error_rate_pct', 0)}],
          backgroundColor: ['#34d399', '#f87171']
        }}]
      }},
      options: {{
        responsive: true,
        maintainAspectRatio: false,
        plugins: {{ legend: {{ position: 'bottom', labels: {{ color: '#94a3b8' }} }} }}
      }}
    }});

    // 4. Cost Chart
    new Chart(document.getElementById('costChart'), {{
      type: 'line',
      data: {{
        labels: labels,
        datasets: [{{
          label: 'Cost (USD)',
          data: costData,
          borderColor: '#fbbf24',
          backgroundColor: 'rgba(251, 191, 36, 0.1)',
          fill: true,
          tension: 0.3
        }}]
      }},
      options: {{
        responsive: true,
        maintainAspectRatio: false,
        plugins: {{ legend: {{ display: false }} }},
        scales: {{ y: {{ beginAtZero: true, grid: {{ color: '#334155' }} }} }}
      }}
    }});

    // 5. Tokens Bar Chart
    new Chart(document.getElementById('tokensChart'), {{
      type: 'bar',
      data: {{
        labels: ['Tokens In', 'Tokens Out'],
        datasets: [{{
          data: [{data.get('tokens_in_total', 0)}, {data.get('tokens_out_total', 0)}],
          backgroundColor: ['#818cf8', '#38bdf8']
        }}]
      }},
      options: {{
        responsive: true,
        maintainAspectRatio: false,
        plugins: {{ legend: {{ display: false }} }},
        scales: {{ y: {{ beginAtZero: true, grid: {{ color: '#334155' }} }} }}
      }}
    }});

    // 6. Quality Gauge Chart
    new Chart(document.getElementById('qualityChart'), {{
      type: 'doughnut',
      data: {{
        labels: ['Quality Score', 'Remaining'],
        datasets: [{{
          data: [{data.get('quality_avg', 0)}, {max(0, round(1.0 - data.get('quality_avg', 0), 2))}],
          backgroundColor: ['#34d399', '#334155'],
          circumference: 180,
          rotation: 270
        }}]
      }},
      options: {{
        responsive: true,
        maintainAspectRatio: false,
        plugins: {{ legend: {{ display: false }} }}
      }}
    }});
  </script>
</body>
</html>
"""
