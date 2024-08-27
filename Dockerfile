FROM python:3.12-slim

WORKDIR /usr/src/app

COPY requirements.txt ./

RUN pip install --no-cache-dir -r requirements.txt

COPY *.py .

RUN python -m venv code_execution_env

CMD [ "python", "./main.py" ]
