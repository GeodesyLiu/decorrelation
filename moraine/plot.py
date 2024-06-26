# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/API/plot.ipynb.

# %% auto 0
__all__ = ['ras_plot', 'ras_stack_plot', 'points', 'points_stack', 'bg_alpha']

# %% ../nbs/API/plot.ipynb 3
import numpy as np
import pandas as pd
from typing import Union
from functools import partial
import math

import holoviews as hv
from holoviews import streams
import holoviews.operation.datashader as hd
import datashader as ds
from .coord_ import Coord

# %% ../nbs/API/plot.ipynb 10
def _hv_ras_callback(x_range,y_range,width,height,scale,data,coord,level_increase):
    # start = time.time()
    if x_range is None:
        x0 = coord.x0; xm = coord.xm
    else:
        x0, xm = x_range
    if y_range is None:
        y0 = coord.y0; ym = coord.ym
    else:
        y0, ym = y_range
    if height is None: height = hv.plotting.bokeh.ElementPlot.height
    if width is None: width = hv.plotting.bokeh.ElementPlot.width

    x_res = (xm-x0)/width; y_res = (ym-y0)/height
    level = math.floor(math.log2(min(x_res,y_res)))
    level += level_increase
    level = sorted((0, level, coord.maxlevel))[1]
    xi0, yi0, xim, yim = coord.hv_bbox2gix_bbox((x0,y0,xm,ym),level)
    coord_bbox = coord.gix_bbox2hv_bbox((xi0, yi0, xim, yim),level)
    plot_data = data[::2**level,::2**level][yi0:yim+1,xi0:xim+1]
    return hv.Image(plot_data[::-1,:],bounds=coord_bbox)

# %% ../nbs/API/plot.ipynb 11
def ras_plot(data:np.ndarray, # 2D numpy array to be visualized
             bounds:tuple=None, # bounding box (x0, y0, x_max, y_max)
             level_increase=0, # amount of zoom level increase for more clear point show and faster responds time
            ):
    '''plot in memory ras data.'''
    ny, nx = data.shape
    
    if bounds is None:
        x0 = 0; dx = 1; y0 = 0; dy = 1
    else:
        x0, y0, xm, ym = bounds
        dx = (xm-x0)/(nx-1); dy = (ym-y0)/(ny-1)
    coord = Coord(x0,dx,nx,y0,dy,ny)
    
    rangexy = streams.RangeXY()
    plotsize = streams.PlotSize()
    images = hv.DynamicMap(partial(_hv_ras_callback,data=data,
                                   coord=coord,level_increase=level_increase),streams=[rangexy,plotsize])
    return images

# %% ../nbs/API/plot.ipynb 16
def _hv_ras_stack_callback(x_range,y_range,width,height,scale,data,coord,level_increase,i=0):
    if x_range is None:
        x0 = coord.x0; xm = coord.xm
    else:
        x0, xm = x_range
    if y_range is None:
        y0 = coord.y0; ym = coord.ym
    else:
        y0, ym = y_range
    if height is None: height = hv.plotting.bokeh.ElementPlot.height
    if width is None: width = hv.plotting.bokeh.ElementPlot.width

    x_res = (xm-x0)/width; y_res = (ym-y0)/height
    level = math.floor(math.log2(min(x_res,y_res)))
    level = sorted((0, level, coord.maxlevel))[1]
    level += level_increase
    xi0, yi0, xim, yim = coord.hv_bbox2gix_bbox((x0,y0,xm,ym),level)
    coord_bbox = coord.gix_bbox2hv_bbox((xi0, yi0, xim, yim),level)
    plot_data = data[::2**level,::2**level,i][yi0:yim+1,xi0:xim+1]
    return hv.Image(plot_data[::-1,:],bounds=coord_bbox)

