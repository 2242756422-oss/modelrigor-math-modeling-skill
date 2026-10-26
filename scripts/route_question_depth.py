#!/usr/bin/env python3
import sys; sys.dont_write_bytecode=True
import argparse
from pathlib import Path
from cqex import route_depth

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("question_plan", type=Path)
    p.add_argument("depth", choices=("L1", "L2", "L3"))
    a = p.parse_args()
    route_depth(a.question_plan, a.depth)
