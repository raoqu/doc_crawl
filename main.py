from flask import Flask, request, jsonify, render_template, send_from_directory
import os

from pydantic import BaseModel, Field
from DocumentStorage import DocumentStorage
from crawler import Crawler, ImageExtractor
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
image_extractor = ImageExtractor()

class CrawlRequest(BaseModel):
    url: str = Field(..., description="URL to crawl")
    category_id: int = Field(..., description="Category ID")

class CrawlResponse(BaseModel):
    success: bool = Field(default=False)
    message: str = Field(default="")
    id: int = Field(default=None)

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

@app.route('/api/documents/<int:document_id>', methods=['DELETE'])
def delete_document(document_id):
    """Delete a document"""
    try:
        # Get document first to get its path
        doc = doc_storage.get_document_by_id(document_id)
        if not doc:
            return jsonify({"error": "Document not found"}), 404

        # Delete document and its content
        if doc_storage.delete_document(document_id):
            return jsonify({"success": True})
        else:
            return jsonify({"error": "Failed to delete document"}), 500
    except Exception as e:
        logger.error(f"Error deleting document: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route('/crawl', methods=['POST'])
def crawl():
    """Crawl a URL and store its content"""
    try:
        data = request.get_json()
        req = CrawlRequest.parse_obj(data)
            
        success, error, doc_id = crawler.crawl(req.url, req.category_id)
        if success:
            return CrawlResponse(success=True, id=doc_id).json(), 200
        else:
            return CrawlResponse(success=False, message=error).json(), 400
    except Exception as e:
        logger.error(f"Error crawling URL: {e}", exc_info=True)
        return CrawlResponse(success=False, message=str(e)).json(), 500

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
                
            # Get the document directory for serving images
            doc_dir = os.path.relpath(markdown_path, doc_storage.doc_path)
            doc_dir = os.path.dirname(doc_dir)
            # Replace image path in markdown to the local path
            content = image_extractor.restore_markdown_images(content, base_path=doc_dir)
                
            return render_template('markdown.html', content=content)
        else:
            return "Document content not found", 404
            
    except Exception as e:
        logger.error(f"Error viewing document: {e}", exc_info=True)
        return "Error viewing document", 500

@app.route('/view_image/<path:imagepath>')
def serve_doc_image(imagepath):
    """Serve document images from the document storage path
    
    Args:
        imagepath: Path to the image relative to doc_storage.doc_path
    """
    try:
        # Construct the full path to the image
        file_path = os.path.join(doc_storage.doc_path, imagepath)
        
        # Get the directory and filename
        images_dir = os.path.dirname(file_path)
        file_name = os.path.basename(file_path)
        
        # Verify the path is within doc_storage.doc_path
        if not os.path.abspath(file_path).startswith(os.path.abspath(doc_storage.doc_path)):
            return "Access denied", 403
            
        return send_from_directory(images_dir, file_name)
    except Exception as e:
        logger.error(f"Error serving image {imagepath}: {e}", exc_info=True)
        return "Image not found", 404

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