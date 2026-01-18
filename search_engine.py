#!/usr/bin/env python3
"""
Phrase Search Engine for Church Fathers Database
Supports exact phrase matching, proximity search, and fuzzy phrase matching
"""

import sqlite3
import re
from typing import List, Dict, Tuple
from collections import defaultdict
import difflib


class PhraseSearchEngine:
    """Search engine with advanced phrase search capabilities"""
    
    def __init__(self, db_path='church_fathers.db'):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
    
    def exact_phrase_search(self, phrase: str, limit=50) -> List[Dict]:
        """
        Search for exact phrase matches
        Uses the pre-computed phrase index for very fast lookups
        """
        cursor = self.conn.cursor()
        
        # Normalize phrase
        normalized_phrase = ' '.join(re.findall(r'\b\w+\b', phrase.lower()))
        
        # Query the phrases table
        cursor.execute('''
            SELECT 
                p.chapter_id,
                p.position,
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
        ''', (normalized_phrase, limit))
        
        results = []
        for row in cursor.fetchall():
            # Extract context around the match
            context = self._get_context(row['content'], normalized_phrase)
            
            results.append({
                'author': row['author_name'],
                'work': row['work_title'],
                'chapter': row['chapter_title'],
                'url': row['url'],
                'context': context,
                'match_type': 'exact'
            })
        
        return results
    
    def proximity_search(self, words: List[str], max_distance=5, limit=50) -> List[Dict]:
        """
        Search for words within a certain distance of each other
        max_distance: maximum number of words between search terms
        """
        cursor = self.conn.cursor()
        
        # Build FTS5 query - use OR to find any document with the words
        fts_query = ' OR '.join(words)
        
        cursor.execute('''
            SELECT 
                c.id as chapter_id,
                c.content,
                c.chapter_title,
                w.title as work_title,
                a.name as author_name,
                w.url
            FROM content_fts AS fts
            JOIN chapters c ON fts.rowid = c.id
            JOIN works w ON c.work_id = w.id
            JOIN authors a ON w.author_id = a.id
            WHERE fts.content MATCH ?
            LIMIT ?
        ''', (fts_query, limit * 3))  # Get more results to filter
        
        results = []
        for row in cursor.fetchall():
            # Check if words appear within max_distance
            content_words = re.findall(r'\b\w+\b', row['content'].lower())
            positions = defaultdict(list)
            
            # Find all positions of each search word
            for i, word in enumerate(content_words):
                for search_word in words:
                    if word == search_word.lower():
                        positions[search_word.lower()].append(i)
            
            # Check if all words are present
            if len(positions) != len(words):
                continue
            
            # Find proximity matches
            for pos1 in positions[words[0].lower()]:
                match_found = True
                max_pos = pos1
                min_pos = pos1
                
                for word in words[1:]:
                    # Find closest position of this word to pos1
                    closest_pos = min(positions[word.lower()], 
                                     key=lambda x: abs(x - pos1))
                    
                    if abs(closest_pos - pos1) > max_distance + len(words):
                        match_found = False
                        break
                    
                    max_pos = max(max_pos, closest_pos)
                    min_pos = min(min_pos, closest_pos)
                
                if match_found and (max_pos - min_pos) <= max_distance + len(words):
                    # Extract context
                    start = max(0, min_pos - 10)
                    end = min(len(content_words), max_pos + 10)
                    context = ' '.join(content_words[start:end])
                    
                    results.append({
                        'author': row['author_name'],
                        'work': row['work_title'],
                        'chapter': row['chapter_title'],
                        'url': row['url'],
                        'context': context,
                        'match_type': f'proximity(distance={max_pos - min_pos})',
                        'distance': max_pos - min_pos
                    })
                    
                    if len(results) >= limit:
                        return results
                    break
        
        return results
    
    def fuzzy_phrase_search(self, phrase: str, threshold=0.8, limit=50) -> List[Dict]:
        """
        Search for phrases similar to the query using similarity matching
        threshold: minimum similarity score (0-1)
        """
        cursor = self.conn.cursor()
        
        # Normalize phrase
        normalized_phrase = ' '.join(re.findall(r'\b\w+\b', phrase.lower()))
        phrase_length = len(normalized_phrase.split())
        
        # Get all phrases of similar length
        cursor.execute('''
            SELECT DISTINCT
                p.phrase,
                p.chapter_id,
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
            LIMIT ?
        ''', (phrase_length - 1, phrase_length + 1, limit * 100))
        
        results = []
        seen_chapters = set()
        
        for row in cursor.fetchall():
            # Calculate similarity
            similarity = difflib.SequenceMatcher(
                None, 
                normalized_phrase, 
                row['phrase']
            ).ratio()
            
            if similarity >= threshold:
                chapter_id = row['chapter_id']
                
                # Avoid duplicate results from same chapter
                if chapter_id in seen_chapters:
                    continue
                seen_chapters.add(chapter_id)
                
                # Extract context
                context = self._get_context(row['content'], row['phrase'])
                
                results.append({
                    'author': row['author_name'],
                    'work': row['work_title'],
                    'chapter': row['chapter_title'],
                    'url': row['url'],
                    'context': context,
                    'match_type': f'fuzzy(similarity={similarity:.2f})',
                    'similarity': similarity,
                    'matched_phrase': row['phrase']
                })
                
                if len(results) >= limit:
                    break
        
        # Sort by similarity
        results.sort(key=lambda x: x['similarity'], reverse=True)
        return results[:limit]
    
    def boolean_search(self, query: str, limit=50) -> List[Dict]:
        """
        Boolean search with AND, OR, NOT operators
        Example: "faith AND hope NOT despair"
        """
        cursor = self.conn.cursor()
        
        cursor.execute('''
            SELECT 
                c.id as chapter_id,
                c.content,
                c.chapter_title,
                w.title as work_title,
                a.name as author_name,
                w.url
            FROM content_fts AS fts
            JOIN chapters c ON fts.rowid = c.id
            JOIN works w ON c.work_id = w.id
            JOIN authors a ON w.author_id = a.id
            WHERE fts.content MATCH ?
            LIMIT ?
        ''', (query, limit))
        
        results = []
        for row in cursor.fetchall():
            # Extract relevant snippet
            words = query.replace(' AND ', ' ').replace(' OR ', ' ').replace(' NOT ', ' ').split()
            snippet = self._extract_snippet(row['content'], words)
            
            results.append({
                'author': row['author_name'],
                'work': row['work_title'],
                'chapter': row['chapter_title'],
                'url': row['url'],
                'context': snippet,
                'match_type': 'boolean'
            })
        
        return results
    
    def combined_search(self, phrase: str, strategies=['exact', 'proximity', 'fuzzy'], 
                       limit=50) -> Dict[str, List[Dict]]:
        """
        Run multiple search strategies and combine results
        Returns a dict with results from each strategy
        """
        results = {}
        
        if 'exact' in strategies:
            results['exact'] = self.exact_phrase_search(phrase, limit)
        
        if 'proximity' in strategies:
            words = phrase.split()
            if len(words) > 1:
                results['proximity'] = self.proximity_search(words, limit=limit)
            else:
                results['proximity'] = []
        
        if 'fuzzy' in strategies:
            results['fuzzy'] = self.fuzzy_phrase_search(phrase, limit=limit)
        
        if 'boolean' in strategies:
            # Convert to simple AND query
            boolean_query = ' AND '.join(phrase.split())
            results['boolean'] = self.boolean_search(boolean_query, limit)
        
        return results
    
    def search_by_author(self, author_name: str, phrase: str = None, limit=50) -> List[Dict]:
        """Filter search results by author"""
        cursor = self.conn.cursor()
        
        if phrase:
            normalized_phrase = ' '.join(re.findall(r'\b\w+\b', phrase.lower()))
            cursor.execute('''
                SELECT 
                    c.content,
                    c.chapter_title,
                    w.title as work_title,
                    a.name as author_name,
                    w.url
                FROM phrases p
                JOIN chapters c ON p.chapter_id = c.id
                JOIN works w ON c.work_id = w.id
                JOIN authors a ON w.author_id = a.id
                WHERE p.phrase = ? AND a.name LIKE ?
                LIMIT ?
            ''', (normalized_phrase, f'%{author_name}%', limit))
        else:
            cursor.execute('''
                SELECT 
                    c.content,
                    c.chapter_title,
                    w.title as work_title,
                    a.name as author_name,
                    w.url
                FROM chapters c
                JOIN works w ON c.work_id = w.id
                JOIN authors a ON w.author_id = a.id
                WHERE a.name LIKE ?
                LIMIT ?
            ''', (f'%{author_name}%', limit))
        
        return [dict(row) for row in cursor.fetchall()]
    
    def _get_context(self, content: str, phrase: str, context_words=20) -> str:
        """Extract context around a phrase in content"""
        # Find phrase in content
        content_lower = content.lower()
        phrase_lower = phrase.lower()
        
        pos = content_lower.find(phrase_lower)
        if pos == -1:
            # If exact match not found, return first few words
            words = content.split()
            return ' '.join(words[:50]) + '...'
        
        # Extract context
        words = content.split()
        content_words = ' '.join(words).lower()
        phrase_pos = content_words.find(phrase_lower)
        
        # Find word boundaries
        before_context = content_words[:phrase_pos].split()[-context_words:]
        after_context = content_words[phrase_pos:].split()[len(phrase.split()):context_words + len(phrase.split())]
        
        context_parts = []
        if before_context:
            context_parts.append(' '.join(before_context))
        context_parts.append(phrase)
        if after_context:
            context_parts.append(' '.join(after_context))
        
        return '...' + ' '.join(context_parts) + '...'
    
    def _extract_snippet(self, content: str, keywords: List[str], max_length=200) -> str:
        """Extract a relevant snippet containing keywords"""
        words = content.split()
        keyword_positions = []
        
        for i, word in enumerate(words):
            if any(kw.lower() in word.lower() for kw in keywords):
                keyword_positions.append(i)
        
        if not keyword_positions:
            return ' '.join(words[:max_length]) + '...'
        
        # Get snippet around first keyword
        start_pos = max(0, keyword_positions[0] - 20)
        end_pos = min(len(words), keyword_positions[0] + 30)
        
        snippet = ' '.join(words[start_pos:end_pos])
        return '...' + snippet + '...'
    
    def get_stats(self) -> Dict:
        """Get database statistics"""
        cursor = self.conn.cursor()
        
        stats = {}
        
        cursor.execute('SELECT COUNT(*) FROM authors')
        stats['total_authors'] = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM works')
        stats['total_works'] = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM chapters')
        stats['total_chapters'] = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(DISTINCT phrase) FROM phrases')
        stats['unique_phrases'] = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM phrases')
        stats['total_phrase_occurrences'] = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM trigrams')
        stats['total_trigrams'] = cursor.fetchone()[0]
        
        return stats
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()


