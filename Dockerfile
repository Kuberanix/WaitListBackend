# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install any dependencies from requirements.txt
RUN pip install --no-cache-dir -r req.txt
RUN python3 dbCreate.py

# Expose the port on which your Flask app will run
EXPOSE 5000

# Command to run Gunicorn with Flask app in production mode
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:create_app()", "--access-logfile", "-", "--error-logfile", "-", "--log-level", "info", "--access-logformat", "%(h)s %(l)s %(u)s %(t)s \"%(r)s\" %(s)s %(b)s \"%(f)s\" \"%(a)s\""]