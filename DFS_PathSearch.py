# ---------------------- Import packages ---------------------- #
# Import basic packages
import pandas as pd
import numpy as np
# Net work packages
import networkx as nx
# Others packages
import os
import copy
import pickle
from itertools import combinations
from datetime import timedelta, datetime, date
from math import sin, cos, sqrt, atan2, radians, asin, ceil

# Path
DF_DAY_PATH= './data/grouped_201804.csv'

# ---------------------- Load data ---------------------- # 
df_18_04 = pd.read_csv(DF_DAY_PATH)
df_day = df_18_04[(df_18_04['date_of_trip'] == '30.04.2018')]
df_day = df_18_04[(df_18_04['date_of_trip'] == '30.04.2018')&(df_18_04['additional_trip'] == False)&\
                  (df_18_04['not_stop'] == False)]
df_day = df_day.reset_index(drop=True)
nan = np.nan
df_day['Timetable'] = df_day.Timetable.map(lambda x: eval(x))
df_day = df_day[['date_of_trip', 'identifies_of_trip', 'Timetable', 'train_number']]
all_station = []
for idx, row in df_day.iterrows():
    station = []
    for i in range(len(row['Timetable'])):
        station.append(row['Timetable'][i][0])
    all_station.append(station)
df_day['station_name'] = all_station

