"""Strict argument parsing shared by the primary and native-tool CLIs.

Long-option abbreviations and repeated long options are ambiguous at an evidence
boundary: `--project A --project B` and `--proj` must fail instead of silently
selecting one interpretation.  Short flags keep argparse's normal behavior.
"""
from __future__ import annotations

import argparse
import sys


class StrictArgumentParser(argparse.ArgumentParser):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("allow_abbrev", False)
        super().__init__(*args, **kwargs)

    def parse_args(self, args=None, namespace=None):
        arguments = list(sys.argv[1:] if args is None else args)
        seen = set()
        for token in arguments:
            if token == "--":
                break
            if token.startswith("--"):
                flag = token.split("=", 1)[0]
                if flag in seen:
                    self.error(f"Repeated option: {flag}")
                seen.add(flag)
        return super().parse_args(arguments, namespace)
