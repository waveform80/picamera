#!/usr/bin/env python
'''This example recipe demonstrates how to capture frames which are
phase locked to the system time modulo the desired frame period.  For
example, frames requested at 20 HZ will be aqcuired at integer
multiples of 50 milliseconds since the unix epoch.

This is accomplished by making small adjustements to the frame rate
until the frequency and phase of the frames converge to integer
multiples of the desired framer period since the epoch.

This in conjunction with ntp, or chrony, should enable many raspberry
pis to capture video frames which are reasonably (sub-millisecond)
synchronized.

This is mostly an example, and is not production ready.

Author: Ethan Rublee <ethan.rublee@gmail.com>
Date: April, 2016
'''

import Queue
import argparse
import ctypes
import os
import math
import picamera
import socket
import threading
import time

# monotonic_time from http://stackoverflow.com/a/1205762
CLOCK_MONOTONIC_RAW = 4 # see <linux/time.h>

class timespec(ctypes.Structure):
    _fields_ = [
        ('tv_sec', ctypes.c_long),
        ('tv_nsec', ctypes.c_long)
    ]

librt = ctypes.CDLL('librt.so.1', use_errno=True)
clock_gettime = librt.clock_gettime
clock_gettime.argtypes = [ctypes.c_int, ctypes.POINTER(timespec)]

def monotonic_time():
    t = timespec()
    if clock_gettime(CLOCK_MONOTONIC_RAW , ctypes.pointer(t)) != 0:
        errno_ = ctypes.get_errno()
        raise OSError(errno_, os.strerror(errno_))
    return t.tv_sec + t.tv_nsec * 1e-9

class PhaseDetector(object):
    def __init__(self, frequency):
        self.frequency = frequency
        self.duration = 1.0/frequency
        self.phase = 0
        self.count = 0
        self.alpha = 0.1

    def Update(self, stamp):
        ref_stamp = self.duration*math.floor(stamp/self.duration + 0.5)
        phase = (stamp - ref_stamp)/self.duration
        if self.count == 0:
            self.phase = phase
        else:
            self.phase = self.phase*(1-self.alpha) + self.alpha*phase
        self.count += 1
        return self.phase

class FrequencyDetector(object):
    def __init__(self, frequency):
        self.period = 1.0/frequency
        self.count = 0
        self.alpha = 0.1
        self.last_stamp = None

    def Update(self, stamp):
        if self.count > 0:
            self.period = self.period*(1-self.alpha) + self.alpha*(stamp - self.last_stamp)
        self.count += 1
        self.last_stamp = stamp
        return 1.0/self.period

class PIDLoop(object):
    def __init__(self, set_point, kp, ki, kd):
        self.set_point = set_point
        self.integral = 0
        self.derivative = 0
        self.proportional = 0
        self.last_err = 0
        self.last_stamp = None
        self.kp = kp
        self.ki = ki
        self.kd = kd

    def Reset(self):
        self.integral = 0
        self.proportional = 0
        self.last_err = 0

    def Update(self, pv, stamp):
        if self.last_stamp is None:
            self.last_stamp = stamp
            return
        dt = stamp - self.last_stamp
        self.last_stamp = stamp
        assert dt >= 0
        err = self.set_point - pv
        self.integral += err*dt
        self.proportional = err
        self.derivative = (err - self.last_err)/dt
        self.last_err = err

    def Err(self):
        return self.last_err

    def PTerm(self):
        return self.proportional * self.kp

    def ITerm(self):
        return self.integral * self.ki

    def DTerm(self):
        return self.derivative * self.kd

    def Offset(self):
        return self.PTerm() + self.ITerm() + self.DTerm()


