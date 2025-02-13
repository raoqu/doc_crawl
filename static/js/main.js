let currentPage = 1;
const perPage = 10;

// Load documents when page loads
document.addEventListener('DOMContentLoaded', function() {
    // Initialize UI elements
    const addDocBtn = document.getElementById('addDocBtn');
    const urlInput = document.getElementById('urlInput');
    const categoryFilter = document.getElementById('categoryFilter');
    const searchForm = document.getElementById('searchForm');
    const searchInput = document.getElementById('searchInput');
    const addCategoryBtn = document.getElementById('addCategoryBtn');
    const newDocBtn = document.querySelector('.btn-new-doc');
    
    // Update New Doc button state based on category selection
    function updateNewDocButton() {
        if (newDocBtn) {
            const categoryId = categoryFilter.value;
            newDocBtn.disabled = !categoryId || categoryId === 'new';
            newDocBtn.title = (!categoryId || categoryId === 'new') ? 
                'Please select a category first' : 'Add new document';
        }
    }

    if (addDocBtn) {
        addDocBtn.addEventListener('click', async () => {
            const url = urlInput.value.trim();
            const categoryId = categoryFilter.value;
            
            if (!url) {
                alert('Please enter a valid URL');
                return;
            }
            
            if (!categoryId) {
                alert('Please select a category');
                return;
            }
            
            try {
                const response = await fetch('/crawl', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        url: url,
                        category_id: categoryId
                    })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    // Close modal and reload documents
                    const modal = bootstrap.Modal.getInstance(document.getElementById('newDocModal'));
                    modal.hide();
                    urlInput.value = '';
                    loadDocuments();
                } else {
                    alert(data.error || 'Failed to crawl URL');
                }
            } catch (error) {
                console.error('Error:', error);
                alert('Error crawling URL');
            }
        });
    }
    
    if (categoryFilter) {
        categoryFilter.addEventListener('change', updateNewDocButton);
    }
    
    if (addCategoryBtn) {
        addCategoryBtn.addEventListener('click', async () => {
            const categoryInput = document.getElementById('categoryInput');
            const name = categoryInput.value.trim();
            
            if (!name) {
                alert('Please enter a category name');
                return;
            }
            
            try {
                const response = await fetch('/api/categories', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ name })
                });
                
                const data = await response.json();
                
                if (response.ok) {
                    const modal = bootstrap.Modal.getInstance(document.getElementById('newCategoryModal'));
                    modal.hide();
                    categoryInput.value = '';
                    await loadCategories(data.id);
                } else {
                    alert(data.error || 'Failed to create category');
                }
            } catch (error) {
                console.error('Error:', error);
                alert('Error creating category');
            }
        });
    }
    
    // Load categories and documents
    loadCategories();
    loadDocuments();
});

function loadCategories(selectCategoryId = null) {
    fetch('/api/categories')
        .then(response => response.json())
        .then(categories => {
            // Update category filter
            const categoryFilter = document.getElementById('categoryFilter');
            if (categoryFilter) {
                categoryFilter.innerHTML = '';
                
                // Only show "Select Category" if there are no categories
                if (categories.length === 0) {
                    categoryFilter.innerHTML = '<option value="">Select Category</option>';
                }
                
                // Add existing categories
                categories.forEach(category => {
                    categoryFilter.innerHTML += `<option value="${category.id}">${category.name}</option>`;
                });
                
                // Always add the "Add New Category" option
                categoryFilter.innerHTML += '<option value="new">+ Add New Category</option>';
                
                // Select the new category if provided
                if (selectCategoryId) {
                    categoryFilter.value = selectCategoryId;
                } else if (categories.length > 0 && !categoryFilter.value) {
                    // Select first category by default if none selected
                    categoryFilter.value = categories[0].id;
                }
                
                // Trigger change event to update UI and store previous value
                categoryFilter.dataset.previousValue = categoryFilter.value;
                const newDocBtn = document.querySelector('.btn-new-doc');
                if (newDocBtn) {
                    const selectedValue = categoryFilter.value;
                    newDocBtn.disabled = !selectedValue || selectedValue === 'new' || selectedValue === '';
                }
            }
        })
        .catch(error => {
            console.error('Error loading categories:', error);
        });
}

function loadDocuments() {
    const query = document.getElementById('searchInput').value;
    const categoryId = document.getElementById('categoryFilter').value;
    
    let url = '/api/documents';
    const params = new URLSearchParams();
    if (query) params.append('q', query);
    if (categoryId && categoryId !== 'new') params.append('category', categoryId);
    if (params.toString()) url += '?' + params.toString();
    
    fetch(url)
        .then(response => response.json())
        .then(documents => {
            displayResults(documents);
        })
        .catch(error => {
            console.error('Error loading documents:', error);
        });
}

function displayResults(documents) {
    const tbody = document.getElementById('resultsBody');
    tbody.innerHTML = '';
    
    if (documents.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" class="text-center">No documents found</td></tr>';
        return;
    }
    
    documents.forEach(doc => {
        const row = document.createElement('tr');
        const createdAt = new Date(doc.created_at).toLocaleDateString();
        
        row.innerHTML = `
            <td>
                <a href="${doc.url}" target="_blank" title="${doc.url}">${doc.title || 'Untitled'}</a>
            </td>
            <td>${doc.category_name || '-'}</td>
            <td>${createdAt}</td>
            <td>
                <div class="btn-group">
                    <a href="/view/${doc.id}" class="btn btn-sm btn-primary" target="_blank">Markdown</a>
                    <a href="${doc.url}" class="btn btn-sm btn-secondary" target="_blank">Original</a>
                    <button class="btn btn-sm btn-danger" onclick="deleteDocument('${doc.url}')">Delete</button>
                </div>
            </td>
        `;
        tbody.appendChild(row);
    });
}

async function deleteDocument(url) {
    if (!confirm('Are you sure you want to delete this document?')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/documents/${encodeURIComponent(url)}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            // Reload document list
            loadDocuments();
        } else {
            const data = await response.json();
            alert('Error deleting document: ' + (data.error || 'Unknown error'));
        }
    } catch (error) {
        console.error('Error deleting document:', error);
        alert('Error deleting document. Please try again.');
    }
}
