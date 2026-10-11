#!/bin/sh
# Rebuild the deck. Needs: SP (a dir with npm/node_modules/pptxgenjs and venv/ with python-pptx, pillow),
# PPTX_SKILL_DIR (the pptx skill directory). Images: run shots.cjs first (Playwright) for the diagram PNGs.
cd "$(dirname "$0")"
NODE_PATH=$SP/npm/node_modules node build.cjs
