#!/bin/bash

ENV_DIR="ENV"

if [ ! -d "$ENV_DIR" ]; then
    echo "Creating virtual environment..."
    python3 -m venv $ENV_DIR

    echo "Activating virtual environment..."
    source $ENV_DIR/bin/activate

    echo "Installing packages from requirements.txt..."
    pip install -r requirements.txt

    echo "Ready! Virtual environment is set up."
else
    echo "Virtual environment already exists."
    echo "Activating virtual environment..."
    source $ENV_DIR/bin/activate
fi

echo "Running the application..."
python main.py
