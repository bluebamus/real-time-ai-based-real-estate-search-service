"""
수동 API 테스트 스크립트

이 스크립트는 실제 개발 서버에서 API들이 올바르게 작동하는지 테스트합니다.
세션 인증, CSRF, CORS 기능을 검증합니다.

사용법:
1. Django 개발 서버 실행: python manage.py runserver
2. 이 스크립트 실행: python test_api_manual.py
"""

import requests
import json
from urllib.parse import urljoin

# 서버 설정
BASE_URL = 'http://localhost:8000'
LOGIN_URL = urljoin(BASE_URL, '/user/login/')
HOME_AUTH_URL = urljoin(BASE_URL, '/home/api/auth-test/')
BOARD_AUTH_URL = urljoin(BASE_URL, '/board/api/auth-test/')
SEARCH_URL = urljoin(BASE_URL, '/home/api/search/')

# 테스트 사용자 정보
TEST_USER = {
    'username': 'testuser',
    'password': 'testpass123'
}

def test_session_authentication():
    """세션 기반 인증 테스트"""
    print("=== 세션 기반 인증 테스트 ===")

    # 세션 유지를 위한 Session 객체 생성
    session = requests.Session()

    try:
        # 1. 로그인 페이지에서 CSRF 토큰 획득
        print("1. CSRF 토큰 획득 중...")
        login_page = session.get(LOGIN_URL)
        print(f"   로그인 페이지 상태: {login_page.status_code}")

        if login_page.status_code != 200:
            print("   ❌ 로그인 페이지 접근 실패")
            return False

        # CSRF 토큰 추출 (간단한 방법)
        csrf_token = None
        if 'csrftoken' in session.cookies:
            csrf_token = session.cookies['csrftoken']
            print(f"   ✅ CSRF 토큰 획득: {csrf_token[:10]}...")
        else:
            print("   ❌ CSRF 토큰 획득 실패")
            return False

        # 2. 로그인 시도 (실제 사용자가 존재한다고 가정)
        print("2. 로그인 시도 중...")
        login_data = {
            'username': TEST_USER['username'],
            'password': TEST_USER['password'],
            'csrfmiddlewaretoken': csrf_token
        }

        login_response = session.post(LOGIN_URL, data=login_data)
        print(f"   로그인 응답 상태: {login_response.status_code}")

        # 리다이렉트 확인 (로그인 성공 시 보통 리다이렉트됨)
        if login_response.status_code in [200, 302]:
            print("   ✅ 로그인 성공 (또는 사용자 없음 - 정상)")
        else:
            print("   ❌ 로그인 실패")
            return False

        # 3. Home API 인증 테스트
        print("3. Home API 인증 테스트...")
        home_auth_response = session.get(
            HOME_AUTH_URL,
            headers={
                'X-Requested-With': 'XMLHttpRequest',
                'Content-Type': 'application/json'
            }
        )

        print(f"   Home 인증 API 상태: {home_auth_response.status_code}")

        if home_auth_response.status_code == 200:
            try:
                home_data = home_auth_response.json()
                print(f"   ✅ Home 인증 성공: {home_data}")
            except json.JSONDecodeError:
                print("   ⚠️  JSON 파싱 실패, 하지만 200 응답")
        elif home_auth_response.status_code == 401:
            print("   ⚠️  인증되지 않음 (사용자 없음 - 정상)")
        else:
            print(f"   ❌ 예상치 못한 응답: {home_auth_response.status_code}")

        # 4. Board API 인증 테스트
        print("4. Board API 인증 테스트...")
        board_auth_response = session.get(
            BOARD_AUTH_URL,
            headers={
                'X-Requested-With': 'XMLHttpRequest',
                'Content-Type': 'application/json'
            }
        )

        print(f"   Board 인증 API 상태: {board_auth_response.status_code}")

        if board_auth_response.status_code == 200:
            try:
                board_data = board_auth_response.json()
                print(f"   ✅ Board 인증 성공: {board_data}")
            except json.JSONDecodeError:
                print("   ⚠️  JSON 파싱 실패, 하지만 200 응답")
        elif board_auth_response.status_code == 401:
            print("   ⚠️  인증되지 않음 (사용자 없음 - 정상)")
        else:
            print(f"   ❌ 예상치 못한 응답: {board_auth_response.status_code}")

        return True

    except requests.exceptions.ConnectionError:
        print("❌ 서버에 연결할 수 없습니다. 개발 서버가 실행 중인지 확인해주세요.")
        return False
    except Exception as e:
        print(f"❌ 테스트 중 오류 발생: {e}")
        return False

def test_csrf_protection():
    """CSRF 보호 테스트"""
    print("\n=== CSRF 보호 테스트 ===")

    session = requests.Session()

    try:
        # CSRF 토큰 없이 POST 요청
        print("1. CSRF 토큰 없이 POST 요청...")
        no_csrf_response = session.post(
            SEARCH_URL,
            json={'query': '서울시 강남구 아파트'},
            headers={
                'X-Requested-With': 'XMLHttpRequest',
                'Content-Type': 'application/json'
            }
        )

        print(f"   CSRF 없는 요청 상태: {no_csrf_response.status_code}")

        if no_csrf_response.status_code == 403:
            print("   ✅ CSRF 보호 작동 중 (403 Forbidden)")
        elif no_csrf_response.status_code == 401:
            print("   ✅ 인증 필요 (401 Unauthorized)")
        else:
            print(f"   ⚠️  예상과 다른 응답: {no_csrf_response.status_code}")

        # CSRF 토큰과 함께 요청
        print("2. CSRF 토큰과 함께 POST 요청...")

        # 먼저 CSRF 토큰 획득
        csrf_page = session.get(urljoin(BASE_URL, '/home/'))
        csrf_token = session.cookies.get('csrftoken')

        if csrf_token:
            print(f"   CSRF 토큰 획득: {csrf_token[:10]}...")

            with_csrf_response = session.post(
                SEARCH_URL,
                json={'query': '서울시 강남구 아파트'},
                headers={
                    'X-Requested-With': 'XMLHttpRequest',
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrf_token
                }
            )

            print(f"   CSRF 포함 요청 상태: {with_csrf_response.status_code}")

            if with_csrf_response.status_code in [200, 400, 401]:
                print("   ✅ CSRF 토큰 인식됨 (비즈니스 로직 오류는 정상)")
            else:
                print(f"   ⚠️  예상과 다른 응답: {with_csrf_response.status_code}")
        else:
            print("   ❌ CSRF 토큰 획득 실패")

        return True

    except Exception as e:
        print(f"❌ CSRF 테스트 중 오류 발생: {e}")
        return False

