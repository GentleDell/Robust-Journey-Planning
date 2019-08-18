#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Jun  6 14:38:10 2019

@author: zhantao
"""

import numpy as np
import pandas as pd
from datetime import datetime

from ast import literal_eval
from path_planning import _WALKING_VELOCITY, _WALKING_VARIANCE, _FORMAT_TIME

_TIME_OFF_BUS = 15          # 30s to get off bus
_DIST_INTERCHANGE = 300     # 5 minutes for interchange 
_NUM_SAMPLING_ = 800


def walking_model( distance: float, mean: float, std: float, num_sample: int):
    '''
        With the given distance and walking model (mean and std of velocity), it 
        generates num_sample samples from gaussian distribution[1].
    
        Reference:
            [1] @article{chandra2013speed,
                title={Speed distribution curves for pedestrians during walking and crossing},
                author={Chandra, Satish and Bharti, Anish Kumar},
                journal={Procedia-Social and Behavioral Sciences},
                volume={104},
                pages={660--667},
                year={2013},
                publisher={Elsevier}
                }
    '''
    walking_velocity = np.random.normal(loc = mean, scale = std, size = num_sample)
    walking_time_second = distance/walking_velocity
    
    return walking_time_second.tolist()


def read_col(trip_table:pd.DataFrame, trip_id: str, station: str, is_dep: bool):
    '''
        The function reads the time of the given trip_id arriving at and departure from the given station.
    '''
    target_col = trip_table[(trip_table.identifies_of_trip == trip_id) & (trip_table.station_name == station)]
    if is_dep:
        # load departure time 
        data = literal_eval(target_col.dep_delay.values[0])
    else:
        # load arrival time
        data = literal_eval(target_col.arr_delay.values[0])
    return np.array(data)


def Monte_Carlo_sampling(arr: list, dep: list, num_sample: int):
    '''
        Bootstrapping arrival and departure list
    '''
    arr_sample = np.random.choice(arr, num_sample, replace = True)
    dep_sample = np.random.choice(dep, num_sample, replace = True)
    
    succeed_p = sum(arr_sample - dep_sample < -10)/num_sample
    
    return succeed_p


def possibility_estimation(trip_table: pd.DataFrame, time_table: pd.DataFrame, 
                           trips_list: list, dist_map: pd.DataFrame, 
                           expect_arrtime: str, num_sampling: int = _NUM_SAMPLING_):
    '''
        It conducts monte carlo sampling on the given trip_table. 
        The target trip ids and satation names are given in the trips_list.
        
        trip_table: pd.DataFrame
            table to convert tripId & station_name to time_difference
            
        time_table: pd.DataFrame
            table to get the absolute time of a given (tripsId, station_name) pair
            
        trips_list: list of str
            list of identifies_of_trip
            
        dist_map: 
            distance map, containing the distance between any two stations 
            
        expect_arrtime:
            the expected arrival time
            
        num_sampling: int
            the number of sampling during monte carlo
    '''
    
    succeed_rate_allchoice = []
    
    # preprocessing
    for trip in trips_list:
        
        succeed_rate_onepath = []
        for stops, buses in trip:
            
            if buses is None:
                continue
            
            target_dep  = [0]
            target_arr  = [0]
            succeed_rate_onestop = []
            for ind in range(len(buses)):
                station = stops[ind]
                if ind < len(buses):
                    trip_id = buses[ind][0]
                
                time_offset_dep = time_table[(time_table.identifies_of_trip == trip_id) & (time_table.station_name==station)]
                time_offset_arr = time_table[(time_table.identifies_of_trip == trip_id) & (time_table.station_name==stops[ind+1])]
                if time_offset_dep.shape[0] == 0:
                    if 'Walk' not in trip_id:
                        # if the trip_id dose not exist in the time table
                        succeed_rate_onestop.append(0)
                        print("Schedule table does not contain trip: {:s}".format(trip_id))
                        continue
                    else:
                        # For walking, a _TIME_OFF_BUS delay is considered as a 
                        # delay for getting off bus. And the succeed_rate will be 
                        # set to 1.0, as walking should be successful a the time.
                        target_dep = np.array([ x + _TIME_OFF_BUS for x in target_arr ])
                        succeed_rate_onestop.append(1.0)
                        dist = dist_map[ (dist_map['placeA'] == station) & (dist_map['placeB'] == stops[ind+1])].distance.values*1000
                        
                        # the time of arrival (to the next transfer stop) is the
                        # time of departure plus the time for walking.  
                        target_arr = target_dep + walking_model(        
                                distance = dist[0], 
                                mean = _WALKING_VELOCITY, 
                                std  = _WALKING_VARIANCE,
                                num_sample = len(target_dep) )
                else:
                    target_dep = read_col(trip_table, trip_id, station, is_dep = True) \
                                 + time_offset_dep.depature_time.values
                    succeed_rate_onestop.append(Monte_Carlo_sampling(target_arr, target_dep, num_sampling))
                    
                    # the time of arrival (to the next transfer stop) is the
                    # time of arrival + time of delay plus the time for interchange.  
                    target_arr = read_col(trip_table, trip_id, stops[ind+1], is_dep = False) + time_offset_arr.arrival_time.values
                                    
                    target_arr = target_arr + walking_model(_DIST_INTERCHANGE,                              
                                                     mean = _WALKING_VELOCITY,      \
                                                     std  = _WALKING_VARIANCE,      \
                                                     num_sample = len(target_arr)) 
            
            # sampling the final arrival time
            expected_arr = np.array( [(datetime.strptime(expect_arrtime, _FORMAT_TIME) - datetime.strptime('00:00', _FORMAT_TIME)).total_seconds()] )
            succeed_rate_onestop.append(Monte_Carlo_sampling(target_arr, expected_arr, num_sampling))
            
            succeed_rate_onepath.append([stops, buses, succeed_rate_onestop])
        
        succeed_rate_allchoice.append(succeed_rate_onepath)
    return succeed_rate_allchoice
