FROM python:3.9-slim-buster

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 5000

# Alteração aqui: Usar Gunicorn para rodar a aplicação
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]