import pandas as pd
import bokeh
import numpy as np
import matplotlib.pyplot as plt

from bokeh.tile_providers import CARTODBPOSITRON
from bokeh.io import push_notebook, show, output_notebook
from bokeh.plotting import figure,save
from bokeh.models import ColumnDataSource, Range1d,HoverTool
from bokeh.plotting import output_file, show 
from pyproj import Proj, transform
import itertools
from math import sin, cos, sqrt, atan2, radians,asin
from itertools import groupby

def plotImage(plotplans,sched,geo):
    """
    This function is used to visualize the found routes on map.
    
    Inputs:
        plotplans: List of lists. Each sublist is one possible plan. And the format inside each possible plan is: [[lontitude],[latitude],[transfer-station names],[methods from one station to next],[probability of catching up the bus/tram/train],[arrival time],[departure time],[minutes taken on the route],[trip id]]
        sched,geo: Pandas dataframe. Storing trip information and geometry information.
    Return:
        None.
    """
    color_bar = bokeh.palettes.brewer['Paired'][12]
    line_type = ['solid', 'dashed', 'dotted', 'dotdash', 'dashdot']
    line_color = {'Zug':0,
                  'Bus':0,
                  'Tram':0,
                  'On foot':2}
    output_notebook()
    
    x_min,x_max = min([min(x[0]) for x in plotplans]),max([max(x[0]) for x in plotplans])
    y_min,y_max = min([min(x[1]) for x in plotplans]),max([max(x[1]) for x in plotplans])

    output_file('./data/Sample_Application.html',mode='inline',root_dir=None) 
    p = figure(x_range=(x_min-1000,x_max+1000), y_range=(y_min-1000,y_max+1000), 
               x_axis_type="mercator", y_axis_type="mercator", 
               plot_width=640,plot_height=650)
    p.add_tile(CARTODBPOSITRON)

    
    for j in range(len(plotplans)): # plot each plan one by one
        xs,ys,names,methods,probs,arr_times,dep_times,last_times,ids = plotplans[j]
        for i in range(len(methods)): # plot each session in one plan one by one
            xs_,ys_,x_,y_,name_ = interpLine(xs[i:i+2],ys[i:i+2],ids[i],names[i:i+2],sched,geo)

            
            source1 = ColumnDataSource(data = dict(lat=ys_,lon=xs_,
                                                   method=[methods[i]]*len(ys_),
                                                   last_time = [last_times[i]]*len(ys_)))
            p1 = p.line(x='lon', y='lat', source = source1,
                   color = color_bar[j*2+1],
                   line_dash = line_type[line_color[methods[i].split(':')[0]]],
                   line_width = 2,line_cap='round',
                   legend='Plan%s'%str(j+1))

            p.add_tools(HoverTool(renderers=[p1],
                                  tooltips=[
                                            ('Methods', '@method'),
                                            ('Minutes','@last_time')]))
            
            source0 = ColumnDataSource(data = dict(lat=y_,lon=x_,
                                       name=name_))

            p0 = p.scatter(x='lon', y='lat',source = source0,legend='Plan%s'%str(j+1),color=color_bar[j*2+1])
            p.add_tools(HoverTool(renderers=[p0],
                                  tooltips=[('Station', '@name')]))

        source2 = ColumnDataSource(data = dict(lat=ys,lon=xs,
                                               name=names,
                                               prob=probs,
                                               arr=arr_times,dep=dep_times))

        p2 = p.scatter(x='lon', y='lat',source = source2,legend='Plan%s'%str(j+1),color=color_bar[j*2+1])
        p.add_tools(HoverTool(renderers=[p2],
                              tooltips=[('Station', '@name'),
                                        ('Probability','@prob'),
                                        ('Arrival Time', '@arr'),
                                        ('Departure Time','@dep')]))
        
    p.legend.location = "top_left"
    p.legend.click_policy="hide"
    save(p)
    # handle=show(p, notebook_handle=False)
    
