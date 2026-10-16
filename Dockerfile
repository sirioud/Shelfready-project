# Small official Python image, same version as the course env (3.12)
FROM python:3.12-slim

WORKDIR /app

# Which requirements file to install: requirements.txt (default, used by Render)
# or requirements-freeze.txt (full course env): docker build --build-arg REQUIREMENTS=requirements-freeze.txt .
ARG REQUIREMENTS=requirements.txt

# Install the requirements first, so Docker can reuse this layer when only the code changes
COPY ${REQUIREMENTS} ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the app and its package (code + sample data)
COPY shelfready_app.py ./
COPY shelfready shelfready/

EXPOSE 8501

# Render gives the port in $PORT; 8501 is used when running locally
CMD ["sh", "-c", "exec streamlit run shelfready_app.py --server.address 0.0.0.0 --server.port ${PORT:-8501} --server.headless true"]
