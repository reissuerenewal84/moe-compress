#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BUILD_CALIBRATION = ROOT / "scripts" / "build_master_calibration_bundle.py"
RENDER_REPORT = ROOT / "scripts" / "render_reap_run_report.py"
PLACEHOLDER_RE = re.compile(r"\{([A-Za-z0-9_]+)\}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run a model-agnostic MoE compression pipeline from a config. "
            "Stages can build calibration bundles, run arbitrary commands, and render reports."
        )
    )
    parser.add_argument("--config", required=True, help="Path to the pipeline config JSON.")
    return parser.parse_args()


def now_slug() -> str:
    return dt.datetime.now().strftime("%Y%m%d-%H%M%S")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def resolve_path(value: str, config_dir: Path) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = (config_dir / path).resolve()
    return path


def expand_string(value: str, variables: dict[str, str]) -> str:
    expanded = value
    for _ in range(8):
        updated = PLACEHOLDER_RE.sub(lambda match: variables.get(match.group(1), match.group(0)), expanded)
        if updated == expanded:
            break
        expanded = updated
    return expanded


def expand_value(value: Any, variables: dict[str, str]) -> Any:
    if isinstance(value, str):
        return expand_string(value, variables)
    if isinstance(value, list):
        return [expand_value(item, variables) for item in value]
    if isinstance(value, dict):
        return {key: expand_value(item, variables) for key, item in value.items()}
    return value


def stage_var_prefix(stage_name: str) -> str:
    return "stage_" + re.sub(r"[^A-Za-z0-9]+", "_", stage_name).strip("_")


def collect_stage_outputs(stage_result: dict[str, Any], variables: dict[str, str]) -> None:
    prefix = stage_var_prefix(stage_result["name"])
    for key in ("output_dir", "log_path", "status"):
        value = stage_result.get(key)
        if value is not None:
            variables[f"{prefix}_{key}"] = str(value)

    output_dir = stage_result.get("output_dir")
    if not output_dir:
        return
    summary_paths = sorted(Path(output_dir).glob("*.summary.json"))
    if not summary_paths:
        return
    summary_path = summary_paths[0]
    variables[f"{prefix}_summary_json"] = str(summary_path)
    summary = read_json(summary_path)
    merged_output = summary.get("merged_output_jsonl")
    if merged_output:
        variables[f"{prefix}_merged_output_jsonl"] = str(merged_output)


def run_subprocess(
    cmd: list[str],
    *,
    cwd: Path,
    env: dict[str, str],
    log_path: Path,
) -> dict[str, Any]:
    started = time.time()
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("w", encoding="utf-8") as handle:
        process = subprocess.run(
            cmd,
            cwd=str(cwd),
            env=env,
            stdout=handle,
            stderr=subprocess.STDOUT,
            text=True,
        )
    ended = time.time()
    return {
        "cmd": cmd,
        "cwd": str(cwd),
        "log_path": str(log_path),
        "returncode": process.returncode,
        "duration_s": round(ended - started, 3),
        "status": "ok" if process.returncode == 0 else "failed",
    }


def materialize_json_input(
    stage_cfg: dict[str, Any],
    *,
    config_key: str,
    inline_key: str,
    stage_dir: Path,
    config_dir: Path,
    file_name: str,
) -> Path:
    inline_payload = stage_cfg.get(inline_key)
    path_value = stage_cfg.get(config_key)
    if inline_payload is not None and path_value is not None:
        raise ValueError(f"Stage cannot define both {config_key!r} and {inline_key!r}.")
    if inline_payload is not None:
        materialized = stage_dir / file_name
        write_json(materialized, inline_payload)
        return materialized
    if path_value is not None:
        return resolve_path(str(path_value), config_dir)
    raise KeyError(f"Stage must define either {config_key!r} or {inline_key!r}.")


def render_summary_markdown(state: dict[str, Any]) -> str:
    rows = [
        "| Stage | Type | Status | Duration s | Log |",
        "| --- | --- | --- | --- | --- |",
    ]
    for stage in state["stages"]:
        rows.append(
            "| {name} | {type} | {status} | {duration} | {log} |".format(
                name=stage["name"],
                type=stage["type"],
                status=stage["status"],
                duration=stage.get("duration_s", "n/a"),
                log=stage.get("log_path", "n/a"),
            )
        )
    lines = [
        f"# {state['pipeline_name']}",
        "",
        f"- Run dir: `{state['run_dir']}`",
        f"- Status: `{state['status']}`",
        f"- Started: `{state['started_at']}`",
        f"- Finished: `{state.get('finished_at', 'n/a')}`",
        "",
        "## Stages",
        "\n".join(rows),
    ]
    return "\n".join(lines) + "\n"


