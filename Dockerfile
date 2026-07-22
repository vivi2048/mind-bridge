FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# 本地 Embedding 模型缓存目录(可通过 volume 挂载宿主机模型目录)
RUN mkdir -p /app/data/embedding_models
ENV SENTENCE_TRANSFORMERS_HOME=/app/data/embedding_models

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
