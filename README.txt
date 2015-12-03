#SmartHome
A python-based distributed operating system for a smart home / internet of things

Author: Samuel DeLaughter
Last Updated: 11/30/15

This is a distributed system simulating a home "internet-of-things" network composed of a gateway, backend database, and user terminal, along with several sensors and smart devices.

I initially created it as a project for my graduate course on Distributed Operating Systems at the University of Massachusetts Amherst.

Three distinct versions are currently included, each its own unique set of features, created for separate assignments.  In general, newer versions are more reliable and feature-rich than older ones, but some event-ordering features were removed between v0.2 and v0.3 to make it easier to implement the Paxos consensus algorithm.  Each version includes its own detailed README, as well as a copy of the original assignment.
