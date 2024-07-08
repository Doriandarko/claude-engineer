## Description of Changes

This pull request introduces the following updates to the Claude Engineer project:

1. Added support for OpenRouter API integration via a new `main-openrouter.py` script.
2. Updated the README.md with comprehensive information about both `main.py` and `main-openrouter.py`.
3. Created a .gitignore file to exclude sensitive information and unnecessary files from version control.
4. Improved documentation on API key setup and usage instructions.

## Key Features Added

- Compatibility with OpenRouter API for flexible model selection
- Detailed comparison between `main.py` and `main-openrouter.py` in the README
- Enhanced installation and setup instructions

## How to Test

1. Clone this branch of the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Set up your `.env` file with the necessary API keys (ANTHROPIC_API_KEY, TAVILY_API_KEY, OPENROUTER_API_KEY)
4. Run both versions of the script:
   - Original: `python main.py`
   - GPT-enhanced: `python main-openrouter.py`
5. Test various commands and features, including automode and image analysis, in both versions

## Additional Notes

- Ensure you have the latest versions of all required libraries
- The OpenRouter integration requires an OpenRouter API key
- Please review the updated README for detailed usage instructions

## Checklist

- [ ] I have tested these changes locally
- [ ] I have updated the documentation accordingly
- [ ] My changes generate no new warnings or errors
- [ ] I have added tests that prove my fix is effective or that my feature works
- [ ] New and existing unit tests pass locally with my changes