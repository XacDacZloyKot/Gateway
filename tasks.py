from celery import Celery
from kombu import Queue
from queue import Empty
from functools import wraps

app = Celery('hello', broker='amqp://guest@localhost//')
app.conf.broker_connection_retry_on_startup = True

task_queues = [
    Queue('message'),
]

# количество запусков в минуту
rate_limits = {
    'message': 60,
}

# автоматически сгенерируем очереди с токенами под все группы, на которые нужен лимит
task_queues += [Queue(name+'_tokens', max_length=2) for name, limit in rate_limits.items()]

app.conf.task_queues = task_queues


@app.task
def token():
    return 1


@app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    for name, limit in rate_limits.items():
        sender.add_periodic_task(
            60 / limit,
            token.signature(queue=name + '_tokens'),
            name=name + '_tokens')


def rate_limit(task_group):
    def decorator_func(func):
        @wraps(func)
        def function(self, *args, **kwargs):
            with self.app.connection_for_read() as conn:
                with conn.SimpleQueue(task_group+'_tokens', no_ack=True, queue_opts={'max_length': 2}) as queue:
                    try:
                        queue.get(block=True, timeout=5)
                        return func(self, *args, **kwargs)
                    except Empty:
                        self.retry(countdown=1)
        return function
    return decorator_func


@app.task(bind=True, max_retries=None)
@rate_limit('message')
def send_request(self, data):
    print('Called message Api 1')
    return {'status': 200}

