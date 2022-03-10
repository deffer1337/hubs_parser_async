import asyncio
from typing import Tuple
from urllib.parse import urljoin

import aiohttp
from aiohttp.client import ClientSession
from aiohttp.web import Request, json_response
from asgiref.sync import sync_to_async
from django.core.exceptions import ObjectDoesNotExist
from pydantic import BaseModel, Field, ValidationError, validator

from app.internal.models.hub import Hub
from app.internal.models.publication import Publication
from app.internal.services.hub_services import get_urls
from app.internal.services.publication_services import get_publication_fields

HUBR = "https://habr.com/"


class _HubValidation(BaseModel):
    """
    Pydantic Hub validate for django model Hub
    """

    name: str = Field()
    url: str = Field()
    crawl_period: int

    @validator("url")
    def url_should_be_contain_habr(cls, url: str) -> str:
        if url.find(HUBR) == -1:
            raise ValueError("url should be contain https://habr.com/")

        return url


class _ParserQueryData(BaseModel):
    """
    Validate data of get query /run_parser?...
    """

    id: int

    @validator("id")
    def id_should_be_positive(cls, id: int) -> int:
        if id <= 0:
            raise ValueError("id should be positive")

        return id


class Parser:
    """
    Aiohttp hub parser
    """

    async def _fetch(self, session: ClientSession, url: str) -> Tuple[str, str]:
        async with session.get(url) as response:
            return await response.text(), url

    async def get(self, request: Request):
        params = request.query
        try:
            parser_query_data = _ParserQueryData(**params)
        except ValidationError as e:
            return json_response(e.json(), status=400)
        try:
            hub = await sync_to_async(Hub.objects.get)(id=parser_query_data.id)
            _HubValidation(**{"name": hub.name, "url": hub.url, "crawl_period": hub.crawl_period})
        except (ValidationError, ObjectDoesNotExist) as e:
            return json_response({f"{type(e).__name__}": str(e)}, status=400)

        exists_urls = await sync_to_async(lambda: {p.url for p in Publication.objects.all()})()
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(hub.url) as response:
                    html_doc, status = await response.text(), response.status
                    if status == 404:
                        return json_response({"result": f"404 Not Found for this hub {hub.url}"}, status=400)

            urls = list({urljoin(HUBR, url) for url in await get_urls(html_doc)}.difference(exists_urls))
            async with aiohttp.ClientSession() as session:
                done = await asyncio.gather(*[self._fetch(session, url) for url in urls])
                done_publications = await asyncio.gather(*[get_publication_fields(d[0], d[1]) for d in done])
                for d_pub in done_publications:
                    print(d_pub.get_information())
                    await sync_to_async(d_pub.save)()
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            return json_response({f"{type(e).__name__}": str(e)}, status=400)

        return json_response({"result": "OK", "id": parser_query_data.id})
