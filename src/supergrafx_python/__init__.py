# SPDX-License-Identifier: MIT
"""supergrafx-python: the NEC SuperGrafx as an add-on to pcengine-python, through its sockets."""

from pcengine_python.state import register_package

from supergrafx_python.board import SuperGrafx
from supergrafx_python.machine import SUPERGRAFX
from supergrafx_python.vpc import VideoPage, Vpc

# Save states (pcengine_python.state) hold this package's objects too: the VPC and the video page.
register_package("supergrafx_python")

__all__ = ["SUPERGRAFX", "SuperGrafx", "VideoPage", "Vpc"]
