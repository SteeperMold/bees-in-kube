FROM python:3.12-slim

WORKDIR /app
RUN pip install --no-cache-dir requests

COPY init.py .

CMD ["python", "-u", "init.py"]