import picamera

with picamera.PiCamera() as camera:
    camera.resolution = (640, 480)
    camera.framerate = 30
    camera.start_recording('motion.h264', motion_output='motion.data')
    camera.wait_recording(10)
    camera.stop_recording()
