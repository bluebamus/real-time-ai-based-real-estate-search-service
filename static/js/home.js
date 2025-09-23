document.addEventListener('DOMContentLoaded', function() {
    console.log('home.js script loaded and DOMContentLoaded event fired.'); // Added log
    const searchInput = document.getElementById('nlp-search');
    const searchBtn = document.getElementById('search-btn');
    const loadingSpinner = document.getElementById('loading-spinner');
    const errorMessageDiv = document.getElementById('error-message');

    // THIS IS A DELIBERATE SYNTAX ERROR FOR DEBUGGING
    // REMOVE THIS LINE AFTER DEBUGGING

    // 자동 인증 테스트 실행
    performAuthTest();


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

    // 인증 테스트 함수
    async function performAuthTest() {
        console.log('Starting authentication test...');
        try {
            const response = await fetch('/home/api/auth-test/', {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                credentials: 'include'
            });

            const data = await response.json();

            if (response.ok) {
                console.log('=== Client Auth Test Result ===');
                console.log('Status:', data.status);
                console.log('Is Authenticated:', data.is_authenticated);
                console.log('Username:', data.username);
                console.log('User ID:', data.user_id);
                console.log('Session Exists:', data.session_exists);
                console.log('Message:', data.message);
                console.log('==============================');

                // 사용자에게 시각적 피드백 제공 (선택적)
                if (data.is_authenticated) {
                    console.log('✅ 인증 성공: 세션 기반 인증이 정상 작동 중');
                    // 추가적인 기능적 확인: 검색 버튼 활성화 등
                    searchBtn.disabled = false;
                    searchInput.disabled = false;
                } else {
                    console.log('❌ 인증 실패: 로그인이 필요합니다');
                    // 사용자를 로그인 페이지로 리다이렉트하거나 메시지 표시
                    showMessage('로그인이 필요합니다. 로그인 페이지로 이동합니다.', true);
                    setTimeout(() => {
                        window.location.href = '/user/login/';
                    }, 2000);
                }
            } else {
                console.error('Auth test failed:', data);
                showMessage('인증 테스트 중 오류가 발생했습니다.', true);
            }
        } catch (error) {
            console.error('Auth test error:', error);
            console.log('❌ 인증 테스트 실행 실패: 네트워크 오류 또는 서버 응답 없음');
        }
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
                credentials: 'include',
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
