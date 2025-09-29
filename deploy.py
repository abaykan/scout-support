#!/usr/bin/env python3
"""
S.C.O.U.T Web Dashboard
Web interface for viewing bug bounty program and subdomain data
"""

import os
import sys

# Add scout project directory to path for imports
scout_project_path = os.path.join(os.path.dirname(__file__), '..', 'scout')
sys.path.append(scout_project_path)

from flask import Flask, render_template, jsonify
from src.db import Database

app = Flask(__name__, template_folder='templates')

def get_database_data():
    """Fetch data from database"""
    try:
        db = Database(config_path=os.path.join(os.path.dirname(__file__), '..', 'scout', 'config.json'))
        if not db.connect():
            return None, None
        
        # Get programs data
        programs = db.execute_query("""
            SELECT id, platform, program_name, program_url, scope, 
                   last_checked, published_at, created_at
            FROM programs 
            ORDER BY last_checked DESC
        """)
        
        # Get subdomains data
        subdomains = db.execute_query("""
            SELECT subdomain, source, first_seen, last_seen, is_new
            FROM subdomains 
            ORDER BY last_seen DESC
        """)
        
        db.disconnect()
        return programs, subdomains
        
    except Exception as e:
        print(f"Database error: {e}")
        return None, None

def get_program_subdomains(program_name):
    """Get subdomains related to a specific program"""
    try:
        db = Database(config_path=os.path.join(os.path.dirname(__file__), '..', 'scout', 'config.json'))
        if not db.connect():
            return []
        
        # Find subdomains that have this program as their source
        subdomains = db.execute_query("""
            SELECT subdomain, source, first_seen, last_seen, is_new
            FROM subdomains
            WHERE source = %s
            ORDER BY last_seen DESC
        """, (program_name,))
        
        db.disconnect()
        return subdomains or []
        
    except Exception as e:
        print(f"Error getting program subdomains: {e}")
        return []

@app.route('/')
def index():
    """Main dashboard page"""
    programs, subdomains = get_database_data()
    
    return render_template('index.html', 
                         programs=programs or [],
                         subdomains=subdomains or [])

@app.route('/program/<program_name>')
def program_detail(program_name):
    """Program detail page showing subdomains"""
    try:
        db = Database(config_path=os.path.join(os.path.dirname(__file__), '..', 'scout', 'config.json'))
        if not db.connect():
            return "Database connection failed", 500
        
        # Get program details
        programs = db.execute_query("""
            SELECT id, platform, program_name, program_url, scope, 
                   last_checked, published_at, created_at
            FROM programs 
            WHERE program_name = %s
        """, (program_name,))
        
        if not programs:
            return "Program not found", 404
        
        program = programs[0]
        subdomains = get_program_subdomains(program_name)
        
        db.disconnect()
        
        return render_template('program_detail.html', 
                             program=program,
                             subdomains=subdomains)
        
    except Exception as e:
        return f"Error: {e}", 500

@app.route('/api/programs')
def api_programs():
    """API endpoint for programs data"""
    programs, _ = get_database_data()
    return jsonify(programs or [])

@app.route('/api/subdomains')
def api_subdomains():
    """API endpoint for subdomains data"""
    _, subdomains = get_database_data()
    return jsonify(subdomains or [])

@app.route('/api/program/<program_name>/subdomains')
def api_program_subdomains(program_name):
    """API endpoint for program-specific subdomains"""
    subdomains = get_program_subdomains(program_name)
    return jsonify(subdomains or [])

@app.route('/api/stats')
def api_stats():
    """API endpoint for statistics"""
    try:
        db = Database(config_path=os.path.join(os.path.dirname(__file__), '..', 'scout', 'config.json'))
        if not db.connect():
            return jsonify({"error": "Database connection failed"})
        
        # Get program count by platform
        platform_stats = db.execute_query("""
            SELECT platform, COUNT(*) as count
            FROM programs
            GROUP BY platform
        """)
        
        # Get total programs and subdomains
        total_programs = db.execute_query("SELECT COUNT(*) as count FROM programs")[0]['count']
        total_subdomains = db.execute_query("SELECT COUNT(*) as count FROM subdomains")[0]['count']
        
        # Get new subdomains (last 24 hours)
        new_subdomains = db.execute_query("""
            SELECT COUNT(*) as count
            FROM subdomains
            WHERE is_new = TRUE
        """)[0]['count']
        
        db.disconnect()
        
        stats = {
            "total_programs": total_programs,
            "total_subdomains": total_subdomains,
            "new_subdomains": new_subdomains,
            "platforms": platform_stats or []
        }
        
        return jsonify(stats)
        
    except Exception as e:
        return jsonify({"error": str(e)})
        
