let currentPage = 1;
const perPage = 10;

// Load documents when page loads
document.addEventListener('DOMContentLoaded', function() {
    const searchForm = document.getElementById('searchForm');
    const searchInput = document.getElementById('searchInput');
    const categoryFilter = document.getElementById('categoryFilter');
    const addDocBtn = document.getElementById('addDocBtn');
    const addCategoryBtn = document.getElementById('addCategoryBtn');
    const newDocBtn = document.querySelector('.btn-new-doc');
    
    // Bootstrap modals
    const newDocModal = new bootstrap.Modal(document.getElementById('newDocModal'));
    const newCategoryModal = new bootstrap.Modal(document.getElementById('newCategoryModal'));
    
    // Update New Doc button state based on category selection
    function updateNewDocButton() {
        if (newDocBtn) {
            const selectedValue = categoryFilter.value;
            newDocBtn.disabled = !selectedValue || selectedValue === 'new' || selectedValue === '';
        }
    }

    // Load categories and documents when page loads
    loadCategories();
    loadDocuments();
    
    // Initially disable New Doc button
    updateNewDocButton();
    
    // Event listeners
    searchForm.addEventListener('submit', function(e) {
        e.preventDefault();
        loadDocuments();
    });
    
    // Handle category filter changes
    if (categoryFilter) {
        categoryFilter.addEventListener('change', function() {
            if (this.value === 'new') {
                this.value = '';  // Reset selection
                newCategoryModal.show();
                updateNewDocButton();
            } else {
                loadDocuments();
                updateNewDocButton();
            }
        });
    }
    
    addDocBtn.addEventListener('click', function() {
        const url = document.getElementById('urlInput').value;
        const categoryId = categoryFilter.value;  // Use the main category filter
        
        if (!url) {
            alert('Please enter a URL');
            return;
        }
        
        // Don't send category_id if it's empty or 'new'
        const requestBody = {
            url: url
        };
        
        if (categoryId && categoryId !== 'new') {
            requestBody.category_id = categoryId;
        }
        
        fetch('/crawl', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(requestBody)
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                newDocModal.hide();
                document.getElementById('urlInput').value = '';
                loadDocuments();
            } else {
                alert('Error: ' + data.error);
            }
        });
    });
    
    addCategoryBtn.addEventListener('click', function() {
        const name = document.getElementById('categoryInput').value;
        
        if (!name) {
            alert('Please enter a category name');
            return;
        }
        
        fetch('/api/categories', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ name: name }),
        })
        .then(response => response.json())
        .then(data => {
            if (data.id) {
                newCategoryModal.hide();
                document.getElementById('categoryInput').value = '';
                // Load categories and select the new one
                loadCategories(data.id);
            } else {
                alert('Error: ' + data.error);
            }
        });
    });
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
    if (!tbody) return;
    
    tbody.innerHTML = '';
    
    if (documents.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" class="text-center">No documents found</td></tr>';
        return;
    }
    
    documents.forEach(doc => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>
                <a href="${doc.url}" target="_blank" title="${doc.url}">${doc.title || 'Untitled'}</a>
            </td>
            <td>${doc.category_name || '-'}</td>
            <td>${new Date(doc.created_at).toLocaleDateString()}</td>
            <td>
                <div class="btn-group">
                    <a href="/view/${encodeURIComponent(doc.url)}" target="_blank" class="btn btn-sm btn-primary">Markdown</a>
                    <a href="${doc.url}" target="_blank" class="btn btn-sm btn-outline-secondary">Original</a>
                </div>
            </td>
        `;
        tbody.appendChild(row);
    });
}

// Handle crawl button click
document.getElementById('crawlButton').addEventListener('click', async () => {
    const urlInput = document.getElementById('urlInput');
    const url = urlInput.value.trim();
    const statusDiv = document.getElementById('crawlStatus');
    const crawlButton = document.getElementById('crawlButton');
    
    if (!url) {
        showCrawlStatus('Please enter a valid URL', 'danger');
        return;
    }
    
    // Disable button and show loading state
    crawlButton.disabled = true;
    crawlButton.innerHTML = 'Crawling...';
    showCrawlStatus('Crawling URL...', 'info');
    
    try {
        const response = await fetch('/crawl', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ url })
        });
        
        const result = await response.json();
        
        if (result.success) {
            showCrawlStatus(`Successfully crawled: ${result.title}`, 'success');
            // Reload documents after successful crawl
            setTimeout(() => {
                loadDocuments();
                // Close modal after 2 seconds
                setTimeout(() => {
                    const modal = bootstrap.Modal.getInstance(document.getElementById('newDocModal'));
                    modal.hide();
                    // Reset form
                    urlInput.value = '';
                    statusDiv.classList.add('d-none');
                }, 2000);
            }, 1000);
        } else {
            showCrawlStatus(`Error: ${result.error}`, 'danger');
        }
    } catch (error) {
        showCrawlStatus(`Error: ${error.message}`, 'danger');
    } finally {
        crawlButton.disabled = false;
        crawlButton.innerHTML = 'Crawl';
    }
});

function showCrawlStatus(message, type) {
    const statusDiv = document.getElementById('crawlStatus');
    statusDiv.className = `alert alert-${type}`;
    statusDiv.classList.remove('d-none');
    statusDiv.textContent = message;
}
