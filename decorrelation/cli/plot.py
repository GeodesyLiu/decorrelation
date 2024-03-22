# AUTOGENERATED! DO NOT EDIT! File to edit: ../../nbs/CLI/plot.ipynb.

# %% auto 0
__all__ = ['zarr_stack_info', 'Coord', 'render_ras_tiles', 'hv_image', 'ras_plot', 'hv_image_stack', 'ras_stack_plot']

# %% ../../nbs/CLI/plot.ipynb 4
import logging
import zarr
import numpy as np
import math
from pathlib import Path
import pandas as pd
from tqdm import tqdm
import sys
from functools import partial
from typing import Callable
import numpy as np
import holoviews as hv
from holoviews import opts
from holoviews import streams

from .utils.logging import de_logger, log_args

# %% ../../nbs/CLI/plot.ipynb 5
def zarr_stack_info(zarr_path_list, #list of zarr path
                   ):
    shape_list = []; chunks_list = []; dtype_list = []
    for zarr_path in zarr_path_list:
        zarr_data = zarr.open(zarr_path,'r')
        shape_list.append(zarr_data.shape)
        chunks_list.append(zarr_data.chunks)
        dtype_list.append(zarr_data.dtype)
    df = pd.DataFrame({'path':zarr_path_list,'shape':shape_list,'chunks':chunks_list,'dtype':dtype_list})
    return df

# %% ../../nbs/CLI/plot.ipynb 6
class Coord(object):
    def __init__(self,x0,dx,nx,y0,dy,ny):
        self.x0 = x0
        self.dx = dx
        self.nx = nx
        self.xm = x0+(nx-1)*dx
        self.y0 = y0
        self.dy = dy
        self.ny = ny
        self.ym = y0+(ny-1)*dy
        self.maxlevel = math.floor(math.log2(min(nx,ny)))
    
    def max_idx(self,level):
        return math.ceil(self.nx/(2**level))-1, math.ceil(self.ny/(2**level))-1
    
    def coord2idx(self,x,y,level): # include a buffer if not x, y not exactly on the grid
        xi = int((x-self.x0)/self.dx/2**level)
        yi = int((y-self.y0)/self.dy/2**level)
        xi_max, yi_max = self.max_idx(level)
        return sorted((0,xi,xi_max))[1], sorted((0,yi,yi_max))[1]
    def idx2coord(self,xi,yi,level):
        xi_max, yi_max = self.max_idx(level)
        xi, yi = sorted((0,xi,xi_max))[1], sorted((0,yi,yi_max))[1]
        return xi*2**level*self.dx+self.x0, yi*2**level*self.dy+self.y0

# %% ../../nbs/CLI/plot.ipynb 7
@log_args
@de_logger
def render_ras_tiles(ras:str, # path to input data, 2D zarr array (one single raster) or 3D zarr array (a stack of rasters)
                     out_dir:str, # output directory to store rendered data
                       ):
    '''render raster data to tiles of difference zoom levels.'''
    logger = logging.getLogger(__name__)
    out_dir = Path(out_dir); out_dir.mkdir(exist_ok=True)
    ras_zarr = zarr.open(ras,'r')
    logger.zarr_info(ras, ras_zarr)
    
    ny, nx = ras_zarr.shape[0:2]
    maxlevel = math.floor(math.log2(min(nx,ny))) # so at least 2 pixels
    logger.info(f'rendered tiles zoom level range from 0 (finest resolution) to {maxlevel} (coarsest resolution).')

    ndim = ras_zarr.ndim
    o_zarr_path_list = []; o_zarr_list = []
    for level in range(maxlevel+1):
        if ndim == 3:
            shape = (math.ceil(ny/(2**level)), math.ceil(nx/(2**level)), ras_zarr.shape[2])
            chunks = (256, 256, 1)
        elif ndim == 2:
            shape = (math.ceil(ny/(2**level)), math.ceil(nx/(2**level)))
            chunks = (256, 256)
        else:
            raise ValueError('ndim of input should be 2 or 3.')
        o_zarr_path = out_dir/f'{level}.zarr'
        o_zarr = zarr.open(zarr.NestedDirectoryStore(o_zarr_path),
                           'w',shape=shape,chunks=chunks,dtype=ras_zarr.dtype)
        o_zarr_path_list.append(o_zarr_path); o_zarr_list.append(o_zarr)

    df_disp = zarr_stack_info(o_zarr_path_list)
    logger.info(f'tiles to be rendered: \n {df_disp}')
    
    logger.info(f'tiles rendering starts.')
    if ndim == 2:
        ras_data = ras_zarr[:]
        for level in tqdm(range(maxlevel+1),file=sys.stdout,desc='Tiles'):
            o_zarr_list[level][:,:] = ras_data[::2**level,::2**level]
    else:
        for i in tqdm(range(ras_zarr.shape[2]),file=sys.stdout,desc='Images'):
            ras_data = ras_zarr[:,:,i]
            for level in range(maxlevel+1):
            # for level in tqdm(range(maxlevel+1),file=sys.stdout,desc='Tiles',position=0):
                o_zarr_list[level][:,:,i] = ras_data[::2**level,::2**level]
    logger.info(f'tiles rendering finished.')

