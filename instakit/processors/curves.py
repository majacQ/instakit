#!/usr/bin/env python
# encoding: utf-8
"""
curves.py

Adapted from this:

    https://gist.github.com/fish2000/5641c3697fa4407fcfd59099575d6938

And also this:

    https://github.com/vbalnt/filterizer/blob/master/extractCurvesFromACVFile.py

Created by FI$H 2000 on 2012-08-23.
Copyright (c) 2012-2019 Objects In Space And Time, LLC. All rights reserved.

"""
from __future__ import print_function

import numpy
import os
import struct

from PIL import Image
from enum import Enum, unique
from scipy import interpolate

from instakit.utils.static import asset
from instakit.utils.mode import Mode
from instakit.abc import Processor

interpolate_mode_strings = ('linear',
                            'nearest',
                            'zero',
                            'slinear',
                            'quadratic', 'cubic',
                            'previous', 'next',
                            'lagrange')

@unique
class InterpolateMode(Enum):
    
    # These correspond to the “kind” arg
    # from “scipy.interpolate.interp1d(…)”:
    LINEAR = 0
    NEAREST = 1
    ZERO = 2
    SLINEAR = 3
    QUADRATIC = 4
    CUBIC = 5
    PREVIOUS = 6
    NEXT = 7
    
    # This specifies LaGrange interpolation,
    # using “scipy.interpolate.lagrange(…)”:
    LAGRANGE = 8
    
    def to_string(self):
        return interpolate_mode_strings[self.value]
    
    def __str__(self):
        return self.to_string()


class SingleCurve(list):
    
    """ A SingleCurve instance is a named list of (x, y) coordinates,
        that provides programmatic access to interpolated values.
        
        It is constructed with `(name, [(x, y), (x, y)...])`; since it
        directly inherits from `__builtins__.list`, the usual methods
        e.g. `append(…)`, `insert(…)` &c. can be used to modify an
        instance of SingleCurve.
        
        Before accessing interpolated values, one first calls the
        method `interpolate(…)` with an optional argument specifying
        the interpolation mode, `mode=InterpolationMode` (q.v. the
        `InterpolationMode` enum supra.) and thereafter, instances
        of SingleCurve are callable with an x-coordinate argument,
        returning the interpolated y-coordinate.
    """
    
    def __init__(self, name, *args):
        self.name = name
        list.__init__(self, *args)
    
    def asarray(self, dtype=None):
        return numpy.array(self, dtype=dtype)
    
    def interpolate(self, mode=InterpolateMode.LAGRANGE):
        xy = self.asarray()
        if mode == InterpolateMode.LAGRANGE or mode is None:
            delegate = interpolate.lagrange(xy.T[0],
                                            xy.T[1])
        else:
            kind = InterpolateMode(mode).to_string()
            delegate = interpolate.interp1d(xy.T[0],
                                            xy.T[1], kind=kind)
        self.delegate = delegate
        return self
    
    def __call__(self, value):
        if not hasattr(self, 'delegate'):
            self.interpolate()
        delegate = self.delegate
        return delegate(value)


