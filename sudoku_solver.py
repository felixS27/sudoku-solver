#!/usr/bin/env python3
"""Entry point for the sudoku solver GUI.

Run with `python sudoku_solver.py`.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

import GUI

if __name__ == "__main__":
    GUI.main()
