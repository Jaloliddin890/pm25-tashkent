FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY service1/ ./service1/
COPY service2_api/ ./service2_api/

EXPOSE 8080

CMD ["uvicorn", "service2_api.main:app", "--host", "0.0.0.0", "--port", "8080"]
