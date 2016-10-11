import time
import picamera
import picamera.array

with picamera.PiCamera() as camera:
    with picamera.array.PiYUVArray(camera) as stream:
        camera.resolution = (100, 100)
        camera.start_preview()
        time.sleep(2)
        camera.capture(stream, 'yuv')
        # Show size of YUV data
        print(stream.array.shape)
        # Show size of RGB converted data
        print(stream.rgb_array.shape)
