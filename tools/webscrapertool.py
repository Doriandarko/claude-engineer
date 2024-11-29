from tools.base import BaseTool
import requests
from bs4 import BeautifulSoup

class WebScraperTool(BaseTool):
    name = "webscrapertool"
    description = '''
    Scrapes the content from a given URL and returns the text content.
    Extracts readable content from web pages while removing unnecessary elements.
    Useful for getting information from websites to provide context.
    '''
    input_schema = {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "The URL of the webpage to scrape"
            }
        },
        "required": ["url"]
    }

    def execute(self, **kwargs) -> str:
        url = kwargs.get("url")
        
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
                
            # Get text content
            text = soup.get_text()
            
            # Clean up text
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = ' '.join(chunk for chunk in chunks if chunk)
            
            if not text:
                return "No readable content found on the webpage."
                
            return text[:8000] if len(text) > 8000 else text
            
        except requests.RequestException as e:
            return f"Error scraping the webpage: {str(e)}"
        except Exception as e:
            return f"An unexpected error occurred: {str(e)}"