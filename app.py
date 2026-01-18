#!/usr/bin/env python3
"""
Flask Web Interface for Church Fathers Search Engine
"""

from flask import Flask, render_template, request, jsonify
from search_engine import PhraseSearchEngine
import os

app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False

# Initialize search engine
DB_PATH = os.environ.get('DB_PATH', 'church_fathers.db')
search_engine = PhraseSearchEngine(DB_PATH)


@app.route('/')
def index():
    """Main search page"""
    stats = search_engine.get_stats()
    return render_template('index.html', stats=stats)


@app.route('/api/search', methods=['POST'])
def api_search():
    """API endpoint for search"""
    data = request.get_json()
    
    query = data.get('query', '').strip()
    search_type = data.get('type', 'combined')
    limit = int(data.get('limit', 20))
    author_filter = data.get('author', '').strip()
    
    if not query:
        return jsonify({'error': 'Query cannot be empty'}), 400
    
    try:
        if search_type == 'exact':
            results = {'exact': search_engine.exact_phrase_search(query, limit)}
        elif search_type == 'proximity':
            words = query.split()
            results = {'proximity': search_engine.proximity_search(words, limit=limit)}
        elif search_type == 'fuzzy':
            results = {'fuzzy': search_engine.fuzzy_phrase_search(query, limit=limit)}
        elif search_type == 'boolean':
            boolean_query = ' AND '.join(query.split())
            results = {'boolean': search_engine.boolean_search(boolean_query, limit)}
        else:  # combined
            results = search_engine.combined_search(query, limit=limit)
        
        # Apply author filter if specified
        if author_filter:
            for key in results:
                results[key] = [r for r in results[key] 
                               if author_filter.lower() in r['author'].lower()]
        
        # Calculate total results
        total = sum(len(v) for v in results.values())
        
        return jsonify({
            'query': query,
            'total_results': total,
            'results': results
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/stats')
def api_stats():
    """Get database statistics"""
    stats = search_engine.get_stats()
    return jsonify(stats)


@app.route('/api/authors')
def api_authors():
    """Get list of all authors"""
    cursor = search_engine.conn.cursor()
    cursor.execute('SELECT name, is_saint, is_doctor FROM authors ORDER BY name')
    authors = [{'name': row[0], 'is_saint': bool(row[1]), 'is_doctor': bool(row[2])} 
               for row in cursor.fetchall()]
    return jsonify(authors)


if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
