FROM python:3.12.8-slim-bookworm AS dependencies
WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.12.8-slim-bookworm
RUN useradd --system --create-home app
WORKDIR /app
COPY --from=dependencies /install /usr/local
COPY app.py index.html ./
USER app
ENV PORT=8000 BIND_HOST=0.0.0.0
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=3s --retries=3 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=2)"
CMD ["python", "app.py"]
