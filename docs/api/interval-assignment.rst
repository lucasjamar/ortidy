Interval assignment
====================

Assign tasks with **fixed** start/end times to a minimum-cost set of resources,
with a minimum gap between consecutive tasks on the same resource and — optionally —
a location-connection rule (a resource can only take a task that starts where its
previous task ended). Real instances: aircraft rotations (gap = turnaround), crew
lines of flying, gate allocation, vehicle/driver duty chaining, machine reservations.

One function; optional columns opt into complexity across four regimes:

===  ==========  =========  ===========================  ==========================
 #   locations   resources  example                      model
===  ==========  =========  ===========================  ==========================
 1   no          no         single fleet, single base    pairwise conflict CP-SAT
 2   yes         no         single fleet, no base         min path cover on a DAG
 3   no          yes        mixed fleet, single base      pairwise + typed used-vars
 4   yes         yes        mixed fleet, free network     per-type flow on a DAG
===  ==========  =========  ===========================  ==========================

The **connection condition subsumes the interval condition**: task ``i`` can precede
``j`` on one resource iff ``end(i) + min_gap <= start(j)`` *and* (no locations *or*
``end_location(i) == start_location(j)``). Regime 1 is regime 2 where every location
is identical, so a single compatibility-arc builder drives all four models.

.. autofunction:: ortidy.scheduling.interval_assignment.interval_assignment
