# .shp 파일을 raster .tif으로 변환 + 크롭

import cv2
import copy
import numpy as np
import pandas as pd
import sys
import os
import random
import errno
import matplotlib.pyplot as plt
import argparse

from osgeo import gdal
from osgeo import ogr
from matplotlib.patches import Polygon



def write_geo_tiff(save_path, im, geo_transform, projection, bcnt):
    ''' save_path -> 저장 경로 (./test.tif)
        im -> 저장할 array
        geo_transform -> gdal.Open(ref_tif_path).GetGeoTransform()
        projection -> gdal.Open(ref_tif_path).GetProjection()
        '''
        
    driver = gdal.GetDriverByName('GTiff')
    # bcnt, width, height = im.shape
    save_path = 'D:/UFO/code/dataset/asiana/result.tif'
    print(save_path)
    print(geo_transform)
    print(projection)
    
    DataSet = driver.Create(save_path, im.shape[1], im.shape[0], bcnt, gdal.GDT_Byte) # gdal.GDT_Byte
    DataSet.SetGeoTransform(geo_transform)
    DataSet.SetProjection(projection)
    
    if len(im.shape) == 3: 
        for n in range(im.shape[-1]):
            DataSet.GetRasterBand(n+1).WriteArray(im[..., n])
    elif len(im.shape) == 2: 
        DataSet.GetRasterBand(1).WriteArray(im)

    DataSet.FlushCache() 
    DataSet = None

def get_field_names(shp_path): 
    source = ogr.Open(shp_path)
    layer = source.GetLayer()
    fieldNames = []
    ldefn = layer.GetLayerDefn()
    for n in range(ldefn.GetFieldCount()):
        fdefn = ldefn.GetFieldDefn(n)
        fieldNames.append(fdefn.name)
    return fieldNames

def get_tif_info(tifFilePath):

    try:
        tifDataset = gdal.Open(tifFilePath)
    except RuntimeError as ex:
        raise IOError(ex)



    img = tifDataset.ReadAsArray()
    print(img.shape)

    if len(img.shape) == 3:
        img = np.transpose(img, (1, 2, 0))  #convert to RGB
        img = (img - np.min(img))/(np.max(img)-np.min(img)) * 255.0
        img = img.astype(np.uint8)

    geoTransFormInfo = tifDataset.GetGeoTransform()

    rasterXSize = tifDataset.RasterXSize
    rasterYSize = tifDataset.RasterYSize
    bands = tifDataset.RasterCount

    xCoordinateLen = rasterXSize * geoTransFormInfo[1]
    yCoordinateLen = rasterYSize * (-1 * geoTransFormInfo[5])

    xCoordinateMin = geoTransFormInfo[0]
    xCoordinateMax = geoTransFormInfo[0] + xCoordinateLen

    yCoordinateMin = geoTransFormInfo[3] - yCoordinateLen
    yCoordinateMax = geoTransFormInfo[3]

    tiffXInfo = [rasterXSize, xCoordinateLen, xCoordinateMin, xCoordinateMax]
    tiffYInfo = [rasterYSize, yCoordinateLen, yCoordinateMin, yCoordinateMax]

    return tiffXInfo, tiffYInfo, bands, tifDataset.GetGeoTransform(), tifDataset.GetProjection(), img


def Raster2pix_coord(inputData, xMax, xMin, yMax, yMin, convertXMax, convertYMax, yFlag=False):
    
    outputdata = copy.deepcopy(inputData)

    for row in outputdata:

        row[0] = (row[0] - xMin) / (xMax - xMin)
        row[0] = row[0] * convertXMax
        row[0] = int(row[0])

        row[1] = (row[1] - yMin) / (yMax - yMin)
        
        if yFlag: # y point start is upper left
            row[1] = (1 - row[1]) * convertYMax
        else:
            row[1] = row[1] * convertYMax
        row[1] = int(row[1])

    return outputdata

