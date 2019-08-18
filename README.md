# Data Science Final Project -- Robust Journey Planning

Team members: Shengzhao Xia, Yan Fu, Yinan Zhang, Yunbei Huang, Yuting Huang, Zhantao Deng (Ordered by first letter of given name)


## Note to run the demo
Please run the `interface.py` to run our demo. But before doing that, you need to:
### Links to data: 
Please download the data from this link (https://drive.google.com/file/d/1jwkWlcUDfqTnCw1pTC7U1iWUGa5ofnS6/view) and unzip it into './data' folder.
### External libraries: 
To run our interface, you may need to use following libraries:
* PyQt
* Bokeh
* pyproj
* Pandas

## Problem description

Given a desired departure, or arrival time, our planner will compute the fastest route between two stops within a provided uncertainty tolerance expressed as interquartiles. For instance, “what route from A to B is the fastest at least Q% of the time if I want to leave from A (resp. arrive at B) at instant T”.

## Solution

In this project we follow these assumptions:
* Delays and travel times on the public transport network are uncorrelated with one another.
* The journey starts at a station and ends at another station.
* One can walk from one station to another if their distance is less than 200m or 400m.
* The walking speed of pedestrain follow the Gaussian distribution~N(1.2,0.04) (m/s).

And we solve this problem by:
* Re-aggreate the history data (where each row shows timing information of one trip at one station) into two highly densed files (one saves full trip and timing for each unique trip id; and the other one saves the distributions of arrival/departure delay of each trip id)
* Building graphs based on SBB bus/train/tram information, and also we add edges between stations within 200-400 metres of each other (which are considered as 'walking path')
* Use Monte Carlo sampling to estimate the probability of catching up/missing a trip.
* For multi-routes plans, we finally return 3 routes: one with the earliest arrival time, one with least walking time, one with the least number of transfers.
* And we compare the routes found by our planner and SBB, and many of them are almost the same.
* Finally, we write a user-interactive interface to actively show our result.

## Pros and Cons
### Pros:
* We consider the different trip schedules for weekday, weekend and public holiday
* We consider two different ways to construct graphs, and each of them take advantages in some area, and both produce satisfactory results (similar to SBB plan)
    * Graph construction via Train/Bus Number: Reduce the amount of data 
    * Graph construction via Trip ID: Embedding schedule information on the graph 


### Cons:
* Consecutive walking plans, that is to say, our plan will suggest walking from A to B, then from B to C, but not directly  walking from A to C, which introduces longer distance.

## Visualization
The following image is our interface. And compared to SBB plan, we can see that our planner can find correct path.

![interface](https://github.com/GentleDell/Robust-Journey-Planning/blob/master/image/interface.png)

![SBB](https://github.com/GentleDell/Robust-Journey-Planning/blob/master/image/SBB.jpg)