class PhaseLockedOutput(object):
    def __init__(self, camera, output=None):
        self.framerate = camera.framerate
        self.camera = camera
        self.output = output

        self.freq_detector = FrequencyDetector(self.framerate)
        self.phase_detector = PhaseDetector(self.framerate)
        # These values seem to work well for 20-30 HZ.
        self.freq_pid = PIDLoop(set_point=self.framerate, kp=20.0/256.0, ki=1.0/256.0, kd=1.0/256.0)
        self.phase_pid = PIDLoop(set_point=0.0, kp=10.0/256.0, ki=5.0/256.0, kd=1.0/256.0)
        self.last_index = 0
        self.last_rate = self.framerate
        self.count = 0

        # Write in queue because the phase locking code is sensitive to
        # latency caused by writing.
        self.write_q = Queue.Queue()
        self.write_thread = threading.Thread(target=self._twrite)
        self.write_thread.daemon = True
        self.write_thread.start()

    def _twrite(self):
        # Writing thread
        while True:
            data = self.write_q.get()
            if self.output is not None:
                self.output.write(data)
            self.write_q.task_done()

    def write(self, s):
        if self.camera.frame.timestamp and self.camera.frame.timestamp > 0 and self.camera.frame.index != self.last_index:
            self.last_index = self.camera.frame.index
            # Compute the time offset between system time, and the
            # monotonic clock, which is what it appears the frame's
            # timestamp is based in. This offset will drift slightly
            # overtime if the system clock is adjusted by NTP, for
            # example.
            time_offset = time.time() - monotonic_time()
            # The presentation timestamp, in the system time frame.
            stamp = 1e-6*self.camera.frame.timestamp + time_offset
            # NOTE it's important to measure the frame rate, because
            # the camera doesn't seem to really quite acheive the
            # commanded frame rate.
            freq = self.freq_detector.Update(stamp)
            phase = self.phase_detector.Update(stamp)
            self.freq_pid.Update(freq, stamp)
            self.phase_pid.Update(phase, stamp)
            phase_err = self.phase_pid.Err()
            freq_err = self.freq_pid.Err()
            command_rate = self.last_rate + self.freq_pid.Offset()
            if abs(freq - self.framerate) < 0.2:
                # Only adjust phase if we're close to the desired
                # frequency.  The negative is because if the phase
                # offset is positive, we need to slow the framerate
                # down a bit.
                command_rate -= self.phase_pid.Offset()
            else:
                # Reset the integral and derivative terms if we're far off.
                self.phase_pid.Reset()

            # Capture the current video_frame_rate for debug/display
            # purposes, this will have some truncation due to the
            # rational nature of the the MMAL parameter.
            video_frame_rate = self.camera.video_frame_rate
            if abs(command_rate - self.framerate) < 5:
                self.camera.video_frame_rate = command_rate
                # Note that we store the floating point command_rate,
                # and not the result of querying the video_frame_rate.
                # This allows us to accumulate the offsets given by
                # the PID controllers.
                self.last_rate = command_rate
            else:
                # We're way off, something is wrong, just reset to the
                # desired FPS, and try again.
                self.camera.video_frame_rate = self.framerate
                self.last_rate = self.framerate
                self.freq_pid.Reset()

            print('stamp:%0.3f status:%0.4f command:%0.4f phase:%0.4f freq:%0.4f'%(
                stamp,
                video_frame_rate,
                command_rate,
                phase,
                freq))

        self.write_q.put(s)

    def flush(self):
        self.write_q.join()
        self.output.flush()

def Main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--codec', type=str, default='h264', choices=('h264','mjpeg'))
    args = parser.parse_args()
    server_socket = socket.socket()
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind(('0.0.0.0', 8000))
    server_socket.listen(0)
    output = server_socket.accept()[0].makefile('wb')
    with picamera.PiCamera(clock_mode='raw') as camera:
        camera.resolution = (2592/2,1944/2)
        # You may need to tune the PID values to
        # get other values of framerate to work.
        camera.framerate = 30
        camera.exposure_mode = 'fixedfps'
        out = PhaseLockedOutput(camera, output=output)
        camera.start_recording(out, format=args.codec)
        while True:
            camera.wait_recording(1)

if __name__ == "__main__":
    Main()
