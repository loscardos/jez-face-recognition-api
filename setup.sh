#!/bin/bash
# Face Recognition System - Complete Setup Script

set -e

echo "========================================"
echo "Face Recognition Attendance System Setup"
echo "========================================"
echo ""

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

# Check if Python is installed
echo -e "${BLUE}Checking Python installation...${NC}"
if ! command -v python3 &> /dev/null; then
    echo "Python 3 is not installed. Please install Python 3.8 or higher."
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
echo -e "${GREEN}✓ Python ${PYTHON_VERSION} found${NC}"
echo ""

# Setup Python Backend
echo -e "${BLUE}Setting up Python Face Recognition Backend...${NC}"

cd /home/royyan/projects/face-attendance-ai

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    echo -e "${GREEN}✓ Virtual environment created${NC}"
else
    echo -e "${GREEN}✓ Virtual environment already exists${NC}"
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate
echo -e "${GREEN}✓ Virtual environment activated${NC}"
echo ""

# Install dependencies
echo -e "${BLUE}Installing Python dependencies...${NC}"
echo "This may take a few minutes..."
pip install --upgrade pip
pip install -r requirements.txt
echo -e "${GREEN}✓ Dependencies installed${NC}"
echo ""

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo -e "${BLUE}Creating .env configuration file...${NC}"
    cp .env.example .env
    echo -e "${GREEN}✓ .env created from template${NC}"
    echo "Please edit .env and set LARAVEL_API_URL and LARAVEL_API_TOKEN"
    echo ""
fi

# Create necessary directories
mkdir -p logs
mkdir -p face_data
echo -e "${GREEN}✓ Directories created${NC}"
echo ""

# Summary
echo "========================================"
echo -e "${GREEN}Setup Complete!${NC}"
echo "========================================"
echo ""
echo "Next steps:"
echo "1. Update .env configuration:"
echo "   nano /home/royyan/projects/face-attendance-ai/.env"
echo ""
echo "2. Start the Python backend:"
echo "   cd /home/royyan/projects/face-attendance-ai"
echo "   source venv/bin/activate"
echo "   python main.py"
echo ""
echo "3. The API will be available at:"
echo "   http://localhost:8000"
echo ""
echo "4. Test with:"
echo "   curl http://localhost:8000/health"
echo ""
