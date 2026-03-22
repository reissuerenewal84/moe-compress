# MoE Compress

Minimal, config-first automation for a full MoE compression run:

1. observations
2. pruning
3. upload pruned weights to Hugging Face
4. quantization
5. upload quantized weights to Hugging Face
6. benchmarking
7. render one auditable run report

This repo is intentionally small. It does not pretend every MoE uses the same vendor command line.

What it does provide:

- one pipeline runner that executes a full run from one JSON config
- one calibration-bundle builder for local JSONL data plus public Hugging Face datasets
- one normalized report renderer

What you configure up front:

- model path or model id
- local calibration dataset path
- public calibration mix size
- prune percentages
- quantization method and scheme such as `w4a16`
- Hugging Face repo names for pruned and quantized outputs
- the exact observe, prune, upload, quantize, benchmark, and manifest-assembly commands for your MoE

## Directory layout

```text
compress/
  README.md
  requirements.txt
  scripts/
    run_moe_pipeline.py
    build_master_calibration_bundle.py
    render_reap_run_report.py
  examples/
    automatic_pipeline.example.json
    master_calibration_bundle.example.json
    run_report_manifest.example.json
```

## Core contract

`run_moe_pipeline.py` is the entrypoint. It runs named stages in order, captures logs, writes pipeline state, and stops on first failure.

Supported stage types:

- `build_calibration_bundle`
- `command`
- `render_report`

The runner is model agnostic because the architecture-specific work stays in your configured `command` stages.

## Variable expansion

The pipeline config supports placeholders like `{model_path}`.

Available variables:

- top-level `parameters.*`
- `{repo_root}`
- `{run_dir}`
- `{pipeline_name}`
- stage outputs such as:
  - `{stage_build_calibration_bundle_output_dir}`
  - `{stage_build_calibration_bundle_summary_json}`
  - `{stage_build_calibration_bundle_merged_output_jsonl}`
  - `{stage_observations_log_path}`
  - `{stage_quantize_status}`

`build_calibration_bundle` and `render_report` both support either a file path or inline JSON:

- `config` or `inline_config`
- `manifest` or `inline_manifest`

That means you can drive the whole pipeline from one file.

## Calibration defaults

The bundled calibration example uses the split that has proven most practical for code and agentic REAP work:

- one long-context lane from local data
- one broad short-mix lane from local data plus public coverage
- `100` rows from each public dataset:
  - `theblackcat102/evol-codealpaca-v1`
  - `Salesforce/xlam-function-calling-60k`
  - `SWE-bench/SWE-smith-trajectories`
  - `open-r1/Mixture-of-Thoughts` `code`
  - `open-r1/Mixture-of-Thoughts` `math`
  - `open-r1/Mixture-of-Thoughts` `science`

If your deployment traffic is not code or agentic, change the mix. Do not cargo-cult this bundle into a different workload.

## Run the full pipeline

From the repo root:

```bash
uv run ./scripts/run_moe_pipeline.py \
  --config ./examples/automatic_pipeline.example.json
```

The example pipeline is a template. Replace the example command strings with the real commands for your MoE stack.

Recommended stage order:

1. build the calibration bundle
2. run observations on the base model
3. prune the requested variants
4. upload pruned checkpoints
5. quantize the validated prune outputs
6. upload quantized checkpoints
7. benchmark the variants you care about
8. assemble one normalized run manifest
9. render the final report

## Build only the calibration bundle

Dry run:

```bash
uv run ./scripts/build_master_calibration_bundle.py \
  --config ./examples/master_calibration_bundle.example.json \
  --output-dir ./output/calibration-plan \
  --dry-run
```

Real build:

```bash
uv run --with datasets ./scripts/build_master_calibration_bundle.py \
  --config ./examples/master_calibration_bundle.example.json \
  --output-dir ./output/master-calibration
```

Outputs:

- one JSONL per lane
- one merged JSONL
- one summary JSON
- one Markdown summary

## Render a normalized report

```bash
uv run ./scripts/render_reap_run_report.py \
  --manifest ./examples/run_report_manifest.example.json \
  --output-dir ./output/example-report
```

Outputs:

- `report.json`
- `report.md`
- `index.html`

## Normalized manifest shape

The report renderer expects a JSON manifest with these sections:

- `model`
- `calibration`
- `pruning`
- `quantization`
- `publishing`
- `benchmarking`
- `results`

The pipeline runner does not invent these facts. Your configured commands should write the artifacts and produce a normalized manifest file at the end of the run.

That is the correct boundary:

- this repo handles orchestration, calibration planning, and reporting
- your MoE-specific tooling handles observations, pruning, quantization, benchmarking, and upload mechanics

## Recommended use

Treat `examples/automatic_pipeline.example.json` as the one file you edit for a new model. Keep the stage order. Replace the command strings. Point the final report stage at the normalized manifest produced by your tooling.
