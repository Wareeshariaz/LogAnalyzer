# LogAnalyzer

A small Python CLI tool that analyzes mixed-format server logs and prints a useful summary report.

## Run the analyzer

1. Ensure Python 3.10+ is installed.
2. Generate a sample log file:

```powershell
cd c:\Users\user\Desktop\LogAnalyzer
python .\scripts\generate_sample_logs.py sample.log --lines 500
```

3. Run the analyzer:

```powershell
python .\main.py .\sample.log
```

4. To output JSON rather than text:

```powershell
python .\main.py .\sample.log --json
```

5. To write the report to a file:

```powershell
python .\main.py .\sample.log --output report.txt
```

6. To read from stdin:

```powershell
Get-Content .\sample.log | python .\main.py -
```

## Tests

Run the built-in unit tests with:

```powershell
python -m unittest discover tests
```

## What it reports

- total lines read
- parsed entries and malformed/skipped count
- time range covered
- 2xx/4xx/5xx breakdown
- top slowest normalized routes
- top routes by error rate
- top client IP addresses

## Sample generator

The repository includes `scripts/generate_sample_logs.py` to create representative log files with:

- multiple timestamp formats
- response time variants (`ms`, `s`, plain numbers)
- missing status codes indicated by `-`
- extra quoted fields such as user agents and referrers
- JSON-formatted lines mixed in
- malformed lines and blank lines
