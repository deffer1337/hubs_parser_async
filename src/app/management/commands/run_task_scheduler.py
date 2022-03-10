import time

import schedule
from django.core.management import BaseCommand

from app.internal.models.hub import Hub
from app.internal.task_scheduler import run_parser


class Command(BaseCommand):
    """
    Command class for run task scheduler.
    """

    def __init__(self):
        super().__init__()
        self.hubs = set()

    def _schedule_new_hub(self) -> None:
        """
        Scheduling new hub
        """
        hubs = {Hub.objects.all()}
        unplanned_hubs = hubs.difference(self.hubs)
        for hub in unplanned_hubs:
            self.hubs.add(hub)
            schedule.every(hub.crawl_period).minutes.do(lambda: run_parser(hub.id))

    def _run_parser(self, id):
        return lambda: run_parser(id)

    def handle(self, *args, **options):
        for hub in Hub.objects.all():
            self.hubs.add(hub)
            schedule.every(hub.crawl_period).minutes.do(self._run_parser(hub.id))

        schedule.every(1).hours.do(self._schedule_new_hub)

        while True:
            schedule.run_pending()
            time.sleep(1)
