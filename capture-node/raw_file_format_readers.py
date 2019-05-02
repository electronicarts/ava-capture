# Copyright (C) 2019 Electronic Arts Inc.  All rights reserved.

import os
import struct
import cv2
import numpy as np

import lz4.block as lz4block

'''
 Example Usage:
 
   # This script extracts all frames of the recorded file test.ava and outputs them as JPG and TIF images.

   from raw_file_format_readers import AvaSequenceFileReader

   reader = AvaSequenceFileReader('test.ava')
   for i in range(reader.frame_count()):
     
      img = reader.frame_as_cv2_sRGB_8bit(i)
      cv2.imwrite('test_%04d.jpg' % i, img)        # Write 8bit sRGB image as JPG

      img = reader.frame_as_cv2_LinearRGB_16bit(i)
      cv2.imwrite('test_%04d.tif' % i, img)        # Write 16bit Linear RGB image as TIF


'''

def Linear_to_sRGB(image):
    ''' Image has to be in the 16 bit range (0-65535.0) '''
    a = 0.055
    x = image / 65535.0
    return (np.where(x <= 0.00313066844, 0, (1 + a) *  cv2.pow(x, 1 / 2.4) - a)   ) * 65535.0

def resize_image(img, width=None, height=None, max_side=None, interpolation=cv2.INTER_AREA):
    original_height, original_width = img.shape[:2]
    if max_side:
        if original_height>original_width:
            height = max_side
            width = None
        else:
            width = max_side
            height = None

    if width and height:
        # Set width and height
        return cv2.resize(img, (width, height), interpolation=interpolation)
    if width:
        # Set width and preserve ratio
        return cv2.resize(img, (width, width*original_height//original_width), interpolation=interpolation)
    if height:
        # Set height and preserve ratio
        return cv2.resize(img, (height*original_width//original_height, height), interpolation=interpolation)

def raw_processing_to_16bit_linear(raw_img, bayer, blacklevel, bitcount, kB, kG, kR, resize_max_side=None):

    img = raw_img

    # Debayer
    if bayer == 'BGGR':
        img = cv2.cvtColor(img, cv2.COLOR_BAYER_RG2RGB)
    elif bayer == 'RGGB':
        img = cv2.cvtColor(img, cv2.COLOR_BAYER_BG2RGB)
    elif bayer == 'GBRG':
        img = cv2.cvtColor(img, cv2.COLOR_BAYER_GR2RGB)
    elif bayer == 'GRBG':
        img = cv2.cvtColor(img, cv2.COLOR_BAYER_GB2RGB)

    # Resize Image
    if resize_max_side:
        img = resize_image(img, max_side=resize_max_side)

    # Black point correction
    image_bpp = (8 if img.dtype==np.uint8 else 16)
    max_value = (2 ** image_bpp - 1)
    img = np.clip(img, blacklevel, max_value) - blacklevel

    # # 10,12,14 bit images need to be moved from LSB to MSB
    if bitcount > 8:
        if np.uint16 != img.dtype:
            raise Exception('Images with bitcount higher than 8 should be stored as 16bit')
        img = img << (16 - bitcount)

    # Color Correction
    if len(img.shape)>2:
        # COLOR
        # integer color balance
        # the image always gets upgraded to 16 bit for color correction
        if np.uint8 == img.dtype:
            # input is 8 bit color
            mat = np.diag(np.array([255*kB,255*kG,255*kR])).astype(np.uint16)
            img = np.matmul(img.astype(np.uint16), mat)
            img = np.clip(img,0,65535)
        elif np.uint16 == img.dtype:
            # input is 16 bit color
            mat = np.diag(np.array([65535*kB,65535*kG,65535*kR])).astype(np.uint32)
            img = np.matmul(img.astype(np.uint32), mat)
            img = np.clip(img >> 16,0,65535).astype(np.uint16)
        else:
            raise Exception('Invalid bit depth for raw image')
    else:
        # GRAYSCALE
        # upgrade image to 16 bit
        if np.uint8 == img.dtype:
            img = img.astype(np.uint16) << 8

    # Image is in Linear RGB, always 16 bit
    return img # img_uint16_linearRGB

class AvaSequenceFileReader():

    def __init__(self, filename, raise_error_on_missing_frame=False):

        self._f = None
        self._raise_error_on_missing_frame = raise_error_on_missing_frame
        self.filename = filename
        with open(self.filename, 'rb') as f:

            self.file_size = os.fstat(f.fileno()).st_size

            # File Header
            # unsigned char magic; // 0xED
            # unsigned char version; // 1
            # unsigned char channels; // 1 or 3
            # unsigned char bitcount; // 8..16
            # unsigned int width;
            # unsigned int height;
            # unsigned int blacklevel;
            # unsigned char bayer0; // first row, first pixel
            # unsigned char bayer1; // first row, second pixel
            # unsigned char bayer2; // second row, first pixel
            # unsigned char bayer3; // second row, second pixel
            # float kR;
            # float kG;
            # float kB;
            # char compression[4];
            # unsigned long long index_start_offset; // offset un bytes from the start of the file where the index will start

            header_format = 'BBBBiii4sfff4sQ'
            header_size = struct.calcsize(header_format)

            # Read Header
            header_buffer = f.read(header_size)
            magic,version,channels,self.bitcount,self.width,self.height,self.blacklevel,self.bayer,self.kR,self.kG,self.kB,compression,index_offset = struct.unpack(header_format, header_buffer)

            self.bayer = self.bayer.decode("utf-8")

            if magic != 0xED:
                raise Exception('Invalid Ava Sequence file (magic)')
            if version != 1:
                raise Exception('Invalid Ava Sequence file (version)')
            if compression.decode('utf-8')[:3] != 'LZ4':
                raise Exception('Invalid Ava Sequence file (unknown compression)')

            self._frame_count = (self.file_size - index_offset)//8
            self.index_offset = index_offset

            # Read Frame index
            index_size = self.file_size - index_offset
            f.seek(index_offset)
            self._frame_indices = np.frombuffer(f.read(index_size), dtype=np.uint64)

            self._img_data_size = (self.bitcount//8)*self.width*self.height

            if self._frame_indices.shape[0] != self._frame_count:
                raise Exception('Invalid Ava Sequence file (invalid index size)')

    def frame_count(self):
        return self._frame_count

    def _get_frame_offset_skip(self, frame_index, is_backward=True):
        while not self._frame_indices[frame_index]:
            frame_index = frame_index + (-1 if is_backward else 1)
        if frame_index < 0 or frame_index >= self._frame_count:
            return None
        return int(self._frame_indices[frame_index])

    def _compute_frame_size(self, frame_index):
        # Compute size of one frame, by looking at the index of the next frame (or the index if this is the last frame)
        offset_of_next_frame = 0
        if frame_index<self._frame_count-1:
            offset_of_next_frame = self._get_frame_offset_skip(frame_index+1, is_backward=False)
        if not offset_of_next_frame:
            offset_of_next_frame = self.index_offset
        return offset_of_next_frame - self._get_frame_offset_skip(frame_index)

    def _read_frame(self, index):

        # open .ava file if needed
        if not self._f:
            self._f = open(self.filename, 'rb', 32*1024*1024)

        # Read one frame from .ava file
        frame_offset = self._get_frame_offset_skip(index)
        self._f.seek(frame_offset)
        buf = self._f.read(self._compute_frame_size(index))

        return buf

    def _read_one_frame_16bit_linear(self, frame_index, resize_max_side):

        if frame_index<0 or frame_index>=self._frame_count:
            raise Exception('Invalid frame index %s' % frame_index)

        if self._raise_error_on_missing_frame and not self._frame_indices[frame_index]:
            raise Exception('Missing frame index %s' % frame_index)

        compressed_buffer = self._read_frame(frame_index)

        buffer = lz4block.decompress(compressed_buffer, uncompressed_size=self._img_data_size)
        raw_img = np.fromstring(buffer, np.uint8 if self.bitcount==8 else np.uint16).reshape((self.height,self.width))
        return raw_processing_to_16bit_linear(raw_img, self.bayer, self.blacklevel, self.bitcount, self.kB, self.kG, self.kR, resize_max_side=resize_max_side)

    def frame_as_cv2_sRGB_8bit(self, frame_index, resize_max_side=None):
        img_16bit_linear = self._read_one_frame_16bit_linear(frame_index, resize_max_side=resize_max_side)
        return (np.clip(Linear_to_sRGB(img_16bit_linear).astype(np.uint16),0,65535) >> 8).astype(np.uint8)

    def frame_as_cv2_LinearRGB_16bit(self, frame_index, resize_max_side=None):
        return self._read_one_frame_16bit_linear(frame_index, resize_max_side=resize_max_side)

class AvaRawImageFileReader():
    def __init__(self, filename):
        self.filename = filename
        with open(self.filename, 'rb') as f:
            buffer = f.read()

            # unsigned char magic; // 0xED
            # unsigned char version; // 1
            # unsigned char channels; // 1 or 3
            # unsigned char bitcount; // 8..16
            # unsigned int width;
            # unsigned int height;
            # unsigned int blacklevel;
            # unsigned char bayer0; // first row, first pixel
            # unsigned char bayer1; // first row, second pixel
            # unsigned char bayer2; // second row, first pixel
            # unsigned char bayer3; // second row, second pixel
            # float kR;
            # float kG;
            # float kB;

            footer_format = 'BBBBiii4sfff'
            raw_footer_size = struct.calcsize(footer_format)
            magic,version,channels,bitcount,width,height,blacklevel,bayer,kR,kG,kB = struct.unpack(footer_format, buffer[-raw_footer_size:])

            bayer = bayer.decode("utf-8")

            if magic != 0xED:
                raise Exception('Invalid Ava RAW file (magic)')
            if version != 1:
                raise Exception('Invalid Ava RAW file (version)')
            if channels != 1 and channels != 3:
                raise Exception('Invalid Ava RAW file (channels)')

            tif_data = buffer[:len(buffer)-raw_footer_size]
            img = cv2.imdecode(np.asarray(bytearray(tif_data), dtype=np.uint8), cv2.IMREAD_UNCHANGED)

            # RAW Processing
            self.img_uint16_linearRGB = raw_processing_to_16bit_linear(img,
                bayer,blacklevel,bitcount,kB,kG,kR)

    def as_cv2_sRGB_8bit(self):
        return (np.clip(Linear_to_sRGB(self.img_uint16_linearRGB).astype(np.uint16),0,65535) >> 8).astype(np.uint8)

    def as_cv2_LinearRGB_16bit(self):
        return self.img_uint16_linearRGB
