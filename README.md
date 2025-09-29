# Scout Support

This is a separate project that provides support tools and web interface for the main S.C.O.U.T bug bounty monitoring system.

## Project Structure

```
scout-support-project/
├── deploy.py          # Web dashboard for viewing programs and subdomains
├── run-gau.py         # GAU tool runner for scanning domains
├── run-httpx.py       # HTTPX tool runner for bulk URL processing
├── requirements.txt   # Python dependencies
├── templates/         # HTML templates for web dashboard
│   ├── index.html
│   └── program_detail.html
└── scans/             # Directory for scan results
    ├── gau/
    └── httpx/
```

## Dependencies

This project depends on the main `scout` project located in the parent directory. It imports modules from `scout/src/` and uses the database configuration from `scout/config.json`.

## Setup

1. Make sure the main `scout` project is installed and configured
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Web Dashboard
```bash
python3 deploy.py
```
Access the dashboard at: http://localhost:5000

### GAU Scanner
```bash
python3 run-gau.py
```
Runs GAU tool on all domains from the scout database and saves results to `scans/gau/`

### HTTPX Scanner
```bash
python3 run-httpx.py
```
Automatically scans all `.txt` files in `scout/scans/` directory using bulk HTTPX processing.

**Command executed:**
```bash
cat "filename.txt" | httpx -sc -td -title -timeout 30 -silent -no-color
```

**Output format:**
```
https://example.com [200] [Example Title] [HSTS]
https://subdomain.example.com [301] [301 Moved Permanently] [HSTS,Varnish]
```

Results are saved to `scans/httpx/{original_filename}-httpx.txt`

## Connection to Scout Project

This project maintains connections to the scout database by:
- Importing modules from `../scout/src/`
- Using database configuration from `../scout/config.json`
- Accessing the same database tables as the main scout project

## Notes

- This project is designed to run independently while maintaining access to the scout database
- All database operations use the same configuration as the main scout project
- The web dashboard provides a user-friendly interface to view scout data
- The GAU scanner extends scout's capabilities with additional reconnaissance tools