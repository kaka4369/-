FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV DATA_DIR=/app/data
ENV STORAGE_DIR=/app/storage
ENV PORT=3020

EXPOSE 3020

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "3020"]
