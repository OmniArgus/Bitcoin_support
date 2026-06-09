FROM python:3.12-slim

WORKDIR /app

# Install dependencies first so they cache across code changes
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# State (subscribers, threshold) is written here; mount a volume to persist it
ENV STATE_FILE=/data/state.json

CMD ["python", "bot.py"]
