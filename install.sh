#!/bin/bash
# Priority Living CLI — Quick Install
set -e

echo "╔═══════════════════════════════════════════╗"
echo "║   Priority Living CLI — Installer         ║"
echo "╚═══════════════════════════════════════════╝"
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required. Install it from https://python.org"
    exit 1
fi

echo "✅ Python 3 found: $(python3 --version)"

# Install the package
echo "📦 Installing Priority Living CLI..."
pip install -e . 2>/dev/null || pip3 install -e .

echo ""
echo "✅ Installation complete!"
echo ""
echo "Usage:"
echo "  pl config set bridge_key pb_YOUR_KEY"
echo "  pl status"
echo "  pl bridge start"
echo ""
echo "For AI features (model download/inference):"
echo "  pip install priority-living-cli[ai]"
echo ""
