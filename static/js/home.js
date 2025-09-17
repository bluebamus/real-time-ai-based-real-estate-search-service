document.addEventListener('DOMContentLoaded', function() {
    console.log('home.js script loaded and DOMContentLoaded event fired.'); // Added log
    const searchInput = document.getElementById('nlp-search');
    const searchBtn = document.getElementById('search-btn');
    const loadingSpinner = document.getElementById('loading-spinner');
    const errorMessageDiv = document.getElementById('error-message');

    // THIS IS A DELIBERATE SYNTAX ERROR FOR DEBUGGING
    // REMOVE THIS LINE AFTER DEBUGGING


    // Function to get CSRF token from cookies
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                // Does this cookie string begin with the name we want?
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    function showLoading() {
        loadingSpinner.style.display = 'block';
        errorMessageDiv.style.display = 'none';
        errorMessageDiv.textContent = '';
        searchBtn.disabled = true;
        searchInput.disabled = true;
    }

    function hideLoading() {
        loadingSpinner.style.display = 'none';
        searchBtn.disabled = false;
        searchInput.disabled = false;
    }

    function showMessage(message, isError = true) {
        errorMessageDiv.textContent = message;
        errorMessageDiv.className = isError ? 'mt-3 text-danger' : 'mt-3 text-success';
        errorMessageDiv.style.display = 'block';
    }

    searchBtn.addEventListener('click', async function() {
        console.log('Search button clicked.'); // Added log
        const query = searchInput.value.trim();
        if (!query) {
            showMessage('검색어를 입력해주세요.', true);
            return;
        }

        showLoading();

        try {
            const response = await fetch('/home/api/search/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: JSON.stringify({ query: query })
            });

            const data = await response.json();

            if (response.ok) {
                showMessage('검색이 성공적으로 완료되었습니다!', false);
                console.log('Search successful:', data);
                // Redirect to results page or display results
                if (data.redirect_url) {
                    window.location.href = data.redirect_url;
                }
            } else {
                showMessage(data.error || '알 수 없는 오류가 발생했습니다.', true);
                console.error('Search failed:', data);
            }
        }
        catch (error) {
            console.error('Fetch error:', error);
            showMessage('네트워크 오류 또는 서버 응답이 없습니다.', true);
        } finally {
            hideLoading();
        }
    });
});
