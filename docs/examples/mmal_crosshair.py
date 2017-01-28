from picamera import mmal, mmalobj as mo, PiCameraPortDisabled
from PIL import Image, ImageDraw
from signal import pause


class Crosshair(mo.MMALPythonComponent):
    def __init__(self):
        super(Crosshair, self).__init__(name='py.crosshair')
        self._crosshair = None
        self.inputs[0].supported_formats = mmal.MMAL_ENCODING_I420

    def _handle_frame(self, port, buf):
        # If we haven't drawn the crosshair yet, do it now and cache the
        # result so we don't bother doing it again
        if self._crosshair is None:
            self._crosshair = Image.new('L', port.framesize)
            draw = ImageDraw.Draw(self._crosshair)
            draw.line([
                (port.framesize.width // 2, 0),
                (port.framesize.width // 2, port.framesize.height)],
                fill=(255,), width=1)
            draw.line([
                (0, port.framesize.height // 2),
                (port.framesize.width , port.framesize.height // 2)],
                fill=(255,), width=1)
        # buf is the buffer containing the frame from our input port. First
        # we try and grab a buffer from our output port
        try:
            out = self.outputs[0].get_buffer(False)
        except PiCameraPortDisabled:
            # The port was disabled; that probably means we're shutting down so
            # return True to indicate we're all done and the component should
            # be disabled
            return True
        else:
            if out:
                # We've got a buffer (if we don't get a buffer here it most
                # likely means things are going too slow downstream so we'll
                # just have to skip this frame); copy the input buffer to the
                # output buffer
                out.copy_from(buf)
                # now grab a locked reference to the buffer's data by using
                # "with"
                with out as data:
                    # Construct a PIL Image over the Y plane at the front of
                    # the data and tell PIL the buffer is writeable
                    img = Image.frombuffer('L', port.framesize, data, 'raw', 'L', 0, 1)
                    img.readonly = False
                    img.paste(self._crosshair, (0, 0), mask=self._crosshair)
                # Send the output buffer back to the output port so it can
                # continue onward to whatever's downstream
                try:
                    self.outputs[0].send_buffer(out)
                except PiCameraPortDisabled:
                    # The port was disabled; same as before this probably means
                    # we're shutting down so return True to indicate we're done
                    return True
            # Return False to indicate that we want to continue processing
            # frames. If we returned True here, the component would be
            # disabled and no further buffers would be processed
            return False


camera = mo.MMALCamera()
preview = mo.MMALRenderer()
transform = Crosshair()

camera.outputs[0].framesize = '720p'
camera.outputs[0].framerate = 30
camera.outputs[0].commit()

transform.connect(camera)
preview.connect(transform)

transform.connection.enable()
preview.connection.enable()

preview.enable()
transform.enable()
camera.enable()

pause()
