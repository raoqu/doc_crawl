from flask import Flask, request, jsonify, render_template, send_file
from DocumentStorage import DocumentStorage
from crawler import Crawler
import os

app = Flask(__name__)
doc_storage = DocumentStorage()
crawler = Crawler(doc_storage)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/categories', methods=['GET'])
def get_categories():
    """Get all categories"""
    try:
        categories = doc_storage.get_categories()
        return jsonify(categories)
    except Exception as e:
        app.logger.error(f"Error getting categories: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/api/categories', methods=['POST'])
def add_category():
    """Add a new category"""
    try:
        data = request.get_json()
        name = data.get('name')
        if not name:
            return jsonify({'error': 'Category name is required'}), 400
        
        category_id = doc_storage.add_category(name)
        if category_id is None:
            return jsonify({'error': 'Category already exists'}), 400
        
        return jsonify({'id': category_id, 'name': name})
    except Exception as e:
        app.logger.error(f"Error adding category: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/api/documents', methods=['GET'])
def get_documents():
    """Get all documents, optionally filtered by category and search query"""
    try:
        query = request.args.get('q', '')
        category_id = request.args.get('category')
        
        if category_id:
            try:
                category_id = int(category_id)
            except ValueError:
                return jsonify({"error": "Invalid category ID"}), 400
        
        if query:
            docs = doc_storage.search_documents(query, category_id)
        else:
            docs = doc_storage.get_documents(category_id)
        
        return jsonify(docs)
    except Exception as e:
        app.logger.error(f"Error getting documents: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/api/documents/<path:url>/category', methods=['PUT'])
def update_document_category(url):
    """Update a document's category"""
    try:
        data = request.get_json()
        category_id = data.get('category_id')
        
        if category_id is None:
            return jsonify({'error': 'Category ID is required'}), 400
        
        doc_storage.update_document_category(url, category_id)
        return jsonify({'success': True})
    except Exception as e:
        app.logger.error(f"Error updating document category: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/crawl', methods=['POST'])
def crawl():
    """Crawl a new URL"""
    try:
        data = request.get_json()
        url = data.get('url')
        category_id = data.get('category_id')
        
        if not url:
            return jsonify({'error': 'URL is required'}), 400
            
        if category_id:
            try:
                category_id = int(category_id)
            except ValueError:
                return jsonify({"error": "Invalid category ID"}), 400
        
        success = crawler.crawl(url, category_id)
        if success:
            return jsonify({'success': True})
        else:
            return jsonify({'error': 'Failed to crawl URL'}), 400
    except Exception as e:
        app.logger.error(f"Error crawling URL: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/view/<path:url>')
def view_document(url):
    """View a document's markdown content"""
    try:
        paths = doc_storage._get_file_path(url)
        markdown_path = os.path.join(paths['markdown'], 'content.md')
        
        if os.path.exists(markdown_path):
            return render_template('view.html', url=url)
        else:
            return 'Document not found', 404
    except Exception as e:
        app.logger.error(f"Error viewing document: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/content/<path:url>')
def get_content(url):
    """Get a document's markdown content"""
    try:
        doc = doc_storage.get_document(url)
        if not doc:
            return jsonify({'error': 'Document not found'}), 404
            
        with open(doc['markdown_path'], 'r', encoding='utf-8') as f:
            content = f.read()
            
        return jsonify({'content': content})
    except Exception as e:
        app.logger.error(f"Error getting content: {e}")
        return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    app.run(debug=True, port=8000)