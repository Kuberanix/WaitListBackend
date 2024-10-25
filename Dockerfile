# Use an official Python runtime as a parent image
FROM python:3.12.6

# Set the working directory
WORKDIR /app

# Copy the requirements file first
COPY req.txt ./

# Install the dependencies
RUN pip install --no-cache-dir -r req.txt

# Copy the rest of your application code
COPY . /app

RUN python3 dbCreate.py

# Expose the port on which your Flask app will run
EXPOSE 5000

# Command to run Gunicorn with Flask app in production mode
CMD ["gunicorn", "-w", "3", "-b", "0.0.0.0:5000", "app:create_app()", "--access-logfile", "-", "--error-logfile", "-", "--log-level", "info", "--access-logformat", "%(h)s %(l)s %(u)s %(t)s \"%(r)s\" %(s)s %(b)s \"%(f)s\" \"%(a)s\""]