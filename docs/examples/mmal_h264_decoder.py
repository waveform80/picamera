from picamera import mmal,mmalobj as mo

source  = mo.MMALPythonSource('test.h264')
decoder = mo.MMALVideoDecoder()
preview = mo.MMALRenderer()

# read the input as h264
source.outputs[0].format = mmal.MMAL_ENCODING_H264
source.outputs[0].framerate = 25
source.outputs[0].framesize = (1280,720)
source.outputs[0].commit()

# decoder input port
decoder.inputs[0].copy_from(source.outputs[0])
decoder.inputs[0].commit()

# decoder output port
decoder.outputs[0].copy_from(decoder.inputs[0])
decoder.outputs[0].format = mmal.MMAL_ENCODING_I420
decoder.outputs[0].commit()

# connect source -> decoder -> preview
decoder.inputs[0].connect(source.outputs[0])
decoder.inputs[0].connection.enable()
preview.inputs[0].connect(decoder.outputs[0])

# enable everything
preview.enable()
decoder.enable()
source.enable()

# start decoding
try:
    print "***** start decoding *****"
    source.wait(15)

finally:
    print "***** done *****"
    source.disable()
    decoder.disable()
    preview.disable()


