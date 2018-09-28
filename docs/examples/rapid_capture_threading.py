import io
import time
import threading
import queue
import picamera

class ImageProcessor(threading.Thread):
    def __init__(self, owner):
        super(ImageProcessor, self).__init__()
        self.terminated = False
        self.owner = owner
        self.start()

    def run(self):
        # This method runs in a separate thread
        while not self.terminated:
            # Get a buffer from the owner's outgoing queue
            try:
                stream = self.owner.outgoing.get(timeout=1)
            except queue.Empty:
                pass
            else:
                stream.seek(0)
                # Read the image and do some processing on it
                #Image.open(stream)
                #...
                #...
                # Set done to True if you want the script to terminate
                # at some point
                #self.owner.done=True
                stream.seek(0)
                stream.truncate()
                self.owner.incoming.put(stream)

class ProcessOutput(object):
    def __init__(self, threads):
        self.done = False
        # Construct a pool of image processors, a queue of incoming buffers,
        # and a (currently empty) queue of outgoing buffers. Prime the incoming
        # queue with proc+1 buffers (+1 to permit output to be written while
        # all procs are busy with existing buffers)
        self.incoming = queue.Queue(threads)
        self.outgoing = queue.Queue(threads)
        self.pool = [ImageProcessor(self) for i in range(threads)]
        buffers = (io.BytesIO() for i in range(threads + 1))
        for buf in buffers:
            self.incoming.put(buf)
        self.buffer = None

    def write(self, buf):
        if buf.startswith(b'\xff\xd8'):
            # New frame; push current buffer to the outgoing queue and attempt
            # to get a buffer from the incoming queue
            if self.buffer is not None:
                self.outgoing.put(self.buffer)
                try:
                    self.buffer = self.incoming.get_nowait()
                except queue.Empty:
                    # No buffers available (means all threads are busy); skip
                    # this frame
                    self.buffer = None
        if self.buffer is not None:
            self.buffer.write(buf)

    def flush(self):
        # When told to flush (this indicates end of recording), shut
        # down in an orderly fashion. Tell all the processor's they're
        # terminated and wait for them to quit
        for proc in self.pool:
            proc.terminated = True
        for proc in self.pool:
            proc.join()

with picamera.PiCamera(resolution='VGA') as camera:
    camera.start_preview()
    time.sleep(2)
    output = ProcessOutput(4)
    camera.start_recording(output, format='mjpeg')
    while not output.done:
        camera.wait_recording(1)
    camera.stop_recording()
