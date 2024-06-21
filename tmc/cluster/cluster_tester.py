from cluster_abx import TMCClient, Cluster
from cluster_abx_actions import TKGSClient


_client = TMCClient()

_cluster = Cluster()
_cluster.Name = 'home-test-4'
_cluster.ClusterGroup = 'home-test'
_cluster.Provisioner = 'test'
#_response = _client.createCluster(_cluster)
#_response = _client.getCluster('home-test-1', 'test', 'supervisor1')
#_response = _client.deleteCluster('home-test-4', 'test', 'supervisor1')
#_response = _client.getClusterAdminKubeConfig('home-test-1', 'test', 'supervisor1')



#print(_response)

_k8sclient = TKGSClient()
_k8sclient.getClusterKubeconfig('home-test-1', 'test')
