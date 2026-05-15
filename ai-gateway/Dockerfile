FROM python:3.11-slim
WORKDIR /app
RUN pip install uv
COPY requirements.txt .
RUN uv pip install --system --no-cache -r requirements.txt
COPY gateway/ ./gateway/
EXPOSE 8002
CMD ["uvicorn", "gateway.server:app", "--host", "0.0.0.0", "--port", "8002"]
