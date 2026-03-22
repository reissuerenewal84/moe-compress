#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render a normalized REAP run manifest into JSON, Markdown, and HTML."
    )
    parser.add_argument("--manifest", required=True, help="Path to the normalized run manifest JSON.")
    parser.add_argument("--output-dir", required=True, help="Directory for report outputs.")
    return parser.parse_args()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def write_json(path: Path, payload: Any) -> None:
    write_text(path, json.dumps(payload, indent=2) + "\n")


def fmt_num(value: Any, digits: int = 2) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def markdown_table(headers: list[str], rows: list[list[Any]]) -> str:
    out = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    for row in rows:
        out.append("| " + " | ".join(str(cell) for cell in row) + " |")
    return "\n".join(out)


def build_report(manifest: dict[str, Any]) -> dict[str, Any]:
    runtime_rows = manifest["benchmarking"]["runtime_rows"]
    successful_rows = [row for row in runtime_rows if row.get("status") == "ok"]
    best_prefill = max(successful_rows, key=lambda row: row.get("prefill_toks_per_s") or 0, default=None)
    best_generation = max(successful_rows, key=lambda row: row.get("generation_toks_per_s") or 0, default=None)
    fastest_ttft = min(
        [row for row in successful_rows if row.get("ttft_s") is not None],
        key=lambda row: row["ttft_s"],
        default=None,
    )

    report = {
        "schema_version": 1,
        "title": manifest["title"],
        "subtitle": manifest.get("subtitle", ""),
        "model": manifest["model"],
        "calibration": manifest["calibration"],
        "pruning": manifest["pruning"],
        "quantization": manifest["quantization"],
        "publishing": manifest["publishing"],
        "benchmarking": manifest["benchmarking"],
        "results": manifest["results"],
        "derived": {
            "best_prefill_variant": None if not best_prefill else best_prefill["variant"],
            "best_prefill_toks_per_s": None if not best_prefill else best_prefill["prefill_toks_per_s"],
            "best_generation_variant": None if not best_generation else best_generation["variant"],
            "best_generation_toks_per_s": None if not best_generation else best_generation["generation_toks_per_s"],
            "fastest_ttft_variant": None if not fastest_ttft else fastest_ttft["variant"],
            "fastest_ttft_s": None if not fastest_ttft else fastest_ttft["ttft_s"],
            "successful_runtime_rows": len(successful_rows),
        },
        "source_artifacts": manifest.get("source_artifacts", []),
    }
    return report


