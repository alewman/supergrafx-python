# Changelog

Releases are git tags. Not on PyPI (the base board is pinned by git commit).

## 0.1.0 (2026-11-12)

The first release: the NEC SuperGrafx as an add-on to pcengine-python.

- The HuC6202 VPC (windows, priority, `ST0-ST2` steering, the video-area decode with the
  compatibility switch), a second VDC and 32 KiB of work RAM, through the base board's sockets.
- The five library cards row-identical to Beetle PCE and, but for one row of Madou King Granzort,
  to Mesen2; the base-mode fallback measured (docs/m6-record.md).
- C-SGX1 decided: the priority codes are read as Mednafen and Mesen2 read them (`PRIORITY_LABELS =
  "detectors"`), after Daimakaimura's cutscene and first stage were compared under both readings.
- Save states through the base board's `pcengine_python.state`; scripted pad input (`--press`).
- Base board: pcengine-python 0.1.0.
