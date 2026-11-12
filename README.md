# supergrafx-python

A readable, pure-Python **NEC SuperGrafx** (1989), built as an **add-on to
[pcengine-python](https://github.com/alewman/pcengine-python)**: the base board runs the HuC6280, the VCE, the PSG and one VDC;
this repository adds what the SuperGrafx has beyond a PC Engine, through the base board's documented
sockets and nothing copied: a **second HuC6270 VDC** (an instance of the base board's own class), the
**HuC6202 VPC** (windows, priority modes, VDC select for `ST0-ST2`, the video-area decode with the
back-panel compatibility switch), and 32 KiB of work RAM.

**Status (2026-11-12, release 0.1.0): built (milestone 6 of the PC Engine family).** The five
library cards are row-identical to Beetle PCE and, but for one row of one card, to Mesen2; past
the title, Daimakaimura's cutscene and first stage are identical to both. Save states are the
base board's and cover this machine (a round trip on all five cards). Nothing here was run on a
real console. See [docs/m6-record.md](docs/m6-record.md) for what was built, the judges, the
picture results, the measured base-mode fallback and the U/C entries with their tiers (the
priority labels, C-SGX1, were decided on 2026-11-12), and [CHANGELOG.md](CHANGELOG.md).
Python floor 3.11 (PyPy supports it); this is a reference board, correct, not fast.

```sh
python -m venv .venv-pypy   # PyPy 3.11 is the platform; CPython works for the tests
.venv-pypy/bin/python -m pip install -e ".[dev]"
.venv-pypy/bin/python -m pytest -q
```

The base board is pinned by its GitHub commit in `pyproject.toml`; `docs/start-here.md` says which sockets are used and why a board change was needed.
HuCards are bring-your-own, read in place by path, never committed.

```python
from pcengine_python.cards import card_from_path
from supergrafx_python import SuperGrafx

sg = SuperGrafx(card=card_from_path("Daimakaimura (Japan) (En).sgx"))
system = sg.build()  # the real HuC6280 core on the board
for _ in range(300):
    system.run_frame()
rows = sg.board.capture.last_frame.rows  # 242 rows of 9-bit palette values
```

Save states: `pcengine_python.state.save_state(system)` and `load_state`
([docs/start-here.md](docs/start-here.md) "Save states"). Paths under `/data/emu/` in the documents,
the scripts' defaults and one test are the author's machine (`PCENGINE_PYTHON` names the base
board's checkout, whose `scripts/` the picture scripts use).
