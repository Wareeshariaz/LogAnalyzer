#!/usr/bin/env python3
import argparse
import json
import random
import time
from datetime import datetime, timedelta

METHODS = ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']
PATHS = [
    '/api/users',
    '/api/users/12',
    '/api/users/42',
    '/api/login',
    '/api/orders',
    '/api/orders/234',
    '/health',
    '/metrics',
    '/api/search',
]
STATUSES = [200, 201, 204, 301, 400, 401, 403, 404, 500, 502, 503]
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
    'curl/7.86.0',
    'PostmanRuntime/7.29.0',
]
REFERERS = [
    'https://example.com/',
    'https://mobile.example.com/',
    'https://app.example.com/login',
]

TIMESTAMP_FORMATS = [
    'iso',
    'slash',
    'dashed',
    'epoch',
]


def random_timestamp(base: datetime, i: int):
    dt = base + timedelta(seconds=i * random.randint(1, 5))
    fmt = random.choice(TIMESTAMP_FORMATS)
    if fmt == 'iso':
        return dt.strftime('%Y-%m-%dT%H:%M:%SZ')
    if fmt == 'slash':
        return dt.strftime('%Y/%m/%d %H:%M:%S')
    if fmt == 'dashed':
        return dt.strftime('%d-%b-%Y %H:%M:%S')
    return str(int(dt.timestamp()))


def random_response_time():
    if random.random() < 0.2:
        return f'{random.randint(10, 150)}ms'
    if random.random() < 0.5:
        return f'{random.random():.3f}s'
    return str(random.randint(10, 500))


def random_line(base: datetime, index: int):
    if random.random() < 0.08:
        return random_malformed_line(base, index)

    if random.random() < 0.1:
        return random_json_line(base, index)

    timestamp = random_timestamp(base, index)
    ip = f'192.168.{random.randint(0, 255)}.{random.randint(0, 255)}'
    method = random.choice(METHODS)
    path = random.choice(PATHS)
    status = random.choice(STATUSES)
    if random.random() < 0.12:
        status = '-'
    response = random_response_time()
    line = f'{timestamp} {ip} {method} {path} {status} {response}'
    if random.random() < 0.25:
        line += f' "{random.choice(USER_AGENTS)}"'
    if random.random() < 0.1:
        line += f' "{random.choice(REFERERS)}"'
    if random.random() < 0.05:
        return '  ' + line
    return line


def random_json_line(base: datetime, index: int):
    timestamp = random_timestamp(base, index)
    payload = {
        'timestamp': timestamp,
        'ip': f'10.0.{random.randint(0, 255)}.{random.randint(0, 255)}',
        'method': random.choice(METHODS),
        'path': random.choice(PATHS),
        'status': random.choice(STATUSES),
        'response_time': random_response_time(),
    }
    return json.dumps(payload)


def random_malformed_line(base: datetime, index: int):
    choices = [
        'MALFORMED ENTRY',
        '2024-03-15T14:23 192.168.1.1 GET /api/users',
        'This is not a valid log line',
        'Traceback (most recent call last):',
        '',
        '2024-03-15T14:23:01Z missing fields',
    ]
    return random.choice(choices)


def write_file(path: str, lines):
    with open(path, 'w', encoding='utf-8') as handle:
        for line in lines:
            handle.write(f'{line}\n')


def main():
    parser = argparse.ArgumentParser(description='Generate representative sample server logs.')
    parser.add_argument('output', help='Output path for the generated sample log')
    parser.add_argument('--lines', type=int, default=500, help='Number of lines to generate')
    args = parser.parse_args()

    base = datetime.now() - timedelta(days=1)
    lines = [random_line(base, i) for i in range(args.lines)]
    write_file(args.output, lines)
    print(f'Generated {args.lines} sample log lines at {args.output}')


if __name__ == '__main__':
    main()
