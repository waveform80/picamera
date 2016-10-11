import picamera

camera = picamera.PiCamera(resolution=(640, 480))
for filename in camera.record_sequence(
        '%d.h264' % i for i in range(1, 11)):
    camera.wait_recording(5)