def render_markdown(report: dict[str, Any]) -> str:
    calibration = report["calibration"]
    model = report["model"]
    pruning = report["pruning"]
    quantization = report["quantization"]
    publishing = report["publishing"]
    benchmarking = report["benchmarking"]
    results = report["results"]
    derived = report["derived"]
    local_dataset_path = calibration.get("local_dataset_path") or "n/a"

    lane_rows = [
        [
            lane["name"],
            lane["selection"],
            lane["input_rows"],
            lane["processed_samples"],
            lane["max_tokens"],
            lane["observed_tokens"],
        ]
        for lane in calibration["lanes"]
    ]
    source_rows = [
        [source["dataset"], source.get("config") or "default", source["rows"]]
        for source in calibration["public_mix"]
    ]
    prune_rows = [
        [
            variant["name"],
            variant["experts_before"],
            variant["experts_pruned"],
            variant["experts_retained"],
            variant["status"],
        ]
        for variant in pruning["variants"]
    ]
    quant_rows = [
        [attempt["name"], attempt["method"], attempt["status"], attempt["note"]]
        for attempt in quantization["attempts"]
    ]
    runtime_rows = [
        [
            row["variant"],
            row["status"],
            fmt_num(row.get("gpu_gib")),
            fmt_num(row.get("cpu_gib")),
            fmt_num(row.get("ttft_s")),
            fmt_num(row.get("prefill_toks_per_s")),
            fmt_num(row.get("generation_toks_per_s")),
            row["note"],
        ]
        for row in benchmarking["runtime_rows"]
    ]
    gate_rows = [
        [gate["gate"], gate["status"], gate["summary"]]
        for gate in benchmarking["gates"]
    ]

    sections = [
        f"# {report['title']}",
        "",
        report.get("subtitle", ""),
        "",
        "## Model",
        f"- Label: `{model['label']}`",
        f"- Base model: `{model['base_model']}`",
        f"- Weights path: `{model['weights_path']}`",
        f"- Architecture: `{model['architecture']}`",
        f"- Topology: `{fmt_num(model['total_layers'])}` total layers, `{fmt_num(model['moe_layers'])}` MoE layers, `{fmt_num(model['experts_per_layer'])}` experts/layer, `{fmt_num(model['experts_per_token'])}` routed experts/token",
        "",
        "## Calibration bundle",
        f"- Bundle: `{calibration['bundle_name']}`",
        f"- Local dataset: `{local_dataset_path}`",
        f"- Merged workflow: `{calibration['merged_workflow']}`",
        f"- Merged processed samples: `{calibration['merged_processed_samples']}`",
        f"- Merged observed tokens: `{fmt_num(calibration['merged_observed_tokens'])}`",
        "",
        markdown_table(
            ["Lane", "Selection", "Input rows", "Processed samples", "Max tokens", "Observed tokens"],
            lane_rows,
        ),
        "",
        "### Public mix",
        markdown_table(["Dataset", "Config", "Rows"], source_rows),
        "",
        "## Pruning",
        markdown_table(["Variant", "Experts before", "Experts pruned", "Experts retained", "Status"], prune_rows),
        "",
        "## Quantization",
        markdown_table(["Variant", "Method", "Status", "Notes"], quant_rows),
        "",
        "## Publishing",
        f"- Publish status: `{publishing['status']}`",
        f"- Artifact repo: `{publishing['artifact_repo']}`",
        f"- Publish manifest: `{publishing['publish_manifest_path']}`",
        "",
        "Published model repos:",
        *[f"- `{repo}`" for repo in publishing["model_repos"]],
        "",
        "## Benchmarking",
        markdown_table(
            ["Variant", "Status", "GPU GiB", "CPU GiB", "TTFT s", "Prefill tok/s", "Gen tok/s", "Notes"],
            runtime_rows,
        ),
        "",
        "### Accuracy",
        f"- Overall accuracy: `{fmt_num(benchmarking['accuracy']['overall_accuracy'])}`",
        f"- Coherence rate: `{fmt_num(benchmarking['accuracy']['coherence_rate'])}`",
        f"- Total samples: `{fmt_num(benchmarking['accuracy']['total_samples'])}`",
        f"- Avg request time: `{fmt_num(benchmarking['accuracy']['avg_request_time_s'])}` s",
        "",
        "### Gates",
        markdown_table(["Gate", "Status", "Summary"], gate_rows),
        "",
        "## Results",
        *[f"- {item}" for item in results["headline_findings"]],
        "",
        "## Derived highlights",
        f"- Successful runtime rows: `{derived['successful_runtime_rows']}`",
        f"- Best prefill: `{derived['best_prefill_variant']}` at `{fmt_num(derived['best_prefill_toks_per_s'])}` tok/s",
        f"- Best generation: `{derived['best_generation_variant']}` at `{fmt_num(derived['best_generation_toks_per_s'])}` tok/s",
        f"- Fastest TTFT: `{derived['fastest_ttft_variant']}` at `{fmt_num(derived['fastest_ttft_s'])}` s",
        "",
        "## Source artifacts",
        *[f"- `{path}`" for path in report["source_artifacts"]],
    ]
    return "\n".join(section for section in sections if section is not None) + "\n"


