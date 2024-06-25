# Claude Engineer

Claude Engineer is an interactive command-line interface (CLI) that leverages the power of Anthropic's Claude-3.5-Sonnet model to assist with software development tasks. This tool combines the capabilities of a large language model with practical file system operations and web search functionality.

## Features

- Interactive chat interface with Claude-3.5-Sonnet
- File system operations (create folders, files, read/write files)
- Web search capabilities using Tavily API
- Syntax highlighting for code snippets
- Project structure creation and management
- Code analysis and improvement suggestions

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/yourusername/claude-engineer.git
   cd claude-engineer
   ```

2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Set up your API keys:
   - Copy the `.env.example` file to create a new `.env` file:
     ```
     cp .env.example .env
     ```
   - Open the `.env` file and replace the placeholder values with your actual API keys:
     ```
     ANTHROPIC_API_KEY=your_actual_anthropic_api_key_here
     TAVILY_API_KEY=your_actual_tavily_api_key_here
     ```
   - The script will automatically load these environment variables using python-dotenv
   - Note: Never commit your actual `.env` file to version control

## Usage

Run the main script to start the Claude Engineer interface:

```
python main.py
```

Once started, you can interact with Claude Engineer by typing your queries or commands. Some example interactions:

- "Create a new Python project structure for a web application"
- "Explain the code in file.py and suggest improvements"
- "Search for the latest best practices in React development"
- "Help me debug this error: [paste your error message]"

Type 'exit' to end the conversation and close the application.

Note: Claude will only have access to the files in the root folders of the script or any folder path you provide it.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
