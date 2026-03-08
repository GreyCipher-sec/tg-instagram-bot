FROM python:3.12-slim
RUN useradd -m -u 1000 botuser
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY --chown=botuser:botuser . .
USER botuser
CMD ["python", "main.py"]
