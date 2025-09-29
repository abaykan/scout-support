# Scout Support

This is a separate project that provides support tools and web interface for the main S.C.O.U.T bug bounty monitoring system.

## Project Structure

```
scout-support/
├── deploy.py                    # Web dashboard for viewing programs and subdomains
├── run-gau.py                   # GAU tool runner for scanning domains
├── run-httpx.py                 # HTTPX tool runner for bulk URL processing
├── requirements.txt             # Python dependencies
├── scout.log                    # Application logs
├── .gitignore                   # Git ignore rules
├── templates/                   # HTML templates for web dashboard
│   ├── index.html
│   ├── program_detail.html
│   ├── httpx_program_detail.html
│   └── httpx_results.html
└── scans/                       # Directory for scan results
    ├── gau/                     # GAU scan results
    └── httpx/                   # HTTPX scan results
```

## Dependencies

This project depends on the main `scout` project located in the parent directory. It imports modules from `scout/src/` and uses the database configuration from `scout/config.json`.

### Python Dependencies

- Flask 2.3.3 - Web framework for the dashboard
- mysql-connector-python 8.1.0 - MySQL database connectivity
- requests 2.31.0 - HTTP library for API calls

## Setup

1. Make sure the main `scout` project is installed and configured
2. Install Python dependencies:
   ```bash
   pip3 install -r requirements.txt
   ```
3. Ensure the main scout project database is properly configured

## Usage

### Web Dashboard
```bash
python3 deploy.py
```
Access the dashboard at: http://localhost:5000

The dashboard provides:
- Overview of all bug bounty programs
- Detailed program information with subdomains
- HTTPX scan results visualization
- Real-time status monitoring

### GAU Scanner
```bash
python3 run-gau.py
```
Runs GAU (Get All URLs) tool on all domains from the scout database and saves results to `scans/gau/`

Features:
- Automatically processes all domains from the scout database
- Generates comprehensive URL lists for each program
- Saves results in individual program files

### HTTPX Scanner
```bash
python3 run-httpx.py
```
Automatically scans all `.txt` files in `scans/gau/` directory using bulk HTTPX processing.

**Command executed:**
```bash
cat "filename.txt" | httpx -sc -td -title -timeout 30 -silent -no-color
```

**Output format:**
```
https://example.com [200] [Example Title] [HSTS]
https://subdomain.example.com [301] [301 Moved Permanently] [HSTS,Varnish]
```

**Features:**
- Processes GAU scan results automatically
- Performs HTTP status code checking
- Extracts page titles and technologies
- Saves results to `scans/httpx/{original_filename}-httpx.txt`

## Connection to Scout Project

This project maintains connections to the scout database by:
- Importing modules from `../scout/src/`
- Using database configuration from `../scout/config.json`
- Accessing the same database tables as the main scout project
- Sharing the same database schema and data

## Features

- **Web Dashboard**: User-friendly interface to browse bug bounty programs and scan results
- **GAU Integration**: Automated URL discovery using Get All URLs tool
- **HTTPX Scanning**: Bulk HTTP probing with detailed response analysis

## Notes

- This project is designed to run independently while maintaining access to the scout database
- All database operations use the same configuration as the main scout project
- The web dashboard provides a user-friendly interface to view scout data
- The GAU scanner extends scout's capabilities with additional reconnaissance tools
- HTTPX scanning provides detailed HTTP response analysis for discovered URLs
- Scan results are organized by program for easy reference and analysis