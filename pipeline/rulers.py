import os
import numpy as np
import json
import cv2
import imageio
import traceback
import random
import utils
import operator
from multiprocessing import Pool
from functools import partial
from tqdm import tqdm

def align(points, d):
    n = len(points)
    for i in range(n):
        for j in range(n):
            if abs(points[i][0] - points[j][0]) < d:
                mean = (points[i][0] + points[j][0]) / 2
                points[i] = (int(mean), points[i][1])
                points[j] = (int(mean), points[j][1])
            if abs(points[i][1] - points[j][1]) < d:
                mean = (points[i][1] + points[j][1]) / 2
                points[i] = (points[i][0], int(mean))
                points[j] = (points[j][0], int(mean))
    return points

def dist2(p1, p2):
    return (p1[0]-p2[0])**2 + (p1[1]-p2[1])**2

def fuse(points, d):
    ret = []
    d2 = d * d
    n = len(points)
    taken = [False] * n
    for i in range(n):
        if not taken[i]:
            count = 1
            point = [points[i][0], points[i][1]]
            taken[i] = True
            for j in range(i+1, n):
                if dist2(points[i], points[j]) < d2:
                    point[0] += points[j][0]
                    point[1] += points[j][1]
                    count+=1
                    taken[j] = True
            point[0] /= count
            point[1] /= count
            ret.append((int(point[0]), int(point[1])))
    return ret

def unique_intersections(intersections):
    return list(set(intersections))

def get_lines_img(img):
    red = np.array([0,0,255])
    mask = cv2.inRange(img, red, red)
    output_img = img.copy()
    output_img[np.where(mask==0)] = 0
    return output_img

def get_hough_lines(img):
    lines = cv2.HoughLinesP(image=img,rho=1,theta=np.pi/180, threshold=4, minLineLength=1, maxLineGap=75)
    lines = list(map(lambda x: [(x[0][0], x[0][1]), (x[0][2], x[0][3])], lines))
    return lines

def filter_lines(lines):
    th_self = 5
    th_other = 5
    # if x and/or y coordinates differ very little, make them equal
    for idx, i in enumerate(lines):
        if abs(i[0][0] - i[1][0]) < th_self:
            i[1] = (i[0][0], i[1][1])
        if abs(i[0][1] - i[1][1]) < th_self:
            i[1] = (i[1][0], i[0][1])

        for j in lines[idx+1:]:
            if abs(i[0][0] - j[0][0]) < th_other and abs(i[1][0] - j[1][0]) < th_other:
                j[0] = (i[0][0], j[0][1])
                j[1] = (i[1][0], j[1][1])
            if abs(i[0][1] - j[0][1]) < th_other and abs(i[1][1] - j[1][1]) < th_other:
                j[0] = (j[0][0], i[0][1])
                j[1] = (j[1][0], i[1][1])
    return lines

def line_intersection(line1, line2, regionBoundary, val=False):
    s = np.vstack([line1[0], line1[1], line2[0], line2[1]])        # s for stacked
    h = np.hstack((s, np.ones((4, 1)))) # h for homogeneous
    l1 = np.cross(h[0], h[1])           # get first line
    l2 = np.cross(h[2], h[3])           # get second line
    x, y, z = np.cross(l1, l2)          # point of intersection
    if z == 0 or (z > -25 and z < 25):   # lines are parallel
        return False

    th = 10


    min1x = min(line1[0][0], line1[1][0]) - th
    min1y = min(line1[0][1], line1[1][1]) - th
    min2x = min(line2[0][0], line2[1][0]) - th
    min2y = min(line2[0][1], line2[1][1]) - th

    max1x = max(line1[0][0], line1[1][0]) + th
    max1y = max(line1[0][1], line1[1][1]) + th
    max2x = max(line2[0][0], line2[1][0]) + th
    max2y = max(line2[0][1], line2[1][1]) + th

    dx1 = max1x-min1x
    dy1 = max1y-min1y
    dx2 = max2x-min2x
    dy2 = max2y-min2y

    cosAngle = abs((dx1 * dx2 + dy1 * dy2) / np.sqrt((dx1 * dx1 + dy1 * dy1) * (dx2 * dx2 + dy2 * dy2)))

    x = x/z
    y = y/z

    if not val:
        max_x = (regionBoundary["x2"] - regionBoundary["x1"])/72*150 + 20
        max_y = (regionBoundary["y2"] - regionBoundary["y1"])/72*150 + 20
    else:
        max_x = (regionBoundary["x2"] - regionBoundary["x1"])/72*150 + 20
        max_y = (regionBoundary["y2"] - regionBoundary["y1"])/72*150 + 20

    # Check if intersection is within regionBoundary
    if(x < -20 or x > max_x or y < -20 or y > max_y) or \
        x < min1x or x > max1x or y < min1y or y > max1y or \
        x < min2x or x > max2x or y < min2y or y > max2y:
        return False

    if(cosAngle > 0.7):
        # print(cosAngle)
        return False
    # print(line1, line2, x, y, z)
    return int(x), int(y)

