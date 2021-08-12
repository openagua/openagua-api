from flask import current_app as app
from celery import Celery


def run_model_rabbitmq(model, run_key, model_kwargs):
    model_key = model.key
    queue_name = 'model-{}'.format(model_key)
    if run_key:
        queue_name += '-{}'.format(run_key)
    vhost = 'model-{}'.format(model_key)

    queue = app.rabbitmq.get_queue(vhost, queue_name)

    if queue.status_code == 404:
        return 'No computer is set up for this run'

    # Celery for starting tasks
    broker_url = 'pyamqp://{username}:{password}@{hostname}:5672/{vhost}'.format(
        username=app.config['RABBITMQ_DEFAULT_USERNAME'],
        password=app.config['RABBITMQ_DEFAULT_PASSWORD'],
        hostname=app.config.get('RABBITMQ_HOST'),
        vhost=vhost
    )
    celery = Celery('openagua', broker=broker_url)
    celery.conf.update(
        task_default_exchange='tasks',
        result_expires=3600,
        broker_pool_limit=None,
        # broker_connection_max_retries=1,
    )
    signature = celery.signature('model.run', expires=3600, retry=False)
    resp = signature.apply_async(args=(), kwargs=model_kwargs, queue=queue_name, routing_key=queue_name)

    return
