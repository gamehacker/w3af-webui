# -*- coding: utf-8 -*-
from logging import getLogger
from dateutil.relativedelta import relativedelta

from django.core.management import call_command

from celery.task import task
from celery.schedules import schedule
from djcelery.models import PeriodicTask
from djcelery.models import IntervalSchedule
from datetime import datetime

from w3af_webui.models import ScanTask

logger = getLogger(__name__)

@task()
def delay_task(*args, **kwargs):
    """
    Run task at time
    args = PeriodicTask.id
    """
    try:
        task_id = args[0]
        print 'task id = %s' % task_id
        task = PeriodicTask.objects.get(task='w3af_webui.tasks.delay_task',
                                        name='delay_%s' % task_id,
                                        )
        task.interval = None
        task.enabled = False
        task.save()
        scan_create_start(task_id)
    except Exception, e:
        logger.error("delay task exception %s" % e)
        raise Exception, e


@task()
def monthly_task(*args, **kwargs):
    try:
        task_id = args[0]
        task = PeriodicTask.objects.get(task='w3af_webui.tasks.monthly_task',
                                        name=task_id,
                                        )
        now = datetime.now()
        next_time = now + relativedelta(months=+1)
        delta = next_time - now
        interval = IntervalSchedule.from_schedule(schedule(delta))
        interval.save()
        logger.info('set interval %s for celery task %s' % (
                    interval,
                    task.name,
                    ))
        task.interval = interval
        task.save()
        scan_create_start(task_id)
    except Exception, e:
        logger.error("monthly task exception %s" % e)
        raise Exception, e


@task()
def scan_start(scan_id, callback_func, *args, **kwargs):
    '''
    Start exist scan
    args = [scan_id, ]
    '''
    try:
        call_command('w3af_run', scan_id)
    except Exception, e:
        logger.error("task.py scan_start exception %s" % e)
        callback_func(scan_id)
        raise Exception, e


@task()
def scan_create_start(*args, **kwargs):
    '''Start scan task and create new scan for it
    args = [scan_task_id, ]
    '''
    try:
        scan_task = ScanTask.objects.get(pk=int(args[0]))
        scan = scan_task.create_scan(scan_task.user)
        call_command('w3af_run', scan.id)
    except ScanTask.DoesNotExist, e:
        logger.error("task.py scan_create_start exception %s" % e)
        raise ScanTask.DoesNotExist, e
    except Exception, e:
        logger.error("task.py scan_create_start exception %s" % e)
        message = (' There was some problems with celery and '
                   ' this task was failed by find_scan celery task')
        scan.unlock_task(message)
        raise Exception, e
