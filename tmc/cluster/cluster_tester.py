from cluster_abx import TMCClient, Cluster
from cluster_abx_actions import TKGSClient
import cluster_abx

_client = TMCClient()

_cluster = Cluster()
_cluster.Name = 'home-test-4'
_cluster.ClusterGroup = 'home-test'
_cluster.Provisioner = 'test'
#_response = _client.createCluster(_cluster)
#_response = _client.getCluster('home-test-1', 'test', 'supervisor1')
#_response = _client.deleteCluster('home-test-4', 'test', 'supervisor1')
#_response = _client.getClusterAdminKubeConfig('home-test-1', 'test', 'supervisor1')



# _k8sclient = TKGSClient()
# _response = _k8sclient.getClusterKubeconfig('home-test-1', 'test')

#_response = _client.getClusterGroupList()
#_response = _client.getClusterList()
#_response = _client.getClusterGroupList()
#_response = _client.getKubernetesReleases('tkgs', 'supervisor1', 'tap')
#_response = _client.getVirtualMachineClasses('supervisor1', 'tap')
#_response = _client.getStorageClasses('tkgs', 'supervisor1', 'tap')
#_response = _client.getProvisionerList('supervisor1')

#inputs = {'action':'form-getclustergrouplist'}
#inputs = {'action':'form-getclusterlist'}
#inputs = {'action':'form-getprovisionerlist'}
inputs = {'action':'form-getnodesizelist','provisioner':'test','managementcluster':'supervisor1'}

_response = cluster_abx.handler('', inputs)
print(_response)
