#!/usr/bin/env bash
set -euo pipefail

echo "=== Cut News Setup ==="

# Check prerequisites
echo "Checking prerequisites..."

if ! command -v uv &> /dev/null; then
    echo "Error: uv is not installed. Install it with: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

if ! command -v pnpm &> /dev/null; then
    echo "Error: pnpm is not installed. Install it with: npm install -g pnpm"
    exit 1
fi

if ! command -v node &> /dev/null; then
    echo "Error: Node.js is not installed."
    exit 1
fi

echo "Prerequisites OK!"

# Install Python dependencies
echo ""
echo "Installing Python dependencies..."
cd apps/backend && uv sync --all-extras && cd ../..
cd apps/crawler && uv sync --all-extras && cd ../..

# Install Node.js dependencies
echo ""
echo "Installing Node.js dependencies..."
cd apps/frontend && pnpm install && cd ../..

echo ""
echo "=== Setup Complete! ==="
echo ""
echo "Available commands:"
echo "  make dev-backend   - Start backend server on :8000"
echo "  make dev-crawler   - Start crawler server on :8001"
echo "  make dev-frontend  - Start frontend on :3000"