class CurveSet(Processor):
    
    """ A CurveSet instance represents an ACV file, as generated by the
        Adobe® Photoshop™ application, whose data encodes a set of
        image-adjustment curves.
        
        The simplest use is to read an existing set of curves from an
        existant ACV file; one instantiates a CurveSet like so:
        
            mycurveset = CurveSet('path/to/curveset.acv')
        
        …one can then use `mycurveset.process(…)` to process PIL images,
        or one can access underlying curve data via `mycurveset.curves`;
        subsequently the curveset can be rewritten to a new ACV file
        with `mycurveset.write_acv(acv_file_path)`.
    """
    
    acv = 'acv'
    dotacv = '.' + acv
    channels = ('composite', 'red', 'green', 'blue')
    valid_modes = ( Mode.RGB, Mode.MONO, Mode.L )
    
    @classmethod
    def builtin(cls, name):
        print("Reading curves [builtin] %s%s" % (name, cls.dotacv))
        acv_path = asset.path(cls.acv, "%s%s" % (name, cls.dotacv))
        out = cls(acv_path)
        out._is_builtin = True
        return out
    
    @classmethod
    def instakit_names(cls):
        return [curve_file.rstrip(cls.dotacv) \
            for curve_file in asset.listfiles(cls.acv) \
            if curve_file.lower().endswith(cls.dotacv)]
    
    @classmethod
    def instakit_curve_sets(cls):
        return [cls.builtin(name) for name in cls.instakit_names()]
    
    @classmethod
    def channel_name(cls, idx):
        try:
            return cls.channels[idx]
        except IndexError:
            return "channel%s" % idx
    
    def __init__(self, path, interpolation_mode=None):
        object.__init__(self)
        self.count = 0
        self.curves = []
        self._is_builtin = False
        self.path = os.path.abspath(path)
        self.name = os.path.basename(path)
        self.interpolation_mode = interpolation_mode
        if os.path.isfile(self.path):
            self.read_acv(self.path,
                          self.interpolation_mode)
    
    @property
    def is_builtin(self):
        return self._is_builtin
    
    @property
    def file_exists(self):
        return os.path.isfile(self.path)
    
    @staticmethod
    def read_one_curve(acv_file, name, interpolation_mode):
        curve = SingleCurve(name)
        points_in_curve, = struct.unpack("!h", acv_file.read(2))
        for _ in range(points_in_curve):
            y, x = struct.unpack("!hh", acv_file.read(4))
            curve.append((x, y))
        return curve.interpolate(interpolation_mode)
    
    @staticmethod
    def write_one_curve(acv_file, curve):
        points_in_curve = len(curve)
        acv_file.write(struct.pack("!h", points_in_curve))
        for idx in range(points_in_curve):
            x, y = curve[idx]
            acv_file.write(struct.pack("!hh", y, x))
        return points_in_curve
    
    def read_acv(self, acv_path, interpolation_mode):
        if not self.file_exists:
            raise IOError("Can't read nonexistent ACV file: %s" % self.path)
        with open(acv_path, "rb") as acv_file:
            _, self.count = struct.unpack("!hh", acv_file.read(4))
            for idx in range(self.count):
                self.curves.append(
                    self.read_one_curve(acv_file,
                                   type(self).channel_name(idx),
                                        interpolation_mode))
    
    def write_acv(self, acv_path):
        if self.count < 1:
            raise ValueError("Can't write empty curveset as ACV data")
        with open(acv_path, "wb") as acv_file:
            acv_file.write(struct.pack("!hh", 0, self.count))
            for curve in self.curves:
                self.write_one_curve(acv_file, curve)
    
    def process(self, image):
        mode = Mode.of(image)
        if mode not in type(self).valid_modes:
            image = Mode.RGB.process(image)
        elif mode is not Mode.RGB:
            return Image.eval(Mode.L.process(image),
                              self.curves[0])
        # has to be RGB at this point -- but we'll use the
        # mode of the operand image for future-proofiness:
        adjusted_channels = []
        for idx, channel in enumerate(image.split()):
            adjusted_channels.append(
                Image.eval(channel,
                           lambda v: self.curves[idx+1](v)))
        return Mode.RGB.merge(*adjusted_channels)
    
    def add(self, curve):
        self.curves.append(curve)
        self.count = len(self.curves)
    
    def __repr__(self):
        cls_name = getattr(type(self), '__qualname__',
                   getattr(type(self), '__name__'))
        address = id(self)
        label = self.is_builtin and '[builtin]' or self.name
        interp = self.interpolation_mode or InterpolateMode.LAGRANGE
        parenthetical = "%s, %d, %s" % (label, self.count, interp)
        return "%s(%s) @ <%s>" % (cls_name, parenthetical, address)


def test():
    curve_sets = CurveSet.instakit_curve_sets()
    
    image_paths = list(map(
        lambda image_file: asset.path('img', image_file),
            asset.listfiles('img')))
    image_inputs = list(map(
        lambda image_path: Mode.RGB.open(image_path),
            image_paths))
    
    for image_input in image_inputs[:1]:
        image_input.show()
        for curve_set in curve_sets:
            curve_set.process(image_input).show()
    
    print(curve_sets)
    print(image_paths)
    
    import tempfile
    temppath = tempfile.mktemp(suffix='.acv')
    assert not CurveSet(path=temppath).file_exists
    
if __name__ == '__main__':
    test()