/**
 * Home & Board App JavaScript 세션 인증 테스트 케이스
 *
 * 이 파일은 세션 기반 인증, CSRF, CORS 테스트를 수행합니다.
 * 사용법: 브라우저 개발자도구 콘솔에서 실행
 */

class SessionAuthTester {
    constructor() {
        this.testResults = [];
        this.csrfToken = this.getCookie('csrftoken');
        this.baseURL = window.location.origin;
    }

    /**
     * CSRF 토큰 가져오기
     */
    getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    /**
     * 테스트 결과 로깅
     */
    logResult(testName, success, details, response = null) {
        const result = {
            test: testName,
            success: success,
            details: details,
            timestamp: new Date().toISOString(),
            response: response
        };
        this.testResults.push(result);

        const icon = success ? '✅' : '❌';
        console.log(`${icon} [${testName}] ${details}`);
        if (response) {
            console.log('   Response:', response);
        }
    }

    /**
     * 1. Home App 인증 테스트
     */
    async testHomeAuth() {
        console.log('\\n=== Home App 세션 인증 테스트 ===');

        try {
            const response = await fetch('/home/api/auth-test/', {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.csrfToken
                },
                credentials: 'include'
            });

            const data = await response.json();

            if (response.ok) {
                this.logResult(
                    'Home Auth Test',
                    true,
                    `인증 성공 - 사용자: ${data.username || 'Anonymous'}, ID: ${data.user_id || 'None'}`,
                    data
                );
                return data;
            } else {
                this.logResult(
                    'Home Auth Test',
                    false,
                    `HTTP ${response.status}: ${data.detail || 'Unknown error'}`,
                    data
                );
                return null;
            }
        } catch (error) {
            this.logResult(
                'Home Auth Test',
                false,
                `네트워크 오류: ${error.message}`,
                error
            );
            return null;
        }
    }

    /**
     * 2. Board App 인증 테스트
     */
    async testBoardAuth() {
        console.log('\\n=== Board App 세션 인증 테스트 ===');

        try {
            const response = await fetch('/board/api/auth-test/', {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.csrfToken
                },
                credentials: 'include'
            });

            const data = await response.json();

            if (response.ok) {
                this.logResult(
                    'Board Auth Test',
                    true,
                    `인증 성공 - 사용자: ${data.username || 'Anonymous'}, 경로: ${data.current_path || 'Unknown'}`,
                    data
                );
                return data;
            } else {
                this.logResult(
                    'Board Auth Test',
                    false,
                    `HTTP ${response.status}: ${data.detail || 'Unknown error'}`,
                    data
                );
                return null;
            }
        } catch (error) {
            this.logResult(
                'Board Auth Test',
                false,
                `네트워크 오류: ${error.message}`,
                error
            );
            return null;
        }
    }

    /**
     * 3. CSRF 토큰 테스트
     */
    async testCSRF() {
        console.log('\\n=== CSRF 토큰 테스트 ===');

        // CSRF 토큰 존재 여부 확인
        if (!this.csrfToken) {
            this.logResult(
                'CSRF Token Check',
                false,
                'CSRF 토큰이 쿠키에서 발견되지 않음'
            );
            return false;
        }

        this.logResult(
            'CSRF Token Check',
            true,
            `CSRF 토큰 발견: ${this.csrfToken.substring(0, 10)}...`
        );

        // CSRF 토큰 없이 POST 요청 테스트 (실패해야 함)
        try {
            const response = await fetch('/home/api/search/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    // X-CSRFToken 헤더 의도적으로 생략
                },
                credentials: 'include',
                body: JSON.stringify({ query: 'CSRF 테스트 쿼리' })
            });

            if (response.status === 403) {
                this.logResult(
                    'CSRF Protection Test',
                    true,
                    'CSRF 보호가 정상 작동 - 403 Forbidden 응답'
                );
            } else {
                this.logResult(
                    'CSRF Protection Test',
                    false,
                    `예상과 다른 응답: HTTP ${response.status}`
                );
            }
        } catch (error) {
            this.logResult(
                'CSRF Protection Test',
                false,
                `CSRF 테스트 중 오류: ${error.message}`
            );
        }

        return true;
    }

    /**
     * 4. CORS 테스트 (다른 origin에서의 요청 시뮬레이션)
     */
    async testCORS() {
        console.log('\\n=== CORS 설정 테스트 ===');

        // 현재 origin 확인
        const currentOrigin = window.location.origin;
        this.logResult(
            'Current Origin',
            true,
            `현재 origin: ${currentOrigin}`
        );

        // credentials: 'include' 설정으로 요청
        try {
            const response = await fetch('/home/api/auth-test/', {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.csrfToken,
                    'Origin': currentOrigin
                },
                credentials: 'include'
            });

            if (response.ok) {
                this.logResult(
                    'CORS Credentials Test',
                    true,
                    'credentials: include 설정으로 요청 성공'
                );
            } else {
                this.logResult(
                    'CORS Credentials Test',
                    false,
                    `HTTP ${response.status} 응답`
                );
            }
        } catch (error) {
            this.logResult(
                'CORS Credentials Test',
                false,
                `CORS 테스트 중 오류: ${error.message}`
            );
        }
    }

    /**
     * 5. 세션 정보 상세 테스트
     */
    async testSessionDetails() {
        console.log('\\n=== 세션 정보 상세 테스트 ===');

        // 쿠키 정보 확인
        const cookies = document.cookie.split(';').map(cookie => cookie.trim());
        const sessionCookie = cookies.find(cookie => cookie.startsWith('sessionid='));
        const csrfCookie = cookies.find(cookie => cookie.startsWith('csrftoken='));

        this.logResult(
            'Session Cookie Check',
            !!sessionCookie,
            sessionCookie ? '세션 쿠키 발견' : '세션 쿠키 없음'
        );

        this.logResult(
            'CSRF Cookie Check',
            !!csrfCookie,
            csrfCookie ? 'CSRF 쿠키 발견' : 'CSRF 쿠키 없음'
        );

        // 현재 사용자 정보
        const homeAuthData = await this.testHomeAuth();
        if (homeAuthData) {
            this.logResult(
                'User Session Info',
                true,
                `사용자 ID: ${homeAuthData.user_id}, 인증됨: ${homeAuthData.is_authenticated}, 세션 존재: ${homeAuthData.session_exists}`
            );
        }
    }

    /**
     * 6. API 엔드포인트 연결성 테스트
     */
    async testAPIConnectivity() {
        console.log('\\n=== API 엔드포인트 연결성 테스트 ===');

        const endpoints = [
            { name: 'Home Auth API', url: '/home/api/auth-test/' },
            { name: 'Board Auth API', url: '/board/api/auth-test/' },
            { name: 'Home Search API', url: '/home/api/search/' },
            { name: 'API Schema', url: '/api/schema/' },
            { name: 'API Docs', url: '/api/docs/' }
        ];

        for (const endpoint of endpoints) {
            try {
                const response = await fetch(endpoint.url, {
                    method: 'GET',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': this.csrfToken
                    },
                    credentials: 'include'
                });

                const success = response.status !== 404;
                this.logResult(
                    `API Endpoint: ${endpoint.name}`,
                    success,
                    `HTTP ${response.status} ${response.statusText}`
                );
            } catch (error) {
                this.logResult(
                    `API Endpoint: ${endpoint.name}`,
                    false,
                    `연결 실패: ${error.message}`
                );
            }
        }
    }

    /**
     * 모든 테스트 실행
     */
    async runAllTests() {
        console.log('🚀 세션 인증, CSRF, CORS 종합 테스트 시작');
        console.log('='.repeat(60));

        const startTime = Date.now();

        // 테스트 순서대로 실행
        await this.testSessionDetails();
        await this.testHomeAuth();
        await this.testBoardAuth();
        await this.testCSRF();
        await this.testCORS();
        await this.testAPIConnectivity();

        const endTime = Date.now();
        const duration = endTime - startTime;

        console.log('\\n' + '='.repeat(60));
        console.log('📊 테스트 결과 요약');
        console.log('='.repeat(60));

        const successCount = this.testResults.filter(r => r.success).length;
        const totalCount = this.testResults.length;
        const successRate = ((successCount / totalCount) * 100).toFixed(1);

        console.log(`총 테스트: ${totalCount}개`);
        console.log(`성공: ${successCount}개`);
        console.log(`실패: ${totalCount - successCount}개`);
        console.log(`성공률: ${successRate}%`);
        console.log(`실행 시간: ${duration}ms`);

        // 실패한 테스트 상세 출력
        const failedTests = this.testResults.filter(r => !r.success);
        if (failedTests.length > 0) {
            console.log('\\n❌ 실패한 테스트:');
            failedTests.forEach(test => {
                console.log(`  - ${test.test}: ${test.details}`);
            });
        }

        console.log('\\n✅ 테스트 완료!');
        console.log('상세 결과는 sessionAuthTester.testResults에서 확인할 수 있습니다.');

        return {
            total: totalCount,
            success: successCount,
            failed: totalCount - successCount,
            successRate: successRate,
            duration: duration,
            results: this.testResults
        };
    }
}

// 전역 인스턴스 생성
const sessionAuthTester = new SessionAuthTester();

// 사용 예시 출력
console.log(`
🔧 세션 인증 테스트 도구 로드됨

사용법:
1. 모든 테스트 실행: sessionAuthTester.runAllTests()
2. 개별 테스트:
   - sessionAuthTester.testHomeAuth()
   - sessionAuthTester.testBoardAuth()
   - sessionAuthTester.testCSRF()
   - sessionAuthTester.testCORS()
   - sessionAuthTester.testSessionDetails()
   - sessionAuthTester.testAPIConnectivity()

예시:
sessionAuthTester.runAllTests().then(result => console.log('최종 결과:', result));
`);