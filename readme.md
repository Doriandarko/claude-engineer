# 🤖 LLM Engineer

LLM Engineer is an advanced interactive command-line interface (CLI) that harnesses the power of Anthropic's Claude-3.5-Sonnet model to assist with a wide range of software development tasks. This tool seamlessly combines the capabilities of a state-of-the-art large language model with practical file system operations, web search functionality, and intelligent code analysis.

## ✨ Features

- 💬 Interactive chat interface with Claude-3.5-Sonnet
- 📁 Comprehensive file system operations (create folders, files, read/write files)
- 🔍 Web search capabilities using Tavily API for up-to-date information
- 🌈 Enhanced syntax highlighting for code snippets
- 🏗️ Intelligent project structure creation and management
- 🧐 Advanced code analysis and improvement suggestions
- 🖼️ Vision capabilities support via drag and drop of images in the terminal
- 🚀 Improved automode for efficient autonomous task completion
- 🔄 Robust iteration tracking and management in automode
- 📊 Precise diff-based file editing for controlled code modifications
- 🛡️ Enhanced error handling and detailed output for tool usage
- 🎨 Color-coded terminal output for improved readability
- 📸 Image processing and analysis capabilities
- 🔧 Detailed logging of tool usage and results

## 🛠️ Installation

1. Clone this repository:


2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Set up your API keys:
   - Add your Anthropic and Tavily API keys at the start of the file:
     ```python
     client = Anthropic(api_key="YOUR API KEY")
     tavily = TavilyClient(api_key="YOUR API KEY")
     ```
  - As alternative to direct usage of Anthropic API - consider Anthropic via Bedrock (authorised by AWS profile), Cohere R+, local Mixtral, or any other LLM supported by LiteLLM

## 🚀 Usage

Run the main script to start the LLM Engineer interface:

```
python main.py
```

Once started, you can interact with LLM Engineer by typing your queries or commands. Some example interactions:

- "Create a new Python project structure for a web application"
- "Explain the code in file.py and suggest improvements"
- "Search for the latest best practices in React development"
- "Help me debug this error: [paste your error message]"

Special commands:
- Type 'exit' to end the conversation and close the application.
- Type 'image' to include an image in your message.
- Type 'automode [number]' to enter Autonomous mode with a specific number of iterations.
- Press Ctrl+C at any time to exit the automode and return to regular chat.

### 🤖 Improved Automode

The enhanced automode allows Claude to work autonomously on complex tasks with greater efficiency and control. When in automode:

1. LLM sets clear, achievable goals based on your request.
2. It works through these goals one by one, using available tools as needed.
3. Claude provides regular updates on its progress, including the current iteration count.
4. Automode continues until goals are completed or the maximum number of iterations is reached.
5. You can specify the maximum number of iterations when entering automode.

To use automode:
1. Type 'automode [number]' when prompted for input, where [number] is the maximum number of iterations.
2. Provide your request when prompted.
3. Claude will work autonomously, providing updates after each iteration.
4. Automode exits when the task is completed, after reaching the maximum number of iterations, or when you press Ctrl+C.

### 📊 Enhanced Diff-based File Editing

Claude Engineer now supports an improved diff-based file editing system, allowing for more precise and controlled modifications to existing files. When editing files, Claude will:

1. Show a detailed diff of the proposed changes, highlighting additions, removals, and unchanged lines with color coding.
2. Focus on adding new code or modifying existing code without unnecessarily removing functionality.
3. Provide explanations for any removed code, ensuring transparency in the editing process.
4. Use regex patterns for precise matching and complex edits.
5. Support various editing scenarios, including targeted changes, appending content, inserting at the beginning, and replacing entire file contents.

This feature enhances LLM's ability to make targeted improvements to your codebase while maintaining the integrity of existing functionality.

### 🧠 Improved System Prompt and Error Handling

The system prompt has been updated with more detailed instructions and best practices, allowing Claude to provide more accurate and helpful responses. Additionally, the code now includes enhanced error handling and more detailed output for tool usage, improving the overall reliability and user experience of the application.

Note: Claude will only have access to the files in the root folders of the script or any folder path you provide it.

## 👥 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=Doriandarko/claude-engineer&type=Date)](https://star-history.com/#Doriandarko/claude-engineer&Date)
