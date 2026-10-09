# Live Dash responsiveness benchmark

`measure_dash_responsiveness.py` measures the availability of the
production-style Dash application while real STACI hydraulic callbacks
are running.

This is a live benchmark, not part of the pytest suite. It sends requests
directly to the Dash callback endpoint and probes the Dash layout endpoint
while the callbacks are in progress.

Use the same host, Docker resource limits, network model, simulation
settings, and number of jobs when comparing results.

## Running the benchmark

Create a temporary data directory shared by the host, Dash application,
and Celery worker:

```powershell
$benchmarkData = Join-Path `
    $env:TEMP `
    ("staci-ui-background-" + [guid]::NewGuid().ToString("N"))

New-Item -ItemType Directory -Path $benchmarkData | Out-Null

$env:BENCHMARK_DATA_DIR = $benchmarkData
```

Start the application with the benchmark-specific Compose override:

```powershell
docker compose `
    -f compose.yaml `
    -f benchmarks/compose.benchmark.yaml `
    up -d --force-recreate redis app worker
```

The benchmark override publishes the Dash application only on
`127.0.0.1:8050`, provides a shared bind mount for `/data`, and limits
the complete stack to 2 CPUs and 2 GiB of memory.

Define the test model:

```powershell
$modelPath = "C:\path\to\Pusztavacs_production.inp"
```

Run four concurrent 720-hour hydraulic simulations:

```powershell
python benchmarks\measure_dash_responsiveness.py `
    --model "$modelPath" `
    --data-root "$benchmarkData" `
    --output "$benchmarkData\background.json" `
    --jobs 4 `
    --duration-hours 720 `
    --timestep-minutes 60 `
    --idle-probes 5 `
    --loaded-probes 12 `
    --callback-poll-interval-seconds 0.5 `
    --request-timeout-seconds 660
```

The benchmark reports:

- idle Dash layout response times;
- loaded Dash layout response times;
- callback enqueue latency;
- complete callback latency;
- background polling count;
- failed callback count;
- loaded-to-idle p95 degradation ratio.

## Synchronous baseline

Recorded on 2026-10-09 before introducing background callbacks.

Configuration:

- Git revision: `9bb6e81`
- Docker CPU limit: 2 CPUs
- Docker memory limit: 2 GiB
- Gunicorn: 1 worker, 4 gthread threads
- Concurrent hydraulic callbacks: 4
- Simulation duration: 720 hours
- Hydraulic timestep: 60 minutes
- Requested frames per callback: 720
- Model: Pusztavacs production network

Results:

| Metric | Result |
|---|---:|
| Benchmark duration | 249.313 s |
| Idle HTTP p50 | 4.476 ms |
| Idle HTTP p95 | 4.957 ms |
| Loaded HTTP p50 | 247167.962 ms |
| Loaded HTTP p95 | 248539.588 ms |
| Loaded HTTP maximum | 248539.588 ms |
| Loaded/idle p95 ratio | 50139.11 |
| Callback p50 | 248915.603 ms |
| Callback maximum | 249312.104 ms |
| Failed callbacks | 0 |

All four callbacks started together and completed successfully. While
they occupied all four Gunicorn threads, new Dash HTTP requests waited
approximately as long as the simulations themselves.

## Background callback result

Recorded on 2026-10-09 after moving hydraulic simulations to Dash
background callbacks backed by Celery and Redis.

Configuration:

- Total Docker CPU limit: 2 CPUs
- Total Docker memory limit: 2 GiB
- Dash application: 0.50 CPU, 512 MiB
- Celery worker: 1.25 CPUs, 1280 MiB
- Redis: 0.25 CPU, 256 MiB
- Celery worker concurrency: 2
- Concurrent hydraulic callbacks submitted: 4
- Simulation duration: 720 hours
- Hydraulic timestep: 60 minutes
- Requested frames per callback: 720
- Background callback polling interval: 0.5 seconds
- Model: Pusztavacs production network

Results:

| Metric | Synchronous baseline | Background callbacks |
|---|---:|---:|
| Benchmark duration | 249.313 s | 295.089 s |
| Idle HTTP p50 | 4.476 ms | 5.667 ms |
| Idle HTTP p95 | 4.957 ms | 7.623 ms |
| Loaded HTTP p50 | 247167.962 ms | 7.377 ms |
| Loaded HTTP p95 | 248539.588 ms | 12.824 ms |
| Loaded HTTP maximum | 248539.588 ms | 12.824 ms |
| Loaded/idle p95 ratio | 50139.11 | 1.68 |
| Callback p50 | 248915.603 ms | 222915.072 ms |
| Callback maximum | 249312.104 ms | 295088.314 ms |
| Failed callbacks | 0 | 0 |

Callback enqueue latency ranged from 59.474 ms to 134.951 ms.

The first two jobs completed after approximately 151 seconds. The
remaining two jobs were intentionally queued by the worker concurrency
limit and completed after approximately 295 seconds.

Loaded HTTP p95 improved by approximately 19,381 times. The queue
increased the longest callback completion time, but kept the Dash
application responsive throughout the computation.

## Stopping the benchmark stack

```powershell
docker compose `
    -f compose.yaml `
    -f benchmarks/compose.benchmark.yaml `
    stop app worker redis
```