FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "experiments/run_demo.py", "--steps", "20", "--fail-at", "4", "--fail-duration", "5"]