def render_html(report: dict[str, Any]) -> str:
    calibration = report["calibration"]
    model = report["model"]
    benchmarking = report["benchmarking"]
    results = report["results"]
    derived = report["derived"]

    def list_items(items: list[str]) -> str:
        return "".join(f"<li>{html.escape(item)}</li>" for item in items)

    def table(headers: list[str], rows: list[list[Any]]) -> str:
        head = "".join(f"<th>{html.escape(str(header))}</th>" for header in headers)
        body_rows = []
        for row in rows:
            cols = "".join(f"<td>{html.escape(str(cell))}</td>" for cell in row)
            body_rows.append(f"<tr>{cols}</tr>")
        return f"<table><thead><tr>{head}</tr></thead><tbody>{''.join(body_rows)}</tbody></table>"

    lane_rows = [
        [
            lane["name"],
            lane["selection"],
            lane["input_rows"],
            lane["processed_samples"],
            lane["max_tokens"],
            lane["observed_tokens"],
        ]
        for lane in calibration["lanes"]
    ]
    source_rows = [
        [source["dataset"], source.get("config") or "default", source["rows"]]
        for source in calibration["public_mix"]
    ]
    runtime_rows = [
        [
            row["variant"],
            row["status"],
            fmt_num(row.get("gpu_gib")),
            fmt_num(row.get("cpu_gib")),
            fmt_num(row.get("ttft_s")),
            fmt_num(row.get("prefill_toks_per_s")),
            fmt_num(row.get("generation_toks_per_s")),
        ]
        for row in benchmarking["runtime_rows"]
    ]
    quant_rows = [
        [attempt["name"], attempt["method"], attempt["status"], attempt["note"]]
        for attempt in report["quantization"]["attempts"]
    ]
    gate_rows = [[gate["gate"], gate["status"], gate["summary"]] for gate in benchmarking["gates"]]
    prune_rows = [
        [
            variant["name"],
            variant["experts_before"],
            variant["experts_pruned"],
            variant["experts_retained"],
            variant["status"],
        ]
        for variant in report["pruning"]["variants"]
    ]

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>{html.escape(report['title'])}</title>
  <style>
    :root {{
      --bg: #f7f2ea;
      --surface: rgba(255,255,255,0.82);
      --surface-strong: #fffaf2;
      --border: rgba(62, 46, 30, 0.14);
      --text: #2f2418;
      --text-dim: #625445;
      --accent: #9a3412;
      --accent-soft: rgba(154, 52, 18, 0.12);
      --sage: #4d6b57;
      --blueprint: #1f3b5b;
      --good: #256c45;
      --warn: #b7791f;
      --bad: #a63d2f;
      --shadow: 0 22px 60px rgba(62, 46, 30, 0.08);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      color: var(--text);
      font: 16px/1.55 "IBM Plex Sans", "Avenir Next", "Segoe UI", sans-serif;
      background:
        radial-gradient(circle at top left, rgba(154, 52, 18, 0.12), transparent 32%),
        radial-gradient(circle at top right, rgba(31, 59, 91, 0.10), transparent 28%),
        linear-gradient(180deg, #fbf7f0 0%, #f3ece2 100%);
    }}
    main {{
      max-width: 1220px;
      margin: 0 auto;
      padding: 32px 20px 72px;
    }}
    .hero, .card {{
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 24px;
      box-shadow: var(--shadow);
      backdrop-filter: blur(10px);
      margin-bottom: 22px;
    }}
    .hero {{
      padding: 30px;
      display: grid;
      gap: 18px;
    }}
    .eyebrow {{
      letter-spacing: 0.18em;
      text-transform: uppercase;
      color: var(--accent);
      font-size: 12px;
      font-weight: 700;
    }}
    h1, h2, h3 {{
      margin: 0;
      font-family: "Bricolage Grotesque", "Avenir Next", sans-serif;
    }}
    h1 {{
      font-size: 44px;
      line-height: 1.02;
      max-width: 16ch;
    }}
    h2 {{
      font-size: 28px;
      margin-bottom: 10px;
    }}
    p, li {{
      color: var(--text-dim);
    }}
    .hero-grid {{
      display: grid;
      grid-template-columns: 1.2fr 0.8fr;
      gap: 18px;
    }}
    .kpis {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 12px;
    }}
    .kpi {{
      border-radius: 18px;
      padding: 16px;
      background: var(--surface-strong);
      border: 1px solid var(--border);
    }}
    .kpi .label {{
      color: var(--text-dim);
      font-size: 12px;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      margin-bottom: 8px;
    }}
    .kpi .value {{
      font-size: 26px;
      font-family: "IBM Plex Mono", "SFMono-Regular", monospace;
      color: var(--blueprint);
      font-weight: 700;
    }}
    .card {{
      padding: 22px;
    }}
    .card-grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 18px;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      overflow: hidden;
      border-radius: 16px;
      border: 1px solid var(--border);
      background: rgba(255,255,255,0.72);
    }}
    th, td {{
      padding: 12px 14px;
      text-align: left;
      vertical-align: top;
      border-bottom: 1px solid var(--border);
    }}
    th {{
      background: rgba(31, 59, 91, 0.08);
      color: var(--blueprint);
      font-size: 13px;
      text-transform: uppercase;
      letter-spacing: 0.06em;
    }}
    tbody tr:nth-child(even) {{
      background: rgba(154, 52, 18, 0.03);
    }}
    .pill {{
      display: inline-block;
      padding: 4px 9px;
      border-radius: 999px;
      background: var(--accent-soft);
      color: var(--accent);
      font-size: 12px;
      font-weight: 700;
      letter-spacing: 0.04em;
      text-transform: uppercase;
    }}
    ul {{
      margin: 0;
      padding-left: 18px;
    }}
    code {{
      font-family: "IBM Plex Mono", "SFMono-Regular", monospace;
      color: var(--blueprint);
      word-break: break-word;
    }}
    .artifact-list li {{
      margin-bottom: 8px;
    }}
    @media (max-width: 920px) {{
      .hero-grid, .card-grid, .kpis {{
        grid-template-columns: 1fr;
      }}
      h1 {{
        font-size: 36px;
      }}
    }}
  </style>
