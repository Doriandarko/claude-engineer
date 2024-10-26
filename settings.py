from flask import Flask, render_template, request, redirect, url_for
import os
from dotenv import load_dotenv

app = Flask(__name__)

# Load environment variables from .env file
load_dotenv()

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if request.method == 'POST':
        # Update environment variables
        anthropic_api_key = request.form.get('ANTHROPIC_API_KEY')
        tavily_api_key = request.form.get('TAVILY_API_KEY')
        eleven_labs_api_key = request.form.get('ELEVEN_LABS_API_KEY')
        base_url = request.form.get('BASE_URL')

        # Save the updated environment variables to the .env file
        with open('.env', 'w') as f:
            f.write(f"ANTHROPIC_API_KEY={anthropic_api_key}\n")
            f.write(f"TAVILY_API_KEY={tavily_api_key}\n")
            f.write(f"ELEVEN_LABS_API_KEY={eleven_labs_api_key}\n")
            f.write(f"BASE_URL={base_url}\n")

        # Reload the environment variables
        load_dotenv()

        return redirect(url_for('settings'))

    # Load current environment variables
    anthropic_api_key = os.getenv('ANTHROPIC_API_KEY')
    tavily_api_key = os.getenv('TAVILY_API_KEY')
    eleven_labs_api_key = os.getenv('ELEVEN_LABS_API_KEY')
    base_url = os.getenv('BASE_URL')

    return render_template('settings.html', 
                           anthropic_api_key=anthropic_api_key, 
                           tavily_api_key=tavily_api_key, 
                           eleven_labs_api_key=eleven_labs_api_key, 
                           base_url=base_url)

if __name__ == '__main__':
    app.run(debug=True)
