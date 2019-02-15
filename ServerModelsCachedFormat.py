import sys, os, time

import numpy as np

import fiona
import fiona.transform
import shapely
import shapely.geometry
import rasterio
import rasterio.mask

import GeoTools

class CachedModel(object):

    def __init__(self, results_dir):
        self.results_dir = results_dir

    def run(self, naip_data, naip_fn, extent, buffer):
        return self.get_cached_by_extent(naip_fn, extent, buffer), "Full USA Pre-run %s" % (self.results_dir)

    def get_cached_by_extent(self, fn, extent, buffer):
        fn = fn.replace("esri-naip/", "full-usa-output/%s/" % (self.results_dir))[:-4] + "_prob.tif"

        f = rasterio.open(fn, "r")
        geom = GeoTools.extent_to_transformed_geom(extent, f.crs["init"])
        pad_rad = 15 # TODO: this might need to be changed for much larger inputs
        buffed_geom = shapely.geometry.shape(geom).buffer(pad_rad)
        minx, miny, maxx, maxy = buffed_geom.bounds
        geom = shapely.geometry.mapping(shapely.geometry.box(minx, miny, maxx, maxy, ccw=True))
        out_image, out_transform = rasterio.mask.mask(f, [geom], crop=True)
        src_crs = f.crs.copy()
        f.close()
        
        dst_crs = {"init": "EPSG:%s" % (extent["spatialReference"]["latestWkid"])}
        dst_transform, width, height = rasterio.warp.calculate_default_transform(
            src_crs,
            dst_crs,
            width=out_image.shape[2], height=out_image.shape[1],
            left=buffed_geom.bounds[0],
            bottom=buffed_geom.bounds[1],
            right=buffed_geom.bounds[2],
            top=buffed_geom.bounds[3],
            resolution=1
        )

        dst_image = np.zeros((out_image.shape[0], height, width), np.uint8)
        rasterio.warp.reproject(
                source=out_image,
                destination=dst_image,
                src_transform=out_transform,
                src_crs=src_crs,
                dst_transform=dst_transform,
                dst_crs=dst_crs,
                resampling=rasterio.warp.Resampling.nearest
        )
        
        # Calculate the correct padding
        #w = extent["xmax"] - extent["xmin"]
        #padding = int(np.round((dst_image.shape[1] - w) / 2))

        dst_image = np.rollaxis(dst_image, 0, 3)
        #dst_image = dst_image[padding:-padding, padding:-padding, :]

        return dst_image / 255.0