"""
Service:        Tanzu Platform Controller Script
Version:        1.0.0
Description:    Through Orchestrator custom objects this script allows for the operational control
                of Tanzu Platform including
                - projects
                - spaces
                - Kuebrnetes resources
                The purpose of this is to allow Tanzu Platform to be integrated with systems also managed by Aria
                such as allowing a Kubernetes Cluster to ba assigned as workload provider in a Tanzu project 
Changelog:      

"""

import json, time, requests, os
from urllib.error import URLError, HTTPError


class TPClient:
    __tpurl = None
    __tptoken = None

    def __init__():
        return True
    
    def __client(self, url, token):
        return True
    
