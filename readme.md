# Claude Engineer v3 🤖

A powerful self-improving AI Assistant designed for creating and managing AI tools with Claude 3.5. This framework enables Claude to generate and manage its own tools, continuously expanding its capabilities through conversation. Via an advanced interactive command-line interface (CLI)

## History and Evolution
This project represents the third major iteration of Claude Engineer, building upon the success of Claude Engineer v2. Key improvements from previous versions include:
- Upgraded to Claude 3.5 Sonnet model
- Enhanced token management with Anthropic's new token counting API
- Self-improving tool creation system
- Streamlined conversation handling
- More precise token usage tracking and visualization
- Autonomous tool generation capabilities
- No need for automode since Claude can intelligently decide when to run tools automatically and sequentially.

## Description
Claude Engineer v3 is a sophisticated framework that allows Claude to expand its own capabilities through dynamic tool creation. During conversations, Claude can identify needs for new tools, design them, and implement them automatically. This self-improving architecture means the framework becomes more powerful the more you use it.

## Self-Improvement Features
- 🧠 Autonomous tool identification and creation
- 🔄 Dynamic capability expansion during conversations
- 🎯 Smart tool dependency management
- 📈 Learning from tool usage patterns
- 🔍 Automatic identification of capability gaps
- 🛠️ Self-optimization of existing tools

## Core Features
- 🔨 Dynamic tool creation and loading
- 🔄 Hot-reload capability for new tools
- 🎨 Rich console interface with progress indicators
- 🧩 Tool abstraction framework with clean interfaces
- 📝 Automated tool code generation
- 🔌 Easy integration with Claude 3.5 AI
- 💬 Persistent conversation history with token management
- 🛠️ Real-time tool usage display
- 🔄 Automatic tool chaining support
- ⚡ Dynamic module importing system
- 📊 Advanced token tracking with Anthropic's token counting API
- 🎯 Precise context window management
- 🔍 Enhanced error handling and debugging
- 💾 Conversation state management

## Installation

For the best possible experience install uv

### macOS and Linux
```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh
# Or using wget if curl is not available:
# wget -qO- https://astral.sh/uv/install.sh | sh

# Clone and setup
git clone https://github.com/Doriandarko/claude-engineer.git
cd claude-engineer
uv venv
source .venv/bin/activate

# Install dependencies and run
uv run ce3.py
```

### Windows
```powershell
# Install uv
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# Clone and setup
git clone https://github.com/Doriandarko/claude-engineer.git
cd claude-engineer
uv venv
.venv\Scripts\activate

# Install dependencies and run
uv run ce3.py
```

### Alternative Installation (Using pip)
If you prefer using traditional pip, you can follow these steps:
```bash
# Clone the repository
git clone github.com/Doriandarko/claude-engineer.git
cd claude-engineer

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY
```


## Usage

### Starting the Assistant
```bash
uv run ce3.py
```

### Command Reference
- Type 'refresh' to reload available tools
- Type 'reset' to clear conversation history and token count
- Type 'quit' to exit the assistant
- Use natural language to interact with tools

### Self-Improving Tool Creation
Claude Engineer v3 can automatically identify needs for new tools and create them during conversations. When you request functionality that isn't available:

1. Claude analyzes the request and existing tools
2. If needed, it designs and implements a new tool
3. The tool is automatically saved and loaded
4. Type 'refresh' to start using the new tool

This creates a continuously expanding toolkit tailored to your needs.

### Token Management
The assistant features advanced token management:
- Real-time token counting using Anthropic's API
- Visual progress bar for token usage
- Automatic warnings when approaching token limits
- Smart conversation management to prevent token overflow
- Detailed token usage statistics

## Project Structure
```
claude-engineer/
├── config.py           # Configuration settings
├── main.py            # Main assistant interface
├── tools/             # Tool implementations
│   ├── base.py        # Base tool class
│   └── ...           # Generated and custom tools
└── prompts/           # System prompts
    └── system_prompts.py
```

## Key Components

### Assistant Class
The core Assistant class provides:
- Dynamic tool loading and management
- Real-time conversation handling with token tracking
- Automatic tool creation and validation
- Tool execution and chaining
- Rich console output with progress indicators
- Token usage optimization

### Configuration Options
The assistant supports various configuration options through the Config class:
- MODEL: Claude 3.5 Sonnet model specification
- MAX_TOKENS: Maximum tokens for individual responses
- MAX_CONVERSATION_TOKENS: Total token limit for conversations
- TOOLS_DIR: Directory for tool storage
- SHOW_TOOL_USAGE: Toggle tool usage display
- ENABLE_THINKING: Toggle thinking indicator
- DEFAULT_TEMPERATURE: Model temperature setting

## Requirements
- Python 3.8+
- Anthropic API Key (Claude 3.5 access)
- Required packages in `requirements.txt`
- Rich terminal support

## Contributing
Contributions are welcome! Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss what you would like to change.

## License
MIT

## Acknowledgments
This project builds upon the foundations of Claude Engineer v2, enhancing its capabilities with self-improving tool generation and advanced token management.

## Built-in Tools
Claude Engineer v3 comes with a comprehensive set of pre-built tools:

### Core Tools
- 🛠️ **Tool Creator** (`toolcreator`): Creates new tools based on natural language descriptions, enabling the framework's self-improvement capabilities.
- 🤔 **Sequential Thinking** (`sequentialthinking`): Enables structured, step-by-step problem analysis with support for branching thoughts and revisions.

### File System Tools
- 📂 **Explorer** (`explorer`): Comprehensive file and directory management with operations like create, list, delete, move, and search.
- 📝 **File Creator** (`filecreatortool`): Creates new files with specified content, supporting both text and binary files.
- 📖 **File Content Reader** (`filecontentreadertool`): Reads content from multiple files simultaneously.
- ✏️ **File Edit** (`fileedittool`): Advanced file editing with support for full content replacement and partial edits.

### Development Tools
- 📦 **UV Package Manager** (`uvpackagemanager`): Interface to the UV package manager for Python dependency management, supporting package installation, removal, updates, and virtual environment management.

### Web Tools
- 🔍 **DuckDuckGo** (`duckduckgotool`): Performs web 
searches using DuckDuckGo.
- 🌐 **Web Scraper** (`webscrapertool`): Extracts readable content from web pages while removing unnecessary elements.
- 🌍 **Browser** (`browsertool`): Opens URLs in the system's default web browser.

Each tool is designed to be:
- Self-documenting with detailed descriptions
- Error-resistant with comprehensive error handling
- Composable for complex operations
- Secure with proper input validation
- Cross-platform compatible where applicable

The tools are dynamically loaded and can be extended during runtime through the Tool Creator, allowing the assistant to continuously expand its capabilities based on user needs.
