FROM python:3.13-slim

WORKDIR /app

# Instala o uv a partir da imagem oficial
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copia os arquivos de dependências e instala (sem dev)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Copia o código-fonte
COPY src/ ./src/

EXPOSE 8501

CMD ["uv", "run", "streamlit", "run", "src/app/main.py", \
     "--server.address=0.0.0.0", \
     "--server.port=8501", \
     "--server.headless=true"]
