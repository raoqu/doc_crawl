from flask import Flask, request, jsonify, render_template
import os
from DocumentStorage import DocumentStorage
from crawler import Crawler
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['DEBUG'] = True
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['SECRET_KEY'] = 'secret_key_here'
doc_storage = DocumentStorage()
crawler = Crawler(doc_storage)

# Add markdown filter to Jinja2
#@app.template_filter('markdown')
#def markdown_filter(text):
#    return markdown.markdown(text, extensions=['extra', 'codehilite'])

@app.route('/')
def index():
    try:
        return render_template('index.html')
    except Exception as e:
        logger.error(f"Error rendering index: {e}", exc_info=True)
        return f"Error: {str(e)}", 500

@app.route('/api/categories', methods=['GET'])
def get_categories():
    """Get all categories"""
    try:
        categories = doc_storage.get_categories()
        return jsonify(categories)
    except Exception as e:
        logger.error(f"Error getting categories: {e}")
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
        
        return jsonify({"id": category_id, "name": name})
    except Exception as e:
        logger.error(f"Error adding category: {e}")
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
        logger.error(f"Error getting documents: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/api/documents/<path:url>/category', methods=['PUT'])
def update_document_category(url):
    """Update a document's category"""
    try:
        data = request.get_json()
        category_id = data.get('category_id')
        
        if category_id is None:
            return jsonify({"error": "Category ID is required"}), 400
            
        doc_storage.update_document_category(url, category_id)
        return jsonify({"success": True})
    except Exception as e:
        logger.error(f"Error updating document category: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/api/documents/<path:url>', methods=['DELETE'])
def delete_document(url):
    """Delete a document"""
    try:
        success = doc_storage.delete_document(url)
        if success:
            return jsonify({'success': True})
        else:
            return jsonify({'error': 'Document not found'}), 404
    except Exception as e:
        logger.error(f"Error deleting document: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/crawl', methods=['POST'])
def crawl():
    """Crawl a new URL"""
    try:
        logger.info("Received crawl request")
        data = request.get_json()
        url = data.get('url')
        category_id = data.get('category_id')
        
        if not url:
            logger.error("URL is required")
            return jsonify({'error': 'URL is required'}), 400
            
        if category_id:
            try:
                category_id = int(category_id)
            except ValueError:
                logger.error("Invalid category ID")
                return jsonify({"error": "Invalid category ID"}), 400
        
        logger.info(f"Crawling URL: {url} with category: {category_id}")
        success, error = crawler.crawl(url, category_id)
        if success:
            logger.info("Crawl successful")
            return jsonify({'success': True})
        else:
            logger.error(f"Crawl failed: {error}")
            return jsonify({'error': error or 'Failed to crawl URL'}), 400
    except Exception as e:
        logger.error(f"Error crawling URL: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route('/view/<int:document_id>')
def view_document(document_id):
    """View a document's markdown content"""
    try:
        # Get document from database
        doc = doc_storage.get_document_by_id(document_id)
        if not doc:
            return "Document not found", 404
            
        # Get markdown content
        markdown_path = doc['markdown_path']
        if os.path.exists(markdown_path):
            with open(markdown_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return render_template('markdown.html', content=content)
        else:
            return "Document content not found", 404
            
    except Exception as e:
        logger.error(f"Error viewing document: {e}", exc_info=True)
        return "Error viewing document", 500

@app.route('/content/<int:document_id>')
def get_content(document_id):
    """Get a document's markdown content"""
    try:
        doc = doc_storage.get_document_by_id(document_id)
        if not doc:
            return jsonify({"error": "Document not found"}), 404
            
        markdown_path = doc['markdown_path']
        if os.path.exists(markdown_path):
            with open(markdown_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return jsonify({"content": content})
        else:
            return jsonify({"error": "Document content not found"}), 404
            
    except Exception as e:
        logger.error(f"Error getting document content: {e}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    app.run(debug=True, port=8000)