import io
import time
import picamera

class SplitFrames(object):
    def __init__(self):
        self.frame_num = 0
        self.output = None

    def write(self, buf):
        if buf.startswith(b'\xff\xd8'):
            # Start of new frame; close the old one (if any) and
            # open a new output
            if self.output:
                self.output.close()
            self.frame_num += 1
            self.output = io.open('image%02d.jpg' % self.frame_num, 'wb')
        self.output.write(buf)

with picamera.PiCamera(resolution='720p', framerate=30) as camera:
    camera.start_preview()
    # Give the camera some warm-up time
    time.sleep(2)
    output = SplitFrames()
    start = time.time()
    camera.start_recording(output, format='mjpeg')
    camera.wait_recording(2)
    camera.stop_recording()
    finish = time.time()
print('Captured %d frames at %.2ffps' % (
    output.frame_num,
    output.frame_num / (finish - start)))