def pix_coord2Raster(inputData, xMax, xMin, yMax, yMin, convertXMax, convertYMax, yFlag=False):

    outputdata = copy.deepcopy(inputData)
    
    for row in outputdata:

        row[0] = int(row[0] * (xMax - xMin) / convertXMax + xMin)
        row[1] = int(row[1] * (yMax - yMin) / convertYMax) # + yMin
    
    return outputdata


def make_directory(path):
    try:
        if not (os.path.isdir(path)):
            os.makedirs(os.path.join(path))
            print('make directory', path)
    except OSError as e:
        if e.errno != errno.EEXIST:
            print('Failed to create directory!!!!!')
            raise

def get_multipolygon(shpFilePath, tiffXInfo, tiffYInfo):
    fieldNames = ['id']
    
    
    # read shape file
    dataSource = ogr.Open(shpFilePath, update=1)
    daLayer = dataSource.GetLayerByIndex(0)

    # number of features
    featureCount = daLayer.GetFeatureCount() # includes all polygons and multipolygons
    
    polygon = []
    pixelPolygonList = []
    pixelPolygonHole = []
    rowList = []
    class_idx = []

    for i in range(featureCount): # loop over all the polygons (one polygon = one feature) in the shp file
        feature = daLayer.GetFeature(i) # ID
        geometryInfo = feature.GetGeometryRef() # get geometry of polygon and holes (if applicable)

        if geometryInfo is None:
            print('geometryInfo is None')
        else:
            polygonBoundary = geometryInfo.GetBoundary() # linestring or multilinestring
            pointCount = polygonBoundary.GetPointCount() # number of x-y point pairs in polygon to define it
            multipolygon = True if pointCount == 0 else False

            print('feature : ', i, '   multipolygon = ', multipolygon)

            # if polygon has holes
            if multipolygon: 
                nbrRings = geometryInfo.GetGeometryCount()

                # get outer polygon (first entry)
                outer = geometryInfo.GetGeometryRef(0)
                for j in range(outer.GetPointCount()): 
                    polygon.append([outer.GetX(j), outer.GetY(j)]) # polygon = [[point1_x, point2_y], [point2_x, point2_y], ...]

                # get inner rings (all other entries)
                for j in range(1, nbrRings): # for each hole
                    ring = geometryInfo.GetGeometryRef(j)
              
                    pt_pairs = []
                    for k in range(ring.GetPointCount()): # for each point
                        pt_pairs.append([ring.GetX(k), ring.GetY(k)])

                    # convert point pairs
                    pixelPolygonHole.append(Raster2pix_coord(
                        pt_pairs, xMax=tiffXInfo[3], xMin=tiffXInfo[2],yMax=tiffYInfo[3], yMin=tiffYInfo[2],
                        convertXMax=tiffXInfo[0], convertYMax=tiffYInfo[0], yFlag=True))
            
            # if polygon doesn't have holes
            else:
                for j in range(pointCount): 
                    polygon.append([polygonBoundary.GetX(j), polygonBoundary.GetY(j)]) # polygon = [[point1_x, point2_y], [point2_x, point2_y], ...]

            # Longitude/Latitude point convert to raster pixel point
            pixelPolygon = Raster2pix_coord(
                polygon, xMax=tiffXInfo[3], xMin=tiffXInfo[2],yMax=tiffYInfo[3], yMin=tiffYInfo[2],
                convertXMax=tiffXInfo[0], convertYMax=tiffYInfo[0], yFlag=True)

            # append points make list
            pixelPolygonList.append(pixelPolygon) # pixelPolygonList = converted polygon, for all features 
            rowList.append(str(daLayer.GetName()) + "_" + str(feature.GetFID()))

            for idx, _ in enumerate(fieldNames):
                class_idx.append(feature.GetField(idx))

            pixelPolygon = []
            polygon = []

    rowList = pd.DataFrame(rowList)
    pixelPolygonList = pd.DataFrame(pixelPolygonList)
    pixelPolygonList = pd.concat([rowList, pixelPolygonList], axis=1, ignore_index=True)

    pixelPolygonHole = pd.DataFrame(pixelPolygonHole)

    return pixelPolygonList, class_idx, pixelPolygonHole

