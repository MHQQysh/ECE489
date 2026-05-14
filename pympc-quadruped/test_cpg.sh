#!/bin/bash

# Test CPG controller
echo "Testing CPG controller..."
unset PYTHONPATH
unset LD_LIBRARY_PATH
unset PKG_CONFIG_PATH
unset CMAKE_PREFIX_PATH

uv run python scripts/mujoco_aliengo_cpg.py --no-viewer --steps 2000

echo "CPG test complete!"
