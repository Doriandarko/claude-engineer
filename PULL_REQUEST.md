# Pull Request: Add OpenRouter Integration and Improve Documentation

## Description

This pull request introduces OpenRouter API integration to the Claude Engineer project, along with significant improvements to the documentation and project structure. The changes aim to enhance the flexibility of the tool by allowing users to choose between the original Anthropic API and the OpenRouter API for model access.

## Changes Made

1. **New File: main-openrouter.py**
   - Introduced a new script that uses the OpenAI client with OpenRouter API.
   - Adapted the existing functionality to work with OpenRouter's API structure.

2. **Updates to README.md**
   - Added comprehensive information about both `main.py` and `main-openrouter.py`.
   - Included a detailed comparison of features and usage between the two versions.
   - Updated installation instructions to include setup for both Anthropic and OpenRouter API keys.
   - Enhanced the description of features, including the new OpenRouter integration.

3. **New File: .gitignore**
   - Created a .gitignore file to exclude sensitive information (like .env) and unnecessary files from version control.

4. **Updates to requirements.txt**
   - Added new dependencies required for OpenRouter integration.

5. **New File: PULL_REQUEST_TEMPLATE.md**
   - Added a pull request template to standardize future contributions.

6. **Modifications to main.py**
   - Minor updates to maintain consistency with the env variables.

7. **New File: tools.py**
   - Separated tool definitions into a separate file for better code organization.

## How to Test

1. Clone this branch of the repository.
2. Install dependencies: `pip install -r requirements.txt`
3. Set up your `.env` file with the necessary API keys:
   ```
   TAVILY_API_KEY=your_tavily_api_key
   ANTHROPIC_API_KEY=your_anthropic_api_key
   // or
   OPENROUTER_API_KEY=your_openrouter_api_key
   ```
4. Run any version of the script:
   - Original: `python main.py`
   - GPT-enhanced: `python main-openrouter.py`
5. Test various commands and features, including:
   - Basic queries and responses
   - File system operations
   - Web searches
   - Automode functionality
   - Image analysis (if applicable)
6. Verify that both versions work as expected and that the OpenRouter integration in `main-openrouter.py` provides the intended functionality.

## Impact

- Users now have the flexibility to choose between Anthropic's API and OpenRouter for accessing language models.
- Improved documentation makes it easier for new users to understand and use the tool.
- Better project structure enhances maintainability and sets the stage for future improvements.
- Bypass the Anthropic's API limits

## Additional Notes

- Ensure you have the latest versions of all required libraries.
- The OpenRouter integration requires an OpenRouter API key.
- Please review the updated README for detailed usage instructions for both versions.

---

By merging this pull request, we significantly enhance the capabilities and user-friendliness of the Claude Engineer project, opening up new possibilities for model access and setting a strong foundation for future development.