"""
Celery configuration for Django project

This module configures Celery for asynchronous task processing including:
- Redis broker configuration
- Celery Beat scheduler for periodic tasks
- Task routing and serialization settings
- Periodic task definitions
"""

import os
from celery import Celery
from celery.schedules import crontab
from django.conf import settings

# Set the default Django settings module for the 'celery' program
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Create Celery application
app = Celery('real_estate_project')

# Configure Celery using settings from Django settings.py
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django app configs
app.autodiscover_tasks()


# Celery Beat periodic task schedule
app.conf.beat_schedule = {
    'update-recommendations': {
        'task': 'utils.tasks.update_recommendations',
        'schedule': 300.0,  # 5분마다 실행 (300초)
        'options': {
            'priority': 6,
            'expires': 240,  # 4분 후 만료
        }
    },
    'backup-redis-to-database': {
        'task': 'utils.tasks.backup_redis_scores_to_database',
        'schedule': 600.0,  # 10분마다 실행 (600초)
        'options': {
            'priority': 4,
            'expires': 540,  # 9분 후 만료
        }
    },
    'cleanup-old-search-history': {
        'task': 'utils.tasks.cleanup_old_search_history',
        'schedule': crontab(hour=2, minute=0),  # 매일 새벽 2시
        'options': {
            'priority': 2,
        }
    },
}

# Celery configuration
app.conf.update(
    # Message Broker 설정
    broker_url=getattr(settings, 'CELERY_BROKER_URL', 'redis://localhost:6379/0'),
    result_backend=getattr(settings, 'CELERY_RESULT_BACKEND', 'redis://localhost:6379/0'),

    # Serialization 설정
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',

    # 시간대 설정
    timezone='Asia/Seoul',
    enable_utc=True,

    # Task 실행 설정
    task_track_started=True,
    task_time_limit=30 * 60,  # 30분 제한
    task_soft_time_limit=25 * 60,  # 25분 소프트 제한

    # Worker 설정
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    worker_disable_rate_limits=False,

    # 결과 백엔드 설정
    result_expires=3600,  # 1시간 후 결과 만료
    result_backend_transport_options={
        'master_name': 'mymaster',
        'retry_on_timeout': True,
    },

    # Beat 스케줄러 설정
    beat_scheduler='django_celery_beat.schedulers:DatabaseScheduler',
    beat_schedule_filename='celerybeat-schedule',

    # Task 라우팅
    task_routes={
        'utils.tasks.update_recommendations': {'queue': 'recommendations'},
        'utils.tasks.backup_redis_scores_to_database': {'queue': 'backup'},
        'utils.tasks.cleanup_old_search_history': {'queue': 'maintenance'},
        'utils.tasks.update_user_keyword_score': {'queue': 'user_activity'},
    },

    # 큐 우선순위
    task_default_queue='default',
    task_default_exchange='default',
    task_default_exchange_type='direct',
    task_default_routing_key='default',

    # Worker 큐 설정
    task_queues={
        'default': {
            'exchange': 'default',
            'routing_key': 'default',
        },
        'recommendations': {
            'exchange': 'recommendations',
            'routing_key': 'recommendations',
        },
        'backup': {
            'exchange': 'backup',
            'routing_key': 'backup',
        },
        'maintenance': {
            'exchange': 'maintenance',
            'routing_key': 'maintenance',
        },
        'user_activity': {
            'exchange': 'user_activity',
            'routing_key': 'user_activity',
        },
    },

    # 재시도 설정
    task_annotations={
        '*': {'rate_limit': '10/s'},
        'utils.tasks.update_recommendations': {'rate_limit': '1/m'},
        'utils.tasks.backup_redis_scores_to_database': {'rate_limit': '1/m'},
    },

    # 모니터링 설정
    worker_send_task_events=True,
    task_send_sent_event=True,

    # 로깅 설정
    worker_log_format='[%(asctime)s: %(levelname)s/%(processName)s] %(message)s',
    worker_task_log_format='[%(asctime)s: %(levelname)s/%(processName)s][%(task_name)s(%(task_id)s)] %(message)s',

    # 에러 핸들링
    task_reject_on_worker_lost=True,
    task_acks_late=True,
)


@app.task(bind=True)
def debug_task(self):
    """
    디버그용 테스트 태스크

    Args:
        self: Celery task instance

    Returns:
        str: 디버그 정보
    """
    print(f'Request: {self.request!r}')
    return 'Debug task completed successfully'


@app.task(bind=True, autoretry_for=(Exception,), retry_kwargs={'max_retries': 3, 'countdown': 60})
def health_check_task(self):
    """
    Celery 헬스 체크 태스크

    Redis 연결, Database 연결 등을 확인하여 시스템 상태를 점검합니다.

    Returns:
        dict: 헬스 체크 결과
    """
    import redis
    from django.db import connection
    from django.core.cache import cache

    health_status = {
        'celery': True,
        'redis': False,
        'database': False,
        'cache': False,
        'timestamp': None
    }

    try:
        # Redis 연결 확인
        redis_client = redis.StrictRedis(
            host=getattr(settings, 'REDIS_HOST', 'localhost'),
            port=getattr(settings, 'REDIS_PORT', 6379),
            db=getattr(settings, 'REDIS_DB', 0)
        )
        redis_client.ping()
        health_status['redis'] = True

        # Database 연결 확인
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
        health_status['database'] = True

        # Cache 연결 확인
        cache.set('health_check', 'ok', 30)
        if cache.get('health_check') == 'ok':
            health_status['cache'] = True

        # 타임스탬프 추가
        from datetime import datetime
        health_status['timestamp'] = datetime.now().isoformat()

    except Exception as e:
        health_status['error'] = str(e)
        raise

    return health_status


# Django 재시작 시 Redis 복원 작업 스케줄링
@app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    """
    Celery 설정 후 주기적 작업 설정

    Django 시작 시 한 번 실행되는 초기화 작업들을 스케줄링합니다.
    """
    # Django 재시작 시 Redis 복원 (5초 후 실행)
    sender.add_periodic_task(
        5.0,
        restore_redis_on_startup.s(),
        name='restore_redis_on_startup',
        expires=30.0
    )

    # 헬스 체크 (1분마다)
    sender.add_periodic_task(
        60.0,
        health_check_task.s(),
        name='health_check_every_minute'
    )


@app.task
def restore_redis_on_startup():
    """
    Django 재시작 시 Redis 복원 작업

    Database에 백업된 키워드 스코어와 추천 캐시를 Redis로 복원합니다.
    """
    from utils.tasks import restore_redis_from_database

    try:
        result = restore_redis_from_database.delay()
        return {'status': 'scheduled', 'task_id': result.id}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}


# Worker 시작 시 실행되는 작업
@app.task
def worker_startup_task():
    """
    Worker 시작 시 실행되는 초기화 작업

    Worker가 시작될 때 필요한 초기화 작업을 수행합니다.
    """
    import logging
    logger = logging.getLogger(__name__)

    logger.info("Celery worker started successfully")

    # Redis 연결 테스트
    try:
        import redis
        redis_client = redis.StrictRedis(
            host=getattr(settings, 'REDIS_HOST', 'localhost'),
            port=getattr(settings, 'REDIS_PORT', 6379),
            db=getattr(settings, 'REDIS_DB', 0)
        )
        redis_client.ping()
        logger.info("Redis connection successful")
    except Exception as e:
        logger.error(f"Redis connection failed: {e}")

    return "Worker startup completed"


if __name__ == '__main__':
    app.start()