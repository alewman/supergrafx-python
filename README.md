# supergrafx-python

A readable, pure-Python **NEC SuperGrafx** (1989), built as an **add-on to
[pcengine-python](../pcengine-python)**: the base board runs the HuC6280, the VCE, the PSG and one VDC;
this repository adds what the SuperGrafx has beyond a PC Engine, through the base board's documented
sockets and nothing copied: a **second HuC6270 VDC** (an instance of the base board's own class), the
**HuC6202 VPC** (windows, priority modes, VDC select for `ST0-ST2`, the video-area decode with the
back-panel compatibility switch), and 32 KiB of work RAM.

**Status (2026-11-05): Milestone 6, local only (no remote, no push).** See
[docs/m6-record.md](docs/m6-record.md) for what was built, the judges, the picture results on the
five library cards, the measured base-mode fallback and the U/C entries with their tiers.
Python floor 3.11 (PyPy supports it); this is a reference board, correct, not fast.

```sh
python -m venv .venv-pypy   # PyPy 3.11 is the platform; CPython works for the tests
.venv-pypy/bin/python -m pip install -e ".[dev]"
.venv-pypy/bin/python -m pytest -q
```

The base board is pinned by git revision in `pyproject.toml` (a local repository until it is
public); `docs/start-here.md` says which sockets are used and why a board change was needed.
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
