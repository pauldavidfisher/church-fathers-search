import sqlite3
from difflib import SequenceMatcher

class PhraseSearchEngine:
    def __init__(self, db_name='church_fathers.db'):
        self.db_name = db_name
        self.conn = None
        self.cursor = None
        
    def connect(self):
        """Connect to the database"""
        self.conn = sqlite3.connect(self.db_name)
        self.cursor = self.conn.cursor()
        
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
    
    def get_stats(self):
        """Get database statistics"""
        self.connect()
        
        stats = {}
        
        # Count authors
        self.cursor.execute('SELECT COUNT(*) FROM authors')
        stats['authors'] = self.cursor.fetchone()[0]
        
        # Count works
        self.cursor.execute('SELECT COUNT(*) FROM works')
        stats['works'] = self.cursor.fetchone()[0]
        
        # Count chapters
        self.cursor.execute('SELECT COUNT(*) FROM chapters')
        stats['chapters'] = self.cursor.fetchone()[0]
        
        # Count phrases
        self.cursor.execute('SELECT COUNT(*) FROM phrases')
        stats['phrases'] = self.cursor.fetchone()[0]
        
        self.close()
        return stats
    
    def exact_phrase_search(self, phrase, limit=20):
        """Search for exact phrase matches using pre-indexed phrases"""
        self.connect()
        
        phrase_lower = phrase.lower()
        
        query = '''
            SELECT 
                p.phrase,
                c.content,
                c.chapter_title,
                w.title as work_title,
                a.name as author_name,
                w.url
            FROM phrases p
            JOIN chapters c ON p.chapter_id = c.id
            JOIN works w ON c.work_id = w.id
            JOIN authors a ON w.author_id = a.id
            WHERE p.phrase = ?
            LIMIT ?
        '''
        
        self.cursor.execute(query, (phrase_lower, limit))
        results = []
        
        for row in self.cursor.fetchall():
            # Get context around the phrase
            content = row[1]
            phrase_pos = content.lower().find(phrase_lower)
            
            if phrase_pos >= 0:
                start = max(0, phrase_pos - 100)
                end = min(len(content), phrase_pos + len(phrase_lower) + 100)
                context = content[start:end]
                
                results.append({
                    'phrase': row[0],
                    'context': context,
                    'chapter': row[2],
                    'work': row[3],
                    'author': row[4],
                    'url': row[5]
                })
        
        self.close()
        return results
    
    def full_text_search(self, query, limit=20):
        """Full-text search using FTS5"""
        self.connect()
        
        sql = '''
            SELECT 
                c.content,
                c.chapter_title,
                w.title as work_title,
                a.name as author_name,
                w.url,
                c.id
            FROM content_fts fts
            JOIN chapters c ON fts.chapter_id = c.id
            JOIN works w ON c.work_id = w.id
            JOIN authors a ON w.author_id = a.id
            WHERE content_fts MATCH ?
            LIMIT ?
        '''
        
        self.cursor.execute(sql, (query, limit))
        results = []
        
        for row in self.cursor.fetchall():
            # Extract relevant context
            content = row[0]
            words = query.lower().split()
            
            # Find first occurrence of any search word
            best_pos = -1
            for word in words:
                pos = content.lower().find(word)
                if pos >= 0 and (best_pos < 0 or pos < best_pos):
                    best_pos = pos
            
            if best_pos >= 0:
                start = max(0, best_pos - 100)
                end = min(len(content), best_pos + 200)
                context = content[start:end]
            else:
                context = content[:200]
            
            results.append({
                'context': context,
                'chapter': row[1],
                'work': row[2],
                'author': row[3],
                'url': row[4]
            })
        
        self.close()
        return results
    
    def proximity_search(self, words, max_distance=10, limit=20):
        """Search for words that appear near each other"""
        self.connect()
        
        # Use FTS to find documents containing all words
        query = ' AND '.join(words)
        
        sql = '''
            SELECT 
                c.content,
                c.chapter_title,
                w.title as work_title,
                a.name as author_name,
                w.url
            FROM content_fts fts
            JOIN chapters c ON fts.chapter_id = c.id
            JOIN works w ON c.work_id = w.id
            JOIN authors a ON w.author_id = a.id
            WHERE content_fts MATCH ?
            LIMIT ?
        '''
        
        self.cursor.execute(sql, (query, limit * 2))
        results = []
        
        for row in self.cursor.fetchall():
            content = row[0].lower()
            
            # Find positions of all words
            positions = {word: [] for word in words}
            for word in words:
                word_lower = word.lower()
                pos = 0
                while True:
                    pos = content.find(word_lower, pos)
                    if pos < 0:
                        break
                    positions[word].append(pos)
                    pos += 1
            
            # Check if any combination is within max_distance
            found_close = False
            for i, word1 in enumerate(words[:-1]):
                for word2 in words[i+1:]:
                    for pos1 in positions[word1]:
                        for pos2 in positions[word2]:
                            distance = abs(pos2 - pos1)
                            if distance <= max_distance * 10:  # rough estimate
                                found_close = True
                                # Get context
                                min_pos = min(pos1, pos2)
                                start = max(0, min_pos - 100)
                                end = min(len(content), max(pos1, pos2) + 100)
                                context = row[0][start:end]
                                
                                results.append({
                                    'context': context,
                                    'chapter': row[1],
                                    'work': row[2],
                                    'author': row[3],
                                    'url': row[4],
                                    'distance': distance
                                })
                                break
                        if found_close:
                            break
                    if found_close:
                        break
                if found_close:
                    break
            
            if len(results) >= limit:
                break
        
        self.close()
        return results[:limit]
    
    def fuzzy_phrase_search(self, phrase, threshold=0.8, limit=20):
        """Search for similar phrases using similarity scoring"""
        self.connect()
        
        phrase_lower = phrase.lower()
        phrase_length = len(phrase_lower.split())
        
        # Get phrases of similar length
        query = '''
            SELECT DISTINCT
                p.phrase,
                c.content,
                c.chapter_title,
                w.title as work_title,
                a.name as author_name,
                w.url
            FROM phrases p
            JOIN chapters c ON p.chapter_id = c.id
            JOIN works w ON c.work_id = w.id
            JOIN authors a ON w.author_id = a.id
            WHERE p.length BETWEEN ? AND ?
            LIMIT 1000
        '''
        
        self.cursor.execute(query, (phrase_length - 1, phrase_length + 1))
        results = []
        
        for row in self.cursor.fetchall():
            stored_phrase = row[0]
            similarity = SequenceMatcher(None, phrase_lower, stored_phrase).ratio()
            
            if similarity >= threshold:
                content = row[1]
                phrase_pos = content.lower().find(stored_phrase)
                
                if phrase_pos >= 0:
                    start = max(0, phrase_pos - 100)
                    end = min(len(content), phrase_pos + len(stored_phrase) + 100)
                    context = content[start:end]
                    
                    results.append({
                        'phrase': stored_phrase,
                        'similarity': similarity,
                        'context': context,
                        'chapter': row[2],
                        'work': row[3],
                        'author': row[4],
                        'url': row[5]
                    })
        
        # Sort by similarity
        results.sort(key=lambda x: x['similarity'], reverse=True)
        
        self.close()
        return results[:limit]
    
    def combined_search(self, query, limit=20):
        """Combine multiple search methods"""
        results = {
            'exact': [],
            'proximity': [],
            'fuzzy': [],
            'full_text': []
        }
        
        # Try exact phrase search
        results['exact'] = self.exact_phrase_search(query, limit=10)
        
        # Try proximity search if query has multiple words
        words = query.split()
        if len(words) > 1:
            results['proximity'] = self.proximity_search(words, limit=10)
        
        # Try fuzzy search
        results['fuzzy'] = self.fuzzy_phrase_search(query, threshold=0.75, limit=10)
        
        # Try full-text search
        results['full_text'] = self.full_text_search(query, limit=10)
        
        return results
    
    def search_by_author(self, author_name, limit=20):
        """Search for all works by a specific author"""
        self.connect()
        
        query = '''
            SELECT 
                w.title,
                w.url,
                c.chapter_title,
                c.content
            FROM authors a
            JOIN works w ON a.id = w.author_id
            JOIN chapters c ON w.id = c.work_id
            WHERE a.name LIKE ?
            LIMIT ?
        '''
        
        self.cursor.execute(query, (f'%{author_name}%', limit))
        results = []
        
        for row in self.cursor.fetchall():
            results.append({
                'work': row[0],
                'url': row[1],
                'chapter': row[2],
                'context': row[3][:200]
            })
        
        self.close()
        return results
    
    def list_authors(self):
        """Get list of all authors"""
        self.connect()
        
        query = '''
            SELECT 
                a.name,
                a.dates,
                a.is_saint,
                a.is_doctor,
                COUNT(w.id) as work_count
            FROM authors a
            LEFT JOIN works w ON a.id = w.author_id
            GROUP BY a.id
            ORDER BY a.name
        '''
        
        self.cursor.execute(query)
        results = []
        
        for row in self.cursor.fetchall():
            results.append({
                'name': row[0],
                'dates': row[1],
                'is_saint': bool(row[2]),
                'is_doctor': bool(row[3]),
                'work_count': row[4]
            })
        
        self.close()
        return results

