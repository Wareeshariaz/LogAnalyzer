from __future__ import annotations
import json
import re
import shlex
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Tuple

ISO_REGEX = re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$')
TIME_REGEX = re.compile(r'^\d{2}:\d{2}:\d{2}(?:\.\d+)?$')
UNIX_EPOCH_REGEX = re.compile(r'^\d{10}(?:\d{3})?$')
RESPONSE_TIME_REGEX = re.compile(r'^(?P<value>\d+(?:\.\d+)?)(?P<unit>ms|s)?$')

@dataclass
class LogEntry:
    timestamp: datetime
    ip: str
    method: str
    path: str
    status: Optional[int]
    response_ms: Optional[int]
    raw_line: str
    line_number: int

@dataclass
class ParseResult:
    entries: List[LogEntry]
    total_lines: int
    malformed_count: int
    blank_lines: int
    json_lines: int
    malformed_examples: List[Tuple[int, str]]

    @property
    def parsed_count(self) -> int:
        return len(self.entries)


def parse_log_file(path: str) -> ParseResult:
    entries: List[LogEntry] = []
    malformed_examples: List[Tuple[int, str]] = []
    total_lines = 0
    blank_lines = 0
    json_lines = 0

    if path == '-':
        handle = sys.stdin
        close_handle = False
    else:
        handle = Path(path).open('r', encoding='utf-8', errors='replace')
        close_handle = True

    try:
        for line_number, raw_line in enumerate(handle, start=1):
            total_lines += 1
            if not raw_line.strip():
                blank_lines += 1
                continue
            if raw_line.lstrip().startswith('{'):
                json_entry = parse_json_line(raw_line.strip())
                if json_entry:
                    json_entry.line_number = line_number
                    json_entry.raw_line = raw_line.rstrip('\n')
                    entries.append(json_entry)
                    json_lines += 1
                    continue
            entry = parse_line(raw_line, line_number)
            if entry is None:
                if len(malformed_examples) < 20:
                    malformed_examples.append((line_number, raw_line.strip()))
                continue
            entries.append(entry)
    finally:
        if close_handle:
            handle.close()

    malformed_count = total_lines - len(entries) - blank_lines
    return ParseResult(
        entries=entries,
        total_lines=total_lines,
        malformed_count=malformed_count,
        blank_lines=blank_lines,
        json_lines=json_lines,
        malformed_examples=malformed_examples,
    )


def parse_line(raw_line: str, line_number: int = 0) -> Optional[LogEntry]:
    text = raw_line.strip()
    if not text:
        return None

    candidate = text
    if candidate.startswith('{'):
        json_entry = parse_json_line(candidate)
        if json_entry:
            json_entry.line_number = line_number
            json_entry.raw_line = raw_line.rstrip('\n')
            return json_entry

    tokens = tokenize_line(candidate)
    if not tokens:
        return None

    timestamp_tokens = extract_timestamp_tokens(tokens)
    if not timestamp_tokens:
        return None

    idx = len(timestamp_tokens)
    if len(tokens) <= idx + 2:
        return None

    ip = tokens[idx]
    method = tokens[idx + 1]
    path = tokens[idx + 2]
    status = None
    response_raw = None

    if len(tokens) > idx + 3:
        candidate_status = tokens[idx + 3]
        if is_response_time_like(candidate_status):
            response_raw = candidate_status
        else:
            status = parse_status(candidate_status)
            if len(tokens) > idx + 4:
                response_raw = tokens[idx + 4]

    if response_raw is None and len(tokens) > idx + 4:
        response_raw = tokens[idx + 4]

    timestamp = parse_timestamp(' '.join(timestamp_tokens))
    if timestamp is None:
        return None

    response_ms = parse_response_time(response_raw) if response_raw else None
    return LogEntry(timestamp=timestamp, ip=ip, method=method, path=path, status=status, response_ms=response_ms, raw_line=raw_line.rstrip('\n'), line_number=line_number)


def tokenize_line(line: str) -> List[str]:
    try:
        return shlex.split(line)
    except ValueError:
        # Fall back to simple whitespace split when quoting is malformed.
        return line.split()


def extract_timestamp_tokens(tokens: Sequence[str]) -> List[str]:
    if not tokens:
        return []

    if UNIX_EPOCH_REGEX.match(tokens[0]) or ISO_REGEX.match(tokens[0]):
        return [tokens[0]]

    if len(tokens) > 1 and TIME_REGEX.match(tokens[1]):
        return [tokens[0], tokens[1]]

    return [tokens[0]]


def parse_json_line(candidate: str) -> Optional[LogEntry]:
    try:
        data = json.loads(candidate)
    except json.JSONDecodeError:
        return None

    timestamp = None
    for key in ('timestamp', 'time', 'ts', 'date'):
        if key in data:
            timestamp = parse_timestamp(str(data[key]))
            if timestamp:
                break

    ip = data.get('ip') or data.get('remote_addr') or data.get('client')
    method = data.get('method') or data.get('verb')
    path = data.get('path') or data.get('uri') or data.get('request')
    status = parse_status(data.get('status') or data.get('status_code'))
    response_raw = data.get('response_time') or data.get('duration') or data.get('latency')

    if not all([timestamp, ip, method, path]):
        return None

    response_ms = parse_response_time(str(response_raw)) if response_raw is not None else None
    return LogEntry(timestamp=timestamp, ip=str(ip), method=str(method), path=str(path), status=status, response_ms=response_ms, raw_line=candidate, line_number=0)


def parse_timestamp(raw: str) -> Optional[datetime]:
    raw = raw.strip()
    if not raw:
        return None

    if ISO_REGEX.match(raw):
        try:
            return datetime.strptime(raw, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)
        except ValueError:
            pass

    if UNIX_EPOCH_REGEX.match(raw):
        seconds = int(raw) / (1000 if len(raw) == 13 else 1)
        return datetime.fromtimestamp(seconds, timezone.utc)

    for fmt in ('%Y/%m/%d %H:%M:%S', '%d-%b-%Y %H:%M:%S', '%Y-%m-%d %H:%M:%S'):
        try:
            return datetime.strptime(raw, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue

    return None


def parse_response_time(raw: Optional[str]) -> Optional[int]:
    if raw is None:
        return None
    candidate = str(raw).strip()
    if not candidate:
        return None

    match = RESPONSE_TIME_REGEX.match(candidate)
    if not match:
        return None

    value = float(match.group('value'))
    unit = match.group('unit') or 'ms'
    if unit == 's':
        return int(value * 1000)
    return int(value)


def is_response_time_like(text: str) -> bool:
    return bool(RESPONSE_TIME_REGEX.match(text))


def parse_status(value: Optional[object]) -> Optional[int]:
    if value is None:
        return None
    text = str(value).strip()
    if text in ('', '-', 'None'):
        return None
    try:
        return int(text)
    except ValueError:
        return None
