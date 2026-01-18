// Church Fathers Search Engine - Frontend JavaScript

const searchInput = document.getElementById('searchInput');
const searchButton = document.getElementById('searchButton');
const searchType = document.getElementById('searchType');
const authorFilter = document.getElementById('authorFilter');
const limitSelect = document.getElementById('limitSelect');
const resultsDiv = document.getElementById('results');
const loadingDiv = document.getElementById('loading');

// Search on button click
searchButton.addEventListener('click', performSearch);

// Search on Enter key
searchInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        performSearch();
    }
});

async function performSearch() {
    const query = searchInput.value.trim();
    
    if (!query) {
        alert('Please enter a search phrase');
        return;
    }
    
    // Show loading
    loadingDiv.style.display = 'block';
    resultsDiv.innerHTML = '';
    
    try {
        const response = await fetch('/api/search', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                query: query,
                type: searchType.value,
                author: authorFilter.value,
                limit: limitSelect.value
            })
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Search failed');
        }
        
        const data = await response.json();
        displayResults(data);
        
    } catch (error) {
        console.error('Search error:', error);
        resultsDiv.innerHTML = `
            <div class="no-results">
                <h3>Error</h3>
                <p>${error.message}</p>
            </div>
        `;
    } finally {
        loadingDiv.style.display = 'none';
    }
}

function displayResults(data) {
    if (data.total_results === 0) {
        resultsDiv.innerHTML = `
            <div class="no-results">
                <h3>No Results Found</h3>
                <p>Try a different search phrase or change the search type.</p>
                <p>Example searches: "love of God", "faith and hope", "holy spirit"</p>
            </div>
        `;
        return;
    }
    
    let html = `<h2 style="margin-bottom: 20px;">Found ${data.total_results} results for "${data.query}"</h2>`;
    
    // Display results by type
    for (const [searchType, results] of Object.entries(data.results)) {
        if (results && results.length > 0) {
            html += createResultGroup(searchType, results);
        }
    }
    
    resultsDiv.innerHTML = html;
}

function createResultGroup(type, results) {
    const typeNames = {
        'exact': 'Exact Phrase Matches',
        'proximity': 'Proximity Matches',
        'fuzzy': 'Similar Phrase Matches',
        'boolean': 'Boolean Matches'
    };
    
    let html = `
        <div class="result-group">
            <h2>
                ${typeNames[type] || type}
                <span class="result-count">${results.length} results</span>
            </h2>
    `;
    
    for (const result of results) {
        html += createResultCard(result);
    }
    
    html += '</div>';
    return html;
}

function createResultCard(result) {
    // Clean up context text
    let context = result.context || '';
    if (context.length > 400) {
        context = context.substring(0, 400) + '...';
    }
    
    // Create match info badge
    let matchInfo = '';
    if (result.match_type) {
        matchInfo = `<span class="match-badge">${result.match_type}</span>`;
    }
    
    // Build the card HTML
    return `
        <div class="result-card">
            <div class="result-header">
                <div class="result-author">${escapeHtml(result.author)}</div>
                <div class="result-work">${escapeHtml(result.work)}</div>
                ${result.chapter ? `<div class="result-chapter">Chapter: ${escapeHtml(result.chapter)}</div>` : ''}
            </div>
            
            <div class="result-context">
                ${highlightText(escapeHtml(context))}
            </div>
            
            <div class="result-meta">
                ${matchInfo}
                ${result.similarity ? `<span>Similarity: ${(result.similarity * 100).toFixed(0)}%</span>` : ''}
                ${result.distance ? `<span>Word Distance: ${result.distance}</span>` : ''}
                ${result.matched_phrase ? `<span>Matched: "${escapeHtml(result.matched_phrase)}"</span>` : ''}
                <a href="${result.url}" target="_blank" class="result-link">Read Full Text →</a>
            </div>
        </div>
    `;
}

function highlightText(text) {
    // Simple highlighting - could be enhanced
    const query = searchInput.value.trim().toLowerCase();
    const words = query.split(/\s+/);
    
    let highlightedText = text;
    for (const word of words) {
        if (word.length > 2) {
            const regex = new RegExp(`\\b(${escapeRegex(word)})\\b`, 'gi');
            highlightedText = highlightedText.replace(regex, '<mark>$1</mark>');
        }
    }
    
    return highlightedText;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function escapeRegex(string) {
    return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

// Load example searches
const examples = [
    "love of God",
    "holy spirit",
    "faith and hope",
    "resurrection of the dead",
    "body of Christ",
    "kingdom of heaven"
];

// Optionally set a random example as placeholder
if (Math.random() > 0.5) {
    const randomExample = examples[Math.floor(Math.random() * examples.length)];
    searchInput.placeholder = `Enter a phrase to search (e.g., '${randomExample}')`;
}
