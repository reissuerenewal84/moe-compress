# The REAP Cookbook

Practical compression pipeline for frontier MoE models on consumer hardware.

This directory is meant to be copied into a new repo as-is. It stays minimal on purpose:

- one pipeline orchestrator
- one calibration-bundle builder
- one manifest-driven report renderer
- one example calibration config
- two example manifests:
  - one failed historical lane
  - one working W4A16 lane

## What this is

This repo is for operators, not paper readers.

It is model agnostic.

The reusable parts here should work for Nemotron, GLM, Qwen, MiniMax, or any other MoE lane where you can produce a normalized manifest.

The pipeline is:

1. build a calibration bundle that matches real usage
2. run REAP observations on the full model
3. generate prune variants
4. validate the BF16 pruned checkpoints first
5. quantize only after BF16 validity is proven
6. benchmark the runtime path
7. publish only when weights, metadata, and benchmark claims are all real

The automation contract is:

- put model-specific commands in a pipeline config
- let the generic runner execute them in order
- capture logs and stage status automatically
- render a normalized report at the end

That is the only credible model-agnostic design. The core repo should not hard-code one architecture-specific observe/prune/quantize path and pretend it covers every MoE.

The core REAP idea is simple:

- MoE models keep far more expert weights resident than any single token uses
- REAP scores experts against your actual workload
- low-saliency experts get pruned permanently
- quantization then shrinks the remaining weights further

That is how you move from server-class checkpoints toward local deployment.

## Directory layout

```text
compress/
  README.md
  requirements.txt
  .gitignore
  scripts/
    run_moe_pipeline.py
    build_master_calibration_bundle.py
    render_reap_run_report.py
  examples/
    automatic_pipeline.example.json
    master_calibration_bundle.example.json
    nemotron_reap_reference_manifest.json
    glm46_w4a16_working_manifest.json
```

## Master calibration strategy

Do not use one flat dataset and call it done.

Use two lanes:

1. Long-context lane
   - preserve trajectory behavior
   - preserve long reasoning
   - preserve agent loops
2. Short-mix lane
   - preserve prompt diversity
   - preserve coding and tool use
   - preserve broad short-turn behavior

The example config uses this exact split:

- long lane: `50` longest personal trajectories at up to `16384` tokens
- short lane: `15000` shortest personal prompts at up to `1024` tokens
- public augmentation: `100` rows each from:
  - `theblackcat102/evol-codealpaca-v1`
  - `Salesforce/xlam-function-calling-60k`
  - `SWE-bench/SWE-smith-trajectories`
  - `open-r1/Mixture-of-Thoughts` `code`
  - `open-r1/Mixture-of-Thoughts` `math`
  - `open-r1/Mixture-of-Thoughts` `science`

This is the right default for code and agentic REAP work. It gives you a master bundle built from your own traffic plus bounded public coverage.

## Why this bundle shape works

If you only calibrate on short prompts, long-context routing collapses.

If you only calibrate on long trajectories, you lose breadth and tool-use coverage.

The split bundle prevents both failure modes.

## Scripts

### 0) Run the full pipeline automatically

This is the entrypoint if you want to drop in a model and let the repo drive the workflow:

```bash
uv run /Users/sero/ai/autoresearch/compress/scripts/run_moe_pipeline.py \
  --config /Users/sero/ai/autoresearch/compress/examples/automatic_pipeline.example.json
```

The runner supports these stage types:

- `build_calibration_bundle`
- `command`
- `render_report`

That means any model-specific observation, prune, quantize, benchmark, or publish step can be automated without changing the runner itself. You swap configs, not core code.

### 1) Build the calibration bundle

Dry-run the plan first:

```bash
uv run /Users/sero/ai/autoresearch/compress/scripts/build_master_calibration_bundle.py \
  --config /Users/sero/ai/autoresearch/compress/examples/master_calibration_bundle.example.json \
  --output-dir /Users/sero/ai/autoresearch/test-output/compress-calibration-plan \
  --dry-run
```

Run the real build:

```bash
uv run --with datasets /Users/sero/ai/autoresearch/compress/scripts/build_master_calibration_bundle.py \
  --config /Users/sero/ai/autoresearch/compress/examples/master_calibration_bundle.example.json \
  --output-dir /Users/sero/ai/autoresearch/output/master-calibration
```

What it writes:

- one JSONL per lane
- one merged JSONL
- one machine-readable summary JSON
- one Markdown summary

### 2) Render the run report

Once you have observation, pruning, quantization, runtime, and publishing artifacts, put the normalized facts into a manifest and render it:

```bash
uv run /Users/sero/ai/autoresearch/compress/scripts/render_reap_run_report.py \
  --manifest /Users/sero/ai/autoresearch/compress/examples/nemotron_reap_reference_manifest.json \
  --output-dir /Users/sero/ai/autoresearch/test-output/compress-reference-report
```

What it writes:

- `report.json`
- `report.md`
- `index.html`

You can also render the shipped working W4A16 example:

```bash
uv run /Users/sero/ai/autoresearch/compress/scripts/render_reap_run_report.py \
  --manifest /Users/sero/ai/autoresearch/compress/examples/glm46_w4a16_working_manifest.json \
  --output-dir /Users/sero/ai/autoresearch/test-output/compress-glm46-w4a16-report
```

### 3) Attach model-specific commands

For a real MoE lane, use `type: "command"` stages for:

