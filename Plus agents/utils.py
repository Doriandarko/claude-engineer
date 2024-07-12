import base64
from PIL import Image
import io
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.markdown import Markdown

console = Console()

def encode_image_to_base64(image_path):
    try:
        with Image.open(image_path) as img:
            max_size = (1024, 1024)
            img.thumbnail(max_size, Image.DEFAULT_STRATEGY)
            if img.mode != 'RGB':
                img = img.convert('RGB')
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format='JPEG')
            return base64.b64encode(img_byte_arr.getvalue()).decode('utf-8')
    except Exception as e:
        return f"Error encoding image: {str(e)}"

def highlight_diff(diff_text):
    return Syntax(diff_text, "diff", theme="monokai", line_numbers=True)

def print_panel(content, title, style="cyan"):
    panel = Panel(content, title=title, expand=False, border_style=style)
    console.print(panel)

def print_markdown(content):
    console.print(Markdown(content))

def parse_goals(response):
    import re
    goals = re.findall(r'Goal \d+: (.+)', response)
    return goals