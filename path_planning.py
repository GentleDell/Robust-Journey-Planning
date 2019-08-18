#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jun 10 15:53:26 2019

@author: zhantao
"""
import itertools
import pandas as pd
import networkx as nx
from datetime import datetime, timedelta

_FORMAT_TIME = '%H:%M'
_LARGEST_DELAY = 15 # in minutes, largest delay of vehicles considered at each station
_WALKING_VELOCITY = 1.0
_WALKING_VARIANCE = 0.2
_RELAXATION_FACTOR = -20


def find_path(G, start, destination, max_edges):
    '''
        It searches all possible paths on the given graph with the given starts,
        destinations and max_edges.
    '''
    trips = []
    for path in nx.all_simple_paths(G, source = start, target = destination, cutoff = max_edges):
        vehicles = []
        for i in range (len(path) - 1):
            stop_1 = path[i]
            stop_2 = path[i + 1]
            edge_dict = G.get_edge_data(stop_1, stop_2)
            vehicles.append(list(edge_dict['train_number']))
        trips.append([path, vehicles])
    return trips   
    

def aggregate_trips(trips_candidates: list, num_interchange: int = 10):
    '''
        It keeps all direct trips and trips having few interchanges.
    '''
    candidates_trips = []
    for trip in trips_candidates:
        # load bus and station 
        bus_list = trip[1]
        station_list = trip[0]
        
        # initialize set
        new_set = {}
        old_set = {}
        aggre_trip = []
        aggre_statation = [station_list[0]]
        
        cnt = 0
        while cnt <= len(bus_list):
            if len(new_set) == 0:
            # new_set being empty meanings this is the first set or this station 
            # is a transfer.
                if len(old_set) != 0:
                # old_set not empty means this is a transfer
                    cnt -= 1
                    aggre_trip.append(list(old_set))
                    aggre_statation.append(station_list[cnt])
                    
                    new_set = set(bus_list[cnt])
                    old_set = {}
                else:
                    new_set = set(bus_list[cnt])
            else:
                # sets intersection to find a path
                old_set = new_set
                if cnt < len(bus_list):
                    new_set = new_set.intersection(set(bus_list[cnt]))   
            cnt += 1
 
        # append possible trips (might be unresonable)
        aggre_trip.append(list(new_set))
        aggre_statation.append(station_list[-1])
        
        if len(aggre_trip) <= num_interchange:
        # throw trips with more than num_interchange transfer
            candidates_trips.append([aggre_statation, aggre_trip])
    
    return candidates_trips


def filter_trips(trips_list: list, bus_to_tripId: dict, time_table: dict, dist_map: pd.DataFrame, start_time: str):
    '''
        It filters out trips that are unresonable. There are two phases:
            1. roughly filtering: filter trips by group to reduce the number of combination
            2. second filtering : filter trips by path
    '''
    # First phase
    trips_list = time_filter(trips_list, bus_to_tripId, time_table, dist_map, start_time )
    
    # Second phase
    candidates_trips = []
    for trip in trips_list:
        new_paths = []
        buses = trip[1]
        stops = trip[0]
        # throw invalid trips
        if buses is None:
            continue
        
        trip_combination = [ i for i in itertools.product(*buses)]
        stops_list = [stops] * len(trip_combination)
        for ind in range(len(trip_combination)):
            new_paths.append( [ stops_list[ind], [ [bus] for bus in trip_combination[ind]] ])
       
        path_list = time_filter(new_paths, bus_to_tripId, time_table, dist_map, start_time, second_phase=True)
        candidates_trips.append(path_list)
        
    return candidates_trips


def time_filter(trips_list: list, bus_to_tripId: dict, time_table: dict, dist_map: pd.DataFrame, start_time: str, second_phase:bool=False):
    '''
        It uses time constraint to filter trips
    '''
    for ind_trips in range(len(trips_list)):
        
        stations, vehicle = trips_list[ind_trips][0], trips_list[ind_trips][1]
        
        old_trips = None
        walk_arr_early = None
        walk_arr_late  = None
        
        for ind in range(len(vehicle)):
        # for the ind-th stop    
            new_transfer = stations[ind]
            new_buses = vehicle[ind]
            
            if old_trips is None:
            # if this is the first stop then use the given start time 
                start_time_earliest = datetime.strptime(start_time, _FORMAT_TIME)
                start_time_latest = start_time_earliest
                
            else:    
            # else this is an intermediate stop then use the latest arrival time as the start time 
                bus_arr_time = [datetime.strptime(time_table[trip][new_transfer][0], _FORMAT_TIME) for trip in old_trips if 'Walk' not in trip]
                    
                if 'Walk' in old_trips:
                    bus_arr_time += [walk_arr_early, walk_arr_late]
                
                arr_time = sorted(bus_arr_time)
                start_time_earliest = arr_time[0]
                start_time_latest = arr_time[-1]
            
            next_transfer = stations[ind+1]
            if sum(['Walk' in choice for choice in new_buses]):
            # if new trips contain walk
                dist = dist_map[ (dist_map['placeA'] == new_transfer) & (dist_map['placeB'] == next_transfer)].distance.values*1000
                walk_arr_early= timedelta(seconds = dist[0]/_WALKING_VELOCITY) + start_time_earliest
                walk_arr_late = timedelta(seconds = dist[0]/_WALKING_VELOCITY) + start_time_latest
                
            filtered_tripId = time_constraint(new_transfer, new_buses, next_transfer, bus_to_tripId, time_table, 
                                              start_time_earliest, start_time_latest, enable_second_phase=second_phase)
            
            if len(filtered_tripId) == 0:
            # if one of the intermediate trips is invalid, throw all current trips
                trips_list[ind_trips][1] = None
                break 
            
            old_trips = filtered_tripId
            trips_list[ind_trips][1][ind] = filtered_tripId
            
    return trips_list


def time_constraint(new_transfer : str, new_buses: list, next_transfer: str, bus_to_tripId: dict, 
                    time_table: dict, start_time_early: str, start_time_late: str, enable_second_phase: bool):
    '''
        It uses two simple time constraints to filter unresonable trips:
            1. departure time must be later than arrival time.
            2. departure time must be earier than arrival time + _LARGEST_DELAY.
    '''
    candidates = []
    for bus in new_buses:
        
        if 'Walk' in bus:
            trip_list = ['Walk']
        elif enable_second_phase:
            trip_list = new_buses               # for second phase filtering
        else:
            trip_list = bus_to_tripId[bus]      # if is not walk, load tripId
             
        for trip in trip_list:            
            if trip == 'Walk':
                candidates.append(trip)
            else:
                try:
                    # if the trip does not stop at the station, we throw the trip.
                    # This is possible when some trains share the same train_number while 
                    # they have different trips and one the target_arr trip pass the station.
                    dep_time = datetime.strptime(time_table[trip][new_transfer][1], _FORMAT_TIME)
                    if time_table[trip][next_transfer][0] == 'nan:nan':
                        continue
                    elif datetime.strptime(time_table[trip][next_transfer][0], _FORMAT_TIME) < dep_time:
                        continue
                except:
                    continue
                    
                if dep_time is None:
                    # if the time is invalid (NaN), we throw this trip
                    continue
                else:
                    # compute time difference
                    time_diff_early = dep_time - start_time_early
                    time_diff_late  = dep_time - start_time_late
                    minutes_late = int(time_diff_late.total_seconds()/60)
                   
                    if minutes_late >= _LARGEST_DELAY or int(time_diff_early.total_seconds()) <= _RELAXATION_FACTOR:
                    # throw trips being later than _LARGEST_DELAY and earler than the earliest trip
                        continue
                    else:
                        candidates.append(trip)
            
    return candidates


def path_planning(start_stations: list, end_stations: list, start_time: str, graph: nx.digraph.DiGraph, 
                  time_table: dict, bus_to_tripId: dict, dist_map: pd.DataFrame, max_stations: int=10, max_interchanges: int=10):
    '''
        It finds all trips starting at stations in start_stations and ending at 
        corresponding stations in end_stations. The max length of the trip should
        be smaller than max_stations and the number of interchanges should be smaller
        than the max_interchanges. 
    '''
    # load Graph
    trip_list = []
    
    for source, target in zip(start_stations, end_stations):
        # searching for all possible trips
        trip = find_path(graph, start = source, destination = target, max_edges = max_stations)
        
        # aggregating trips
        aggregate_trip = aggregate_trips(trips_candidates=trip, num_interchange=max_interchanges)
        
        # roughly filtering trips
        filtered_trips = filter_trips(aggregate_trip, bus_to_tripId, time_table, dist_map, start_time)
        
        trip_list.append(filtered_trips)
        
    return trip_list[0]
        
        