def find_cell(intersection, intersections):
    for i in intersections:
        if intersection[0] < i[0] and intersection[1] < i[1]:
            width = i[0] - intersection[0]
            height = i[1] - intersection[1]
            if width < 20 or height < 10:
                return None
            else:
                return (intersection, i)
    return None

def preprocess_image(img):
    img = cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)
    img = cv2.copyMakeBorder(img,10,10,10,10,cv2.BORDER_CONSTANT,value=(255,255,255))
    low_threshold = 50
    high_threshold = 150
    img = cv2.Canny(img, low_threshold, high_threshold)
    cv2.imwrite("data/" + "_canny.png", img)
    kernel = np.ones((3,3),np.uint8)
    img = cv2.dilate(img, kernel, iterations = 1)
    cv2.imwrite("data/" + "_dilate.png", img)
    kernel = np.ones((5,5),np.uint8)
    img = cv2.erode(img,kernel, iterations = 1, borderType=cv2.BORDER_CONSTANT)
    img = img[10:len(img[0])-10, 10:len(img[1])-10]
    img = cv2.line(img, (0,0), (1024,0), (255,255,255))
    img = cv2.line(img, (0,0), (0, 1024), (255,255,255))
    cv2.imwrite("data/" + "_erode.png", img)
    return img

def get_intersections(lines, regionBoundary, val=False):
    intersection_points = []
    for idx, i in enumerate(lines):
        for j in lines[idx+1:]:
            intersection = line_intersection(i, j, regionBoundary, val)
            if not intersection:
                continue
            intersection_points.append(intersection)
    return intersection_points

def grid_intersections(name, intersection_points, lines):
    th_x = 5
    th_y = 7
    intersections = []
    x_points = list(map(lambda item: item[0], intersection_points))
    y_points = list(map(lambda item: item[1], intersection_points))
    # x_points = list(set(sorted(filter(lambda x: x_points.count(x) > 3, x_points))))
    # y_points = list(set(sorted(filter(lambda y: y_points.count(y) > 3, y_points))))
    x_points = sorted(list(set(x_points)))
    y_points = sorted(list(set(y_points)))
    #print(name, "points", x_points, y_points)

    for k, x in enumerate(x_points):
        br = False
        # Find intersection with similar x cooird
        for p in intersections:
            if p[0] != x and abs(p[0] - x) <= th_x:
                # Which x coord exists more often
                pref1 = sum(map(lambda i: i[0] == p[0], intersection_points))
                pref2 = sum(map(lambda i: i[0] == x, intersection_points))
                # If the other x coord exists more often, ignore this one
                if pref1 >= pref2:
                    br = True
                    break
                for i in intersections:
                    if i[0] == p[0]:
                        # print('remove ', i)
                        #print(name, "x remove", i, x)
                        intersections.remove(i)
                        if i[0] in x_points: x_points.remove(i[0])
        if br:
            continue

                    # Also do Y
        for j, y in enumerate(y_points):
            br = False
            for p in intersections:
                if p[1] != y and abs(p[1] - y) <= th_y:
                    # print('Found similar intersection Y:', p[1], y)
                    pref1 = sum(map(lambda i: i[1] == p[1], intersection_points))
                    pref2 = sum(map(lambda i: i[1] == y, intersection_points))
                    if pref1 >= pref2:
                        br = True
                        break
                    for i in intersections:
                        if i[1] == p[1]:
                            #print(name, "y remove", i, y)
                            # print('remove ', i)
                            intersections.remove(i)
                            if i[1] in y_points: y_points.remove(i[1])
            if br:
                continue
            #print(name, "add intersection", x,y)
            intersections.append((x,y))
    return intersections

