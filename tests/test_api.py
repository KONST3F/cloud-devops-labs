import json
import os
import threading
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

os.environ.setdefault('DATABASE_URL', 'postgresql://unused')
import app


class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = app.ThreadingHTTPServer(('127.0.0.1', 0), app.Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = 'http://127.0.0.1:%d' % cls.server.server_port

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def test_health(self):
        with patch.object(app, 'query', return_value=None):
            with urlopen(self.base + '/api/health') as response:
                self.assertEqual(response.status, 200)
                self.assertEqual(json.load(response)['status'], 'ok')

    def test_add_note(self):
        with patch.object(app, 'query', return_value=[(7, 'hello')]) as query:
            request = Request(self.base + '/api/notes', data=b'{"body":"hello"}', headers={'Content-Type': 'application/json'})
            with urlopen(request) as response:
                self.assertEqual(response.status, 201)
                self.assertEqual(json.load(response)['body'], 'hello')
            self.assertEqual(query.call_args.args[1], ('hello',))

    def test_empty_note_is_rejected(self):
        request = Request(self.base + '/api/notes', data=b'{"body":""}', headers={'Content-Type': 'application/json'})
        with self.assertRaises(HTTPError) as error:
            urlopen(request)
        self.assertEqual(error.exception.code, 400)


if __name__ == '__main__':
    unittest.main()
