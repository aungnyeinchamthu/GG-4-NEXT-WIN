# Use official Python image
FROM python:3.10-slim

# Set work directory
WORKDIR /app

# Install pip dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy bot code
COPY . .

# Set environment variables for Python
ENV PYTHONUNBUFFERED=1

# Run your bot
CMD ["python", "bot.py"]
