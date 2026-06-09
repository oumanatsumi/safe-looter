#!/bin/bash
# ===========================================================================
# Package script for touchi deployment
# Run this from the touchi/ directory:  bash workspace/package.sh
# ===========================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJ_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJ_DIR"

OUTDIR="$PROJ_DIR/workspace/packages"
rm -rf "$OUTDIR"
mkdir -p "$OUTDIR"

echo "=== Packaging touchi-backend ==="
tar -czf "$OUTDIR/touchi-backend.tar.gz" \
    -C "$PROJ_DIR/backend" \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='data/*.db' \
    --exclude='output/*.gif' \
    --exclude='output/*.png' \
    app.py wsgi.py config.py config.yaml database.py requirements.txt \
    api/ game/ resources/

echo "=== Packaging touchi-frontend ==="
tar -czf "$OUTDIR/touchi-frontend.tar.gz" \
    -C "$PROJ_DIR/frontend" \
    index.html css/ js/

echo ""
echo "Packages created in workspace/packages/:"
ls -lh "$OUTDIR"
echo ""
echo "=== Done ==="
