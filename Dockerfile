# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app/backend

# Copy requirements.txt file into the container at /app
COPY backend /app/backend

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt


# Copy the main.py and llm.py files into the container at /app
# COPY main.py user_session.py /app/

# Make port 8000 available to the world outside this container --> this change
EXPOSE 8000

# Run app.py when the container launches
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
