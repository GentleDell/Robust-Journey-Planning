#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jun 10 15:49:24 2019

@author: zhantao
"""    
import pickle
import numpy as np
import pandas as pd
import networkx as nx
from datetime import datetime, timedelta

from DFS_PathSearch import get_zurich_neighbor, create_graph, DFS_route_recommend
from path_planning import path_planning, _WALKING_VELOCITY, _FORMAT_TIME
from sampling import possibility_estimation, _TIME_OFF_BUS
from visualization_tools import *

_DEFAULT_YEAR_ = 2018
_MAX_STATIONS_ = 10
_MIN_PROB_THRES_ = 0.6
    
    
def load_data(date: datetime):
    
    weekday = date.weekday()
    
    if  weekday <= 4:   # weekday data
        path_schedual = './data/schedule_430.csv'        # the data are for weekday infact
        path_graph    = './data/graph_400_0430.gpickle'  
        path_lineID   = './data/lineid_trip180430.pickle'   
        path_stdtime  = './data/timetable180430.pickle'   
        
    elif weekday == 5:  # weekend data
        path_schedual = './data/schedule_428.csv'        
        path_graph    = './data/graph_200_0428.gpickle'
        path_lineID   = './data/lineid_trip180428.pickle'
        path_stdtime  = './data/timetable180428.pickle'
        
    else:               # public holiday data
        path_schedual = './data/schedule_429.csv'        
        path_graph    = './data/graph_200_0429.gpickle'    
        path_lineID   = './data/lineid_trip180429.pickle'       
        path_stdtime  = './data/timetable180429.pickle'    
        
    with open(path_lineID,'rb') as file:       # bus number -> tripID
        line_id = pickle.load(file)                             
    
    with open(path_stdtime,'rb') as file:      # tripID -> time
        tripID_2_time = pickle.load(file)
        
    time_table = pd.read_csv(path_schedual)                             # table to get the absolute time of a given (tripsId, station_name) pair
    graph = nx.read_gpickle(path_graph)                                 # graph
    dist_map = pd.read_csv('./data/distMap.csv')                        # distance map betew
    trip_table = pd.read_csv('./data/group_dense_time_table.csv')       # tripID -> all available time difference
    
    return time_table, graph, dist_map, trip_table, tripID_2_time, line_id, weekday


def format_trips(recommend_trips: list, departure_at: str, tripID_2_time: dict, time_table: pd.DataFrame, dist_map: pd.DataFrame):
    
    trip_list = []
    for trip_group in recommend_trips:
        
        for trip in trip_group:
            
            trip_dict = {}
            prob = np.prod(trip[2])
            if prob < _MIN_PROB_THRES_:
                continue
            else:
                data = get_schedual(trip[0], trip[1], trip[2], departure_at, tripID_2_time, time_table, dist_map)
    
                trip_dict['station']  = trip[0]
                trip_dict['data']     = data
            
            trip_list.append(trip_dict)
            
    return trip_list


def get_schedual(station: list, tripId: list, prob: list, departure_at: str, time: dict, service_data: pd.DataFrame, dist_map: pd.DataFrame):
    
    station_data = {}
    for stop in station:
        station_data[stop] = {}

    for cnt in range(len(tripId)):
        
        if 'Walk' not in tripId[cnt][0]:
            service = service_data[ (service_data.identifies_of_trip == tripId[cnt][0]) & (service_data.station_name == station[cnt]) ]        
            vehicle_type = service.product_id.values[0]
            if vehicle_type == 'Zug':
                product_id = service.train_number.values[0]
            else:
                product_id = service.service_type.values[0]
                
            dep_time = time[ tripId[cnt][0] ][ station[cnt] ][1]
            arr_time = time[ tripId[cnt][0] ][ station[cnt+1] ][0]
        else:
            vehicle_type = 'On foot'
            product_id   = None
            if cnt > 0:
                dep_datetime = datetime.strptime(station_data[station[cnt]]['arr_time'], _FORMAT_TIME) + timedelta(seconds = _TIME_OFF_BUS)
                dep_time = '{:02d}:{:02d}'.format(dep_datetime.hour, dep_datetime.minute)
                
                dist = dist_map[ (dist_map['placeA'] == station[cnt]) & (dist_map['placeB'] == station[cnt+1])].distance.values*1000
                arr_datetime = dep_datetime + timedelta(seconds = dist[0]/_WALKING_VELOCITY)
                arr_time = '{:02d}:{:02d}'.format(arr_datetime.hour, arr_datetime.minute)
            else:
                dist = dist_map[ (dist_map['placeA'] == station[cnt]) & (dist_map['placeB'] == station[cnt+1])].distance.values*1000
                dep_time = departure_at
                
                arr_datetime = datetime.strptime(dep_time, _FORMAT_TIME) + timedelta(seconds = dist[0]/_WALKING_VELOCITY)
                arr_time = '{:02d}:{:02d}'.format(arr_datetime.hour, arr_datetime.minute)
                
        station_data[station[cnt]]['tripID'] = tripId[cnt][0]
        station_data[station[cnt]]['method'] = vehicle_type
        station_data[station[cnt]]['No.']    = product_id
        station_data[station[cnt]]['prob']   = prob[cnt]
        station_data[station[cnt]]['dep_time'] = dep_time
        station_data[station[cnt+1]]['arr_time'] = arr_time
                
    station_data[station[cnt+1]]['prob'] = prob[-1]
    return station_data
    

def visualize_path(trips: list):
    
    sched = pd.read_csv('./data/schedule_0430.csv')
    geo = pd.read_csv('./data/geo.csv')
    
    plotplans = createPlotPlans(trips[0],geo)
    plotImage(plotplans,sched,geo)
    
    return plotplans


def path_and_probability(start: str, destination: str, max_transfer_stop: int, 
                         departure_at: str, arrive_at: str, date: datetime, use_fast_algo: bool = False):
    
    time_table, graph, dist_map, trip_table, tripID_2_time, line_id, weekday = load_data(date)
    
    if use_fast_algo:
        trips_candidates = path_planning(
                start_stations=[start],  end_stations =[destination],  start_time =departure_at,
                time_table=tripID_2_time,  bus_to_tripId = line_id  ,  dist_map = dist_map,
                graph = graph,  max_interchanges = max_transfer_stop,  max_stations = _MAX_STATIONS_)  
    else:
        
        GEO_DATA_PATH = './data/BFKOORD_GEO'
        GRAPH2_400_PATH = './data/graph2_400_0430.gpickle'
        
        # Compute distance map
        zurichNeighStation = get_zurich_neighbor(GEO_DATA_PATH)

        # Construct graph
        G_multidi_400 = create_graph(GRAPH2_400_PATH, zurichNeighStation, dist_map, True, 0.4)
        
        # Find path
        trips_candidates = DFS_route_recommend(G_multidi_400, dist_map, start, destination, departure_at, last_arr_time = arrive_at)

    trips_recommended = possibility_estimation(
            trip_table = trip_table, time_table = time_table,
            trips_list = trips_candidates, dist_map=dist_map,
            expect_arrtime = arrive_at )
    
    trips_to_interface = format_trips(trips_recommended, departure_at, tripID_2_time, time_table, dist_map)
    
    output = [trips_to_interface, weekday]
    
    plotplans = visualize_path( output )
    
    return plotplans

