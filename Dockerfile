# syntax=docker/dockerfile:1
FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY backend /app/backend
COPY frontend /app/frontend
COPY final_dataset.csv /app/
COPY load_questions.py /app/

# Default command runs app + load_questions
CMD ["sh", "-c", "-u","python load_questions.py && exec python backend/app.py"]