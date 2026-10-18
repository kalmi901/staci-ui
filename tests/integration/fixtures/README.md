# Integration test fixtures

## `tiny_network.inp`

Synthetic network created specifically for the `staci-ui` integration tests.

## `net1.inp`

Copied unchanged from the USEPA/WNTR repository:

- Source: `examples/networks/Net1.inp`
- Upstream commit: `11eec7d5bf0a9367ffe04d75707918f0c0a890a1`
- URL: https://github.com/USEPA/WNTR/blob/11eec7d5bf0a9367ffe04d75707918f0c0a890a1/examples/networks/Net1.inp

WNTR is distributed under the Revised BSD License. The upstream license and
copyright notice are reproduced in `WNTR-LICENSE.md`.

## staci_flush_network.inp

Small synthetic three-hydrant network copied from the upstream STACI
worked flushing example.

- Source: `examples/flushing/network.inp`
- Repository: https://github.com/hoscsaba/staci
- Revision: `b215127e10acce0d404922dbcd2eda623f8f47e2`
- Hydrant junctions: `A`, `B`, `C`


## STACI Calibrate smoke fixtures

`staci_calibrate_network_0.spr` and `staci_calibrate_targets.csv` are copied
from the upstream STACI optimizer smoke test. The SPR file is the upstream
`tests/anytown_1med.spr` fixture; it is renamed to match the period-based
filename convention expected by `staci_calibrate`.

- Sources: `tests/anytown_1med.spr` and `tests/calibrate_targets.csv`
- Repository: https://github.com/hoscsaba/staci
- Revision: `b215127e10acce0d404922dbcd2eda623f8f47e2`
- Scope: subprocess integration and output-file smoke coverage only

The upstream configuration deliberately uses one period, a population of
four and one generation. It does not validate calibration quality or
represent a production calibration dataset.