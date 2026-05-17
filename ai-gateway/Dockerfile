FROM python:3.11-slim
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*
WORKDIR /app
RUN pip install uv
COPY requirements.txt .
RUN uv pip install --system --no-cache -r requirements.txt
COPY gateway/ ./gateway/
EXPOSE 8002
CMD ["uvicorn", "gateway.server:app", "--host", "0.0.0.0", "--port", "8002"]
