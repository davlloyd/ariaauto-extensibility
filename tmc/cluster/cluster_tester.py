from cluster_abx import TMCClient, Cluster
from enum import Enum
_client = TMCClient()


_cluster = Cluster()
_cluster.Name = 'home-test-1'
_cluster.ClusterGroup = 'home-test'
_cluster.Provisioner = 'test'
#_response = _client.createCluster(_cluster)
#_response = _client.getCluster('home-test-1', 'test', 'supervisor1')
#_response = _client.deleteCluster('home-test-1', 'test', 'supervisor1')
#print(_response)

