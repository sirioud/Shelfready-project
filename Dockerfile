# Small official Python image, same version as the course env (3.12)
FROM python:3.12-slim

WORKDIR /app

# Which requirements file to install: requirements.txt (default, used by Render)
# or requirements-freeze.txt (full course env, kept locally, not in git): docker build --build-arg REQUIREMENTS=requirements-freeze.txt .
ARG REQUIREMENTS=requirements.txt

# Install the requirements first, so Docker can reuse this layer when only the code changes
COPY ${REQUIREMENTS} ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the app and its package (code + sample data)
COPY shelfready_app.py shelfready_server.py ./
COPY shelfready shelfready/

# Safer settings for the online version (running locally keeps streamlit's defaults)
# - uploads up to 5 MB: the default 200 MB could use all the memory of the server
# - visitors only see a short error message, the full error stays in the server logs
# - no usage statistics sent to streamlit
ENV STREAMLIT_SERVER_MAX_UPLOAD_SIZE=5 \
    STREAMLIT_CLIENT_SHOW_ERROR_DETAILS=none \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

# Run as a normal user, not root, so the app cannot change its own files or the system
RUN useradd --create-home shelfready
USER shelfready

EXPOSE 8501

# Render gives the port in $PORT; 8501 is used when running locally
# shelfready_server.py runs shelfready_app.py and hides the /_stcore/metrics page
CMD ["sh", "-c", "exec streamlit run shelfready_server.py --server.address 0.0.0.0 --server.port ${PORT:-8501} --server.headless true"]