def line_between_points(point1, point2, lines, horizontal):
    #print("Points: %s and %s" % (point1, point2))
    th_line_var_x = 5 # Allowed line cooird variation as lines may not be straight
    th_line_var_y = 7 # Allowed line cooird variation as lines may not be straight
    th = 5 # If line between two points but near misses the intersection

    # FINE TUNING THIS VALUE, DECIDE HOW MUCH OF A LINE IS CONSIDERED TO BE A SEPARATOR
    min_line = 0.5
    llen = 0
    for l in lines:

        if horizontal:
            start = min(l)
            end = max(l)
            # Check if start y coord matches end y coord and if it matches the point y coord
            if abs(start[1]-end[1]) <= th_line_var_y and abs(start[1]-point1[1]) <= th_line_var_y:

                # Check if line between two points
                if start[0] <= point1[0]+th and end[0] >= point2[0]-th:
                    #print("line accept")
                    return True
                else:
                    # Check for parts of line between points
                    if start[0] >= point1[0] and end[0] <= point2[0]:
                        llen += end[0] - start[0]
                        #print("Added len, total: ", llen)
                    elif start[0] <= point1[0] and end[0] >= point1[0] and end[0] <= point2[0]:
                        llen += end[0] - point1[0]
                        #print("Added len, total: ", llen)
                    elif start[0] >= point1[0] and start[0] <= point2[0] and end[0] >= point2[0]:
                        llen += point2[0] - start[0]
                        #print("Added len, total: ", llen)
                    if float(llen) / (point2[0] - point1[0]) >= min_line:
                        return True
        else:
            start = min(l, key=operator.itemgetter(1,0))
            end = max(l, key=operator.itemgetter(1,0))

            # Check if start x coord matches end x coord and if it matches the point x coord
            if abs(start[0]-end[0]) <= th_line_var_x and abs(start[0]-point1[0]) <= th_line_var_x:

                # Check if line between two points
                if start[1] <= point1[1]+th and end[1] >= point2[1]-th:
                    #print("line accept")
                    return True
                else:
                    # Check for parts of line between points
                    if start[1] >= point1[1] and end[1] <= point2[1]:
                        llen += end[1] - start[1]
                        #print("Added len, total: ", llen)
                    elif start[1] <= point1[1] and end[1] >= point1[1] and end[1] <= point2[1]:
                        llen += end[1] - point1[1]
                        #print("Added len, total: ", llen)
                    elif start[1] >= point1[1] and start[1] <= point2[1] and end[1] >= point2[1]:
                        llen += point2[1] - start[1]
                        #print("Added len, total: ", llen)
                    if float(llen) / (point2[1] - point1[1]) > min_line:
                        #print("Found line with len: ", llen)
                        return True
    return False

def get_cell_right(cell, cells):
    for cell_right in cells:
        if cell[1][0] == cell_right[0][0] and cell[0][1] == cell_right[0][1] and cell[1][1] == cell_right[1][1]: # RIGHT=LEFT, and TOP BOTTOM equal
            return cell_right
    return None

def get_cell_bottom(cell, cells):
    for cell_bot in cells:
        if cell[1][1] == cell_bot[0][1] and cell[0][0] == cell_bot[0][0] and cell[1][0] == cell_bot[1][0]: # BOTTOM=TOP, and LEFT RIGHT equal
            return cell_bot
    return None

def get_cell(cell, idx, cells, lines):

    right = cell
    bright = None
    while not line_between_points((right[1][0], right[0][1]), right[1], lines, False): # Top right, bottom right
        tmp = get_cell_right(right, cells)
        if tmp == None: break
        right = tmp
        cells.remove(right)
        # cell = [cell[0], cell[1], right[2], cell[3]]

        bleft = cell
        bright = right
        while not line_between_points((bleft[0][0], bleft[1][1]), bleft[1], lines, True) \
                and not line_between_points((bright[0][0], bright[1][1]), bright[1], lines, True):
            bottom_l = get_cell_bottom(bleft, cells)
            bottom_r = get_cell_bottom(bright, cells)
            if bottom_l == None or bottom_r == None: break
            if line_between_points((bleft[1][0], bleft[0][1]), bleft[1], lines, False): break
            bleft = bottom_l
            bright = bottom_r
            cells.remove(bleft)
            cells.remove(bright)
    if right != None and right != cell:
        if bright != None:
            return cells, (cell[0], bright[1])
        return cells, (cell[0], right[1])

    bottom = cell
    while not line_between_points((bottom[0][0], bottom[1][1]), bottom[1], lines, True):
        tmp = get_cell_bottom(bottom, cells)
        if tmp == None: break
        bottom = tmp
        cells.remove(bottom)

    if bottom != None and bottom != cell:
        return cells, (cell[0], bottom[1])

    return cells, cell


    # cell_trs = [i for i in points if i[1] == cell_tl[1] and i[0] > cell_tl[0]]
    # for cell_tr in cell_trs:
    #     if line_between_points(cell_tl, cell_tr, lines, True):
    #         #print("yes top line")
    #         cell_brs = [i for i in points if i[0] == cell_tr[0] and i[1] > cell_tr[1]]
    #         for cell_br in cell_brs:
    #             #print("look for right")
    #             if line_between_points(cell_tr, cell_br, lines, False):
    #                 #print("yes right line")
    #                 cell_bls = [i for i in points if i[1] == cell_br[1] and i[0] < cell_br[0]]
    #                 # or x equals top left x?
    #                 for cell_bl in cell_bls:
    #                     if line_between_points(cell_bl, cell_br, lines, True):
    #                         #print("yes bottom line")
    #                         if line_between_points(cell_tl, cell_bl, lines, False):
    #                             #print("yes left line")
    #                             return [cell_tl, cell_tr, cell_bl, cell_br]
    return None


