import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import psycopg

ROOT = Path(__file__).resolve().parent
DATABASE_URL = os.environ.get('DATABASE_URL')
if not DATABASE_URL:
    raise RuntimeError('Set DATABASE_URL before starting the application')
INSTANCE = os.environ.get('INSTANCE_ID', 'local')
PORT = int(os.environ.get('PORT', '18081'))
BIND_HOST = os.environ.get('BIND_HOST', '127.0.0.1')


def query(sql, params=(), *, rows=False):
    with psycopg.connect(DATABASE_URL, autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            return cursor.fetchall() if rows else None


class Handler(BaseHTTPRequestHandler):
    def respond(self, status, payload, content_type='application/json; charset=utf-8'):
        data = payload if isinstance(payload, bytes) else json.dumps(payload, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(data)))
        self.send_header('X-Backend-Instance', INSTANCE)
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path == '/':
            self.respond(200, (ROOT / 'index.html').read_bytes(), 'text/html; charset=utf-8')
        elif self.path == '/api/notes':
            try:
                notes = query('SELECT id, body FROM notes ORDER BY id DESC', rows=True)
                self.respond(200, {'notes': [{'id': i, 'body': body} for i, body in notes], 'instance': INSTANCE})
            except psycopg.Error:
                self.respond(503, {'error': 'База данных недоступна'})
        elif self.path == '/api/health':
            try:
                query('SELECT 1')
                self.respond(200, {'status': 'ok', 'instance': INSTANCE})
            except psycopg.Error:
                self.respond(503, {'error': 'База данных недоступна'})
        else:
            self.respond(404, {'error': 'Не найдено'})

    def do_POST(self):
        if self.path != '/api/notes':
            self.respond(404, {'error': 'Не найдено'})
            return
        try:
            size = int(self.headers.get('Content-Length', '0'))
            if size < 1 or size > 4096:
                raise ValueError('Неверный размер запроса')
            data = json.loads(self.rfile.read(size))
            body = data.get('body', '').strip()
            if not isinstance(body, str) or not 1 <= len(body) <= 500:
                raise ValueError('Введите текст до 500 символов')
            result = query('INSERT INTO notes (body) VALUES (%s) RETURNING id, body', (body,), rows=True)
            self.respond(201, {'id': result[0][0], 'body': result[0][1]})
        except (ValueError, TypeError, AttributeError, json.JSONDecodeError):
            self.respond(400, {'error': 'Нужен текст длиной от 1 до 500 символов'})
        except psycopg.Error:
            self.respond(503, {'error': 'База данных недоступна'})


if __name__ == '__main__':
    query('CREATE TABLE IF NOT EXISTS notes (id BIGSERIAL PRIMARY KEY, body VARCHAR(500) NOT NULL)')
    print(f'Server listening at http://127.0.0.1:{PORT}', flush=True)
    ThreadingHTTPServer((BIND_HOST, PORT), Handler).serve_forever()
