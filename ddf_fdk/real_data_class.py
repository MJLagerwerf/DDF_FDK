#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jan 23 13:16:18 2018

@author: lagerwer
"""


import numpy as np
import odl
import scipy.ndimage.morphology as sp
import gc

    

class real_data:
    def __init__(self, dataset, pix_size, src_rad, det_rad, ang_freq,
                 vox=None, vecs=None, zoom=False, offset=0):
        self.data_type = 'real'
        # %% load data
        self.vecs = vecs
        self.ang_freq = ang_freq
        self.dataset = dataset
        self.offset = offset
        if type(dataset) == dict:
            g_vec = np.load(dataset['g'])
            # %% adapt data
            self.angles_in = np.shape(g_vec)[0]
            g_vec = g_vec[::ang_freq, :, :]
            rs_detu = np.min(np.shape(g_vec)[1:]) * 2
            diff = int((rs_detu - np.size(g_vec, 1)) / 2)
            g_vec = np.concatenate((np.zeros((
                    np.size(g_vec, 0), diff, np.size(g_vec, 2))), g_vec,
                    np.zeros((np.size(g_vec, 0), diff, np.size(g_vec, 2)))), 1)
        else:
            g_vec = dataset
        
        # Define the dimensions of the problem in cm
        self.pix_size = pix_size
        self.angles = g_vec.shape[0]
        self.src_rad = src_rad
        self.det_rad = det_rad
        if zoom:
            self.magn = 1 
        else:
            self.magn = self.src_rad / (self.src_rad + self.det_rad)
        
        self.dpix = [np.size(g_vec, 1), np.size(g_vec, 2)]
        u_size = self.dpix[0] * pix_size / 2
        v_size = self.dpix[1] * pix_size / 2
        self.detecsize = np.array([u_size, v_size])
        
        if vox is None:
            self.voxels = [self.dpix[1], self.dpix[1], self.dpix[1]]

            self.volumesize = np.array([self.detecsize[1] * self.magn,
                                        self.detecsize[1] * self.magn,
                                        self.detecsize[1] * self.magn],
                                        dtype='float32')
        else:
            self.voxels = [vox, vox, vox]
            volsize = vox * self.pix_size * self.magn / 2
            self.volumesize = np.array([volsize, volsize, volsize], 
                                       dtype='float32')
        # %%
        # Make the reconstruction space
        self.reco_space = odl.uniform_discr(min_pt=-self.volumesize,
                                            max_pt=self.volumesize,
                                            shape=self.voxels,
                                            dtype='float32')
        if 'ground_truth' in dataset:
            self.f = self.reco_space.element(np.load(dataset['ground_truth']))
            self.mask_name = dataset['mask']

        # Make a circular scanning geometry
        angle_partition = odl.uniform_partition(offset, 2 * np.pi + offset,
                                                self.angles)

        # Make a flat detector space
        det_partition = odl.uniform_partition(-self.detecsize,
                                              self.detecsize,
                                                   self.dpix)
        self.det_space = odl.uniform_discr_frompartition(det_partition,
                                                         dtype='float32')
        # Create geometry
        self.geometry = odl.tomo.ConeFlatGeometry(
                angle_partition, det_partition, src_radius=self.src_rad,
                                det_radius=self.det_rad, axis=[0, 0, 1])
        
        self.angle_space = odl.uniform_discr_frompartition(
                self.geometry.motion_partition)
        # Forward Projection
        self.FwP = odl.tomo.RayTransform(self.reco_space, self.geometry,
                                         use_cache=False)

        # Backward Projection
        self.BwP = odl.tomo.RayBackProjection(self.reco_space,
                                              self.geometry,
                                              use_cache=False)
        if self.vecs is None:
            self.g = self.BwP.domain.element(g_vec)
        else:
            self.g = g_vec
            self.geometry = vecs
        
        gc.collect()
    def mask(self, x):
        if hasattr(self, 'f'):
            mask = np.load(self.mask_name)
            self.mask_size = np.sum(mask)
            return self.reco_space.element(mask * x)




