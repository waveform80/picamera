import picamera
import math


# An output class, to be passed to PiCamera.start_recording.
class RateAdjuster(object):
    def __init__(self, camera):
        self.framerate = camera.framerate
        self.camera = camera
        self.last_stamp = 0
        self.last_index = 0

    def write(self, data):
        stamp = self.camera.frame.timestamp
        index = self.camera.frame.index
        if not stamp or stamp <= 0 or index == self.last_index:
            # for h264 write is called multiple times per frame, and
            # sometimes the stamp is not populated.  mjpeg doesn't
            # appear to express this behavior.
            return
        self.last_index = index
        measured_rate = 1 / (1e-6 * (stamp - self.last_stamp))
        self.last_stamp = stamp
        current_frame_rate = float(self.camera.video_frame_rate)
        command_frame_rate = self.framerate + math.sin(index / 100.0) * 5
        # Vary frame rate slowly between +- 5 fps around the original frame
        # rate.
        self.camera.video_frame_rate = command_frame_rate
        print 'index: %d current rate: %0.3f commanded rate: %s0.3f measured rate: %0.3f' % (
            index, current_frame_rate, command_frame_rate, measured_rate)

    def flush(self):
        pass

with picamera.PiCamera() as camera:
    camera.resolution = (2592 / 2, 1944 / 2)
    camera.framerate = 25
    camera.exposure_mode = 'fixedfps'
    camera.start_recording(RateAdjuster(camera), format='mjpeg')
    while True:
        camera.wait_recording(1)
