# Use a more stable Python version
FROM python:3.11-slim-bullseye

WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    wget \
    gnupg2 \
    gpg \
    ca-certificates \
    unzip \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libatspi2.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    xdg-utils \
    gcc \
    g++ \
    xvfb \
    libaio1 \
    python3-dev \
    build-essential \
    libssl-dev \
    zlib1g-dev \
    gconf-service \
    libasound2 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libc6 \
    libcairo2 \
    libcups2 \
    libdbus-1-3 \
    libexpat1 \
    libfontconfig1 \
    libgcc1 \
    libgconf-2-4 \
    libgdk-pixbuf2.0-0 \
    libglib2.0-0 \
    libgtk-3-0 \
    libnspr4 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libstdc++6 \
    libx11-6 \
    libx11-xcb1 \
    libxcb1 \
    libxcomposite1 \
    libxcursor1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxi6 \
    libxrandr2 \
    libxrender1 \
    libxss1 \
    libxtst6 \
    ca-certificates \
    fonts-liberation \
    libappindicator1 \
    libnss3 \
    lsb-release \
    xdg-utils \
    && rm -rf /var/lib/apt/lists/*

# Install newer version of SQLite for chromadb
RUN cd /tmp && \
    wget https://www.sqlite.org/2023/sqlite-autoconf-3420000.tar.gz && \
    tar -xvf sqlite-autoconf-3420000.tar.gz && \
    cd sqlite-autoconf-3420000 && \
    ./configure --prefix=/usr/local && \
    make && \
    make install && \
    ldconfig && \
    cd .. && \
    rm -rf sqlite-autoconf-3420000 && \
    rm sqlite-autoconf-3420000.tar.gz

# Install Chrome latest stable version
RUN apt-get update && \
    # Remove any existing Chrome installation
    apt-get remove -y google-chrome-stable || true && \
    # Install latest Chrome stable
    wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /usr/share/keyrings/google-chrome.gpg && \
    echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome.gpg] http://dl.google.com/linux/chrome/deb/ stable main" | tee /etc/apt/sources.list.d/google-chrome.list && \
    apt-get update && \
    apt-get install -y google-chrome-stable && \
    # Show installed version for debugging
    google-chrome --version && \
    # Create symlink and set permissions
    ln -sf /usr/bin/google-chrome-stable /usr/bin/google-chrome && \
    chown root:root /usr/bin/google-chrome && \
    chmod 755 /usr/bin/google-chrome && \
    # Cleanup
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Verify Chrome installation and version
RUN echo "Checking Chrome binary..." && \
    which google-chrome && \
    echo "Chrome binary permissions:" && \
    ls -la /usr/bin/google-chrome* && \
    echo "Chrome version:" && \
    google-chrome --version

# Install Oracle Instant Client
RUN mkdir -p /opt/oracle && \
    cd /opt/oracle && \
    wget https://download.oracle.com/otn_software/linux/instantclient/instantclient-basiclite-linuxx64.zip && \
    unzip instantclient-basiclite-linuxx64.zip && \
    rm -f instantclient-basiclite-linuxx64.zip && \
    cd /opt/oracle/instantclient* && \
    rm -f *jdbc* *occi* *mysql* *README *jar uidrvci genezi adrci && \
    echo /opt/oracle/instantclient* > /etc/ld.so.conf.d/oracle-instantclient.conf && \
    ldconfig

# Set Oracle environment variables
ENV ORACLE_HOME=/opt/oracle/instantclient_21_1
ENV LD_LIBRARY_PATH=$LD_LIBRARY_PATH:$ORACLE_HOME
ENV PATH=$ORACLE_HOME:$PATH

# Create non-root user and set up Chrome directories
RUN useradd -ms /bin/bash appuser && \
    mkdir -p /app/.local /app/.cache /app/.config /app/downloads /app/screenshots /app/html_logs /app/vector_stores && \
    chown -R appuser:appuser /app && \
    chown root:root /usr/bin/google-chrome* && \
    chmod 755 /usr/bin/google-chrome* && \
    chmod 4755 /usr/bin/google-chrome-stable # setuid bit for sandbox

# Copy project files
COPY . /app/

# Modify legal_scraper.py to set Chrome binary path
RUN sed -i '/options = uc.ChromeOptions()/a\            # Definir explicitamente o caminho do binário do Chrome\n            options.binary_location = "/usr/bin/google-chrome"' /app/legal_scraper.py

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PATH="/usr/local/bin:$PATH"
ENV CHROME_BIN=/usr/bin/google-chrome
ENV PYTHONPATH="${PYTHONPATH}:/app"
# Flask configuration
ENV FLASK_APP=app
ENV FLASK_ENV=production
ENV FLASK_RUN_HOST=0.0.0.0
ENV FLASK_RUN_PORT=7860
# Set HOME for Chrome
ENV HOME=/app

# Create and activate virtual environment
RUN python -m venv /app/venv
ENV PATH="/app/venv/bin:$PATH"

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Setup Chrome and X11 configuration
RUN mkdir -p /opt/google/chrome && \
    mkdir -p /usr/lib/chrome && \
    mkdir -p /tmp/.X11-unix && \
    chmod 1777 /tmp/.X11-unix && \
    chown -R appuser:appuser /opt/google/chrome && \
    chown -R appuser:appuser /usr/lib/chrome && \
    # Set final permissions
    chgrp -R 0 /app && \
    chmod -R g=u /app && \
    chmod -R 777 /app/.local /app/.cache /app/.config /app/downloads /app/screenshots /app/html_logs /app/vector_stores && \
    chmod 4755 /usr/bin/chrome-sandbox || true && \
    chmod 1777 /dev/shm && \
    # Ensure X11 socket directory persists and is accessible
    chown root:root /tmp/.X11-unix && \
    chmod 1777 /tmp/.X11-unix

# Chrome environment configuration
ENV CHROME_EXECUTABLE_PATH="/usr/bin/google-chrome" \
    CHROME_BIN="/usr/bin/google-chrome" \
    DISPLAY=:99 \
    DBUS_SESSION_BUS_ADDRESS=/dev/null \
    PYTHONWARNINGS="ignore:Unverified HTTPS request" \
    SELENIUM_CHROME_ARGS="--no-sandbox --disable-dev-shm-usage --disable-gpu --headless=new --enable-automation --disable-dev-tools --no-zygote --single-process --remote-debugging-port=9222 --ignore-certificate-errors --no-default-browser-check --no-first-run --ignore-ssl-errors"

# Expose port
EXPOSE 7860

USER appuser

# Start Xvfb and run the application
CMD (Xvfb :99 -screen 0 1024x768x16 -nolisten tcp -nolisten unix & \
    sleep 1 && \
    python -c "from app import app; app.run(host='0.0.0.0', port=7860)")
