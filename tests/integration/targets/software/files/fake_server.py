import asyncio
import logging
from typing import Any

from aiohttp import web
from aiohttp import web_server

class RequestHandler(web.RequestHandler):
    async def _handle_request(self, request, *args, **kwargs):
        if request.path.endswith("drop_me"):
            self.force_close()
        return await super()._handle_request(request, *args, **kwargs)


# Monkey-patch with a version that can drop connections
web_server.RequestHandler = RequestHandler


class Handler:
    def index(self, request):
        return web.json_response({"name": "dstanek"})

    def generic_version(self, request):
        return web.Response(text="v2.0")

    def generic_download(self, request):
        software_name = request.match_info["software_name"]
        version = request.match_info["version"]
        return web.Response(text=f"<>{software_name}@{version}</>")

    def generic_download_5XX(self, request):
        software_name = request.match_info["software_name"]
        version = request.match_info["version"]
        return web.Response(status=500)

    def github_latest(self, request):
        user = request.match_info["user"]
        project = request.match_info["project"]
        version = "v2.0"
        return web.Response(status=302, headers={"Location":
        f"/{user}/{project}/releases/tag/{version}",
        })

    def github_download_file(self, request):
        project = request.match_info["project"]
        version = request.match_info["version"]
        return web.Response(text=f"<>{project}@{version}</>")

    def github_download_tarball(self, request):
        project = request.match_info["project"]
        version = request.match_info["version"]
        return web.Response(text=f"<>{project}@{version}</>")


def init_app():
    h = Handler()
    app = web.Application()
    app.router.add_get("/", h.index)

    # Generic paths
    app.router.add_get("/generic/stable-version.txt", h.generic_version)
    app.router.add_get("/generic/download/{version}/{software_name}", h.generic_download)
    app.router.add_get("/generic/download/{version}/{software_name}/5XX", h.generic_download_5XX)

    # GitHub paths
    app.router.add_get("/{user}/{project}/releases/latest", h.github_latest)
    app.router.add_get(
        "/{user}/{project}/releases/download/{version}/{software_name}",
        h.github_download_file
    )
    app.router.add_get(
        "/{user}/{project}/releases/download/{version}/{software_name}.tar.gz",
        h.github_download_tarball
    )

    return app


def main():
    logging.basicConfig(level=logging.DEBUG)
    app = init_app()
    web.run_app(app, host="0.0.0.0", port=8080)


if __name__ == '__main__':
    main()
