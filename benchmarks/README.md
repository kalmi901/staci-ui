# Live Dash responsiveness benchmark

`measure_dash_responsiveness.py` measures the availability of the
production-style Dash application while real STACI hydraulic callbacks
are running.

This is a live benchmark, not part of the pytest suite. It sends requests
directly to the Dash callback endpoint and probes the Dash layout endpoint
while the callbacks are in progress.

Use the same host, Docker resource limits, network model, simulation
settings, and number of jobs when comparing results.

## Baseline

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

## Example invocation

```powershell
python benchmarks\measure_dash_responsiveness.py `
    --model "$modelPath" `
    --data-root "$benchmarkData" `
    --output "$benchmarkData\benchmark.json"