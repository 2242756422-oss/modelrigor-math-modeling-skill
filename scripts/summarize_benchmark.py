#!/usr/bin/env python3
import sys; sys.dont_write_bytecode=True
import argparse
from pathlib import Path
from cqex import benchmark

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("protocol", type=Path)
    p.add_argument("runs", type=Path)
    a = p.parse_args()
    benchmark(a.protocol, a.runs)
