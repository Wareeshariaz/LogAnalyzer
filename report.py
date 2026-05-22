from __future__ import annotations
import re
from collections import Counter
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional

from parser import LogEntry, ParseResult


@dataclass
class RouteStats:
    count: int = 0
    total_ms: int = 0
    max_ms: int = 0
    errors: int = 0
    statuses: Dict[int, int] = None

    def __post_init__(self):
        if self.statuses is None:
            self.statuses = {}

    def add(self, entry: LogEntry) -> None:
        self.count += 1
        if entry.response_ms is not None:
            self.total_ms += entry.response_ms
            self.max_ms = max(self.max_ms, entry.response_ms)
        if entry.status is not None and entry.status >= 400:
            self.errors += 1
        if entry.status is not None:
            self.statuses[entry.status] = self.statuses.get(entry.status, 0) + 1

    @property
    def average_ms(self) -> Optional[float]:
        if self.count == 0 or self.total_ms == 0:
            return None
        return self.total_ms / self.count

    @property
    def error_rate(self) -> float:
        return self.errors / self.count if self.count else 0.0


def build_report(result: ParseResult, top_n: int = 10, output_json: bool = False) -> str:
    if output_json:
        return build_json_report(result, top_n)
    return build_text_report(result, top_n)


def build_text_report(result: ParseResult, top_n: int = 10) -> str:
    lines: List[str] = []
    lines.append('LOG ANALYSIS REPORT')
    lines.append('===================')
    lines.append(f'Total lines read: {result.total_lines}')
    lines.append(f'Parsed entries: {result.parsed_count}')
    lines.append(f'Blank lines skipped: {result.blank_lines}')
    lines.append(f'JSON lines parsed: {result.json_lines}')
    lines.append(f'Malformed/skipped lines: {result.malformed_count}')

    if result.entries:
        lines.append('')
        lines.extend(summary_lines(result))
        lines.append('')
        lines.extend(route_lines(result.entries, top_n))
        lines.append('')
        lines.extend(ip_lines(result.entries, top_n))
    else:
        lines.append('')
        lines.append('No parsed entries could be extracted from the log file.')

    return '\n'.join(lines)


def build_json_report(result: ParseResult, top_n: int = 10) -> str:
    import json
    summary = {
        'total_lines': result.total_lines,
        'parsed_entries': result.parsed_count,
        'blank_lines': result.blank_lines,
        'json_lines': result.json_lines,
        'malformed_lines': result.malformed_count,
        'top_slowest_routes': [],
        'top_error_routes': [],
        'top_client_ips': []
    }
    route_counts = route_stats(result.entries)
    summary['top_slowest_routes'] = [
        {
            'route': route,
            'average_response_ms': stats.average_ms,
            'max_response_ms': stats.max_ms,
            'count': stats.count,
            'error_rate': round(stats.error_rate, 3)
        }
        for route, stats in sorted(route_counts.items(), key=lambda item: (item[1].average_ms or 0), reverse=True)[:top_n]
    ]
    summary['top_error_routes'] = [
        {
            'route': route,
            'error_rate': round(stats.error_rate, 3),
            'count': stats.count,
            'errors': stats.errors
        }
        for route, stats in sorted(route_counts.items(), key=lambda item: item[1].error_rate, reverse=True)[:top_n]
        if stats.count >= 5
    ]
    ip_counts = Counter(entry.ip for entry in result.entries)
    summary['top_client_ips'] = [{'ip': ip, 'requests': count} for ip, count in ip_counts.most_common(top_n)]
    return json.dumps(summary, indent=2)


def summary_lines(result: ParseResult) -> List[str]:
    first = min(entry.timestamp for entry in result.entries)
    last = max(entry.timestamp for entry in result.entries)
    status_counts = Counter((entry.status if entry.status is not None else 'unknown') for entry in result.entries)
    good = sum(count for status, count in status_counts.items() if isinstance(status, int) and 200 <= status < 300)
    client = sum(count for status, count in status_counts.items() if isinstance(status, int) and 400 <= status < 500)
    server = sum(count for status, count in status_counts.items() if isinstance(status, int) and 500 <= status < 600)
    unknown = status_counts.get('unknown', 0)
    lines: List[str] = [
        f'Period: {first.isoformat()} to {last.isoformat()}',
        f'Total parsed requests: {result.parsed_count}',
        f'2xx successes: {good}',
        f'4xx client errors: {client}',
        f'5xx server errors: {server}',
        f'Unknown status count: {unknown}',
        f'Top status codes:'
    ]
    for status, count in status_counts.most_common(6):
        label = str(status) if status != 'unknown' else 'unknown'
        lines.append(f'  {label}: {count}')
    return lines


def route_stats(entries: Iterable[LogEntry]) -> Dict[str, RouteStats]:
    stats: Dict[str, RouteStats] = {}
    for entry in entries:
        route = normalize_route(entry.path)
        bucket = stats.setdefault(route, RouteStats())
        bucket.add(entry)
    return stats


def normalize_route(path: str) -> str:
    normalized = re.sub(r'/\d+\b', '/:id', path)
    normalized = re.sub(r'/[0-9a-fA-F]{8,}\b', '/:id', normalized)
    return normalized


def route_lines(entries: Iterable[LogEntry], top_n: int) -> List[str]:
    stats = route_stats(entries)
    sorted_by_avg = sorted(stats.items(), key=lambda item: (item[1].average_ms or 0), reverse=True)
    lines: List[str] = ['Top slowest routes:']
    for route, route_stat in sorted_by_avg[:top_n]:
        avg = f'{route_stat.average_ms:.0f}ms' if route_stat.average_ms is not None else 'n/a'
        lines.append(f'  {route}: avg={avg}, max={route_stat.max_ms}ms, count={route_stat.count}, error_rate={route_stat.error_rate:.2%}')

    sorted_by_errors = sorted(stats.items(), key=lambda item: item[1].error_rate, reverse=True)
    lines.append('')
    lines.append('Top routes by error rate (min 5 requests):')
    for route, route_stat in sorted_by_errors[:top_n]:
        if route_stat.count < 5:
            continue
        lines.append(f'  {route}: {route_stat.errors}/{route_stat.count} errors ({route_stat.error_rate:.2%})')
    return lines


def ip_lines(entries: Iterable[LogEntry], top_n: int) -> List[str]:
    ip_counts = Counter(entry.ip for entry in entries)
    lines = ['Top client IP addresses:']
    for ip, count in ip_counts.most_common(top_n):
        lines.append(f'  {ip}: {count}')
    return lines
