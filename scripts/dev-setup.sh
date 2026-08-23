#!/usr/bin/env bash
# Zero to GEO — Development setup script
# Run from the repository root: ./scripts/dev-setup.sh

set -e

echo "=== Zero to GEO — Dev Setup ==="

# Backend
echo ""
echo "→ Setting up backend..."
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
echo ""
echo "→ Backend ready. Run: cd backend && source venv/bin/activate && uvicorn app.main:app --reload --port 8000"

# Frontend
cd ../frontend
echo ""
echo "→ Setting up frontend..."
npm install
echo ""
echo "→ Frontend ready. Run: cd frontend && npm run dev"

echo ""
echo "=== Setup complete ==="
echo ""
echo "Start backend:  cd backend && source venv/bin/activate && uvicorn app.main:app --reload --port 8000"
echo "Start frontend: cd frontend && npm run dev"
echo "API docs:       http://localhost:8000/docs"
echo "Frontend:       http://localhost:5173"
