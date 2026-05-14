from __future__ import absolute_import, unicode_literals
import os
from celery import Celery
from celery.schedules import crontab
from core.settings import CELERY_TIMEZONE
from kombu import Queue, Exchange


# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

app = Celery('core')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Define exchanges
basalam_exchange = Exchange('basalam', type='direct')

# Define queues
app.conf.task_queues = [
    Queue('basalam_control', basalam_exchange, routing_key='basalam_control'),
    Queue('basalam_worker_1', basalam_exchange, routing_key='basalam1'),
    # Queue('basalam_worker_2', basalam_exchange, routing_key='basalam2'),
]


app.conf.task_routes = {
    # Basalam control
    'website.tasks.basalam_engine.bs_queue_workers.start_basalam_workers': {'queue': 'basalam_control'},

    # Basalam routine
    'website.tasks.basalam_engine.bs_routine_tasks.prepare_and_queue_basalam_products': {'queue': 'celery'},
}


# Load task modules from all registered Django apps.
app.conf.imports = getattr(app.conf, "imports", ()) + (
    "website.tasks.basalam_engine.bs_queue_workers",
    "website.tasks.basalam_engine.bs_routine_tasks",
)

# Timezone configuration
app.conf.enable_utc = False
app.conf.timezone = CELERY_TIMEZONE

# Beat schedule configuration
app.conf.beat_schedule = {
    "basalam-queue-products": {
        "task": "website.tasks.basalam_engine.bs_routine_tasks.prepare_and_queue_basalam_products",
        "schedule": crontab(minute="*/30"),
        "options": {"queue": "celery"},
    },
    "basalam-start-workers": {
        "task": "website.tasks.basalam_engine.bs_queue_workers.start_basalam_workers",
        "schedule": crontab(minute="*/5"),
        "options": {"queue": "basalam_control"},
    },
}

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request}!')
