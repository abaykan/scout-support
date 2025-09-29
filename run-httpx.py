#!/usr/bin/env python3
"""
HTTPX Runner for S.C.O.U.T
Menjalankan tool httpx untuk semua subdomain dari database
"""

import subprocess
import os
import sys
import logging
import re
from datetime import datetime

# Add scout project directory to path for imports
scout_project_path = os.path.join(os.path.dirname(__file__), '..', 'scout')
sys.path.append(scout_project_path)

from src.db import Database

def setup_logging():
    """Setup basic logging configuration"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('scout.log'),
            logging.StreamHandler(sys.stdout)
        ]
    )

class HTTPXRunner:
    """HTTPX tool runner untuk scan semua subdomain dari database"""
    
    def __init__(self, output_dir: str = "scans/httpx"):
        self.logger = logging.getLogger(__name__)
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        self.db = Database(config_path=os.path.join(os.path.dirname(__file__), '..', 'scout', 'config.json'))
    
    def get_subdomains_from_database(self):
        """Ambil semua subdomain dari tabel subdomains"""
        try:
            # Connect to database first
            if not self.db.connect():
                self.logger.error("Failed to connect to database")
                return []
            
            cursor = self.db.connection.cursor()
            cursor.execute("SELECT subdomain FROM subdomains")
            subdomains = cursor.fetchall()
            cursor.close()
            self.db.disconnect()
            self.logger.info(f"Found {len(subdomains)} subdomains in database")
            return [subdomain[0] for subdomain in subdomains]
        except Exception as e:
            self.logger.error(f"Error getting subdomains from database: {e}")
            return []
    
    def run_httpx(self, subdomain: str):
        """Jalankan httpx untuk satu subdomain"""
        try:
            # Gunakan echo untuk pipe subdomain ke httpx
            cmd = f'echo "{subdomain}" | httpx -sc -td -title -silent'
            self.logger.info(f"Running httpx for: {subdomain}")
            
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                output = result.stdout.strip()
                if output:
                    # Parse output httpx
                    parts = output.split(' ')
                    if len(parts) >= 3:
                        url = parts[0]
                        status_code = parts[1] if parts[1].isdigit() else "N/A"
                        title = ' '.join(parts[2:]) if len(parts) > 2 else "N/A"
                        tech_detected = "N/A"  # httpx -td output format may vary
                        
                        result_data = {
                            'url': url,
                            'status_code': status_code,
                            'title': title,
                            'tech_detected': tech_detected,
                            'subdomain': subdomain
                        }
                        self.logger.info(f"HTTPX result for {subdomain}: {status_code} - {title}")
                        return result_data
                    else:
                        self.logger.warning(f"Unexpected httpx output format for {subdomain}: {output}")
                        return None
                else:
                    self.logger.info(f"No response from {subdomain}")
                    return None
            else:
                self.logger.warning(f"HTTPX failed for {subdomain}: {result.stderr}")
                return None
                
        except subprocess.TimeoutExpired:
            self.logger.error(f"HTTPX timeout for {subdomain}")
            return None
        except FileNotFoundError:
            self.logger.error("HTTPX tool not found. Install dengan: go install -v github.com/projectdiscovery/httpx/cmd/httpx@latest")
            return None
        except Exception as e:
            self.logger.error(f"Error running HTTPX for {subdomain}: {e}")
            return None

    def run_httpx_bulk_file(self, input_file: str, output_file: str = None):
        """Jalankan httpx untuk file input secara bulk"""
        try:
            if not os.path.exists(input_file):
                self.logger.error(f"Input file not found: {input_file}")
                return False
            
            # Jika output_file tidak ditentukan, buat nama file otomatis
            if not output_file:
                base_name = os.path.splitext(os.path.basename(input_file))[0]
                output_file = os.path.join(self.output_dir, f"{base_name}-httpx.txt")
            
            # Jalankan command: cat file.txt | httpx -sc -td -title -timeout 10 -silent -no-color
            cmd = f'cat "{input_file}" | httpx -sc -td -title -timeout 30 -silent -no-color'
            self.logger.info(f"Running bulk httpx for file: {input_file}")
            
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                output = result.stdout.strip()
                if output:
                    # Simpan hasil langsung ke file output
                    with open(output_file, 'w', encoding='utf-8') as f:
                        f.write(output + '\n')
                    
                    self.logger.info(f"Bulk httpx completed. Results saved to: {output_file}")
                    self.logger.info(f"Output preview:\n{output}")
                    return True
                else:
                    self.logger.warning(f"No results from bulk httpx for file: {input_file}")
                    return False
            else:
                self.logger.error(f"Bulk httpx failed for file {input_file}: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            self.logger.error(f"Bulk httpx timeout for file: {input_file}")
            return False
        except FileNotFoundError:
            self.logger.error("HTTPX tool not found. Install dengan: go install -v github.com/projectdiscovery/httpx/cmd/httpx@latest")
            return False
        except Exception as e:
            self.logger.error(f"Error running bulk httpx for file {input_file}: {e}")
            return False
    
    def save_results(self, results: list, program_name: str):
        """Simpan hasil ke file dengan pola penamaan yang konsisten"""
        if not results:
            self.logger.warning(f"No results found for {program_name}, skipping")
            return
        
        # Buat slug dari program_name (mirip dengan file yang sudah ada)
        slug = program_name.lower().replace(' ', '-').replace('_', '-')
        filename = f"{slug}-httpx.txt"
        filepath = os.path.join(self.output_dir, filename)
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write("URL\tStatus Code\tTitle\tTech Detected\tSubdomain\n")
                for result in results:
                    if result:
                        f.write(f"{result['url']}\t{result['status_code']}\t{result['title']}\t{result['tech_detected']}\t{result['subdomain']}\n")
            
            self.logger.info(f"Saved {len(results)} results to {filepath}")
            
        except Exception as e:
            self.logger.error(f"Error saving results for {program_name}: {e}")
    
    def run_all_subdomains(self):
        """Jalankan httpx untuk semua subdomain dari database"""
        subdomains = self.get_subdomains_from_database()
        
        if not subdomains:
            self.logger.error("No subdomains found in database")
            return
        
        # Group subdomains by program untuk organized output
        programs_results = self.group_subdomains_by_program(subdomains)
        
        total_results = 0
        for program_name, program_subdomains in programs_results.items():
            program_results = []
            for subdomain in program_subdomains:
                result = self.run_httpx(subdomain)
                if result:
                    program_results.append(result)
            
            self.save_results(program_results, program_name)
            total_results += len(program_results)
        
        self.logger.info(f"HTTPX scanning completed. Total results found: {total_results}")
    
    def group_subdomains_by_program(self, subdomains: list):
        """Group subdomains berdasarkan program mereka"""
        programs_results = {}
        
        for subdomain in subdomains:
            # Extract program name dari subdomain
            program_name = self.extract_program_name(subdomain)
            if program_name not in programs_results:
                programs_results[program_name] = []
            programs_results[program_name].append(subdomain)
        
        return programs_results
    
    def extract_program_name(self, subdomain: str) -> str:
        """Extract program name dari subdomain"""
        try:
            # Remove TLD dan subdomain parts untuk mendapatkan program name
            parts = subdomain.split('.')
            if len(parts) >= 2:
                # Ambil domain utama (biasanya bagian kedua dari belakang)
                main_domain = parts[-2]
                return main_domain
            return "unknown"
        except Exception as e:
            self.logger.warning(f"Error extracting program name from {subdomain}: {e}")
            return "unknown"

def main():
    """Main entry point - automatically scan all .txt files in scout/scans directory"""
    setup_logging()
    logger = logging.getLogger(__name__)
    
    # Path to scout/scans directory
    scout_scans_path = os.path.join(os.path.dirname(__file__), '..', 'scout', 'scans')
    
    if not os.path.exists(scout_scans_path):
        logger.error(f"Scout scans directory not found: {scout_scans_path}")
        sys.exit(1)
    
    try:
        runner = HTTPXRunner()
        processed_count = 0
        
        # Find all .txt files in scout/scans directory
        for root, dirs, files in os.walk(scout_scans_path):
            for file in files:
                if file.endswith('.txt'):
                    input_file = os.path.join(root, file)
                    logger.info(f"Processing file: {input_file}")
                    
                    # Process file with bulk httpx
                    success = runner.run_httpx_bulk_file(input_file)
                    if success:
                        processed_count += 1
                        logger.info(f"Successfully processed: {file}")
                    else:
                        logger.error(f"Failed to process: {file}")
        
        logger.info(f"Bulk httpx processing completed. Processed {processed_count} files.")
        
    except KeyboardInterrupt:
        logger.info("HTTPX runner stopped by user")
    except Exception as e:
        logger.error(f"HTTPX runner error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()