def main():
    """Command-line interface for testing"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Search Church Fathers database')
    parser.add_argument('--query', help='Search query')
    parser.add_argument('--type', choices=['exact', 'proximity', 'fuzzy', 'combined', 'fts'], 
                       default='combined', help='Search type')
    parser.add_argument('--limit', type=int, default=20, help='Number of results')
    parser.add_argument('--stats', action='store_true', help='Show database statistics')
    parser.add_argument('--authors', action='store_true', help='List all authors')
    
    args = parser.parse_args()
    
    engine = PhraseSearchEngine()
    
    if args.stats:
        stats = engine.get_stats()
        print("\n=== Database Statistics ===")
        for key, value in stats.items():
            print(f"{key.capitalize()}: {value:,}")
        return
    
    if args.authors:
        authors = engine.list_authors()
        print("\n=== Authors ===")
        for author in authors:
            saint = " [SAINT]" if author['is_saint'] else ""
            doctor = " [DOCTOR]" if author['is_doctor'] else ""
            print(f"{author['name']}{saint}{doctor} ({author['dates']}) - {author['work_count']} works")
        return
    
    if not args.query:
        print("Please provide a --query or use --stats or --authors")
        return
    
    print(f"\nSearching for: '{args.query}' (type: {args.type})")
    print("=" * 60)
    
    if args.type == 'exact':
        results = engine.exact_phrase_search(args.query, args.limit)
    elif args.type == 'proximity':
        words = args.query.split()
        results = engine.proximity_search(words, limit=args.limit)
    elif args.type == 'fuzzy':
        results = engine.fuzzy_phrase_search(args.query, limit=args.limit)
    elif args.type == 'fts':
        results = engine.full_text_search(args.query, limit=args.limit)
    else:  # combined
        all_results = engine.combined_search(args.query, args.limit)
        print(f"\nFound {len(all_results['exact'])} exact matches")
        print(f"Found {len(all_results['proximity'])} proximity matches")
        print(f"Found {len(all_results['fuzzy'])} fuzzy matches")
        print(f"Found {len(all_results['full_text'])} full-text matches")
        
        # Show first few of each type
        for result_type, result_list in all_results.items():
            if result_list:
                print(f"\n--- {result_type.upper()} RESULTS ---")
                for i, result in enumerate(result_list[:3], 1):
                    print(f"\n{i}. {result['author']} - {result['work']}")
                    print(f"   Chapter: {result['chapter']}")
                    print(f"   Context: ...{result['context']}...")
        return
    
    print(f"\nFound {len(results)} results\n")
    
    for i, result in enumerate(results, 1):
        print(f"{i}. {result['author']} - {result['work']}")
        print(f"   Chapter: {result['chapter']}")
        print(f"   Context: ...{result['context']}...")
        print()

if __name__ == '__main__':
    main()