def draw_mask(class_idx, tiffXInfo, tiffYInfo, staticPixelPolygon, pixelPolygonHoleList, bands): 

    src = np.zeros(shape=[tiffYInfo[0], tiffXInfo[0], bands], dtype=np.uint8)
    img = src.copy()

    polygonPoints = staticPixelPolygon.iloc[:, 1:]

    polygon = []
    count = -1
    # loop over all points in all polygons
    for i in range(polygonPoints.shape[0]): # for all points in ith polygon
        count += 1 
        for j in range(polygonPoints.shape[1]): # for jth point in ith polygon
            if polygonPoints.iloc[i, j] is not None: 
                polygon.append([polygonPoints.iloc[i, j][0], polygonPoints.iloc[i, j][1]])
                if class_idx[count] == None:
                    continue
                color = class_idx[count]

        polygon = np.asarray(polygon, np.int32) # all points in ith polygon

        if len(polygon) != 0:
            img = cv2.fillPoly(img, np.int32([polygon]), int(color))
        
        polygon = []
    

    # loop over all points in all holes
    polygon = []
    for i in range(pixelPolygonHoleList.shape[0]): # for all points in ith polygon
        count += 1 
        for j in range(pixelPolygonHoleList.shape[1]): # for jth point in ith polygon
            if pixelPolygonHoleList.iloc[i, j] is not None: 
                polygon.append([pixelPolygonHoleList.iloc[i, j][0], pixelPolygonHoleList.iloc[i, j][1]])
            
        polygon = np.asarray(polygon, np.int32) # all points in ith polygon

        if len(polygon) != 0:
            img = cv2.fillPoly(img, np.int32([polygon]), (0))

        polygon = []

    return img



