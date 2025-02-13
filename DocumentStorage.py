import os
import yaml
import sqlite3
import hashlib
import redis
from datetime import datetime
from urllib.parse import urlparse
import uuid
import mimetypes
import logging
import shutil

# Initialize logger
logger = logging.getLogger(__name__)

class DocumentStorage:
    def __init__(self, config_path='config.yaml'):
        # Get the directory of the main script
        main_dir = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(main_dir, config_path)
        
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        # Convert relative paths to absolute paths
        storage_config = self.config.get('storage', {})
        self.db_path = os.path.join(main_dir, storage_config.get('db_path', ''))
        self.doc_path = os.path.join(main_dir, storage_config.get('doc_path', ''))
        
        os.makedirs(self.db_path, exist_ok=True)
        os.makedirs(self.doc_path, exist_ok=True)
        
        # Initialize SQLite
        self.db_path = os.path.join(self.db_path, 'documents.db')
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_db()
        
        # Initialize Redis if enabled
        redis_config = self.config.get('redis', {})
        if redis_config.get('enabled', False):
            self.redis_client = redis.Redis(
                host=redis_config.get('host', 'localhost'),
                port=redis_config.get('port', 6379),
                db=redis_config.get('db', 0)
            )
        else:
            self.redis_client = None
    
    def _init_db(self):
        """Initialize the SQLite database with tables"""
        cursor = self.conn.cursor()
        
        # Create categories table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create documents table with category support
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT UNIQUE NOT NULL,
                title TEXT,
                markdown_path TEXT,
                category_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (category_id) REFERENCES categories(id)
            )
        ''')
        
        self.conn.commit()

    def add_category(self, name):
        """Add a new category"""
        cursor = self.conn.cursor()
        try:
            cursor.execute('INSERT INTO categories (name) VALUES (?)', (name,))
            self.conn.commit()
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            return None

    def get_categories(self):
        """Get all categories"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT id, name, created_at FROM categories ORDER BY name')
        categories = []
        for row in cursor.fetchall():
            categories.append({
                'id': row[0],
                'name': row[1],
                'created_at': row[2]
            })
        return categories

    def update_document_category(self, url, category_id):
        """Update a document's category"""
        cursor = self.conn.cursor()
        cursor.execute('''
            UPDATE documents 
            SET category_id = ?
            WHERE url = ?
        ''', (category_id, url))
        self.conn.commit()

    def add_document(self, url, title, raw_content, markdown, category_id=None) -> bool:
        """Add a new document to storage"""
        try:
            # Get paths for the document
            paths = self._get_file_path(url, category_id)
            
            # Create directories
            os.makedirs(os.path.dirname(paths['markdown']), exist_ok=True)
            
            # Save markdown content
            with open(paths['markdown'], 'w', encoding='utf-8') as f:
                f.write(markdown)
                
            # Save raw content
            raw_path = os.path.join(os.path.dirname(paths['markdown']), 'content.txt')
            with open(raw_path, 'w', encoding='utf-8') as f:
                f.write(raw_content)
            
            # Add to database
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT INTO documents 
                (url, title, markdown_path, category_id, created_at) 
                VALUES (?, ?, ?, ?, ?)
            ''', (url, title, paths['markdown'], category_id, datetime.now().isoformat()))
            self.conn.commit()
            
            return True
        except Exception as e:
            print(f"Error adding document: {e}")
            return False

    def get_document_by_url(self, url):
        """Get a document by URL"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT d.id, d.url, d.title, d.markdown_path, d.category_id, d.created_at, c.name as category_name
            FROM documents d 
            WHERE d.url = ? 
        ''', (url))
        return cursor.fetchone()

    def get_document_by_id(self, document_id):
        """Get a document by ID"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT d.*, c.name as category_name
            FROM documents d 
            LEFT JOIN categories c ON d.category_id = c.id
            WHERE d.id = ?
        ''', (document_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_documents(self, category_id=None):
        """Get all documents, optionally filtered by category"""
        cursor = self.conn.cursor()
        
        if category_id:
            cursor.execute('''
                SELECT 
                    d.id,
                    d.url,
                    d.title,
                    d.markdown_path,
                    d.category_id,
                    d.created_at,
                    c.name as category_name
                FROM documents d 
                LEFT JOIN categories c ON d.category_id = c.id 
                WHERE d.category_id = ?
                ORDER BY d.created_at DESC
            ''', (category_id,))
        else:
            cursor.execute('''
                SELECT 
                    d.id,
                    d.url,
                    d.title,
                    d.markdown_path,
                    d.category_id,
                    d.created_at,
                    c.name as category_name
                FROM documents d 
                LEFT JOIN categories c ON d.category_id = c.id 
                ORDER BY d.created_at DESC
            ''')
            
        rows = cursor.fetchall()
        return [{
            'id': row[0],
            'url': row[1],
            'title': row[2],
            'markdown_path': row[3],
            'category_id': row[4],
            'created_at': row[5],
            'category_name': row[6] if row[6] else None
        } for row in rows]

    def search_documents(self, query, category_id=None):
        """Search documents with optional category filter"""
        cursor = self.conn.cursor()
        
        # Build search query
        sql = '''
            SELECT d.*, c.name as category_name 
            FROM documents d 
            LEFT JOIN categories c ON d.category_id = c.id 
            WHERE (d.title LIKE ? OR d.url LIKE ?)
        '''
        params = [f'%{query}%', f'%{query}%']
        
        if category_id:
            sql += ' AND d.category_id = ?'
            params.append(category_id)
            
        sql += ' ORDER BY d.created_at DESC'
        
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        
        return [{
            'id': row[0],
            'url': row[1],
            'title': row[2],
            'markdown_path': row[3],
            'category_id': row[4],
            'created_at': row[5],
            'category_name': row[6] if row[6] else None
        } for row in rows]

    def delete_document(self, document_id):
        """Delete a document and its associated files"""
        try:
            # First get the document to find its path
            cursor = self.conn.cursor()
            cursor.execute('SELECT markdown_path FROM documents WHERE id = ?', (document_id,))
            doc = cursor.fetchone()
            
            if not doc:
                return False
                
            # Delete the document's directory (containing markdown and images)
            doc_dir = os.path.dirname(doc['markdown_path'])
            try:
                if os.path.exists(doc_dir):
                    shutil.rmtree(doc_dir)
            except Exception as e:
                # Ignore file system errors - proceed with database deletion
                logger.warning(f"Could not delete document directory {doc_dir}: {e}")
            
            # Delete from database
            cursor.execute('DELETE FROM documents WHERE id = ?', (document_id,))
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error deleting document: {e}", exc_info=True)
            return False

    def get_document_path(self, url, category_id=None) -> str:
        if category_id is None:
            raise Exception('category_id is required')

        base_path = self.config.get('storage', {}).get('doc_path', 'docs')
        
        # Get category name if category_id is provided
        category_name = 'uncategorized'
        if category_id:
            cursor = self.conn.cursor()
            cursor.execute('SELECT name FROM categories WHERE id = ?', (category_id,))
            row = cursor.fetchone()
            if row:
                category_name = row[0].lower().replace(' ', '_')
        
        # Parse URL for path components
        parsed = urlparse(url)
        domain = parsed.netloc
        
        # Generate a unique ID for this document
        doc_id = hashlib.md5(url.encode()).hexdigest()[:8]
        
        # Create paths
        doc_dir = os.path.join(base_path, category_name, domain, doc_id)
        return doc_dir

    def _get_file_path(self, url, category_id=None):
        """Generate storage path based on URL and category"""
        doc_dir = self.get_document_path(url, category_id)
        markdown_file = os.path.join(doc_dir, 'content.md')
        images_dir = os.path.join(doc_dir, 'images')
        
        return {
            'base': doc_dir,
            'markdown': markdown_file,
            'images': images_dir
        }