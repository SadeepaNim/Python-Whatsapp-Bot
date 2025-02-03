# Base image with Python installed
FROM python:3.10-slim

# Set working directory in the container
WORKDIR /app

# Copy requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application files into the container
COPY . /app

# Expose the port your app runs on
EXPOSE 5000

# Run the application
CMD ["python", "app/run.py"]
