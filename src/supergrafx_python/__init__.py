"""supergrafx-python: the NEC SuperGrafx as an add-on to pcengine-python, through its sockets."""

from supergrafx_python.board import SuperGrafx
from supergrafx_python.machine import SUPERGRAFX
from supergrafx_python.vpc import VideoPage, Vpc

__all__ = ["SUPERGRAFX", "SuperGrafx", "VideoPage", "Vpc"]