def draw_mask_from_shpfile(shpFilePath, tiffXInfo, tiffYInfo, bands = 1):
    fieldNames = ['id']
    
    src = np.zeros(shape=[tiffYInfo[0], tiffXInfo[0], bands], dtype=np.uint8)
    img = src.copy()
    # read shape file
    dataSource = ogr.Open(shpFilePath, update=1)
    daLayer = dataSource.GetLayerByIndex(0)

    # number of features
    featureCount = daLayer.GetFeatureCount() # includes all polygons and multipolygons
    

    rowList = []
    class_idx = []
    polygon_dict = {'multipolygon':[], 'simple_polygon':[]}
    polygon = []

    for i in range(featureCount): # loop over all the polygons (one polygon = one feature) in the shp file
        temp_dict = {}
        feature = daLayer.GetFeature(i) # ID
        geometryInfo = feature.GetGeometryRef() # get geometry of polygon and holes (if applicable)
        id = feature.GetField('id')
        temp_dict['id'] = id

        if geometryInfo is None:
            print('geometryInfo is None')
        else:
            polygonBoundary = geometryInfo.GetBoundary() # linestring or multilinestring
            pointCount = polygonBoundary.GetPointCount() # number of x-y point pairs in polygon to define it
            multipolygon = True if pointCount == 0 else False

            # print('feature : ', id, '   multipolygon = ', multipolygon)

            # if polygon has holes
            if multipolygon: 
                temp_dict['rings'] = []
                nbrRings = geometryInfo.GetGeometryCount()

                # get outer polygon (first entry)
                outer = geometryInfo.GetGeometryRef(0)
                polygon = []
                for j in range(outer.GetPointCount()):                     
                    polygon.append([outer.GetX(j), outer.GetY(j)]) # polygon = [[point1_x, point2_y], [point2_x, point2_y], ...]
                polygon = Raster2pix_coord(polygon, xMax=tiffXInfo[3], xMin=tiffXInfo[2],yMax=tiffYInfo[3], yMin=tiffYInfo[2],convertXMax=tiffXInfo[0], convertYMax=tiffYInfo[0], yFlag=True)
                temp_dict['polygon'] = polygon

                
                # get inner rings (all other entries)
                for j in range(1, nbrRings): # for each hole
                    ring = geometryInfo.GetGeometryRef(j)
              
                    pt_pairs = []
                    for k in range(ring.GetPointCount()): # for each point
                        pt_pairs.append([ring.GetX(k), ring.GetY(k)])
                    ring_polygon = Raster2pix_coord(pt_pairs, xMax=tiffXInfo[3], xMin=tiffXInfo[2],yMax=tiffYInfo[3], yMin=tiffYInfo[2],convertXMax=tiffXInfo[0], convertYMax=tiffYInfo[0], yFlag=True)
                    temp_dict['rings'].append(ring_polygon)
                polygon_dict['multipolygon'].append(temp_dict)

            
            # if polygon doesn't have holes
            else:
                polygon = []
                # print(polygonBoundary)
                for j in range(pointCount): 
                    polygon.append([polygonBoundary.GetX(j), polygonBoundary.GetY(j)]) # polygon = [[point1_x, point2_y], [point2_x, point2_y], ...]
                polygon = Raster2pix_coord(polygon, xMax=tiffXInfo[3], xMin=tiffXInfo[2],yMax=tiffYInfo[3], yMin=tiffYInfo[2],convertXMax=tiffXInfo[0], convertYMax=tiffYInfo[0], yFlag=True)
                temp_dict['polygon'] = polygon
                
                polygon_dict['simple_polygon'].append(temp_dict)

    for multipolygon_dict in polygon_dict['multipolygon']:
        id = multipolygon_dict['id']
        polygon = multipolygon_dict['polygon']
        if len(polygon) != 0:
            img = cv2.fillPoly(img, np.int32([polygon]), id)

        rings = multipolygon_dict['rings']
        
        for ring in rings:
            if len(ring) != 0:
                img = cv2.fillPoly(img, np.int32([ring]), 0)

    for simple_polygon_dict in polygon_dict['simple_polygon']:
        id = simple_polygon_dict['id']
        polygon = simple_polygon_dict['polygon']

        if len(polygon) != 0:
            img = cv2.fillPoly(img, np.int32([polygon]), id)


    return img
        


def save_patch(img, save_path, shp_name, tifDataset, gridWidth, gridHeight, stride, bands): 
    
    print('-' * 20, 'generating patch', '-' * 20)

    datasetCount = 0
    cutPixel = (bands * gridWidth * gridHeight) * 0.5

    xPointStart = 0
    yPointStart = 0

    # 자르기
    for y in range(int(np.ceil((tiffYInfo[0]) / (gridHeight - stride))+1)):
        for x in range(int(np.ceil((tiffXInfo[0]) / (gridWidth - stride))+1)):
            yPointStart = y*(gridHeight - stride) if (y*(gridHeight - stride) + gridHeight) <= tiffYInfo[0] else tiffYInfo[0] - gridHeight
            xPointStart = x*(gridWidth - stride) if (x*(gridWidth - stride) + gridWidth) <= tiffXInfo[0] else tiffXInfo[0] - gridWidth

            tifCrop = tifDataset.ReadAsArray(xPointStart, yPointStart, gridWidth, gridHeight)

            # calculate no value data
            arr = np.where(tifCrop == 0)
            arr = np.asarray(arr)

            # if no value data bigger than cutPixel(rate)
            if arr.shape[1] <= cutPixel:
                crop = img[yPointStart:yPointStart+gridHeight, xPointStart:xPointStart+gridWidth]

                tifCrop = np.transpose(tifCrop, (1, 2, 0))
                tifCrop = tifCrop[...,:4]

                cv2.imwrite(save_path + '/mask/' + shp_name[:-4] + '_' + str(datasetCount) + '.tif', crop)                    
                cv2.imwrite(save_path + '/patch/' + shp_name[:-4] + '_' + str(datasetCount) + '.tif', tifCrop)

            datasetCount += 1

            # redundant crops
            if xPointStart == (tiffXInfo[0] - gridWidth): 
                break
        if yPointStart == (tiffYInfo[0] - gridHeight): 
            break


