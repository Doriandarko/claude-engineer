#!/bin/bash

# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh
# Or using wget if curl is not available:
# wget -qO- https://astral.sh/uv/install.sh | sh

# Clone and setup
git clone https://github.com/Doriandarko/claude-engineer.git
cd claude-engineer

# Create a virtual environment and activate it
uv venv
source .venv/bin/activate

# Install dependencies from requirements.txt
pip install -r requirements.txt
