FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY service1/ ./service1/
COPY service2_api/ ./service2_api/

EXPOSE 7860

CMD ["uvicorn", "service2_api.main:app", "--host", "0.0.0.0", "--port", "7860"]