def shp2tif(shpFilePath, tifFilePath, save_path):

        # make save directory
        make_directory(save_path)

        # get width, height of original tif 
        tiffXInfo, tiffYInfo, band,_,_,_= get_tif_info(tifFilePath)

        # get all shape file field names

        img = draw_mask_from_shpfile(shpFilePath, tiffXInfo, tiffYInfo, bands = 1)
        geo_transform = gdal.Open(tifFilePath).GetGeoTransform()

        if geo_transform:
            print("Origin = ({}, {})".format(geo_transform[0], geo_transform[3]))
            print("Pixel Size = ({}, {})".format(geo_transform[1], geo_transform[5]))

        projection = gdal.Open(tifFilePath).GetProjection()
        
        save_name = os.path.join(shpFilePath, 'result.TIF')

        write_geo_tiff(save_name, img, geo_transform, projection, bcnt = 1)


def get_cropped_images(shpFile, Part_List, tifFilePath):

    # make save directory
    print("Reading tif file...")
    # get width, height of original tif 
    tiffXInfo, tiffYInfo, band,_,_, orig_img= get_tif_info(tifFilePath)

    print("Reading tif file complete.")

    # get all shape file field names
    res_dict = {}

    print("Processing shape file : ",shpFilePath)
    
    mask = draw_mask_from_shpfile(shpFilePath, tiffXInfo, tiffYInfo, bands = 1)

    for _class in Part_List:
        temp = np.where(mask == _class, 1, 0)

        sumx = np.sum(temp, axis = 0)
        sumy = np.sum(temp, axis = 1)

        xindexes = [i for i,x in enumerate(sumx) if x != 0]
        yindexes = [i for i,x in enumerate(sumy) if x != 0]

        xmin, xmax = np.min(xindexes), np.max(xindexes)
        ymin, ymax = np.min(yindexes), np.max(yindexes)

        img_masked = orig_img[ymin:ymax,xmin:xmax]*temp[ymin:ymax,xmin:xmax]

        res_dict[_class] = img_masked


        print(f"Part {_class} process complete...")

    print("Done processing images form original image and shape file(s)")
    return res_dict

def get_cropped_roi_image(shpFilePath, roi, tifFilePath):

    # make save directory
    print("Reading tif file...")
    # get width, height of original tif 
    tiffXInfo, tiffYInfo, band,_,_, orig_img= get_tif_info(tifFilePath)

    print("Reading tif file complete.")

    # get all shape file field names
    res_dict = {}

    print("Processing shape file : ",shpFilePath)
    mask = draw_mask_from_shpfile(shpFilePath, tiffXInfo, tiffYInfo, bands = 1)

    _class = roi
    temp = np.where(mask == _class, 1, 0)

    sumx = np.sum(temp, axis = 0)
    sumy = np.sum(temp, axis = 1)

    xindexes = [i for i,x in enumerate(sumx) if x != 0]
    yindexes = [i for i,x in enumerate(sumy) if x != 0]

    xmin, xmax = np.min(xindexes), np.max(xindexes)
    ymin, ymax = np.min(yindexes), np.max(yindexes)

    img_masked = orig_img[ymin:ymax,xmin:xmax]*temp[ymin:ymax,xmin:xmax]


    print(f"Part {_class} process complete...")

    print("Done processing images form original image and shape file(s)")
    return img_masked