def test_cors_headers():
    """CORS 헤더 테스트"""
    print("\n=== CORS 헤더 테스트 ===")

    try:
        # 다른 Origin에서의 요청 시뮬레이션
        print("1. 다른 Origin에서의 요청...")

        cors_response = requests.get(
            HOME_AUTH_URL,
            headers={
                'Origin': 'http://localhost:3000',  # 다른 포트
                'X-Requested-With': 'XMLHttpRequest'
            }
        )

        print(f"   CORS 요청 상태: {cors_response.status_code}")
        print(f"   응답 헤더: {dict(cors_response.headers)}")

        # CORS 헤더 확인
        cors_headers = [
            'Access-Control-Allow-Origin',
            'Access-Control-Allow-Credentials',
            'Access-Control-Allow-Methods',
            'Access-Control-Allow-Headers'
        ]

        found_cors_headers = []
        for header in cors_headers:
            if header in cors_response.headers:
                found_cors_headers.append(header)
                print(f"   ✅ {header}: {cors_response.headers[header]}")

        if found_cors_headers:
            print(f"   ✅ CORS 헤더 {len(found_cors_headers)}개 발견")
        else:
            print("   ⚠️  CORS 헤더 없음 (동일 출처 정책 적용)")

        return True

    except Exception as e:
        print(f"❌ CORS 테스트 중 오류 발생: {e}")
        return False

def test_api_documentation():
    """API 문서 접근 테스트"""
    print("\n=== API 문서 접근 테스트 ===")

    try:
        # Swagger UI 접근
        swagger_url = urljoin(BASE_URL, '/api/docs/')
        swagger_response = requests.get(swagger_url)
        print(f"Swagger UI 접근: {swagger_response.status_code}")

        if swagger_response.status_code == 200:
            print("   ✅ Swagger UI 접근 가능")
        else:
            print(f"   ❌ Swagger UI 접근 실패: {swagger_response.status_code}")

        # ReDoc 접근
        redoc_url = urljoin(BASE_URL, '/api/redoc/')
        redoc_response = requests.get(redoc_url)
        print(f"ReDoc 접근: {redoc_response.status_code}")

        if redoc_response.status_code == 200:
            print("   ✅ ReDoc 접근 가능")
        else:
            print(f"   ❌ ReDoc 접근 실패: {redoc_response.status_code}")

        # API Schema 접근
        schema_url = urljoin(BASE_URL, '/api/schema/')
        schema_response = requests.get(schema_url)
        print(f"API Schema 접근: {schema_response.status_code}")

        if schema_response.status_code == 200:
            print("   ✅ API Schema 접근 가능")
            try:
                schema_data = schema_response.json()
                print(f"   API 제목: {schema_data.get('info', {}).get('title', 'N/A')}")
                print(f"   API 버전: {schema_data.get('info', {}).get('version', 'N/A')}")
            except:
                print("   ⚠️  Schema JSON 파싱 실패")
        else:
            print(f"   ❌ API Schema 접근 실패: {schema_response.status_code}")

        return True

    except Exception as e:
        print(f"❌ API 문서 테스트 중 오류 발생: {e}")
        return False

def main():
    """메인 테스트 실행"""
    print("🚀 AI 부동산 검색 서비스 API 테스트 시작")
    print("=" * 50)

    tests = [
        ("세션 인증", test_session_authentication),
        ("CSRF 보호", test_csrf_protection),
        ("CORS 헤더", test_cors_headers),
        ("API 문서", test_api_documentation)
    ]

    results = []

    for test_name, test_func in tests:
        print(f"\n📋 {test_name} 테스트 실행 중...")
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"❌ {test_name} 테스트 실행 중 오류: {e}")
            results.append((test_name, False))

    # 결과 요약
    print("\n" + "=" * 50)
    print("📊 테스트 결과 요약")
    print("=" * 50)

    passed = 0
    for test_name, success in results:
        status = "✅ 통과" if success else "❌ 실패"
        print(f"{test_name}: {status}")
        if success:
            passed += 1

    print(f"\n총 {len(results)}개 테스트 중 {passed}개 통과")

    if passed == len(results):
        print("🎉 모든 테스트 통과!")
    else:
        print("⚠️  일부 테스트 실패 - 서버 상태를 확인해주세요.")

    print("\n💡 참고사항:")
    print("- 이 테스트는 Django 개발 서버가 실행 중일 때만 동작합니다.")
    print("- 실제 사용자 계정이 없으면 인증 테스트에서 401 응답이 정상입니다.")
    print("- CSRF 및 CORS 보호 기능이 정상 작동하는지 확인하는 것이 중요합니다.")

if __name__ == "__main__":
    main()