Modifica este programa de python para que funcione con el sdk de openai (con base_url apuntando a Open Router), utiliza el modelo 'openai/gpt-4o-mini', considera que esto será un pull request, por lo cual es escencial no modificar tanto el código. 

El proyecto tendrá lugar en el folder 'pa', si no existe, crealo. Considera también lo siguiente:

1. Preguntarle al usuario si desea utilizar Anthropic u Open Router cuando se inicializa el programa (solo habrá dos opciones y el usuario se puede desplazar con flechitas arria/abajo y enter en consola)

2. Transformar la llamada al client para que coincida con el sdk (chat.completions.) y 
client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=os.getenv("OPENROUTER_API_KEY"))

3. Transformar la estructura de la definición de funciones para que coincida con el formato de openai en caso de que el usuario haya selccionado usar Open Router. Asegúrate de que el uso de las tools ocurra bien:

# This function transforms the CLAUDE_TOOLS object into an openai-compatible object
def get_openai_tools(tools):
    openai_tools = []
    for tool in tools:
        openai_tools.append({
            "type": "function",
            "function": {
                "name": tool["name"],
                "parameters": tool["input_schema"],
                "description": tool["description"]
            }
        })
    return openai_tools


4. Que la respuesta se hile correctamente en la conversación y no falle al usar functions & tools, que siempre haga correctamente la distinción cuando es Anthropic y cuando es Open Router para leer bien la response

5. Que mantenga las mismas funcionalidades que actualmente se tienen con Anthropic (Buscar en Tavily, Leer archivos, Escribir archivos, etc.) con OpenAI

6. Modificar la menor cantidad de código posible o bien, crear un adaptador para seleccionar entre Anthropic u OpenRouter para el modelo, puesto que crearé un pull request

7. Asegúrate de que se importen todas las dependencias y que no falte nada para que funcione bien, tanto en Mac/Windows/Linux

8. Que el automode ocurra bien en Anthropic (ya ocurre bien) y también en OpenAI

9. MUY IMPORTANTE: que el conteo de tokens y precio solo ocurra cuando se esta usando Anthropic.

10. Asegúrate de refactorizar lo necesario para lograr un código minimalista y funcional

Codigo a modificar:
/Users/obedvargasvillarreal/Documents/obeskay/proyectos/experimentos/claude-engineer/pa/main.py