def get_idx(shpFilePath):
    fieldNames = ['id']
    class_idx = []
    dataSource = ogr.Open(shpFilePath, update=1)
    daLayer = dataSource.GetLayerByIndex(0)

    featureCount = daLayer.GetFeatureCount()

     # ID
    
    for i in range(featureCount):
        feature = daLayer.GetFeature(i)
        for idx, _ in enumerate(fieldNames):
                    class_idx.append(feature.GetField(idx))
    return class_idx
    



def get_green_image_from_scene(shpFilepath, tifFilePath, p_var=None, pb=None):
 
    # make save directory
    print("Reading tif file...")
    # get width, height of original tif 
    tiffXInfo, tiffYInfo, band, geoTransformInfo, geoProjectionInfo, orig_img= get_tif_info(tifFilePath)
    geoinfo = [tiffXInfo, tiffYInfo, geoTransformInfo, geoProjectionInfo]

    if p_var is not None:
        progress = 20
        p_var.set(progress)
        pb.update() 
    print("Reading tif file complete.")

    green_id_list = [1,11,2,22,3,41,42,43,44,45,46]

    res_dict = {}
    count = 0
    
    print("Processing shape file : ",shpFilepath)
    pixelPolygonList, class_idx, pixelPolygonHoleList = get_multipolygon(shpFilepath, tiffXInfo, tiffYInfo)

    if p_var is not None:
        progress = 40
        p_var.set(progress)
        pb.update() 

    mask = draw_mask(class_idx, tiffXInfo, tiffYInfo, pixelPolygonList, pixelPolygonHoleList, bands = 1).astype(np.uint8)
    res_mask = np.zeros_like(mask)

    if p_var is not None:
        progress = 60
        p_var.set(progress)
        pb.update() 

    for id in green_id_list:
        temp = np.where(mask == id, 1, 0).astype(np.uint8)
        res_mask += temp

    if p_var is not None:
        progress = 80
        p_var.set(progress)
        pb.update() 

    image_filtered = orig_img*res_mask

    if p_var is not None:
        progress = 100
        p_var.set(progress)
        pb.update() 
            
    print("Done processing images form original image and shape file")

    return image_filtered, geoinfo

def save_georeferenced_image(img, save_path, RasterXSize, RasterYSize, GeoTransformInfo, GetProjectionInfo):

    driver = gdal.GetDriverByName('GTiff')
    out_ds = driver.Create(save_path, RasterXSize, RasterYSize, 1, gdal.GDT_Byte)
    out_ds.SetGeoTransform(GeoTransformInfo) 
    out_ds.SetProjection(GetProjectionInfo)


    if len(img.shape) == 3: 
        for n in range(img.shape[-1]):
            out_ds.GetRasterBand(n+1).WriteArray(img[..., n])
    elif len(img.shape) == 2: 
        out_ds.GetRasterBand(1).WriteArray(img)

def save_cropped_georeferenced_image(img, save_path, RasterXSize, RasterYSize, GeoTransformInfo, GetProjectionInfo):

    driver = gdal.GetDriverByName('GTiff')
    out_ds = driver.Create(save_path, RasterXSize, RasterYSize, 1, gdal.GDT_Byte)
    out_ds.SetGeoTransform(GeoTransformInfo) 
    out_ds.SetProjection(GetProjectionInfo)


    if len(img.shape) == 3: 
        for n in range(img.shape[-1]):
            out_ds.GetRasterBand(n+1).WriteArray(img[..., n])
    elif len(img.shape) == 2: 
        out_ds.GetRasterBand(1).WriteArray(img)

