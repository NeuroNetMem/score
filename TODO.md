TODO
----

- make the first set of changes work 
- get comments to work
- get the video to work as well as the camera 
    X stop raw video save for video in
    X get the correct times when scoring video in
X separate experiment logic from manager
- add object manager
- add the tracking
    - add logger
    - make interface for adding/removing animals, background
    - debug crash
    - make simplified profiling interface/profile
    - optimize with numba/cython
    - add the output 
    - add animal numbers
    - add interface for set background, add animals, add animals auto
    set image threshold, set speed threshold for inversions
- filename include datetime, included in results file
- factor out the actual video reader, provide, read, move to frame, speed, 
the timer?
- add automatic scoring/handling
- add tracking visualization, gaze, trajectory, perspec

- solve start from next trial crash, other corner cases


STRATEGY
--------

- Analyzer does the set background. Calculate background is communicated on control (use signal). Analyzer becomes QObject
(probably needed for visualizations anyways)
- Init animals uses the CoM of connected components
- a reset animals button needed
- 