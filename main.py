#!/usr/bin/python3
import os
from tornado import ioloop, web
from tornado.options import define, options, parse_command_line
from scheduler import ScheduleTranscodingHandler

app = web.Application([
    (r'/transcoding/.*',ScheduleTranscodingHandler),
])

if __name__ == "__main__":
    define("port", default=os.getenv("PORT", 8000), help="port", type=int)
    define("ip", default=os.getenv("HOST", "localhost"), help="host")
    parse_command_line()
    print("[VIDEO-CONTENT-PROCESSING-MS]: Server running: " + options.ip + ":" + str(options.port))
    app.listen(options.port, address=options.ip)
    ioloop.IOLoop.instance().start()