def get_httpx_results():
    """Get all httpx scan results from scans/httpx directory"""
    httpx_results = []
    httpx_dir = os.path.join(os.path.dirname(__file__), 'scans', 'httpx')
    
    if not os.path.exists(httpx_dir):
        return httpx_results
    
    try:
        for filename in os.listdir(httpx_dir):
            if filename.endswith('-httpx.txt'):
                filepath = os.path.join(httpx_dir, filename)
                program_name = filename.replace('-httpx.txt', '')
                
                with open(filepath, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    for line in lines:
                        line = line.strip()
                        if line and not line.startswith('URL'):
                            # Parse httpx output format: https://example.com [200] [Title] [Tech]
                            parts = line.split(' [')
                            if len(parts) >= 3:
                                url = parts[0].strip()
                                status_code = parts[1].replace(']', '').strip()
                                title = parts[2].replace(']', '').strip()
                                tech = parts[3].replace(']', '').strip() if len(parts) > 3 else ""
                                
                                httpx_results.append({
                                    'program': program_name,
                                    'url': url,
                                    'status_code': status_code,
                                    'title': title,
                                    'tech': tech,
                                    'source_file': filename
                                })
        
        return httpx_results
    except Exception as e:
        print(f"Error reading httpx results: {e}")
        return []

@app.route('/httpx')
def httpx_results():
    """Page showing all httpx scan results"""
    results = get_httpx_results()
    
    # Group results by program
    programs_results = {}
    for result in results:
        program = result['program']
        if program not in programs_results:
            programs_results[program] = []
        programs_results[program].append(result)
    
    return render_template('httpx_results.html',
                         programs_results=programs_results,
                         total_results=len(results))

@app.route('/api/httpx')
def api_httpx():
    """API endpoint for httpx results"""
    results = get_httpx_results()
    return jsonify(results)

@app.route('/httpx/<program_name>')
def httpx_program_detail(program_name):
    """Page showing httpx scan results for specific program"""
    results = get_httpx_results()
    
    # Filter results for specific program
    program_results = [result for result in results if result['program'] == program_name]
    
    return render_template('httpx_program_detail.html',
                         program_name=program_name,
                         results=program_results,
                         total_results=len(program_results))

@app.route('/api/httpx/<program_name>')
def api_httpx_program(program_name):
    """API endpoint for program-specific httpx results"""
    results = get_httpx_results()
    program_results = [result for result in results if result['program'] == program_name]
    return jsonify(program_results)

@app.route('/api/httpx/stats')
def api_httpx_stats():
    """API endpoint for httpx statistics"""
    results = get_httpx_results()
    
    if not results:
        return jsonify({"error": "No httpx results found"})
    
    # Calculate statistics
    status_codes = {}
    tech_count = {}
    program_count = {}
    
    for result in results:
        # Status code stats
        status_code = result['status_code']
        status_codes[status_code] = status_codes.get(status_code, 0) + 1
        
        # Technology stats
        tech = result['tech']
        if tech:
            tech_count[tech] = tech_count.get(tech, 0) + 1
        
        # Program stats
        program = result['program']
        program_count[program] = program_count.get(program, 0) + 1
    
    stats = {
        "total_urls": len(results),
        "status_codes": status_codes,
        "technologies": tech_count,
        "programs": program_count,
        "unique_programs": len(program_count)
    }
    
    return jsonify(stats)

if __name__ == '__main__':
    print("🚀 Starting S.C.O.U.T Web Dashboard...")
    print("📊 Dashboard available at: http://localhost:5000")
    print("🔍 Program detail pages available at: /program/<program_name>")
    print("🔬 HTTPX results available at: /httpx")
    print("🛑 Press Ctrl+C to stop the server")
    
    app.run(debug=True, host='0.0.0.0', port=5000)