if __name__ == '__main__': 
    # shpFilePath = 'D:/UFO/code/dataset/asiana/asi-1.shp'
    # tifFilePath = 'D:/UFO/code/dataset/asiana/0902_west_dsm_100_ortho_merge.tif'
    # save_path = 'D:/UFO/code/dataset/asiana'

    
    # shp2tif(shpFilePath, tifFilePath, save_path)

    tifFilePath = r'D:\Project\UFO\green_eye\dataset\asiana\8241ASIANA@A-0913\8241ASIANA@A.tif'
    shpFilePath = r'D:\Project\UFO\green_eye\dataset\asiana\8241ASIANA@A-0913\8241ASIANA@A#01.shp'
    tiffXInfo, tiffYInfo, bands, GeoTransform, Projection, img = get_tif_info(tifFilePath)
    ymin = 4000
    ymax = 5000
    xmin = 4000
    xmax = 5000

    crop = img[ymin:ymax, xmin:xmax]
    
    save_georeferenced_image(crop, r'D:\Project\UFO\green_eye\dataset\asiana\8241ASIANA@A-0913\test.tif', 2000, 2000, GeoTransform, Projection)
    

    # Raster2pix_coord(pt_pairs, xMax=tiffXInfo[3], xMin=tiffXInfo[2], yMax=tiffYInfo[3], yMin=tiffYInfo[2], convertXMax=tiffXInfo[0], convertYMax=tiffYInfo[0], yFlag=True)
    
    

    
    # shpFilePath = 'D:/UFO/code/dataset/asiana/asi-1.shp'
    # tifFilePath = r'D:\Project\UFO\green_eye\dataset\asiana\8241ASIANA@A-0913\8241ASIANA@A.tif'
    # Part_List = [1,2,3,4,5]

    # res_dict = get_cropped_images(shpFilePath, Part_List, tifFilePath)

    # for i in range(len(res_dict)):
    #     img = res_dict[i+1].astype(np.uint8)
    #     plt.imsave(f'{i+1}.jpg', img)
        # plt.imshow(res_list[i]["image"])
        # plt.show()





    # parser = argparse.ArgumentParser()

    # parser.add_argument("--img_dir", help="Set in-image_path")
    # parser.add_argument("--save_dir", help="Save img dir after processing")

    # parser_args = parser.parse_args()
    # tif_path = parser_args.img_dir
    # shp_path = parser_args.img_dir


    # shps = [f for f in os.listdir(shp_path) if f.endswith('.shp')]
    # print(f'num of shps: {len(shps)} ')

    # save_path = parser_args.save_dir
    # if not os.path.exists(save_path) :
    #     os.mkdir(save_path)

    # for shp in shps: 
    #     shpFilePath = os.path.join(shp_path, shp)
    #     tifFilePath = os.path.join(tif_path, shp[:-4] + '.TIF')
    #     print(tifFilePath)

    #     # make save directory
    #     make_directory(save_path)

    #     # get width, height of original tif 


    #     tiffXInfo, tiffYInfo, band,_,_= get_tif_info(tifFilePath)
    #     # get all shape file field names
        
    #     # fieldNames = get_field_names(shpFilePath)
    #     # print('__name__ ', fieldNames)
    #     # get all multipolygons, holes, and classes
    #     pixelPolygonList, class_idx, pixelPolygonHoleList = get_multipolygon(shpFilePath, tiffXInfo, tiffYInfo)
    #     print(tiffXInfo[0])
    #     print(tiffYInfo[0])

    #     # save un-cropped raster tif
    #     img = draw_mask(class_idx, save_path, tiffXInfo, tiffYInfo,shp[:-4 ], pixelPolygonList, pixelPolygonHoleList, bands = 1) 
    #     print(img.shape)
    #     geo_transform = gdal.Open(tifFilePath).GetGeoTransform()
    #     if geo_transform:
    #         print("Origin = ({}, {})".format(geo_transform[0], geo_transform[3]))
    #         print("Pixel Size = ({}, {})".format(geo_transform[1], geo_transform[5]))

    #     projection = gdal.Open(tifFilePath).GetProjection()
        
    #     save_name = os.path.join(save_path, shp[:-4] + '.TIF')

    #     write_geo_tiff(save_name, img, geo_transform, projection, bcnt = 1)
    #     # save cropped raster tif
    #     # save_patch(img, save_path, shp, tifDataset, gridWidth = 512, gridHeight = 512, stride = 64, bands = 1)