def interpLine(x,y,id_,names_,sched,geo):
    """
    This function is used for linear interpolation between two station, and to find stations between two transfer stations.
    Input:
        x,y,names_: Float, float, string. Longitude and latitude and station name of two consecutive transfer stations.
        id_: String. Trip id.
        sched,geo: Pandas dataframe. Storing trip information and geometry information.
    Return:
        x_, y_: Float. Longitude and latitude of interpolated points.
        names: String. Station names in between two transfer stations.
    """
    x = x
    y = y
    x_ = []
    y_ = []
    names = []
    if id_ != 'Walk':
        sched_ = sched.loc[sched.identifies_of_trip==id_].fillna(0).sort_values(by='arrival_time')
        sched_.reset_index(drop=True,inplace=True)
        start_idx = min(sched_.loc[sched_.station_name==names_[0]].index[0],sched_.loc[sched_.station_name==names_[1]].index[0])
        end_idx = max(sched_.loc[sched_.station_name==names_[0]].index[0],sched_.loc[sched_.station_name==names_[1]].index[0])
        stations = sched_.station_name.get_values()[start_idx+1:end_idx]
        for station in stations:
            xy = transform(Proj(init='epsg:4326'), Proj(init='epsg:3857'), 
                           geo.set_index('station_name').loc[station].longtitude,
                           geo.set_index('station_name').loc[station].latitude)
            x.insert(-1,xy[0])
            y.insert(-1,xy[1])
        names = stations
    for i in range(len(x)-1):
        x_.extend(list(np.linspace(x[i],x[i+1],50)))
        y_.extend(list(np.linspace(y[i],y[i+1],50)))
        
    return x_, y_, x[1:-1],y[1:-1],names

def stationOnTrip(geo,plan):
    """
    This function is used to extract information from the plan dictionary.
    
    Input:
        geo: Pandas dataframe. Storing the geometric information of stations.
        plan: Dictionary. Storing the information of each transfer station.
    Return:
        xs,ys,names: Float, string. Longitude, latitude, station names of stations
        methods,probs,arr_times,dep_times,last_times: String. methods from one station to next,probability of catching up the bus/tram/train,arrival time,departure time,minutes taken on the route
        ids: String. trip ids.
    """
    names = []
    xs = []
    ys = []
    
    methods = []
    probs = []
    
    arr_times = []
    dep_times = []
    
    ids = []
    for x in plan:
        name = x
        xy = transform(Proj(init='epsg:4326'), Proj(init='epsg:3857'), 
                       geo.set_index('station_name').loc[x].longtitude,
                       geo.set_index('station_name').loc[x].latitude)
        names.append(name)
        xs.append(xy[0])
        ys.append(xy[1])
        method = plan[x]['method'] if 'method' in plan[x] else 'Null'
        if method != 'Null':
            method = method + ':' + plan[x]['No.'] if bool(plan[x]['No.']) else method
        arr = plan[x]['arr_time'] if 'arr_time' in plan[x] else plan[x]['dep_time']
        dep = plan[x]['dep_time'] if 'dep_time' in plan[x] else plan[x]['arr_time']
        
        methods.append(method)
        probs.append(plan[x]['prob'])
        
        arr_times.append(arr)
        dep_times.append(dep)
        
        id_ = plan[x]['tripID'] if 'tripID' in plan[x] else 'Null'
        ids.append(id_)
    last_times = calculateLastTime(arr_times,dep_times)
    return xs,ys,names,methods[:-1],probs,arr_times,dep_times,last_times,ids[:-1]

def calculateLastTime(arr_times,dep_times):
    """
    The function is used to calculate the minutes spent on trip.
    
    Inputs:
        arr_times, dep_times: List of String. Arrival time, depature time.
        
    Return:
        last_times: List of Float. Minute spent on trip.
    """
    last_times = []
    for i in range(len(dep_times)-1):
        arr = arr_times[i+1].split(':')
        dep = dep_times[i].split(':')
        
        last_time = (int(arr[0])-int(dep[0]))*60 + (int(arr[1])-int(dep[1]))
        
        last_times.append(last_time)
    return last_times

