#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path

from parser import parse_log_file
from report import build_report

def main():
    parser = argparse.ArgumentParser(
        description='Analyze mixed-format server logs and print a summary report.'
    )
    parser.add_argument('logfile', help='Path to the log file to analyze, or - for stdin')
    parser.add_argument('--top', type=int, default=10, help='Number of top items to show')
    parser.add_argument('--json', action='store_true', help='Output report as JSON')
    parser.add_argument('--output', '-o', help='Write report to a file instead of stdout')
    args = parser.parse_args()

    result = parse_log_file(args.logfile)
    report_text = build_report(result, top_n=args.top, output_json=args.json)
    if args.output:
        Path(args.output).write_text(report_text + '\n', encoding='utf-8')
        print(f'Report written to {args.output}')
    else:
        print(report_text)

    if result.malformed_count or result.blank_lines:
        print('\nParse anomalies:')
        if result.blank_lines:
            print(f'  blank lines skipped: {result.blank_lines}')
        if result.malformed_count:
            print(f'  malformed lines skipped: {result.malformed_count}')
        for line_num, sample in result.malformed_examples:
            print(f'    {line_num}: {sample}')

if __name__ == '__main__':
    main()
