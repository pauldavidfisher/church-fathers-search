#!/usr/bin/env python3
"""
Church Fathers Database Scraper
Scrapes content from newadvent.org/fathers and builds a searchable index
with support for phrase searching using n-grams and trigram indexing.
"""

import requests
from bs4 import BeautifulSoup
import sqlite3
import re
import time
import json
from urllib.parse import urljoin, urlparse
from typing import Dict, List, Set, Tuple
import logging
from collections import defaultdict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ChurchFathersScraper:
    """Scrapes and indexes Church Fathers texts from New Advent"""
    
    BASE_URL = "https://www.newadvent.org/fathers/"
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Educational Research Project)'
    }
    
    def __init__(self, db_path='church_fathers.db'):
        self.db_path = db_path
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)
        self.conn = None
        self.setup_database()
        
    def setup_database(self):
        """Create database schema for storing and searching texts"""
        self.conn = sqlite3.connect(self.db_path)
        cursor = self.conn.cursor()
        
        # Authors/Fathers table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS authors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                dates TEXT,
                description TEXT,
                is_saint BOOLEAN DEFAULT 0,
                is_doctor BOOLEAN DEFAULT 0
            )
        ''')
        
        # Works/Documents table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS works (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                author_id INTEGER,
                title TEXT NOT NULL,
                url TEXT UNIQUE NOT NULL,
                work_type TEXT,
                century INTEGER,
                FOREIGN KEY (author_id) REFERENCES authors(id)
            )
        ''')
        
        # Chapters/Sections table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chapters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                work_id INTEGER,
                chapter_number INTEGER,
                chapter_title TEXT,
                content TEXT,
                FOREIGN KEY (work_id) REFERENCES works(id)
            )
        ''')
        
        # Full-text search table for content
        cursor.execute('''
            CREATE VIRTUAL TABLE IF NOT EXISTS content_fts USING fts5(
                chapter_id,
                content,
                content='chapters',
                content_rowid='id'
            )
        ''')
        
        # Trigram index for phrase searching
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trigrams (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trigram TEXT NOT NULL,
                chapter_id INTEGER,
                position INTEGER,
                FOREIGN KEY (chapter_id) REFERENCES chapters(id)
            )
        ''')
        
        # N-gram index for flexible phrase matching
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS phrases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                phrase TEXT NOT NULL,
                chapter_id INTEGER,
                position INTEGER,
                length INTEGER,
                FOREIGN KEY (chapter_id) REFERENCES chapters(id)
            )
        ''')
        
        # Create indexes for performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_trigrams_trigram ON trigrams(trigram)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_trigrams_chapter ON trigrams(chapter_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_phrases_phrase ON phrases(phrase)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_phrases_chapter ON phrases(chapter_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_works_author ON works(author_id)')
        
        self.conn.commit()
        logger.info("Database schema created successfully")
    
    def parse_index_page(self):
        """Parse the main fathers index page to get all authors and works"""
        logger.info("Fetching main index page...")
        response = self.session.get(self.BASE_URL)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        authors_data = []
        
        # Find all author sections
        # The page has author names in links to the Catholic Encyclopedia
        content = soup.find('span', {'index': '1-1'})
        if not content:
            logger.error("Could not find main content")
            return authors_data
        
        # Parse each author entry
        current_author = None
        for element in content.find_all(['a', 'strong']):
            # Check if this is an author name (links to cathen)
            if element.name == 'a' and 'cathen' in element.get('href', ''):
                author_name = element.get_text(strip=True)
                if author_name and len(author_name) > 2:
                    # Look for saint/doctor markers nearby
                    parent_text = element.parent.get_text()
                    is_saint = '[SAINT]' in parent_text or 'SAINT' in parent_text
                    is_doctor = '[DOCTOR]' in parent_text or 'DOCTOR' in parent_text
                    
                    current_author = {
                        'name': author_name,
                        'is_saint': is_saint,
                        'is_doctor': is_doctor,
                        'works': []
                    }
                    authors_data.append(current_author)
            
            # Check for work links (links to /fathers/)
            elif element.name == 'a' and '/fathers/' in element.get('href', ''):
                href = element.get('href', '')
                if href.startswith('../fathers/'):
                    work_url = urljoin(self.BASE_URL, href)
                    work_title = element.get_text(strip=True)
                    
                    if current_author and work_title:
                        current_author['works'].append({
                            'title': work_title,
                            'url': work_url
                        })
        
        logger.info(f"Found {len(authors_data)} authors")
        return authors_data
    
    def extract_text_content(self, soup):
        """Extract clean text content from a page"""
        # Remove navigation, headers, footers
        for elem in soup.find_all(['script', 'style', 'nav', 'header', 'footer']):
            elem.decompose()
        
        # Find main content span
        content_span = soup.find('span', class_=lambda x: x and x.startswith('index'))
        if content_span:
            # Get text and clean it
            text = content_span.get_text(separator='\n')
            # Remove excessive whitespace
            text = re.sub(r'\n\s*\n', '\n\n', text)
            text = re.sub(r' +', ' ', text)
            return text.strip()
        return ""
    
    def parse_document(self, url):
        """Parse a single document and extract chapters/sections"""
        logger.info(f"Fetching document: {url}")
        
        try:
            time.sleep(1)  # Be respectful to the server
            response = self.session.get(url)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            chapters = []
            
            # Try to find chapter divisions (h2, h3 headers)
            headers = soup.find_all(['h2', 'h3'])
            
            if headers:
                # Document has clear chapter divisions
                for i, header in enumerate(headers):
                    chapter_title = header.get_text(strip=True)
                    
                    # Get content until next header
                    content_parts = []
                    for sibling in header.find_next_siblings():
                        if sibling.name in ['h2', 'h3']:
                            break
                        text = sibling.get_text(strip=True)
                        if text:
                            content_parts.append(text)
                    
                    content = '\n\n'.join(content_parts)
                    
                    if content:
                        chapters.append({
                            'number': i + 1,
                            'title': chapter_title,
                            'content': content
                        })
            else:
                # No clear divisions, treat as single chapter
                content = self.extract_text_content(soup)
                if content:
                    chapters.append({
                        'number': 1,
                        'title': 'Full Text',
                        'content': content
                    })
            
            return chapters
            
        except Exception as e:
            logger.error(f"Error parsing {url}: {e}")
            return []
    
    def generate_trigrams(self, text):
        """Generate character trigrams for fuzzy matching"""
        text = text.lower()
        trigrams = []
        for i in range(len(text) - 2):
            trigrams.append(text[i:i+3])
        return trigrams
    
    def generate_phrases(self, text, min_length=2, max_length=10):
        """Generate word n-grams for phrase searching"""
        # Tokenize into words
        words = re.findall(r'\b\w+\b', text.lower())
        phrases = []
        
        for length in range(min_length, max_length + 1):
            for i in range(len(words) - length + 1):
                phrase = ' '.join(words[i:i+length])
                phrases.append({
                    'phrase': phrase,
                    'position': i,
                    'length': length
                })
        
        return phrases
    
    def store_author(self, author_data):
        """Store author in database"""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT OR IGNORE INTO authors (name, is_saint, is_doctor)
            VALUES (?, ?, ?)
        ''', (author_data['name'], author_data['is_saint'], author_data['is_doctor']))
        self.conn.commit()
        
        cursor.execute('SELECT id FROM authors WHERE name = ?', (author_data['name'],))
        return cursor.fetchone()[0]
    
    def store_work(self, author_id, work_data):
        """Store work in database"""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT OR IGNORE INTO works (author_id, title, url)
            VALUES (?, ?, ?)
        ''', (author_id, work_data['title'], work_data['url']))
        self.conn.commit()
        
        cursor.execute('SELECT id FROM works WHERE url = ?', (work_data['url'],))
        return cursor.fetchone()[0]
    
    def store_chapter(self, work_id, chapter_data):
        """Store chapter and build search indexes"""
        cursor = self.conn.cursor()
        
        # Store chapter
        cursor.execute('''
            INSERT INTO chapters (work_id, chapter_number, chapter_title, content)
            VALUES (?, ?, ?, ?)
        ''', (work_id, chapter_data['number'], chapter_data['title'], chapter_data['content']))
        chapter_id = cursor.lastrowid
        
        # Index in FTS
        cursor.execute('''
            INSERT INTO content_fts (rowid, chapter_id, content)
            VALUES (?, ?, ?)
        ''', (chapter_id, chapter_id, chapter_data['content']))
        
        # Generate and store trigrams
        trigrams = self.generate_trigrams(chapter_data['content'])
        for pos, trigram in enumerate(trigrams):
            cursor.execute('''
                INSERT INTO trigrams (trigram, chapter_id, position)
                VALUES (?, ?, ?)
            ''', (trigram, chapter_id, pos))
        
        # Generate and store phrases
        phrases = self.generate_phrases(chapter_data['content'])
        for phrase_data in phrases:
            cursor.execute('''
                INSERT INTO phrases (phrase, chapter_id, position, length)
                VALUES (?, ?, ?, ?)
            ''', (phrase_data['phrase'], chapter_id, phrase_data['position'], phrase_data['length']))
        
        self.conn.commit()
        logger.info(f"Indexed chapter {chapter_id} with {len(trigrams)} trigrams and {len(phrases)} phrases")
    
    def scrape_all(self, limit=None):
        """Scrape all content from the database"""
        authors_data = self.parse_index_page()
        
        work_count = 0
        for author_data in authors_data:
            logger.info(f"Processing author: {author_data['name']}")
            author_id = self.store_author(author_data)
            
            for work_data in author_data['works']:
                if limit and work_count >= limit:
                    logger.info(f"Reached limit of {limit} works")
                    return
                
                logger.info(f"  Processing work: {work_data['title']}")
                work_id = self.store_work(author_id, work_data)
                
                chapters = self.parse_document(work_data['url'])
                for chapter_data in chapters:
                    self.store_chapter(work_id, chapter_data)
                
                work_count += 1
                logger.info(f"  Completed work {work_count}")
        
        logger.info(f"Scraping complete! Processed {work_count} works")
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Scrape Church Fathers database')
    parser.add_argument('--limit', type=int, help='Limit number of works to scrape (for testing)')
    parser.add_argument('--db', default='church_fathers.db', help='Database file path')
    args = parser.parse_args()
    
    scraper = ChurchFathersScraper(db_path=args.db)
    try:
        scraper.scrape_all(limit=args.limit)
    finally:
        scraper.close()


if __name__ == '__main__':
    main()