def compute_distance(point_1_lat, point_1_lon, point_2_lat, point_2_lon):
    """"
    The function is used to calculate the distance between two points on the earth.
    
    Inputs:
        point_1_lat, point_1_lon, point_2_lat, point_2_lon: Float. Latitude and longitude of two points.
    Return:
        Float, distance between two points (in km)
    """
    R = 6378.137 # earth radius

    lat1 = radians(float(point_1_lat))
    lon1 = radians(float(point_1_lon))
    lat2 = radians(float(point_2_lat))
    lon2 = radians(float(point_2_lon))

    dlon = lon2 - lon1
    dlat = lat2 - lat1

    a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
    c = 2 * asin(sqrt(a))

    distance = R * c
    return np.round(distance,3) # return distance in kilometres

def walkDistance(geo,plan):
    """
    This function is used to calculate the walking distance, transfer time and journey time.
    
    Inputs:
        geo: Pandas dataframe. Storing the geometric information of stations.
        plan: Dictionary. Storing the information of each transfer station.
    Return:
        Float. sum of total walking distance, transfer count, total journey time
    """
    xs = []
    ys = []
    methods = []
    distance = []
    
    arr_times = []
    dep_times = []
    for station in plan:
        xy = geo.set_index('station_name').loc[station].longtitude,geo.set_index('station_name').loc[station].latitude
        xs.append(xy[0])
        ys.append(xy[1])
        method = plan[station]['method'] if 'method' in plan[station] else 'Null'
        methods.append(method)
        
        
        arr = plan[station]['arr_time'] if 'arr_time' in plan[station] else plan[station]['dep_time']
        dep = plan[station]['dep_time'] if 'dep_time' in plan[station] else plan[station]['arr_time']
        arr_times.append(arr)
        dep_times.append(dep)

    arr = arr_times[-1].split(':')
    dep = dep_times[0].split(':')

    last_time = (int(arr[0])-int(dep[0]))*60 + (int(arr[1])-int(dep[1]))

    for i in range(len(methods)):
        if methods[i] == 'On foot':
            dis = compute_distance(ys[i], xs[i], ys[i+1], xs[i+1])
            distance.append(dis)
    transfer_cnt = [next(g) for _, g in groupby(methods[:-1], key=lambda x:x)] 
    return np.round(sum(distance),3),len(transfer_cnt),last_time

def createPlotPlans(plans,geo):
    """
    This function is used to rank and select three plans from multi plans for visualization.
    
    Inputs:
        geo: Pandas dataframe. Storing the geometric information of stations.
        plan: Dictionary. Storing the information of each transfer station.
    Return:
        plotplans: List of lists. Storing three plans for visualization.
    """
    walkDis = [walkDistance(geo,plan['data']) for plan in plans]
    # find the plan with shortest walking distance
    shortwalk = list(np.argsort([x[0] for x in walkDis]))
    # find the plan with least transfer counts
    leasttransfer = list(np.argsort([x[1] for x in walkDis]))
    # find the plan with shortest journey time
    shorttime = list(np.argsort([x[2] for x in walkDis]))
    
    plotplans = []
    
    if len(walkDis)>3:
        idx1 = shortwalk[0]
        shorttime.remove(idx1)
        idx2 = shorttime[0]
        leasttransfer.remove(idx1)
        leasttransfer.remove(idx2)
        idx3 = leasttransfer[0]
 
        plotplans = []
        
        idxs = [idx1,idx2,idx3]
        for idx in idxs:
            xs,ys,names,methods,probs,arr_times,dep_times,last_times,ids = stationOnTrip(geo,plans[idx]['data'])
    
            plotplans.append([xs,ys,names,methods,probs,arr_times,dep_times,last_times,ids])
    else:
        for i in range(len(walkDis)):
            xs,ys,names,methods,probs,arr_times,dep_times,last_times,ids = stationOnTrip(geo,plans[i]['data'])
            plotplans.append([xs,ys,names,methods,probs,arr_times,dep_times,last_times,ids])
    return plotplans