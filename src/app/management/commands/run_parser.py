from aiohttp import web
from aiohttp.web import get
from django.core.management.base import BaseCommand

from app.internal.parser import Parser


class Command(BaseCommand):
    """
    Command class for run parser.
    """

    def handle(self, *args, **options):
        parser = Parser()
        routes = [
            get("/run_parser", parser.get),
        ]
        app = web.Application()
        app.add_routes(routes)
        web.run_app(app)