- observation collection
- pruning and export
- BF16 smoke tests
- quantization
- runtime benchmarks
- publishing

The orchestrator will execute them sequentially, capture logs per stage, and fail fast if one breaks.

## Manifest contract

The report manifest is intentionally simple. It should answer:

- what model was compressed
- what calibration data was used
- how many samples and tokens were observed
- what prune variants were generated
- what quantization attempts were made
- what runtime rows succeeded or failed
- what accuracy and benchmark evidence exists
- what was actually published

If a claim is not backed by an artifact, it should not go in the manifest.

The schema is intentionally allowed to be partial.

That matters because some real lanes have:

- a working quantization and published repo, but no bundled local benchmark JSON
- runtime benchmarks, but no completed quantization
- structural prune validity, but runtime fragility

Do not force fake completeness into the manifest.

## Exact reference workflow

The bundled example manifest uses the Nemotron lane as the concrete reference.

That reference manifest is historical evidence from the actual lane we ran. It still shows `20` public rows per dataset because that is what the Nemotron observation pass actually used. The reusable master calibration config has been raised to `100` rows per public dataset.

Reference model:

- `nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-BF16`
- `88` total layers
- `40` MoE layers
- `512` routed experts per layer
- `22` routed experts per token

Reference calibration totals:

- long lane: `50` processed samples, `819200` observed tokens
- short lane: `15120` source rows, `40` processed batches, `321560` observed tokens
- merged total: `90` processed units, `1140760` observed tokens

Reference prune variants:

- `reap_25pct`: `512 -> 384` experts/layer
- `reap_50pct`: `512 -> 256` experts/layer

Reference runtime evidence:

- `original_1gpu_plain_customprompt`: `21.53` prefill tok/s, `2.58` gen tok/s
- `original_2gpu_plain_customprompt`: `32.39` prefill tok/s, `5.01` gen tok/s
- `original_8gpu_multiplex_dynamic_plan`: `32.60` prefill tok/s, `7.59` gen tok/s

Reference accuracy baseline:

- overall accuracy: `0.8`
- coherence rate: `1.0`
- total samples: `10`

Reference quantization reality:

- all AutoRound `W4A16` attempts failed in the artifact window

That is why the example report is useful: it is honest about both what worked and what did not.

## Working W4A16 examples

The repo now carries both sides of reality:

1. A failed quantization lane:
   - [nemotron_reap_reference_manifest.json](/Users/sero/ai/autoresearch/compress/examples/nemotron_reap_reference_manifest.json)
2. A working published W4A16 lane:
   - [glm46_w4a16_working_manifest.json](/Users/sero/ai/autoresearch/compress/examples/glm46_w4a16_working_manifest.json)

Current working W4A16 reference included in `/compress`:

- `0xSero/GLM-4.6-REAP-218B-A32B-W4A16-AutoRound`
- published on Hugging Face
- model card states:
  - `W4A16` quantization
  - about `436GB -> 116GB`
  - deployment target of `8x RTX 3090` or `4x RTX 4090`
  - calibration mix of:
    - `700` `evol-codealpaca-v1`
    - `330` `xlam-function-calling-60k`
    - `330` `SWE-smith-trajectories`

That example is intentionally not Nemotron-specific. It exists so the cookbook does not imply that W4A16 is only a failure story.

## Operator rules

1. Calibration quality is the most important decision in the pipeline.
2. Benchmark the BF16 pruned checkpoint before quantization.
3. Never call a publish successful until weights, README metadata, and runtime claims are all verified.
4. Keep runtime failures separate from structural validity. A checkpoint can be structurally valid and still be runtime-fragile.
5. Do not hide failed quantization or failed serving rows. Those are part of the report.

## Recommended artifact set

For every model variant keep:

- config
- tokenizer files
- generation smoke output
- benchmark JSON
- benchmark Markdown
- model card
- upload verification record

## External references

- Paper: [Router-weighted Expert Activation Pruning](https://arxiv.org/abs/2510.13999)
- Code: [CerebrasResearch/reap](https://github.com/CerebrasResearch/reap)
- MLX port: [0xSero/reap-mlx](https://github.com/0xSero/reap-mlx)
- Working GLM W4A16 reference: [0xSero/GLM-4.6-REAP-218B-A32B-W4A16-AutoRound](https://huggingface.co/0xSero/GLM-4.6-REAP-218B-A32B-W4A16-AutoRound)
- Public datasets:
  - [theblackcat102/evol-codealpaca-v1](https://huggingface.co/datasets/theblackcat102/evol-codealpaca-v1)
  - [Salesforce/xlam-function-calling-60k](https://huggingface.co/datasets/Salesforce/xlam-function-calling-60k)
  - [SWE-bench/SWE-smith-trajectories](https://huggingface.co/datasets/SWE-bench/SWE-smith-trajectories)
  - [open-r1/Mixture-of-Thoughts](https://huggingface.co/datasets/open-r1/Mixture-of-Thoughts)

## Publish checklist

Before pushing this into a new GitHub repo:

1. Replace the example personal dataset path with the path you actually want to support.
2. Replace the example Nemotron manifest with your current run manifest.
3. Decide whether you want generated `output/` committed or ignored.
4. Run the dry-run builder and one report render as proof before publishing.

This directory is intentionally small enough to survive extraction into its own repo without dragging the rest of `autoresearch` with it.
