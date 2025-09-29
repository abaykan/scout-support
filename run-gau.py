#!/usr/bin/env python3
"""
GAU Runner for S.C.O.U.T
Menjalankan tool gau untuk semua domain dari tabel subdomains
"""

import subprocess
import os
import sys
import logging
import re
from datetime import datetime
from urllib.parse import urlparse, parse_qs, unquote

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

class GAURunner:
    """GAU tool runner untuk scan semua domain dari database"""
    
    def __init__(self, output_dir: str = "scans/gau"):
        self.logger = logging.getLogger(__name__)
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        self.db = Database(config_path=os.path.join(os.path.dirname(__file__), '..', 'scout', 'config.json'))
    
    def get_programs_from_database(self):
        """Ambil semua program dari tabel programs"""
        try:
            # Connect to database first
            if not self.db.connect():
                self.logger.error("Failed to connect to database")
                return []
            
            cursor = self.db.connection.cursor()
            cursor.execute("SELECT program_name, program_url FROM programs")
            programs = cursor.fetchall()
            cursor.close()
            self.db.disconnect()
            self.logger.info(f"Found {len(programs)} programs in database")
            return programs
        except Exception as e:
            self.logger.error(f"Error getting programs from database: {e}")
            return []
    
    def run_gau(self, domain: str):
        """Jalankan gau untuk satu domain"""
        try:
            cmd = ['gau', domain]
            self.logger.info(f"Running gau for: {domain}")
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                urls = [line.strip() for line in result.stdout.split('\n') if line.strip()]
                self.logger.info(f"Found {len(urls)} URLs for {domain}")
                return urls
            else:
                self.logger.warning(f"GAU failed for {domain}: {result.stderr}")
                return []
                
        except subprocess.TimeoutExpired:
            self.logger.error(f"GAU timeout for {domain}")
            return []
        except FileNotFoundError:
            self.logger.error("GAU tool not found. Install dengan: go install github.com/lc/gau/v2/cmd/gau@latest")
            return []
        except Exception as e:
            self.logger.error(f"Error running GAU for {domain}: {e}")
            return []
    
    def save_results(self, urls: list, program_name: str):
        """Simpan hasil ke file dengan pola penamaan yang konsisten"""
        if not urls:
            self.logger.warning(f"No URLs found for {program_name}, skipping")
            return
        
        # Buat slug dari program_name (mirip dengan file yang sudah ada)
        slug = program_name.lower().replace(' ', '-').replace('_', '-')
        filename = f"{slug}-gau.txt"
        filepath = os.path.join(self.output_dir, filename)
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                for url in urls:
                    f.write(url + '\n')
            
            self.logger.info(f"Saved {len(urls)} URLs to {filepath}")
            
        except Exception as e:
            self.logger.error(f"Error saving results for {program_name}: {e}")
    
    def run_all_programs(self):
        """Jalankan gau untuk semua program dari database"""
        programs = self.get_programs_from_database()
        
        if not programs:
            self.logger.error("No programs found in database")
            return
        
        total_urls = 0
        for program_name, program_url in programs:
            # Extract domain dari program_url
            domain = self.extract_domain_from_url(program_url)
            if domain:
                raw_urls = self.run_gau(domain)
                # Parse dan filter URLs
                filtered_urls = self.parse_and_filter_urls(raw_urls)
                self.save_results(filtered_urls, program_name)
                total_urls += len(filtered_urls)
        
        self.logger.info(f"GAU scanning completed. Total URLs found: {total_urls}")
    
    def extract_domain_from_url(self, url: str) -> str:
        """Extract domain dari URL program"""
        try:
            # Remove protocol
            if '://' in url:
                url = url.split('://', 1)[1]
            
            # Remove path and get domain
            domain = url.split('/')[0]
            
            # Remove www. prefix jika ada
            if domain.startswith('www.'):
                domain = domain[4:]
            
            return domain
        except Exception as e:
            self.logger.error(f"Error extracting domain from {url}: {e}")
            return None
    
    def parse_and_filter_urls(self, urls: list) -> list:
        """Parse dan filter URLs: remove duplicates dan similar URLs"""
        if not urls:
            return []
        
        # Step 1: Remove exact duplicates
        unique_urls = list(set(urls))
        self.logger.info(f"After removing duplicates: {len(unique_urls)} URLs")
        
        # Step 2: Pisahkan URL yang mengandung ID/UUID (jangan difilter)
        urls_with_ids, urls_without_ids = self.separate_urls_with_ids(unique_urls)
        self.logger.info(f"URLs with IDs/UUIDs: {len(urls_with_ids)}, URLs without IDs: {len(urls_without_ids)}")
        
        # Step 3: Group similar URLs hanya untuk yang tanpa ID/UUID
        grouped_urls = self.group_similar_urls(urls_without_ids)
        
        # Step 4: Select one representative dari setiap group
        filtered_urls_without_ids = self.select_representative_urls(grouped_urls)
        
        # Step 5: Gabungkan kembali dengan URLs yang mengandung ID/UUID
        final_urls = urls_with_ids + filtered_urls_without_ids
        final_urls.sort()  # Urutkan untuk konsistensi
        
        self.logger.info(f"Final URLs after filtering: {len(final_urls)} URLs")
        return final_urls
    
    def separate_urls_with_ids(self, urls: list) -> tuple:
        """Pisahkan URL yang mengandung ID numeric atau UUID"""
        urls_with_ids = []
        urls_without_ids = []
        
        for url in urls:
            if self.contains_id_or_uuid(url):
                urls_with_ids.append(url)
            else:
                urls_without_ids.append(url)
        
        return urls_with_ids, urls_without_ids
    
    def contains_id_or_uuid(self, url: str) -> bool:
        """Cek apakah URL mengandung ID numeric atau UUID pattern"""
        try:
            parsed = urlparse(url)
            path = parsed.path
            
            # Pattern untuk ID numeric: /users/123, /id/456, /item/789
            numeric_id_patterns = [
                r'/\d+$',           # /123
                r'/\d+/',           # /123/
                r'/id/\d+',         # /id/123
                r'/users/\d+',      # /users/123
                r'/customer/\d+',   # /customer/123
                r'/\d{5,}',         # ID dengan 5+ digit
            ]
            
            # Pattern untuk UUID: format standard UUID
            uuid_pattern = r'/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
            
            # Cek numeric ID patterns
            for pattern in numeric_id_patterns:
                if re.search(pattern, path, re.IGNORECASE):
                    return True
            
            # Cek UUID pattern
            if re.search(uuid_pattern, path, re.IGNORECASE):
                return True
            
            # Cek query parameters dengan ID/UUID
            if parsed.query:
                query_params = parse_qs(parsed.query)
                for param_name, param_values in query_params.items():
                    for value in param_values:
                        # Cek jika parameter value adalah numeric ID atau UUID
                        if (re.search(r'^\d+$', value) or
                            re.search(uuid_pattern, f'/{value}', re.IGNORECASE)):
                            return True
            
            return False
            
        except Exception:
            # Jika parsing gagal, assume tidak mengandung ID/UUID
            return False
    
    def group_similar_urls(self, urls: list) -> dict:
        """Group URLs berdasarkan similarity pattern"""
        groups = {}
        
        for url in urls:
            try:
                parsed = urlparse(url)
                base_path = self.get_base_path(parsed.path)
                
                # Untuk URL dengan query parameters, group berdasarkan base pattern
                if parsed.query:
                    # Decode URL-encoded parameters
                    decoded_query = unquote(parsed.query)
                    group_key = f"{parsed.netloc}{base_path}?{self.get_query_pattern(decoded_query)}"
                else:
                    group_key = f"{parsed.netloc}{base_path}"
                
                if group_key not in groups:
                    groups[group_key] = []
                groups[group_key].append(url)
                
            except Exception as e:
                self.logger.warning(f"Error parsing URL {url}: {e}")
                # Jika parsing gagal, treat sebagai unique URL
                groups[url] = [url]
        
        return groups
    
    def get_base_path(self, path: str) -> str:
        """Extract base path pattern"""
        if not path or path == '/':
            return '/'
        
        # Split path dan ambil bagian yang meaningful
        parts = path.strip('/').split('/')
        if len(parts) > 0:
            # Return first meaningful path segment
            return f"/{parts[0]}"
        return '/'
    
    def get_query_pattern(self, query: str) -> str:
        """Extract query parameter pattern"""
        try:
            params = parse_qs(query)
            if 'site' in params:
                return 'site=*'  # Pattern untuk external_redirect
            elif len(params) == 1:
                # Single parameter, ambil nama parameter saja
                param_name = list(params.keys())[0]
                return f"{param_name}=*"
            else:
                # Multiple parameters, return pattern berdasarkan parameter names
                param_names = sorted(params.keys())
                return '&'.join([f"{name}=*" for name in param_names])
        except:
            return query  # Fallback ke query asli jika parsing gagal
    
    def select_representative_urls(self, grouped_urls: dict) -> list:
        """Pilih satu URL representatif dari setiap group"""
        representative_urls = []
        
        for group_key, urls_in_group in grouped_urls.items():
            if len(urls_in_group) == 1:
                # Hanya satu URL di group, langsung ambil
                representative_urls.append(urls_in_group[0])
            else:
                # Pilih URL yang paling "clean" atau pendek
                urls_in_group.sort(key=len)  # Urutkan berdasarkan panjang
                representative_url = urls_in_group[0]
                
                # Log grouping information untuk debugging
                self.logger.debug(f"Group {group_key}: selected {representative_url} from {len(urls_in_group)} similar URLs")
                representative_urls.append(representative_url)
        
        return representative_urls

def main():
    """Main entry point"""
    setup_logging()
    logger = logging.getLogger(__name__)
    
    try:
        runner = GAURunner()
        runner.run_all_programs()
        logger.info("GAU runner completed successfully")
        
    except KeyboardInterrupt:
        logger.info("GAU runner stopped by user")
    except Exception as e:
        logger.error(f"GAU runner error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()