def execute_stage(
    stage_cfg: dict[str, Any],
    *,
    run_dir: Path,
    config_dir: Path,
    base_env: dict[str, str],
    variables: dict[str, str],
) -> dict[str, Any]:
    expanded_stage = expand_value(stage_cfg, variables)
    stage_name = expanded_stage["name"]
    stage_type = expanded_stage["type"]
    stage_dir = run_dir / "stages" / stage_name
    stage_dir.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env.update(base_env)
    env.update({str(key): str(value) for key, value in expanded_stage.get("env", {}).items()})
    log_path = stage_dir / "stage.log"

    if stage_type == "build_calibration_bundle":
        bundle_config = materialize_json_input(
            expanded_stage,
            config_key="config",
            inline_key="inline_config",
            stage_dir=stage_dir,
            config_dir=config_dir,
            file_name="bundle-config.json",
        )
        out_dir = stage_dir / "output"
        cmd = [
            "uv",
            "run",
            "--with",
            "datasets",
            str(BUILD_CALIBRATION),
            "--config",
            str(bundle_config),
            "--output-dir",
            str(out_dir),
        ]
        if expanded_stage.get("dry_run"):
            cmd.append("--dry-run")
        result = run_subprocess(cmd, cwd=config_dir, env=env, log_path=log_path)
        result["output_dir"] = str(out_dir)
        return {"name": stage_name, "type": stage_type, **result}

    if stage_type == "render_report":
        manifest = materialize_json_input(
            expanded_stage,
            config_key="manifest",
            inline_key="inline_manifest",
            stage_dir=stage_dir,
            config_dir=config_dir,
            file_name="report-manifest.json",
        )
        out_dir = stage_dir / "output"
        cmd = [
            "uv",
            "run",
            str(RENDER_REPORT),
            "--manifest",
            str(manifest),
            "--output-dir",
            str(out_dir),
        ]
        result = run_subprocess(cmd, cwd=config_dir, env=env, log_path=log_path)
        result["output_dir"] = str(out_dir)
        return {"name": stage_name, "type": stage_type, **result}

    if stage_type == "command":
        cmd = [str(part) for part in expanded_stage["cmd"]]
        cwd = resolve_path(expanded_stage.get("cwd", "."), config_dir)
        result = run_subprocess(cmd, cwd=cwd, env=env, log_path=log_path)
        return {"name": stage_name, "type": stage_type, **result}

    raise ValueError(f"Unsupported stage type {stage_type!r}")


def main() -> None:
    args = parse_args()
    config_path = Path(args.config).resolve()
    config_dir = config_path.parent
    config = read_json(config_path)

    run_root = resolve_path(str(config.get("output_root", str(ROOT / "output"))), config_dir)
    pipeline_name = config["name"]
    run_dir = run_root / f"{pipeline_name}-{now_slug()}"
    run_dir.mkdir(parents=True, exist_ok=True)

    state: dict[str, Any] = {
        "pipeline_name": pipeline_name,
        "run_dir": str(run_dir),
        "started_at": dt.datetime.now().isoformat(),
        "status": "running",
        "model": config.get("model", {}),
        "stages": [],
    }
    write_json(run_dir / "pipeline-config.json", config)
    write_json(run_dir / "pipeline-state.json", state)

    base_env = {str(key): str(value) for key, value in config.get("env", {}).items()}
    variables: dict[str, str] = {
        "repo_root": str(ROOT),
        "run_dir": str(run_dir),
        "pipeline_name": pipeline_name,
    }
    for key, value in config.get("parameters", {}).items():
        variables[str(key)] = str(value)

    try:
        for stage_cfg in config["stages"]:
            stage_result = execute_stage(
                stage_cfg,
                run_dir=run_dir,
                config_dir=config_dir,
                base_env=base_env,
                variables=variables,
            )
            state["stages"].append(stage_result)
            collect_stage_outputs(stage_result, variables)
            write_json(run_dir / "pipeline-state.json", state)
            if stage_result["status"] != "ok":
                state["status"] = "failed"
                break
        else:
            state["status"] = "ok"
    except Exception as exc:
        state["status"] = "failed"
        state["error"] = str(exc)

    state["finished_at"] = dt.datetime.now().isoformat()
    write_json(run_dir / "pipeline-state.json", state)
    (run_dir / "pipeline-summary.md").write_text(render_summary_markdown(state), encoding="utf-8")

    print(run_dir / "pipeline-state.json")
    print(run_dir / "pipeline-summary.md")
    if state["status"] != "ok":
        sys.exit(1)


if __name__ == "__main__":
    main()
