FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py README.md NOTICE.md ./
COPY static ./static

ENV DATA_DIR=/app/data
ENV STORAGE_DIR=/app/storage
ENV PORT=3020

EXPOSE 3020

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:' + os.environ.get('PORT', '3020') + '/readyz', timeout=3).read()"

CMD ["sh", "-c", "exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-3020}"]