# %% ../../nbs/CLI/plot.ipynb 13
def hv_image(x_range,y_range,width,height,scale,data_dir,post_proc,coord):
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
    data_zarr = zarr.open(data_dir/f'{level}.zarr','r')
    xi0, yi0 = coord.coord2idx(x0,y0,level)
    xim, yim = coord.coord2idx(xm,ym,level)
    x0, y0 = coord.idx2coord(xi0,yi0,level)
    xm, ym = coord.idx2coord(xim,yim,level)
    data = data_zarr[yi0:yim+1,xi0:xim+1]
    data = post_proc(data)
    return hv.Image(data[::-1,:],bounds=(x0, y0, xm, ym))

# %% ../../nbs/CLI/plot.ipynb 14
def ras_plot(rendered_tiles_dir:str, # directory to the rendered images
             post_proc:Callable=None, # function for the post processing
             bounds:tuple=None, # bounding box (x0, y0, x_max, y_max)
            ):
    '''plot rendered ras tiles.'''
    rendered_tiles_dir = Path(rendered_tiles_dir)
    data_zarr = zarr.open(rendered_tiles_dir/'0.zarr','r')
    ny, nx = data_zarr.shape
    
    if post_proc is None: post_proc = lambda x: x
    if bounds is None:
        x0 = 0; dx = 1; y0 = 0; dy = 1
    else:
        x0, y0, xm, ym = bounds
        dx = (xm-x0)/(nx-1); dy = (ym-y0)/(ny-1)
    coord = Coord(x0,dx,nx,y0,dy,ny)
    
    rangexy = streams.RangeXY()
    plotsize = streams.PlotSize()
    images = hv.DynamicMap(partial(hv_image,data_dir=rendered_tiles_dir,post_proc=post_proc,coord=coord),streams=[rangexy,plotsize])
    return images

# %% ../../nbs/CLI/plot.ipynb 23
def hv_image_stack(x_range,y_range,width,height,scale,data_dir,post_proc,coord,i=0):
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
    data_zarr = zarr.open(data_dir/f'{level}.zarr','r')
    xi0, yi0 = coord.coord2idx(x0,y0,level)
    xim, yim = coord.coord2idx(xm,ym,level)
    x0, y0 = coord.idx2coord(xi0,yi0,level)
    xm, ym = coord.idx2coord(xim,yim,level)
    data = post_proc(data_zarr,slice(xi0,xim+1),slice(yi0,yim+1),i)
    return hv.Image(data[::-1,:],bounds=(x0, y0, xm, ym))

# %% ../../nbs/CLI/plot.ipynb 24
def ras_stack_plot(rendered_tiles_dir:str, # directory to the rendered images
                   post_proc:Callable=None, # function for the post processing
                   bounds:tuple=None, # bounding box (x0, y0, x_max, y_max)
                  ):
    '''plot rendered stack of ras tiles.'''
    rendered_tiles_dir = Path(rendered_tiles_dir)
    data_zarr = zarr.open(rendered_tiles_dir/'0.zarr','r')
    ny, nx = data_zarr.shape[:2]
    
    if post_proc is None: post_proc = lambda x: x
    if bounds is None:
        x0 = 0; dx = 1; y0 = 0; dy = 1
    else:
        x0, y0, xm, ym = bounds
        dx = (xm-x0)/(nx-1); dy = (ym-y0)/(ny-1)
    coord = Coord(x0,dx,nx,y0,dy,ny)
    
    rangexy = streams.RangeXY()
    plotsize = streams.PlotSize()
    images = hv.DynamicMap(partial(hv_image_stack,data_dir=rendered_tiles_dir,post_proc=post_proc,coord=coord),streams=[rangexy,plotsize],kdims='i')
    return images
