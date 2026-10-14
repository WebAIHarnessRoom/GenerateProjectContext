#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""兼容旧调用的入口脚本；内部转发到 project_context.cli.main。"""
import sys
from project_context.cli import main

if __name__ == "__main__":
    sys.exit(main())