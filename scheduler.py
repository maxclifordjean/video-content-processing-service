#!/usr/bin/python3

from tornado import web, gen, ioloop
import os
from os.path import isfile
import time
from video_content_transcoder.transcoder import start

dashls_path = os.getenv(
    "DASH_HLS_OUTPUT_BASED_PATH", "./video-storage"
)  # target output folder


class ScheduleTranscodingHandler(web.RequestHandler):
    def __init__(self, app, request, **kwargs):
        super(ScheduleTranscodingHandler, self).__init__(app, request, **kwargs)

    @gen.coroutine
    def get(self):
        stream = self.request.uri.replace("/transcoding/", "")

        # schedule transcoding the stream
        print(
            "[ScheduleTranscodingHandler#GET] : schedule transcoding the stream: "
            + stream,
            flush=True,
        )
        ioloop.IOLoop.current().spawn_callback(start, stream)  # treats in async

        start_time = time.time()
        while time.time() - start_time < 15:
            if isfile(dashls_path + "/" + stream):
                self.set_header("X-Accel-Redirect", "/" + stream)
                self.set_status(200, "SUCCESS")
                return
            yield gen.sleep(0.5)

        self.set_status(503, "Transcoding scheduled.")
