import sqlite3
import requests
from bs4 import BeautifulSoup
import time
import logging
import argparse
from urllib.parse import urljoin
import re

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BASE_URL = 'https://www.newadvent.org/fathers/'

class ChurchFathersScraper:
    def __init__(self, db_name='church_fathers.db'):
        self.db_name = db_name
        self.conn = None
        self.cursor = None
        
    def setup_database(self):
        """Create database tables if they don't exist"""
        self.conn = sqlite3.connect(self.db_name)
        self.cursor = self.conn.cursor()
        
        # Authors table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS authors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                dates TEXT,
                is_saint BOOLEAN DEFAULT 0,
                is_doctor BOOLEAN DEFAULT 0
            )
        ''')
        
        # Works table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS works (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                author_id INTEGER,
                title TEXT NOT NULL,
                url TEXT UNIQUE,
                work_type TEXT,
                century INTEGER,
                FOREIGN KEY (author_id) REFERENCES authors(id)
            )
        ''')
        
        # Chapters table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS chapters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                work_id INTEGER,
                chapter_number INTEGER,
                chapter_title TEXT,
                content TEXT,
                FOREIGN KEY (work_id) REFERENCES works(id)
            )
        ''')
        
        # Phrases table (n-grams for phrase search)
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS phrases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                phrase TEXT NOT NULL,
                chapter_id INTEGER,
                position INTEGER,
                length INTEGER,
                FOREIGN KEY (chapter_id) REFERENCES chapters(id)
            )
        ''')
        
        # Create indexes
        self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_phrases_phrase ON phrases(phrase)')
        self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_phrases_chapter ON phrases(chapter_id)')
        self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_works_author ON works(author_id)')
        
        # Full-text search table
        self.cursor.execute('''
            CREATE VIRTUAL TABLE IF NOT EXISTS content_fts USING fts5(
                content, 
                chapter_id UNINDEXED
            )
        ''')
        
        self.conn.commit()
        logger.info("Database schema created successfully")
    
    def fetch_page(self, url):
        """Fetch a web page with error handling"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Educational Church Fathers Research Project)'
            }
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            logger.error(f"Error fetching {url}: {e}")
            return None
    
    def parse_main_index(self):
        """Parse the main Church Fathers index page"""
        logger.info("Fetching main index page...")
        html = self.fetch_page(BASE_URL)
        
        if not html:
            logger.error("Could not fetch main index page")
            return []
        
        soup = BeautifulSoup(html, 'html.parser')
        authors_data = []
        current_author = None
        
        # The page structure has author links pointing to ../cathen/
        # followed by bullet points with work links pointing to ../fathers/
        for element in soup.find_all(['a', 'br']):
            if element.name == 'a':
                href = element.get('href', '')
                
                # Check if this is an author link (points to cathen)
                if href.startswith('../cathen/'):
                    # Save previous author if exists
                    if current_author and current_author.get('works'):
                        authors_data.append(current_author)
                    
                    # Start new author
                    author_name = element.text.strip()
                    parent_text = element.parent.get_text()
                    
                    is_saint = '[SAINT]' in parent_text
                    is_doctor = '[DOCTOR]' in parent_text
                    
                    # Extract dates
                    dates = ''
                    date_match = re.search(r'\(([^)]+)\)', author_name)
                    if date_match:
                        dates = date_match.group(1)
                        author_name = author_name[:date_match.start()].strip()
                    
                    current_author = {
                        'name': author_name,
                        'dates': dates,
                        'is_saint': is_saint,
                        'is_doctor': is_doctor,
                        'works': []
                    }
                    
                # Check if this is a work link (points to fathers)
                elif href.startswith('../fathers/') and current_author:
                    work_url = urljoin(BASE_URL, href)
                    work_title = element.text.strip()
                    if work_title and len(work_title) > 2:
                        current_author['works'].append({
                            'title': work_title,
                            'url': work_url
                        })
        
        # Don't forget the last author
        if current_author and current_author.get('works'):
            authors_data.append(current_author)
        
        logger.info(f"Found {len(authors_data)} authors total")
        return authors_data
    
    def save_author(self, author_data):
        """Save author to database"""
        try:
            self.cursor.execute('''
                INSERT OR IGNORE INTO authors (name, dates, is_saint, is_doctor)
                VALUES (?, ?, ?, ?)
            ''', (author_data['name'], author_data['dates'], 
                  author_data['is_saint'], author_data['is_doctor']))
            
            self.cursor.execute('SELECT id FROM authors WHERE name = ?', (author_data['name'],))
            author_id = self.cursor.fetchone()[0]
            
            self.conn.commit()
            return author_id
        except Exception as e:
            logger.error(f"Error saving author {author_data['name']}: {e}")
            return None
    
    def save_work(self, work_data, author_id):
        """Save work to database"""
        try:
            self.cursor.execute('''
                INSERT OR IGNORE INTO works (author_id, title, url)
                VALUES (?, ?, ?)
            ''', (author_id, work_data['title'], work_data['url']))
            
            self.cursor.execute('SELECT id FROM works WHERE url = ?', (work_data['url'],))
            result = self.cursor.fetchone()
            
            self.conn.commit()
            return result[0] if result else None
        except Exception as e:
            logger.error(f"Error saving work {work_data['title']}: {e}")
            return None
    
    def scrape_work_content(self, work_url):
        """Scrape the content of a specific work"""
        html = self.fetch_page(work_url)
        if not html:
            return []
        
        soup = BeautifulSoup(html, 'html.parser')
        chapters = []
        
        # Try to find the main content
        # New Advent typically wraps content in specific structures
        content_paragraphs = soup.find_all('p')
        
        if content_paragraphs:
            # Combine paragraphs into one chapter for simplicity
            content = ' '.join([p.get_text().strip() for p in content_paragraphs if p.get_text().strip()])
            
            if content and len(content) > 50:  # Make sure we have substantial content
                chapters.append({
                    'number': 1,
                    'title': 'Full Text',
                    'content': content[:10000]  # Limit to first 10k chars for now
                })
        
        return chapters
    
    def save_chapter(self, chapter_data, work_id):
        """Save chapter and create search indexes"""
        try:
            self.cursor.execute('''
                INSERT INTO chapters (work_id, chapter_number, chapter_title, content)
                VALUES (?, ?, ?, ?)
            ''', (work_id, chapter_data['number'], chapter_data['title'], chapter_data['content']))
            
            chapter_id = self.cursor.lastrowid
            
            # Add to FTS index
            self.cursor.execute('''
                INSERT INTO content_fts (content, chapter_id)
                VALUES (?, ?)
            ''', (chapter_data['content'], chapter_id))
            
            # Create phrase n-grams (2-5 words)
            words = chapter_data['content'].lower().split()
            for n in range(2, min(6, len(words) + 1)):
                for i in range(len(words) - n + 1):
                    if i > 100:  # Limit phrases per chapter for performance
                        break
                    phrase = ' '.join(words[i:i+n])
                    self.cursor.execute('''
                        INSERT INTO phrases (phrase, chapter_id, position, length)
                        VALUES (?, ?, ?, ?)
                    ''', (phrase, chapter_id, i, n))
            
            self.conn.commit()
            return chapter_id
        except Exception as e:
            logger.error(f"Error saving chapter: {e}")
            return None
    
    def scrape_all(self, limit=None):
        """Main scraping function"""
        self.setup_database()
        
        authors = self.parse_main_index()
        
        if limit:
            logger.info(f"Limiting to first {limit} works")
        
        works_processed = 0
        
        for author in authors:
            logger.info(f"Processing author: {author['name']}")
            author_id = self.save_author(author)
            
            if not author_id:
                continue
            
            for work in author['works']:
                if limit and works_processed >= limit:
                    logger.info(f"Reached limit of {limit} works")
                    return
                
                logger.info(f"  Processing work: {work['title']}")
                work_id = self.save_work(work, author_id)
                
                if not work_id:
                    continue
                
                # Scrape the work content
                time.sleep(1)  # Be polite to the server
                chapters = self.scrape_work_content(work['url'])
                
                for chapter in chapters:
                    self.save_chapter(chapter, work_id)
                
                works_processed += 1
                logger.info(f"  Saved {len(chapters)} chapters from {work['title']}")
        
        logger.info(f"Scraping complete! Processed {works_processed} works")
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()

def main():
    parser = argparse.ArgumentParser(description='Scrape Church Fathers writings from New Advent')
    parser.add_argument('--limit', type=int, help='Limit number of works to scrape (for testing)')
    parser.add_argument('--db', default='church_fathers.db', help='Database file name')
    
    args = parser.parse_args()
    
    scraper = ChurchFathersScraper(args.db)
    try:
        scraper.scrape_all(limit=args.limit)
    finally:
        scraper.close()

if __name__ == '__main__':
    main()
