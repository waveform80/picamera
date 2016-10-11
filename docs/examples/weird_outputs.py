import io
import os
import picamera

with picamera.PiCamera(resolution='VGA') as camera:
    os.mkfifo('video_fifo')
    f = io.open('video_fifo', 'wb', buffering=0)
    try:
        camera.start_recording(f, format='h264')
        camera.wait_recording(10)
        camera.stop_recording()
    finally:
        f.close()
        os.unlink('video_fifo')
