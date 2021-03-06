#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Sep  3 14:29:41 2018

@author: lagerwer
"""
import numpy as np
import astra
import odl
import pylab

from . import support_functions as sup

def FDK_astra(g, filt, geom, reco_space, w_du, ang_freq=None, ang_offset=0):
    # %% Create geometry
    # Make a circular scanning geometry
    ang, u, v = g.shape
    minvox = reco_space.min_pt[0]
    maxvox = reco_space.max_pt[0]
    vox = np.shape(reco_space)[0]
    vol_geom = astra.create_vol_geom(vox, vox, vox, minvox, maxvox, minvox,
                                     maxvox, minvox, maxvox)
    # Build the projection geometry, through vecs or odl geometry
    if type(geom) == np.ndarray:
        vecs = geom
        proj_geom = astra.create_proj_geom('cone_vec', v, u, vecs)
    elif type(geom) == odl.tomo.geometry.conebeam.ConeFlatGeometry:
        angles = np.linspace((1/ ang) * np.pi + ang_offset,
                             (2 +1 / ang) * np.pi + ang_offset, ang, False)
        w_du, w_dv = 2 * geom.detector.partition.max_pt / [u, v]
        proj_geom = astra.create_proj_geom('cone', w_dv, w_du, v, u,
                                           angles, geom.src_radius,
                                           geom.det_radius)
    elif geom == 'xHQ':
        ang = 1000
        src_rad = 100
        det_rad = 0
        angles = np.linspace((1 / ang) * np.pi, (2 + 1 / ang) * np.pi, ang,
                      False)
#        angles = np.linspace(0, (2) * np.pi, ang,
#                      False)
        obj_size = 2 * reco_space.max_pt[0]
        w_du = 2 * obj_size / u
        w_dv = obj_size / v
        proj_geom = astra.create_proj_geom('cone', w_dv, w_du, v, u,
                                           angles, src_rad * obj_size,
                                           det_rad * obj_size)
    g = np.transpose(np.asarray(g.copy()), (2, 0, 1))

    cfg = astra.astra_dict('FDK_CUDA')
    # %%
    # Create a data object for the reconstruction
    rec = np.zeros(astra.geom_size(vol_geom), dtype=np.float32)
    rec_id = astra.data3d.link('-vol', vol_geom, rec)
#    rec_id = astra.data3d.create('-vol', vol_geom)

    proj_id = astra.data3d.create('-proj3d', proj_geom, g)


#    rec_id = astra.data3d.link('-vol', vol_geom, rec)
#    if geom == 'xHQ':
#        cfg['option'] = { 'FilterType': 'hann' }
#    else:
    fullFilterSize = int(2 ** (np.ceil(np.log2(2 * u))))
    halfFilterSize = fullFilterSize // 2 + 1
    # %% Make the matrix columns of the matrix B
    filter2d = np.zeros((ang, halfFilterSize))
    for i in range(ang):
        filter2d[i, :] = filt * 4 * w_du

    # %% Make a filter geometry
    filter_geom = astra.create_proj_geom('parallel', w_du,  halfFilterSize,
                                         np.zeros((ang)))
    filter_id = astra.data2d.create('-sino', filter_geom, filter2d)
    cfg['option'] = { 'FilterSinogramId': filter_id}


    cfg['ReconstructionDataId'] = rec_id
    cfg['ProjectionDataId'] = proj_id

    # Create the algorithm object from the configuration structure
    alg_id = astra.algorithm.create(cfg)

    # %%
    astra.algorithm.run(alg_id)
    rec = np.transpose(rec, (2, 1, 0))

    # %%
    # Clean up. Note that GPU memory is tied up in the algorithm object,
    # and main RAM in the data objects.
    astra.algorithm.delete(alg_id)
    astra.data3d.delete(rec_id)
    astra.data3d.delete(proj_id)
    if geom == 'xHQ':
        pass
    else:
        astra.data2d.delete(filter_id)
    return rec