# %% ../nbs/API/plot.ipynb 17
def ras_stack_plot(data:str, # 3D numpy array, (nlines, width, nimages)
                   bounds:tuple=None, # bounding box (x0, y0, x_max, y_max)
                   level_increase=0, # amount of zoom level increase for more clear point show and faster responds time
                  ):
    '''plot rendered stack of ras tiles.'''
    ny, nx = data.shape[:2]
    
    if bounds is None:
        x0 = 0; dx = 1; y0 = 0; dy = 1
    else:
        x0, y0, xm, ym = bounds
        dx = (xm-x0)/(nx-1); dy = (ym-y0)/(ny-1)
    coord = Coord(x0,dx,nx,y0,dy,ny)
    
    rangexy = streams.RangeXY()
    plotsize = streams.PlotSize()
    images = hv.DynamicMap(partial(_hv_ras_stack_callback,data=data,
                                   coord=coord,level_increase=level_increase),streams=[rangexy,plotsize],kdims='i')
    return images

# %% ../nbs/API/plot.ipynb 22
def points(data:pd.DataFrame, # dataset to be plot
           kdims:list,# colomn name of Mercator coordinate in dataframe
           pdim:str, # column name of data to be plotted in dataframe
           prange:tuple=None, # range of data to be plotted, it is interactively adjusted by default
           aggregator=ds.first, # aggregator for data rasterization
           use_hover:bool=True, # use hover to show data
           vdims:list=None, # column name of data showed on hover except kdims and pdim. These two are always showed.
           google_earth:bool=False, # if use google earth imagery as the background
           ):
    '''Interative visulization of a point cloud image.
    '''
    if prange is None: prange = (None, None)
    if vdims is None: vdims = []
    if pdim in vdims: vdims.remove(pdim)
    vdims = [hv.Dimension(pdim,range=prange)] + vdims
    points = hv.Points(data,kdims=kdims, vdims=vdims)
    points = hd.rasterize(points,aggregator=aggregator(pdim),vdim_prefix='')
    points = hd.dynspread(points, max_px=5, threshold=0.2)
    if use_hover:
        highlight = hd.inspect_points(points).opts(marker='o',size=10,tools=['hover'])
        points = points*highlight
    if google_earth:
        geo_bg = hv.Tiles('https://mt1.google.com/vt/lyrs=s&x={X}&y={Y}&z={Z}',name='GoogleMapsImagery')
        points = geo_bg*points
    return points

# %% ../nbs/API/plot.ipynb 28
def points_stack(data:pd.DataFrame, # common data in all plots
                 kdims:list,# colomn name of Mercator coordinate in dataframe
                 pdata:pd.DataFrame, # data to be plotted as color
                 pdim:str, # label of pdata
                 prange:tuple=None, # range of pdata, it is interactively adjusted by default
                 aggregator=ds.first, # aggregator for data rasterization
                 use_hover:bool=True, # use hover to show other column
                 vdims:list=None, # column name of data showed on hover except kdims which are always showed.
                 google_earth:bool=False, # if use google earth imagery as the background
                ):
    '''Interative visulization of a stack of point cloud images.
    '''
    if prange is None: prange = (None, None)
    if vdims is None: vdims = []
    if pdim in vdims: vdims.remove(pdim)
    vdims = [hv.Dimension(pdim,range=prange)] + vdims

    plot_stack = {}
    for (name, column) in pdata.items():
        _data = data.copy(deep=False)
        _data[pdim] = column
        plot_stack[name] = hv.Points(_data,kdims=kdims,vdims=vdims)

    hmap = hv.HoloMap(plot_stack, kdims=pdim)
    hmap = hd.rasterize(hmap, aggregator=aggregator(pdim),vdim_prefix='')
    hmap = hd.dynspread(hmap, max_px=5, threshold=0.2)

    if use_hover:
        highlight = hd.inspect_points(hmap).opts(marker='o',size=10,tools=['hover'])
        hmap = hmap*highlight
    if google_earth:
        geo_bg = hv.Tiles('https://mt1.google.com/vt/lyrs=s&x={X}&y={Y}&z={Z}',name='GoogleMapsImagery')
        hmap = geo_bg*hmap
    return hmap

# %% ../nbs/API/plot.ipynb 36
def bg_alpha(pwr):
    _pwr = np.power(pwr,0.35)
    cv = _pwr.mean()*2.5
    v = (_pwr.clip(0., cv))/cv
    return v
