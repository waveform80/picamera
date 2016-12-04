import io
import datetime as dt
from threading import Thread, Lock
from collections import namedtuple
from math import sin, cos, pi
from time import sleep

from picamera import mmal, mmalobj as mo, PiCameraMMALError
from PIL import Image, ImageDraw


class Coord(namedtuple('Coord', ('x', 'y'))):
    @classmethod
    def clock_arm(cls, radians):
        return Coord(sin(radians), -cos(radians))

    def __add__(self, other):
        try:
            return Coord(self.x + other[0], self.y + other[1])
        except TypeError:
            return Coord(self.x + other, self.y + other)

    def __sub__(self, other):
        try:
            return Coord(self.x - other[0], self.y - other[1])
        except TypeError:
            return Coord(self.x - other, self.y - other)

    def __mul__(self, other):
        try:
            return Coord(self.x * other[0], self.y * other[1])
        except TypeError:
            return Coord(self.x * other, self.y * other)

    def __floordiv__(self, other):
        try:
            return Coord(self.x // other[0], self.y // other[1])
        except TypeError:
            return Coord(self.x // other, self.y // other)

    # yeah, I could do the rest (truediv, radd, rsub, etc.) but there's no
    # need here...


class ClockSplitter(mo.MMALPythonComponent):
    def __init__(self):
        super(ClockSplitter, self).__init__(name='py.clock', outputs=2)
        self._lock = Lock()
        self._clock_image = None
        self._clock_thread = None

    def _commit_port(self, port):
        # only accept I420 format on the input port
        if port.type == 'in':
            self._accept_formats(port, mmal.MMAL_ENCODING_I420)
        # the super call will take care of the rest (copying input format
        # to outputs, checking output formats match input)
        super(ClockSplitter, self)._commit_port(port)

    def _clock_run(self):
        # draw the clock face up front (no sense drawing that every time)
        origin = Coord(0, 0)
        size = Coord(100, 100)
        center = size // 2
        face = Image.new('L', size)
        draw = ImageDraw.Draw(face)
        draw.ellipse([origin, size - 1], outline=(255,))
        while self.enabled:
            # loop round rendering the clock hands on a copy of the face
            img = face.copy()
            draw = ImageDraw.Draw(img)
            now = dt.datetime.now()
            midnight = now.replace(
                hour=0, minute=0, second=0, microsecond=0)
            timestamp = (now - midnight).total_seconds()
            hour_pos = center + Coord.clock_arm(2 * pi * (timestamp % 43200 / 43200)) * 30
            minute_pos = center + Coord.clock_arm(2 * pi * (timestamp % 3600 / 3600)) * 45
            second_pos = center + Coord.clock_arm(2 * pi * (timestamp % 60 / 60)) * 45
            draw.line([center, hour_pos], fill=(200,), width=2)
            draw.line([center, minute_pos], fill=(200,), width=2)
            draw.line([center, second_pos], fill=(200,), width=1)
            # assign the rendered image to the internal variable
            with self._lock:
                self._clock_image = img
            sleep(0.2)

    def _callback(self, port, buf):
        out1 = self.outputs[0].get_buffer(False)
        out2 = self.outputs[1].get_buffer(False)
        if out1:
            # copy the input frame to the first output buffer
            out1.copy_from(buf)
            with out1 as data:
                # construct an Image using the Y plane of the output
                # buffer's data and tell PIL we can write to the buffer
                img = Image.frombuffer('L', port.framesize, data, 'raw', 'L', 0, 1)
                img.readonly = 0
                with self._lock:
                    if self._clock_image:
                        img.paste(self._clock_image, (10, 10), self._clock_image)
            # if we've got a second output buffer replicate the first
            # buffer into it (note the difference between replicate and
            # copy_from)
            if out2:
                out2.replicate(out1)
            try:
                self.outputs[0].send_buffer(out1)
            except PiCameraMMALError as e:
                # if EINVAL occurs here the port's shutting down so stop
                # the callbacks anyway
                if e.status != mmal.MMAL_EINVAL:
                    raise
                return True
        if out2:
            try:
                self.outputs[1].send_buffer(out2)
            except PiCameraMMALError as e:
                if e.status != mmal.MMAL_EINVAL:
                    raise
                return True
        return False

    def enable(self):
        super(ClockSplitter, self).enable()
        self._clock_thread = Thread(target=self._clock_run)
        self._clock_thread.daemon = True
        self._clock_thread.start()

    def disable(self):
        super(ClockSplitter, self).disable()
        if self._clock_thread:
            self._clock_thread.join()
            self._clock_thread = None
            with self._lock:
                self._clock_image = None


def main(output_filename):
    camera = mo.MMALCamera()
    preview = mo.MMALRenderer()
    encoder = mo.MMALVideoEncoder()
    clock = ClockSplitter()

    # Configure camera output 0
    camera.outputs[0].framesize = (640, 480)
    camera.outputs[0].framerate = 24
    camera.outputs[0].commit()

    # Configure H.264 encoder
    encoder.outputs[0].format = mmal.MMAL_ENCODING_H264
    encoder.outputs[0].bitrate = 2000000
    encoder.outputs[0].commit()
    p = encoder.outputs[0].params[mmal.MMAL_PARAMETER_PROFILE]
    p.profile[0].profile = mmal.MMAL_VIDEO_PROFILE_H264_HIGH
    p.profile[0].level = mmal.MMAL_VIDEO_LEVEL_H264_41
    encoder.outputs[0].params[mmal.MMAL_PARAMETER_PROFILE] = p
    encoder.outputs[0].params[mmal.MMAL_PARAMETER_VIDEO_ENCODE_INLINE_HEADER] = True
    encoder.outputs[0].params[mmal.MMAL_PARAMETER_INTRAPERIOD] = 30
    encoder.outputs[0].params[mmal.MMAL_PARAMETER_VIDEO_ENCODE_INITIAL_QUANT] = 22
    encoder.outputs[0].params[mmal.MMAL_PARAMETER_VIDEO_ENCODE_MAX_QUANT] = 22
    encoder.outputs[0].params[mmal.MMAL_PARAMETER_VIDEO_ENCODE_MIN_QUANT] = 22
    output = io.open(output_filename, 'wb')
    def output_callback(port, buf):
        output.write(buf.data)
        return bool(buf.flags & mmal.MMAL_BUFFER_HEADER_FLAG_EOS)

    # Connect everything up (no need to enable capture on camera port 0)
    clock.connect(camera.outputs[0])
    preview.connect(clock.outputs[0])
    encoder.connect(clock.outputs[1])
    encoder.outputs[0].enable(output_callback)
    try:
        sleep(10)
    finally:
        preview.disconnect()
        encoder.disconnect()
        clock.disconnect()


if __name__ == '__main__':
    main('output.h264')
