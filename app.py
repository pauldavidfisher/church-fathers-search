from flask import Flask, render_template, request, jsonify
from search_engine import PhraseSearchEngine
import os

app = Flask(__name__)

@app.route('/')
def index():
    """Main search page"""
    engine = PhraseSearchEngine()
    try:
        stats = engine.get_stats()
        # Make sure all expected stats exist
        if 'phrases' not in stats:
            stats['phrases'] = 0
        stats['unique_phrases'] = stats.get('phrases', 0)  # Add unique_phrases
    except Exception as e:
        print(f"Error getting stats: {e}")
        stats = {
            'authors': 0,
            'works': 0,
            'chapters': 0,
            'phrases': 0,
            'unique_phrases': 0
        }
    
    return render_template('index.html', stats=stats)

@app.route('/api/search', methods=['POST'])
def search():
    """API endpoint for searching"""
    data = request.get_json()
    
    query = data.get('query', '')
    search_type = data.get('type', 'combined')
    author_filter = data.get('author', '')
    limit = data.get('limit', 20)
    
    if not query:
        return jsonify({'error': 'No query provided'}), 400
    
    engine = PhraseSearchEngine()
    
    try:
        if search_type == 'exact':
            results = {'exact': engine.exact_phrase_search(query, limit)}
        elif search_type == 'proximity':
            words = query.split()
            results = {'proximity': engine.proximity_search(words, limit=limit)}
        elif search_type == 'fuzzy':
            results = {'fuzzy': engine.fuzzy_phrase_search(query, limit=limit)}
        elif search_type == 'fts':
            results = {'full_text': engine.full_text_search(query, limit=limit)}
        else:  # combined
            results = engine.combined_search(query, limit)
        
        # Filter by author if specified
        if author_filter:
            for key in results:
                results[key] = [r for r in results[key] 
                               if author_filter.lower() in r.get('author', '').lower()]
        
        # Count total results
        total = sum(len(results[key]) for key in results)
        
        return jsonify({
            'query': query,
            'total_results': total,
            'results': results
        })
    
    except Exception as e:
        print(f"Search error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/stats')
def get_stats():
    """Get database statistics"""
    engine = PhraseSearchEngine()
    try:
        stats = engine.get_stats()
        stats['unique_phrases'] = stats.get('phrases', 0)
        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/authors')
def get_authors():
    """Get list of all authors"""
    engine = PhraseSearchEngine()
    try:
        authors = engine.list_authors()
        return jsonify({'authors': authors})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
