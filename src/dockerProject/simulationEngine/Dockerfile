# Use a base image
FROM python:3.11-slim

# Set the working directory
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt . 

# Install required packages
RUN pip install --no-cache-dir -r requirements.txt

# Copy all Python files into the container
COPY *.py ./

# Set Python path to include the app directory
ENV PYTHONPATH=/app

# Command to run the application
CMD ["python", "app.py"]