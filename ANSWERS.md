# ANSWERS

## 1. How to run

1. Install Python 3.10 or later.
2. Open a terminal in `c:\Users\user\Desktop\LogAnalyzer`.
3. Generate a sample log file:

```powershell
python .\scripts\generate_sample_logs.py sample.log --lines 500
```

4. Run the analyzer:

```powershell
python .\main.py .\sample.log
```

5. Optional JSON report:

```powershell
python .\main.py .\sample.log --json
```

## 2. Stack choice

I chose Python because it is ideal for CLI tooling, text processing, and quick delivery with no external dependencies. Python's standard library supports robust parsing, JSON, and date handling, making it a practical choice for a log analyzer.

A worse choice would have been a heavy web stack like React/Node or a desktop GUI framework, because that would add unnecessary installation overhead, slow development, and distract from the core job of safely parsing arbitrary log files.

## 3. One real edge case handled

The parser handles lines where the status code is missing or replaced with `-`, and response time still appears later on the same line. This is implemented in `parser.py` around lines 91-94 in the `parse_line` function.

Without that handling, a line like:

```
2024-03-15T14:23:01Z 192.168.1.42 GET /api/users - 142ms
```

would fail to parse and be counted as malformed instead of contributing a parsed request.

## 4. AI usage

- Used GitHub Copilot chat (Raptor mini preview) to design the CLI and parser structure.
- Asked for a robust Python parser strategy for mixed-format logs and got a shlex/tokenize + JSON fallback pattern.
- Asked for a readable report layout and got the summary/error-rate/top-slowest route idea.

I changed the AI output by tightening the parse logic around missing status tokens and by ensuring malformed lines were skipped gracefully with a visible count.

## 5. Honest gap

The submission now includes an automated unit test suite under `tests/`. It validates parser edge cases such as multiple timestamp formats, JSON lines, missing status values, and route normalization.
