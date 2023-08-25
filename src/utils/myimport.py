"""Temporary fix allowing to import files from upper directory."""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
