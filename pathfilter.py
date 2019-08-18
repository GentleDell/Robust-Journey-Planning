def filter_trips(trips_candidates: list, num_interchange: int = 10):
    '''
        It keeps all direct trips and trips having few interchanges.
    '''
    filtered_trips = []
    filteres_stations = []
    for trip in trips_candidates:
        bus_list = trip[1]
        station_list = trip[0]
        
        new_set = {}
        old_set = {}
        aggre_trip = []
        aggre_statation = [station_list[0]]
        
        cnt = 0
        while cnt <= len(bus_list):
            if len(new_set) == 0:
                if len(old_set) != 0:
                    cnt -= 1
                    aggre_trip.append(list(old_set))
                    aggre_statation.append(station_list[cnt])   
                    
                    new_set = set(bus_list[cnt])
                    old_set = {}
                else:
                    new_set = set(bus_list[cnt])
            else:
                old_set = new_set
                if cnt < len(bus_list):
                    new_set = new_set.intersection(set(bus_list[cnt]))   
            cnt += 1
        
        aggre_trip.append(list(new_set))
        aggre_statation.append(station_list[-1])
        if len(aggre_trip) <= num_interchange:
            filtered_trips.append(aggre_trip)
            filteres_stations.append(aggre_statation)
            
    return filteres_stations,filtered_trips
    
trips = [ [['a','b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j'],
           [[1],[2],[3],[4],[5],[6],[7],[8],[9]]]]
#           [[1,2,3,4,5],[3,4,5,6],[6,7,8,9], [9,12,4,6], [7,0,6,4], [11,31,33,32], [33,32,705], [705], [705]]] ]
ans = filter_trips(trips_candidates=trips)
