# 🤖 Claude Engineer

Claude Engineer is an interactive command-line interface (CLI) that leverages the power of Anthropic's Claude-3.5-Sonnet model or OpenRouter API to assist with software development tasks. This tool combines the capabilities of advanced language models with practical file system operations and web search functionality.

## ✨ Features

- 💬 Interactive chat interface with Claude-3.5-Sonnet or OpenRouter models
- 🔀 Choice between Anthropic and OpenRouter APIs at startup
- 📁 File system operations (create folders, files, read/write files)
- 🔍 Web search capabilities using Tavily API
- 🌈 Syntax highlighting for code snippets
- 🏗️ Project structure creation and management
- 🧐 Code analysis and improvement suggestions
- 🖼️ Vision capabilities support via drag and drop of images in the terminal
- 🚀 Automode for autonomous task completion
- 🔄 Iteration tracking in automode
- 📊 Diff-based file editing for precise code modifications
- 🔐 Environment variable management for secure configuration
- 🔄 OpenRouter API integration for improved AI capabilities and model flexibility

## 🛠️ Installation

1. Clone this repository:
   ```
   git clone https://github.com/Doriandarko/claude-engineer.git
   cd claude-engineer
   ```

2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Set up your environment variables:
   - Copy the `.env.template` file to `.env`
   - Fill in your API keys in the `.env` file:
     ```
     ANTHROPIC_API_KEY=your_anthropic_api_key_here
     OPENROUTER_API_KEY=your_openrouter_api_key_here
     TAVILY_API_KEY=your_tavily_api_key_here
     ```

## 🚀 Usage

Run the main script to start the Claude Engineer interface:

```
python main.py
```

When starting the script, you'll be prompted to choose between the Anthropic API and OpenRouter API:
```
Choose API (1 for Anthropic, 2 for OpenRouter):
```

Once started, you can interact with Claude Engineer by typing your queries or commands. Some example interactions:

- "Create a new Python project structure for a web application"
- "Explain the code in file.py and suggest improvements"
- "Search for the latest best practices in React development"
- "Help me debug this error: [paste your error message]"

Special commands:
- Type 'exit' to end the conversation and close the application.
- Type 'image' to include an image in your message.
- Type 'automode [number]' to enter Autonomous mode with a specific number of iterations.
- Press Ctrl+C at any time to exit the automode to return to regular chat.

### 🤖 Automode

Automode allows Claude to work autonomously on complex tasks. When in automode:

1. Claude sets clear, achievable goals based on your request.
2. It works through these goals one by one, using available tools as needed.
3. Claude provides regular updates on its progress.
4. Automode continues until goals are completed or the maximum number of iterations is reached.

To use automode:
1. Type 'automode [number]' when prompted for input, where [number] is the maximum number of iterations.
2. Provide your request when prompted.
3. Claude will work autonomously, providing updates after each iteration.
4. Automode exits when the task is completed or after reaching the maximum number of iterations.

### 📊 Diff-based File Editing

Claude Engineer supports diff-based file editing, allowing for more precise and controlled modifications to existing files. When editing files, Claude will:

1. Show a diff of the proposed changes, highlighting additions, removals, and unchanged lines.
2. Focus on adding new code or modifying existing code without unnecessarily removing functionality.
3. Provide explanations for any removed code, ensuring transparency in the editing process.

This feature enhances Claude's ability to make targeted improvements to your codebase while maintaining the integrity of existing functionality.

### 🔐 Environment Variables and API Integration

Claude Engineer uses environment variables for secure configuration management. The `.env` file stores sensitive information like API keys, which are loaded using the `python-dotenv` library.

The integration with both Anthropic and OpenRouter APIs provides improved AI capabilities and flexibility in choosing different language models. You can switch between these APIs at the start of each session, allowing you to leverage the strengths of different models as needed.

Note: Claude will only have access to the files in the root folders of the script or any folder path you provide it.

## 👥 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=Doriandarko/claude-engineer&type=Date)](https://star-history.com/#Doriandarko/claude-engineer&Date)