def main():
    """Interactive search interface"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Search Church Fathers database')
    parser.add_argument('--db', default='church_fathers.db', help='Database file path')
    parser.add_argument('--query', help='Search query')
    parser.add_argument('--type', default='combined', 
                       choices=['exact', 'proximity', 'fuzzy', 'boolean', 'combined'],
                       help='Search type')
    parser.add_argument('--limit', type=int, default=10, help='Max results')
    parser.add_argument('--stats', action='store_true', help='Show database statistics')
    
    args = parser.parse_args()
    
    engine = PhraseSearchEngine(db_path=args.db)
    
    try:
        if args.stats:
            stats = engine.get_stats()
            print("\n=== Database Statistics ===")
            for key, value in stats.items():
                print(f"{key}: {value:,}")
            return
        
        if not args.query:
            # Interactive mode
            print("Church Fathers Phrase Search Engine")
            print("=" * 50)
            while True:
                query = input("\nEnter search phrase (or 'quit'): ").strip()
                if query.lower() == 'quit':
                    break
                
                if not query:
                    continue
                
                print(f"\nSearching for: '{query}'")
                print("-" * 50)
                
                if args.type == 'combined':
                    results = engine.combined_search(query, limit=args.limit)
                    for search_type, result_list in results.items():
                        if result_list:
                            print(f"\n{search_type.upper()} MATCHES ({len(result_list)}):")
                            for i, result in enumerate(result_list[:3], 1):
                                print(f"\n{i}. {result['author']} - {result['work']}")
                                print(f"   Chapter: {result['chapter']}")
                                print(f"   {result['context'][:150]}...")
                elif args.type == 'exact':
                    results = engine.exact_phrase_search(query, args.limit)
                    for i, result in enumerate(results, 1):
                        print(f"\n{i}. {result['author']} - {result['work']}")
                        print(f"   {result['context'][:200]}...")
                elif args.type == 'proximity':
                    words = query.split()
                    results = engine.proximity_search(words, limit=args.limit)
                    for i, result in enumerate(results, 1):
                        print(f"\n{i}. {result['author']} - {result['work']}")
                        print(f"   Distance: {result['distance']}")
                        print(f"   {result['context'][:200]}...")
                elif args.type == 'fuzzy':
                    results = engine.fuzzy_phrase_search(query, limit=args.limit)
                    for i, result in enumerate(results, 1):
                        print(f"\n{i}. {result['author']} - {result['work']}")
                        print(f"   Matched: '{result['matched_phrase']}' (similarity: {result['similarity']:.2f})")
                        print(f"   {result['context'][:200]}...")
        else:
            # Single query mode
            print(f"Searching for: '{args.query}'")
            
            if args.type == 'combined':
                results = engine.combined_search(args.query, limit=args.limit)
                for search_type, result_list in results.items():
                    print(f"\n{search_type.upper()} - {len(result_list)} results")
            elif args.type == 'exact':
                results = engine.exact_phrase_search(args.query, args.limit)
                print(f"\nFound {len(results)} exact matches")
                for result in results[:5]:
                    print(f"- {result['author']}: {result['work']}")
    
    finally:
        engine.close()


if __name__ == '__main__':
    main()