</head>
<body>
  <main>
    <section class="hero">
      <div class="eyebrow">REAP Cookbook Report</div>
      <div class="hero-grid">
        <div>
          <h1>{html.escape(report['title'])}</h1>
          <p>{html.escape(report.get('subtitle', ''))}</p>
          <p>This report turns one REAP/quantization/publication lane into a single auditable artifact: calibration design, sample sizes, token totals, prune variants, quantization status, runtime results, and benchmark gates.</p>
        </div>
        <div class="kpis">
          <div class="kpi"><div class="label">Merged observed tokens</div><div class="value">{calibration['merged_observed_tokens']}</div></div>
          <div class="kpi"><div class="label">Successful runtime rows</div><div class="value">{derived['successful_runtime_rows']}</div></div>
          <div class="kpi"><div class="label">Best prefill</div><div class="value">{fmt_num(derived['best_prefill_toks_per_s'])}</div></div>
          <div class="kpi"><div class="label">Accuracy baseline</div><div class="value">{benchmarking['accuracy']['overall_accuracy']}</div></div>
        </div>
      </div>
      <div>
        <span class="pill">{html.escape(model['label'])}</span>
        <span class="pill">{fmt_num(model['experts_per_layer'])} experts/layer</span>
        <span class="pill">{fmt_num(model['experts_per_token'])} routed experts/token</span>
      </div>
    </section>

    <section class="card">
      <h2>Reference model</h2>
      <div class="card-grid">
        <div>
          <p><strong>Base model:</strong> <code>{html.escape(model['base_model'])}</code></p>
          <p><strong>Weights path:</strong> <code>{html.escape(model['weights_path'])}</code></p>
          <p><strong>Architecture:</strong> <code>{html.escape(model['architecture'])}</code></p>
        </div>
        <div>
          <p><strong>Total layers:</strong> {fmt_num(model['total_layers'])}</p>
          <p><strong>MoE layers:</strong> {fmt_num(model['moe_layers'])}</p>
          <p><strong>Experts/layer:</strong> {fmt_num(model['experts_per_layer'])}</p>
        </div>
      </div>
    </section>

    <section class="card">
      <h2>Calibration bundle</h2>
      <p>The winning practical pattern is a split bundle: one long-context lane to preserve trajectory behavior, and one broad short-mix lane to preserve coding, tool use, and prompt diversity.</p>
      {table(["Lane", "Selection", "Input rows", "Processed samples", "Max tokens", "Observed tokens"], lane_rows)}
      <div style="height:16px"></div>
      {table(["Dataset", "Config", "Rows"], source_rows)}
    </section>

    <section class="card">
      <h2>Pruning and quantization</h2>
      {table(["Variant", "Experts before", "Experts pruned", "Experts retained", "Status"], prune_rows)}
      <div style="height:16px"></div>
      {table(["Variant", "Method", "Status", "Notes"], quant_rows)}
    </section>

    <section class="card">
      <h2>Runtime and benchmarking</h2>
      {table(["Variant", "Status", "GPU GiB", "CPU GiB", "TTFT s", "Prefill tok/s", "Gen tok/s"], runtime_rows)}
      <div style="height:16px"></div>
      {table(["Gate", "Status", "Summary"], gate_rows)}
    </section>

    <section class="card">
      <h2>Headline findings</h2>
      <ul>{list_items(results['headline_findings'])}</ul>
    </section>

    <section class="card">
      <h2>Source artifacts</h2>
      <ul class="artifact-list">{list_items(report['source_artifacts'])}</ul>
    </section>
  </main>
</body>
</html>
"""


def main() -> None:
    args = parse_args()
    manifest = read_json(Path(args.manifest))
    report = build_report(manifest)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    write_json(output_dir / "report.json", report)
    write_text(output_dir / "report.md", render_markdown(report))
    write_text(output_dir / "index.html", render_html(report))
    print(output_dir / "report.json")
    print(output_dir / "report.md")
    print(output_dir / "index.html")


if __name__ == "__main__":
    main()
