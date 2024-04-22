FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /usr/src/app

# Copy the current directory contents into the container at /usr/src/app
COPY . /usr/src/app

RUN pip install --no-cache-dir websockets aioredis

# Make port 3000 to 3003 available to the world outside this container
EXPOSE 3000 3001 3002 3003

CMD ["python", "app.py"]