# ---------------------- Functions for building distance map ---------------------- #
def compute_distance(point_1_lat, point_1_lon, point_2_lat, point_2_lon):
    """
    Approximate radius of earth in km.

    Input:
        point_1_lat:           Latitude of point 1
        point_1_lon:           Longtitude of point 1
        point_2_lat:           Latitude of point 2
        point_2_lon:           Longtitude of point 2
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
    return np.round(distance, 3) # return distance in kilometres

def get_zurich_neighbor(GEO_DATA_PATH):
    """
    Get the DataFrame discribing the information of Zurich's neighbor stations.
    
    Input:
        GEO_DATA_PATH:          File path of the geo data.
    """
    # Load geo data
    geo = pd.read_csv(GEO_DATA_PATH, sep="%", header=None,error_bad_lines=False)
    geo.columns = ['data','name']
    geo.name = geo.name.apply(str.lstrip).apply(str.rstrip)
    geo[['station_number','longtitude','latitude','height']] = geo.data.str.split(expand=True)#.apply(float)
    geo.drop('data',axis=1,inplace=True)

    # Keep Zurich neighbourhood stations (<10km)
    zurich = geo[geo.station_number=="8503000"].reset_index(drop=True)
    distance = []
    for log,lat in zip(geo.longtitude,geo.latitude):
        distance.append(compute_distance(lat,log, zurich.latitude, zurich.longtitude))
    geo['distance'] = distance
    zurich_neigh_station = geo[geo.distance <= 10]
    
    return zurich_neigh_station

def load_dist_map(zurich_neigh_station, DIST_MAP_PATH):
    """
    Create distance map showing the distance of every two places. 
    """
    print('---------- {} ----------'.format('Load the Distance Map'))

    if os.path.exists(DIST_MAP_PATH):
        distMapNewDf = pd.read_csv(DIST_MAP_PATH, index_col=0) 
        print('=>Distance map has been loaded!')

    else:
        # Create distance map
        distMap       = []
        nodes_list    = list(zurich_neigh_station.name)
        combiList     = list(combinations(nodes_list, 2))
        count, length = 0, len(combiList)
        print('Start to create distance map...')
        for placeA, placeB in combiList:
            placeAdf = zurich_neigh_station[zurich_neigh_station['name']==placeA]
            placeBdf = zurich_neigh_station[zurich_neigh_station['name']==placeB]
            distance = compute_distance(placeAdf.latitude.values[0], 
                                        placeAdf.longtitude.values[0], 
                                        placeBdf.latitude.values[0], 
                                        placeBdf.longtitude.values[0])
            count += 1
            if count % np.ceil(length/100) == 0:
                print('=>Task has been done:{:.2f}% \t'.format(count / np.ceil(length/100)), end='\r')
            distMap.append([placeA, placeB, distance])
            distMap.append([placeB, placeA, distance])
        distMapNewDf = pd.DataFrame(distMap, columns=['placeA', 'placeB', 'distance'])
        distMapNewDf.to_csv(DIST_MAP_PATH)
        print('Done!')

    print('-----------{}-----------'.format(len('Load the Distance Map')*'-'))
    return distMapNewDf

def add_walk_edge(G, distMapNewDf, maxWalk=0.15): 
    """
    This function is used to add edges that signify "Walk" on graph.

    Input:
        G      :              The original 
        maxWalk:              The maximum walking distance.
    """
    distMap = distMapNewDf[distMapNewDf.distance < maxWalk]
    for idx, row in distMap.iterrows():
        G.add_edge(row['placeA'], 
                   row['placeB'], 
                   trip_id = 'Walk',
                   distance = row['distance'],
                   arrToNext   = None,
                   depFromLast = None)
    return G

# ---------------------- Functions for find the path ---------------------- #
def all_simple_paths_multigraph(last_arr_time, G, source, target, StartTime, interval, StopN, PathN, TripN):
    """
    Compute all paths of a multigraph from source to target using DFS.
    Visited: [A              , B              , C               ...]
    Stack  : [Next Layer of A, Next Layer of B, Next Layer of C ...]
    
    Input:
        last_arr_time: Set the lastest arrival time of the journey
        G:               Graph
        source:          Source vertex
        target:          Target Vertex
        StartTime:       Start time, should be in format (%H:%M)
        interval:        Longest time the user can wait
        StopN:           Largest number of vertex in path (at least 2, at most len(G))
        TripN:           The maximum number of trip ids in a journey
        PathN:           Top N fastest path will be returned
        maxWalk:         Max length (/km) limit of walk
    """ 
    def reset_walk_edge_attr(val):
        distance = val['distance']
        walkTime = timedelta(minutes=ceil(distance/walkSpeed*60))

        if type(lastchildAttr) == type(None):
            val['depFromLast'] = StartTime
            val['arrToNext']   = StartTime + walkTime

        else:
            val['depFromLast'] = lastchildAttr[2]['arrToNext']
            val['arrToNext']   = lastchildAttr[2]['arrToNext'] + walkTime
        return val
    
    def set_time_constrints(nodeAttr):
        # Reset the atttibutes of walk edge
        if nodeAttr[2]['trip_id'] == 'Walk':
            reset_walk_edge_attr(nodeAttr[2])
                
        # Last node is source       
        if type(lastchildAttr) == type(None):
            if nodeAttr[2]['depFromLast'] + timedelta(seconds=1) <= StartTime or nodeAttr[2]['depFromLast'] + timedelta(seconds=1) >= StartTime + interval:
                return False, nodeAttr
        else:
            # Drop edges with one side unknown
            if type(nodeAttr[2]['depFromLast']) == type(None) or lastchildAttr[2]['arrToNext'] == type(None):
                return False, nodeAttr
            # Drop edges with wrong order
            elif nodeAttr[2]['depFromLast'] + timedelta(seconds=1) <= lastchildAttr[2]['arrToNext'] or nodeAttr[2]['depFromLast'] + timedelta(seconds=1) >= lastchildAttr[2]['arrToNext'] + interval:
                return False, nodeAttr
        return True, nodeAttr
    
    def get_path_with_attribute(G, node):
        # Final next layer nodes
        pathWithAttr  = []
        G_dict        = G[node]
        # Add bus edges
        for vertex, attribute in G_dict.items():
            # Set non-loop constraint
            if vertex not in visited:
                for key, value in attribute.items():
                    
                    flag, nodeAttr = set_time_constrints((node, vertex, value))
                    if flag:
                        pathWithAttr.append(nodeAttr)
        return pathWithAttr
    
    def update_shortest_path(shortest_path_, last_arr_time_, childAttr):
        childAttrCopy = copy.deepcopy(childAttr)
        path    = (visitedWithAttr + [childAttrCopy])[1:]
        tripnum = len(list(set([i[2]['trip_id'] for i in path if i[2]['trip_id'] != 'Walk'])))
        walknum = np.sum([1 for i in path if i[2]['trip_id'] == 'Walk'])
        trip_id_list = [i[2]['trip_id'] for i in path]
        consecutive_walk = \
        any(trip_id_list[i] == trip_id_list[i+1] for i in range(len(trip_id_list)-1) if trip_id_list[i] == 'Walk')
        
        # Sort top N fastest paths, the number of walks is no more than 2 and one cannot walk consecutively
        if (tripnum <= TripN)&(walknum <=2)&(consecutive_walk == False):
            if len(shortest_path_) < PathN:
                shortest_path_.append(path)
                shortest_path_ = sorted(shortest_path_, key=lambda x: x[-1][2]['arrToNext'])
                last_arr_time_ = shortest_path_[0][-1][2]['arrToNext']
            else:
                if childAttr[2]['arrToNext'] < last_arr_time_:
                    shortest_path_.append(path)
                    shortest_path_ = sorted(shortest_path_, key=lambda x: x[-1][2]['arrToNext'])[:PathN]
                    last_arr_time_ = shortest_path_[0][-1][2]['arrToNext']
        return shortest_path_, last_arr_time_
    
    # ---------------------------------------- Start ---------------------------------------- #
    # Set the number of vertex in path (Depth of the path)
    if StopN is None:
        cutoff = len(G) - 1
    elif StopN < 2:
        return
    else:
        cutoff = StopN - 1
       
    # Set walk speed
    walkSpeed = 5
    
    # Maintain the list of first 'PathN' shortest path
    shortest_path = []
    
    # The vertices that have been visited
    visited, visitedWithAttr = [source], [None]
    lastchild, lastchildAttr = source,    None
    
    # Stack used to store the depth tree
    stack = [(path for path in get_path_with_attribute(G, source))]

    # Run until the tree is totally searched
    while stack:
        lastchild     = visited[-1]
        lastchildAttr = visitedWithAttr[-1]
        
        # Generator: Next layer of last vertex in visited list
        children  = stack[-1]
        # *It will apply to the same generator as used last time
        childAttr = next(children, None)
        child = childAttr[1] if type(childAttr)!=type(None) else None
        
        # All the child have been searched  
        if child is None:
            stack.pop()
            visited.pop()
            visitedWithAttr.pop()
            
        else:
            # If the child is not None, and visited nodes < cutoff
            if len(visited) < cutoff:
                # If the target is reached
                if child == target:
                    if childAttr[2]['arrToNext'] <= last_arr_time:
                        shortest_path, last_arr_time = update_shortest_path(shortest_path, last_arr_time, childAttr)
                    
                # Set constrints to depth
                elif child not in visited:
                    tripnum = len(list(set([i[2]['trip_id'] for i in visitedWithAttr[1:] if i[2]['trip_id'] != 'Walk'])))
                    # If the child 'arrToNext' larger than last_arr_time, its children will not be searched
                    if childAttr[2]['arrToNext'] >= last_arr_time or tripnum > TripN - 1:
                        pass
                    else:
                        visited.append(child)
                        visitedWithAttr.append(copy.deepcopy(childAttr))
                        lastchildAttr = visitedWithAttr[-1]
                        lastchild     = visited[-1]
                        stack.append((path for path in get_path_with_attribute(G, child)))
                        
            else: 
                targetDict = G.get_edge_data(lastchild, target)
                if type(targetDict)!=type(None):
                    for _, val in targetDict.items():
                        
                        if val['trip_id'] == 'Walk':
                            reset_walk_edge_attr(val)
                        if type(lastchildAttr) != type(None) \
                            and lastchildAttr[2]['arrToNext'] < val['depFromLast'] + timedelta(seconds=1) \
                            and lastchildAttr[2]['arrToNext'] + interval > val['depFromLast'] + timedelta(seconds=1):
                            shortest_path, last_arr_time = update_shortest_path(shortest_path, last_arr_time, (lastchild, target, val))
                           
                        # Only 2 stops in path
                        elif type(lastchildAttr) == type(None)\
                             and val['depFromLast'] <= val['arrToNext'] \
                             and val['depFromLast'] >= StartTime and val['depFromLast'] <= StartTime + interval:
                             shortest_path, last_arr_time = update_shortest_path(shortest_path, last_arr_time, (lastchild, target, val))
                stack.pop()
                visited.pop()
                visitedWithAttr.pop()
    return shortest_path

def create_graph(path, zurich_neigh_station, distMapNewDf, multi=True, maxWalk=0.15):
    """
    This function is used to create a multiedge graph.
    Nodes:                  Station names
    Edges:                  Draw an edge between node A and node B when they are linked by train/ bus/ tram
    Edge attributes:        Trip id, lines id, departure time from node A and arrival time at node B

    Input:
        path                :         Path to load or read graph
        zurich_neigh_station:         DataFrame describing neighbor station of Zurich station
        distMapNewDf        :         DataFrame of distMap
        multi               :         Whether to create a multi-edges direction graph
        maxWalk             :         The maximum walking distance (/km)
    """
    print('---------- {} ----------'.format('Create Graph'))
    if os.path.exists(path):
        if multi:
            print('=>MultiGraph has been loaded!')
        else:
            print('=>DiGraph has been loaded!')
        G = nx.read_gpickle(path)
    else:
        if multi:
            G = nx.MultiDiGraph()
        else:
            G = nx.DiGraph()
        # Add nodes to graph'
        print('=>Building graph...')
        nodes_list = list(set(zurich_neigh_station['name'].unique()))
        G.add_nodes_from(nodes_list)
        # Add directed edges
        for idx, row in df_day.iterrows():
            trip_id = row['identifies_of_trip']
            for j in range(len(row['Timetable'])-1):
                
                # Assume that nodes are ordered by default
                node1 = row['Timetable'][j][0]
                node2 = row['Timetable'][j+1][0]
                depFromLast = row['Timetable'][j][3]
                arrToNext   = row['Timetable'][j+1][1]
                
                # Only add the edges having the aimed time and not None
                if np.isnan(depFromLast) == False and np.isnan(arrToNext) == False and depFromLast <= arrToNext:
                    G.add_edge(node1, node2, 
                               trip_id =trip_id, trainId=row['train_number'], 
                               arrToNext  =datetime(2017,9,13,0,0) + timedelta(seconds=arrToNext), \
                               depFromLast=datetime(2017,9,13,0,0) + timedelta(seconds=depFromLast)) 
        # Save the graph
        G = add_walk_edge(G, distMapNewDf, maxWalk)
        nx.write_gpickle(G, path)
        if multi:
            print('==>MultiGraph has been created!')
        else:
            print('==>DiGraph has been created!')
    print('-----------{}-----------'.format(len('Create Graph') * '-'))  
    return G

def direct_trip(df_day, source, target, start_time, interval):
    """
    This function is used to find direct trips.

    Input: 
        df_day     :        DataFrame of day data of transformation
        source     :        The orgin of the journey
        target     :        The destination of the journey
        start_time :        Departure time
        interval   :        Find journeys that start within 30 minutes (default) from the departure time 
    """
    result = []
    start_time = datetime.strptime('2017/09/13 '+start_time, '%Y/%m/%d %H:%M')
    for idx, row in df_day.iterrows():
        if (source in row['station_name'])&(target in row['station_name']):
            source_idx = row['station_name'].index(source)
            target_idx = row['station_name'].index(target)
            if source_idx < target_idx:
                dep_time = row['Timetable'][source_idx][3]
                dep_time = datetime(2017,9,13,0,0) + timedelta(seconds=dep_time)
                arr_time = row['Timetable'][target_idx][1]
                arr_time = datetime(2017,9,13,0,0) + timedelta(seconds=arr_time)
                if (dep_time>=start_time)&(dep_time<=start_time+interval):
                    station_list = row['station_name'][source_idx:target_idx+1]
                    value = {'trip_id': row['identifies_of_trip'],
                             'arrToNext': arr_time,
                             'depFromLast': dep_time}
                    result.append((station_list, value))
        result = sorted(result,key=lambda x: x[-1]['arrToNext'])
    return result

def get_paths(G, source, target, StartTime, interval, stopnum, TripN, PathN, last_arr_time):
    """
    Get recommmended paths from the graph.
    """
    StartTime = datetime.strptime('2017/09/13 '+StartTime, '%Y/%m/%d %H:%M')
    if last_arr_time == None:
        last_arr_time = StartTime + timedelta(minutes=40)
    else: 
        last_arr_time = datetime.strptime('2017/09/13 '+last_arr_time, '%Y/%m/%d %H:%M')
    paths = []
    count = 0
    while len(paths) == 0:
        paths = all_simple_paths_multigraph(last_arr_time, G, source, target, StartTime, interval=interval, StopN=stopnum, TripN=TripN, PathN=PathN)
        last_arr_time = last_arr_time + timedelta(minutes=30)
        count +=1
        if count == 5:
            break
    return paths

def get_all_paths(G, df_day, source,  target, StartTime, interval, stopnum, TripN, PathN, last_arr_time):
    """
    Concatenate path solutions, combining directed journeys and others that need transfering.
    """
    # Find path directly arriving at the destination without changing trip
    result_direct = []
    paths_direct  = direct_trip(df_day, source, target, StartTime, interval)
    print('=>Looking for directed path...')
    if not paths_direct:
        print("==>No directed path is found.")
    else:
        print("==>{} directed path are found.".format(len(paths_direct)))
        for path in paths_direct:
            station_list1 = [path[0][0], path[0][-1]]
            trip_id_list1 = [path[1]['trip_id']]
            trip_id_list1 = [[i] for i in trip_id_list1]
            result_direct.append([station_list1, trip_id_list1])

    # Find other paths from the graph
    result_graph = []
    print('=>Looking for other paths from the graph...')
    paths_graph  = get_paths(G, source, target, StartTime, interval=interval, stopnum=stopnum, TripN=TripN, PathN=PathN, last_arr_time=last_arr_time)
    for path in paths_graph:
        station_list2 = [i[1] for i in path]
        trip_id_list2 = [i[2]['trip_id'] for i in path]
        # Not count the directed in above part
        change_index = np.where(np.array(trip_id_list2[:-1]) != np.array(trip_id_list2[1:]))[0]
        if len(change_index)>0:
            station_list2 = [station_list2[i] for i in change_index]
            station_list2 = [path[0][0]] + station_list2 + [path[-1][1]]
            trip_id_list2 = [trip_id_list2[i] for i in change_index] + [trip_id_list2[-1]]
            trip_id_list2 = [[i] for i in trip_id_list2]
            result_graph.append([station_list2, trip_id_list2])
    print('==>{} other paths are found.'.format(len(result_graph)))
    return result_direct + result_graph

def set_stopnum(df_day, source, target, start_time, distMapNewDf, interval):
    """
    Set the number of stops in a journey.
    """
    stopnum = 15
    if direct_trip(df_day, source, target, start_time, interval):
        candidate = max([len(i[0]) for i in direct_trip(df_day, source, target, start_time, interval)])
        if candidate < 10:
            stopnum = candidate
    elif float(distMapNewDf[(distMapNewDf['placeA'] == source)&(distMapNewDf['placeB'] == target)].distance) <0.5:
        stopnum = 2
    return stopnum


def DFS_route_recommend(G, distMap, source, target, StartTime, interval=timedelta(minutes=10), stopN=None, TripN=4, PathN=20, last_arr_time=None):
    """
    Compute all paths of a multigraph from source to target using DFS.
    
    Input:
        last_arr_time: Set the lastest arrival time of the journey
        G             :           Graph
        distMap       :           Distance map
        source        :           Source vertex
        target        :           Target Vertex
        StartTime     :           Start time, should be in format (%H:%M)
        interval      :           Longest time the user can wait
        StopN         :           Largest number of vertex in path (at least 2, at most len(G))
        TripN         :           The maximum number of trip ids in a journey
        PathN         :           Top N fastest path will be returned
        maxWalk       :           Max length (/km) limit of walk
        last_arr_time :           Limit the end time of the journey
    """
    print('---------- {} ----------'.format('DFS Route Recommmended'))
    if type(stopN) == type(None):
        stopN = set_stopnum(df_day, source, target, StartTime, distMap, interval)
        
    final_result = get_all_paths(G, df_day, source, target, StartTime, interval=interval, stopnum=stopN, TripN=TripN, PathN=PathN, last_arr_time=None)
    print('-----------{}-----------'.format(len('DFS Route Recommmended') * '-'))
    return [[trip] for trip in final_result]