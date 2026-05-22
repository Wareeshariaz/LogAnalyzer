import os
import tempfile
import unittest
from datetime import datetime, timezone

from parser import parse_line, parse_log_file, parse_response_time, parse_timestamp, parse_status
from report import normalize_route


class ParserTests(unittest.TestCase):
    def test_parse_timestamp_formats(self):
        self.assertEqual(
            parse_timestamp('2024-03-15T14:23:01Z'),
            datetime(2024, 3, 15, 14, 23, 1, tzinfo=timezone.utc)
        )
        self.assertEqual(
            parse_timestamp('2024/03/15 14:23:01'),
            datetime(2024, 3, 15, 14, 23, 1, tzinfo=timezone.utc)
        )
        self.assertEqual(
            parse_timestamp('15-Mar-2024 14:23:01'),
            datetime(2024, 3, 15, 14, 23, 1, tzinfo=timezone.utc)
        )
        self.assertEqual(
            parse_timestamp('1710512581'),
            datetime.fromtimestamp(1710512581, timezone.utc)
        )

    def test_parse_response_time_variants(self):
        self.assertEqual(parse_response_time('142ms'), 142)
        self.assertEqual(parse_response_time('0.142s'), 142)
        self.assertEqual(parse_response_time('142'), 142)
        self.assertIsNone(parse_response_time('bad'))

    def test_parse_missing_status_and_response(self):
        entry = parse_line('2024-03-15T14:23:01Z 192.168.1.42 GET /api/users - 142ms', 1)
        self.assertIsNotNone(entry)
        self.assertEqual(entry.status, None)
        self.assertEqual(entry.response_ms, 142)
        self.assertEqual(entry.method, 'GET')
        self.assertEqual(entry.path, '/api/users')

    def test_parse_json_line(self):
        line = '{"timestamp":"2024-03-15T14:23:01Z","ip":"10.0.0.1","method":"POST","path":"/api/login","status":401,"response_time":"89ms"}'
        entry = parse_line(line, 1)
        self.assertIsNotNone(entry)
        self.assertEqual(entry.ip, '10.0.0.1')
        self.assertEqual(entry.method, 'POST')
        self.assertEqual(entry.status, 401)
        self.assertEqual(entry.response_ms, 89)

    def test_parse_status_empty_and_dash(self):
        self.assertIsNone(parse_status('-'))
        self.assertIsNone(parse_status(''))
        self.assertIsNone(parse_status(None))
        self.assertEqual(parse_status('200'), 200)

    def test_parse_log_file_blank_and_json_lines(self):
        contents = '\n'.join([
            '2024-03-15T14:23:01Z 192.168.1.42 GET /api/users 200 142ms',
            '',
            '{"timestamp":"2024-03-15T14:23:02Z","ip":"10.0.0.7","method":"POST","path":"/api/login","status":401,"response_time":"89ms"}',
            'bad line here',
        ])
        file_path = None
        try:
            with tempfile.NamedTemporaryFile('w+', delete=False, encoding='utf-8') as handle:
                file_path = handle.name
                handle.write(contents)
                handle.flush()
            result = parse_log_file(file_path)
            self.assertEqual(result.total_lines, 4)
            self.assertEqual(result.parsed_count, 2)
            self.assertEqual(result.blank_lines, 1)
            self.assertEqual(result.json_lines, 1)
            self.assertEqual(result.malformed_count, 1)
        finally:
            if file_path and os.path.exists(file_path):
                os.remove(file_path)


class ReportTests(unittest.TestCase):
    def test_normalize_route_ids(self):
        self.assertEqual(normalize_route('/api/users/12'), '/api/users/:id')
        self.assertEqual(normalize_route('/api/orders/abcdef1234'), '/api/orders/:id')
        self.assertEqual(normalize_route('/api/users'), '/api/users')


if __name__ == '__main__':
    unittest.main()
