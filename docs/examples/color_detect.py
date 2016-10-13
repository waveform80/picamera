import picamera
import numpy as np
from picamera.array import PiRGBAnalysis
from picamera.color import Color

class MyColorAnalyzer(PiRGBAnalysis):
    def __init__(self, camera):
        super(MyColorAnalyzer, self).__init__(camera)
        self.last_color = ''

    def analyze(self, a):
        # Convert the average color of the pixels in the middle box
        c = Color(
            r=int(np.mean(a[30:60, 60:120, 0])),
            g=int(np.mean(a[30:60, 60:120, 1])),
            b=int(np.mean(a[30:60, 60:120, 2]))
            )
        # Convert the color to hue, saturation, lightness
        h, l, s = c.hls
        c = 'none'
        if s > 1/3:
            if h > 8/9 or h < 1/36:
                c = 'red'
            elif 5/9 < h < 2/3:
                c = 'blue'
            elif 5/36 < h < 4/9:
                c = 'green'
        # If the color has changed, update the display
        if c != self.last_color:
            self.camera.annotate_text = c
            self.last_color = c

with picamera.PiCamera(resolution='160x90', framerate=24) as camera:
    # Fix the camera's white-balance gains
    camera.awb_mode = 'off'
    camera.awb_gains = (1.4, 1.5)
    # Draw a box over the area we're going to watch
    camera.start_preview(alpha=128)
    box = np.zeros((96, 160, 3), dtype=np.uint8)
    box[30:60, 60:120, :] = 0x80
    camera.add_overlay(memoryview(box), size=(160, 90), layer=3, alpha=64)
    # Construct the analysis output and start recording data to it
    with MyColorAnalyzer(camera) as analyzer:
        camera.start_recording(analyzer, 'rgb')
        try:
            while True:
                camera.wait_recording(1)
        finally:
            camera.stop_recording()
