# Claude Engineer

Claude Engineer is an interactive command-line interface (CLI) that leverages the power of Anthropic's Claude-3.5-Sonnet model to assist with software development tasks. This tool combines the capabilities of a large language model with practical file system operations and web search functionality.

## Features

- Interactive chat interface with Claude-3.5-Sonnet
- File system operations (create folders, files, read/write files)
- Web search capabilities using Tavily API
- Syntax highlighting for code snippets
- Project structure creation and management
- Code analysis and improvement suggestions
- Vision capabilities support for via drag and drop of images in the terminal

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/Doriandarko/claude-engineer.git
   cd claude-engineer
   ```

2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Set up your API keys:
   - Add your Anthropic and Tavily API keys at the start of the file:
     ```
     client = Anthropic(api_key="YOUR API KEY")
     tavily = TavilyClient(api_key="YOUR API KEY")
     ```

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
