Write-Host "Setting up Curio AI Monorepo..."

if (-Not (Test-Path .env)) {
    Write-Host "Creating .env from .env.example..."
    Copy-Item .env.example .env
}

Write-Host "Installing Backend dependencies..."
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
cd ..

Write-Host "Installing Frontend dependencies..."
cd frontend
npm install
cd ..

Write-Host "Done! You can now start the services as detailed in README.md."
