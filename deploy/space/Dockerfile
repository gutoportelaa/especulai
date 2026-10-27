FROM python:3.12-slim

RUN useradd -m -u 1000 usuario
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY --chown=usuario app.py inferencia.py modelo.enc ./
USER usuario

# MODEL_KEY entra como segredo da hospedagem; --factory faz o processo falhar ao subir sem ela.
EXPOSE 7860
CMD ["uvicorn", "--factory", "app:criar_app", "--host", "0.0.0.0", "--port", "7860"]
