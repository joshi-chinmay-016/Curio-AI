#!/bin/bash
set -e

echo "Setting up Curio AI Monorepo..."

if [ ! -f .env ]; then
  echo "Creating .env from .env.example..."
  cp .env.example .env
fi

echo "Installing Backend dependencies..."
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cd ..

echo "Installing Frontend dependencies..."
cd frontend
npm install
cd ..

echo "Done! You can now start the services as detailed in README.md."
