#!/usr/bin/env python3

"""
    Picamera MJPEG multithread streaming server with producer and consumer method

    Usage:
        /home
            main page shown after login (user:pass)
        /stream.mjpeg
            camera mjpeg straming (shown in main page)
        /screen.jpeg
            camera single shot
        /info
            number of connected clients

    How it works:
        There is a (consumer) thread for each client.
        When a new frame is available, the producer thread notify all consumer threads.
        If a consumer thread was in wait (finished sending the previous frame), it will
        send the new frame to the connected client.

    Why:
        Without the producer and consumer method, if a client was too slow, all the other ones
        were affected.
        With the producer and consumer method, each client is indipendent from other ones, if a
        client is too slow, its thread will send less frame per second, while others threads will
        continue to send all the frames.

    Author:
        BigNerd95
"""

import picamera, socketserver, base64
from threading import Condition
from http import server

PORT = 8000

USERPASS = {'user': 'pass',
            'user1': 'pass1',
            'user2': 'pass2'
            }

PAGE = """\
<html>
<head>
<title>picamera MJPEG streaming multithread demo</title>
</head>
<body>
<h1>PiCamera MJPEG Streaming Demo</h1>
<img src="stream.mjpeg" />
</body>
</html>
"""

# producer thread
class StreamingOutput(object):
    def __init__(self):
        self.screen = bytes()
        self.condition = Condition()
        self.clients = 0

    def write(self, frame):
        size = str(len(frame)).encode('utf-8')
        # each consumer thread will read and send this content to the connected client
        self.screen =   b'Content-Type: image/jpeg\r\n'\
                        b'Content-Length: ' + size + b'\r\n\r\n'\
                        + frame + b'\r\n'
        self.condition.acquire()
        self.condition.notifyAll() # producer notify all consumer threads that a new frame is available
        self.condition.release()


class StreamingHandler(server.BaseHTTPRequestHandler):
    def do_GET(self):
        if isAuth(self.headers['Authorization']):

            if self.path == '/':
                self.send_response(301)
                self.send_header('Location', '/home')
                self.end_headers()

            elif self.path == '/home':
                content = PAGE.encode('utf-8')
                self.send_response(200)
                self.send_header('Content-Type', 'text/html')
                self.send_header('Content-Length', len(content))
                self.end_headers()
                self.wfile.write(content)

            elif self.path == '/info':
                content = b'Clienti: ' + str(output.clients).encode('utf-8')
                self.send_response(200)
                self.send_header('Content-Type', 'text/html')
                self.send_header('Content-Length', len(content))
                self.end_headers()
                self.wfile.write(content)

            elif self.path == '/stream.mjpeg':
                output.clients += 1
                self.close_connection = False
                self.send_response(200)
                self.send_header('Age', 0)
                self.send_header('Cache-Control', 'no-cache, private')
                self.send_header('Pragma', 'no-cache')
                self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=FRAME')
                self.end_headers()
                # consumer thread (one for each client)
                while True:
                    try:
                        self.wfile.write(b'--FRAME\r\n')
                        self.wfile.write(output.screen)
                        output.condition.acquire()
                        output.condition.wait() # thread wait until a new frame is available
                        output.condition.release()
                    except Exception as e:
                        break
                output.clients -= 1

            elif self.path == '/screen.jpeg':
                self.wfile.write(b'HTTP/1.0 200 OK\r\n')
                self.wfile.write(output.screen)

            else:
                self.send_error(404)
                self.end_headers()

        else:
            self.send_response(401)
            self.send_header('WWW-Authenticate', 'Basic realm=\"Picamera server\"')
            self.send_header('Content-Type', 'text/html')
            self.end_headers()

class StreamingServer(socketserver.ThreadingMixIn, server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True
    pass

def isAuth(auth):
    try:
        sep = auth.index(' ')
        decUP = base64.b64decode(bytes(auth[sep+1:], 'utf-8'))
        sep = decUP.index(b':')
        user = decUP[:sep].decode('utf-8')
        password = decUP[sep+1:].decode('utf-8')
        if USERPASS.get(user) == password:
            return True
        else:
            return False
    except Exception as e:
        return False

if __name__ == '__main__':
    with picamera.PiCamera(resolution='480x480', framerate=20) as camera:
        camera.vflip = True
        output = StreamingOutput() # producer class
        camera.start_recording(output, format='mjpeg') # use producer class as write object
        try:
            address = ('', PORT)
            server = StreamingServer(address, StreamingHandler)
            print("Server Started on port:", PORT)
            server.serve_forever()
        except Exception as e:
            pass
        finally:
            camera.stop_recording()
