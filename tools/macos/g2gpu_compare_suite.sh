#!/bin/sh
# CPU (SIM_G2_GPU=0) vs GPU 2D comparison suite, headless lockstep.
# See g2gpu_compare_suite.py in this directory. ASCII only.
exec python3 "$(dirname "$0")/g2gpu_compare_suite.py" "$@"