def get_cells(cells, lines):
    done = []
    idx = 0
    while idx < len(cells):
        cell = cells[idx]
        if cell in done: continue
        cells, cell = get_cell(cell, idx, cells, lines)
        cells[idx] = cell
        done.append(cell)
        idx += 1

    return cells

def grid_cells(intersection_points):
    cells = []
    x_points = list(map(lambda item: item[0], intersection_points))
    y_points = list(map(lambda item: item[1], intersection_points))
    # x_points = list(set(sorted(filter(lambda x: x_points.count(x) > 3, x_points))))
    # y_points = list(set(sorted(filter(lambda y: y_points.count(y) > 3, y_points))))
    x_points = sorted(list(set(x_points)))
    y_points = sorted(list(set(y_points)))

    for idx_y, y in enumerate(y_points[:-1]):
        for idx_x, x in enumerate(x_points[:-1]):
            cells.append([(x,y), (x_points[idx_x+1],y_points[idx_y+1])])
    return cells

def rule_json_file(json_file, json_folder, opt, val=False):
    json_file_location = os.path.join(json_folder, json_file)
    with open(json_file_location, 'r+', encoding=utils.get_encoding_type(json_file_location), errors='ignore') as jfile:
        result = [] # eventually new json file
        tables = json.load(jfile) # current json file
        for table in tables:
            try:
                img_src = os.path.join(json_folder.replace("json", "png"), os.path.basename(table["renderURL"])[:-4] + ".png")
                if not os.path.exists(img_src): continue
                img_outlines = os.path.join(json_folder.replace("json", "outlines_"+opt.model), os.path.basename(table["renderURL"])[:-4] + ".png")
                img = cv2.imread(img_outlines)
                # print(table["renderURL"])
                table["renderURL"] = img_src
                #img = cv2.imread(os.path.splitext(table["renderURL"])[0].replace("png", "outlines_"+opt.model)+".png")
                img = preprocess_image(img)

                # cv2.imwrite(json_folder + table["name"] + "_test.png", img)

                # img2 = np.zeros((1024, 1024, 3), np.uint8)

                lines = get_hough_lines(img)

                # for line in lines:
                #     cv2.line(img2, line[0], line[1], (0, 0, 255), 1)

                lines = filter_lines(lines)
                # for line in lines:
                #     cv2.line(img2, line[0], line[1], (0, 255, 0), 1)
                #cv2.imwrite(json_folder + table["name"] + "_test2.png", img2)

                intersection_points = get_intersections(lines, table["regionBoundary"], val=True)
                #print("intersections 1", table["name"], intersection_points)
                intersection_points = sorted(unique_intersections(intersection_points))
                #print("intersections 2", table["name"], intersection_points)
                intersection_points = grid_intersections(table["name"], intersection_points, lines)

                #print("intersections 3", table["name"], intersection_points)

                # for point in intersection_points:
                #     cv2.circle(img2, point, 1, (255, 0, 0), -1)
                # cv2.imwrite(json_folder + table["name"] + "_test2.png", img2)

                cells = grid_cells(intersection_points)
                cells = get_cells(cells, lines)

                # img3 = np.zeros((1024, 1024, 3), np.uint8)
                # for cell in cells:
                #     #cv2.line(img3, cell[0], (cell[1][0], cell[0][1]), (0, 255, 0), 1)
                #     #cv2.line(img3, cell[0], (cell[0][0], cell[1][1]), (0, 255, 0), 1)
                #     cv2.line(img3, (cell[1][0], cell[0][1]), cell[1], (0, 255, 0), 1)
                #     cv2.line(img3, (cell[0][0], cell[1][1]), cell[1], (0, 255, 0), 1)
                # cv2.imwrite(json_folder + table["name"] + "_test3.png", img3)

                table["cells"] = cells
                table["name"] = os.path.basename(table["renderURL"])[:-4]
                result.append(table)
            except Exception as e:
                print("Error when ruling for %s | error: %s" % (json_file, e))
                continue

        jfile.seek(0)
        jfile.write(json.dumps(result))
        jfile.truncate()

def rule_pdffigures(json_folder, outlines_folder, opt):
    json_file_list = os.listdir(json_folder)

    pool = Pool(5)
    pool.map(partial(rule_json_file, json_folder=json_folder, opt=opt), json_file_list)
    pool.close()

def rule(json_folder, outlines_folder, opt):
    json_file_list = os.listdir(json_folder)

    pool = Pool(5)
    pool.map(partial(rule_json_file, json_folder=json_folder, opt=opt, val=True), json_file_list)
    pool.close()
