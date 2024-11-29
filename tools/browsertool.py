from tools.base import BaseTool
import webbrowser
import validators
from typing import Union, List
from urllib.parse import urlparse

class BrowserTool(BaseTool):
    name = "browsertool"
    description = '''
    Opens URLs in the system's default web browser.
    Accepts a single URL or a list of URLs.
    Validates URL format and supports http/https protocols.
    Returns feedback on which URLs were successfully opened.
    '''
    input_schema = {
        "type": "object",
        "properties": {
            "urls": {
                "type": ["string", "array"],
                "items": {"type": "string"},
                "description": "Single URL or list of URLs to open"
            }
        },
        "required": ["urls"]
    }

    def _validate_url(self, url: str) -> bool:
        if not isinstance(url, str):
            return False
        if not validators.url(url):
            return False
        parsed = urlparse(url)
        return parsed.scheme in ['http', 'https']

    def execute(self, **kwargs) -> str:
        urls = kwargs.get('urls', [])
        if isinstance(urls, str):
            urls = [urls]

        results = []
        for url in urls:
            try:
                if not self._validate_url(url):
                    results.append(f"Failed to open {url}: Invalid URL format")
                    continue
                
                webbrowser.open(url)
                results.append(f"Successfully opened {url}")
            except Exception as e:
                results.append(f"Error opening {url}: {str(e)}")

        return "\n".join(results)