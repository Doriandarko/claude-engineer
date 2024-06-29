# 🤖 Claude Engineer

Claude Engineer is an advanced interactive command-line interface (CLI) that harnesses the power of Anthropic's Claude-3.5-Sonnet model to assist with a wide range of software development tasks. This tool seamlessly integrates the capabilities of a large language model with practical file system operations and web search functionality, creating a powerful AI-driven development environment.

## ✨ Features

- 💬 Interactive chat interface powered by Claude-3.5-Sonnet
- 📁 File system operations (create, read, write, and list files and folders)
- 🔍 Web search capabilities using Tavily API for up-to-date information
- 🌈 Syntax highlighting for code snippets in various programming languages
- 🏗️ Intelligent project structure creation and management
- 🧐 Advanced code analysis and improvement suggestions
- 🖼️ Vision capabilities for analyzing images via terminal drag-and-drop
- 🚀 Autonomous mode for complex task completion
- 🔄 Iteration tracking and goal-oriented execution in autonomous mode
- 🔐 Secure API key management using .env file

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

3. Set up your API keys:
   - Create a `.env` file in the root directory of the project
   - Add your Anthropic and Tavily API keys to the `.env` file:
     ```
     ANTHROPIC_API_KEY=your_anthropic_api_key_here
     TAVILY_API_KEY=your_tavily_api_key_here
     ```

## 📁 Project Structure

The project is organized into multiple files for improved maintainability and modularity:

- `main.py`: Entry point of the application
- `config.py`: Configuration settings, constants, and system prompt
- `utils.py`: Utility functions for printing, code highlighting, and image processing
- `file_operations.py`: Functions for file and folder operations
- `tools.py`: Definitions and execution logic for Claude's available tools
- `claude_chat.py`: Core Claude interaction logic and chat functionality

## 🚀 Usage

To start the Claude Engineer interface, run:

```
python main.py
```

Once started, you can interact with Claude Engineer using the following commands:

- Type your queries or requests directly to interact with Claude
- Type 'exit' to end the conversation and close the application
- Type 'image' to include an image in your message (you'll be prompted to provide the image path)
- Type 'automode' to enter Autonomous mode for complex tasks

### 🤖 Autonomous Mode

Autonomous mode allows Claude to work independently on complex tasks:

1. Claude sets clear, achievable goals based on your request
2. It works through these goals one by one, using available tools as needed
3. Regular progress updates are provided after each iteration
4. Autonomous mode continues until goals are completed or the maximum number of iterations is reached

To use Autonomous mode:
1. Type 'automode' when prompted for input
2. Provide your request when prompted
3. Claude will work autonomously, providing updates after each iteration
4. Autonomous mode exits when the task is completed or after reaching the maximum number of iterations

## 🛠️ Available Tools

Claude Engineer has access to the following tools:

1. `create_folder`: Create a new folder at a specified path
2. `create_file`: Create a new file at a specified path with optional content
3. `write_to_file`: Write or update content in an existing file
4. `read_file`: Read the contents of a file at a specified path
5. `list_files`: List all files and directories in a specified folder
6. `tavily_search`: Perform a web search using the Tavily API for up-to-date information

These tools allow Claude to interact with the file system and gather current information from the web, enhancing its ability to assist with development tasks.

## 🤝 Contributing

Contributions to Claude Engineer are welcome! If you have ideas for improvements or new features, please feel free to:

1. Fork the repository
2. Create a new branch for your feature
3. Implement your changes
4. Submit a pull request with a clear description of your improvements

Please ensure that your code adheres to the existing style and includes appropriate tests and documentation.

## 📄 License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgements

- [Anthropic](https://www.anthropic.com) for the Claude-3.5-Sonnet model
- [Tavily](https://tavily.com) for their powerful search API
- All contributors and users of Claude Engineer

## 🔒 Security Note

This project uses environment variables to manage API keys securely. Never commit your `.env` file or share your API keys publicly. The `.env` file is included in the `.gitignore` to prevent accidental commits.

For any questions or support, please open an issue on the GitHub repository.