from cluster_abx import TMCClient, Cluster
from cluster_abx_actions import TKGSClient
import cluster_abx
import cluster_abx_actions

_client = TMCClient()

_cluster = Cluster()
_cluster.Name = 'home-test-2'
_cluster.ClusterGroup = 'home-test'
_cluster.Provisioner = 'test'
#_cluster.Version = 'v1.27.11+vmware.1-fips.1-tkg.2'
_cluster.Version = 'v1.28.8+vmware.1-fips.1-tkg.2'
_cluster.NodeVersion = '5'
_cluster.StorageClass = 'general-usage'
_cluster.NodeSize = 'best-effort-medium-cpu'
_cluster.ControlPlaneReplicas = 1
_cluster.WorkerNodeCount = 2
_cluster.ManagementCluster = 'supervisor1'
_response = _client.createCluster(_cluster)
#_response = _client.getCluster('home-test-2', 'test', 'supervisor1')
#_response = _client.deleteCluster('home-test-4', 'test', 'supervisor1')
#_response = _client.getClusterAdminKubeConfig('home-test-1', 'test', 'supervisor1')
#_response = _client.updateCluster(_cluster)


_k8sclient = TKGSClient()
#_response = _k8sclient.getClusterKubeconfig('home-test-2', 'test')
#_response = _k8sclient.createServiceAccount(_response, 'kube-system', 'sa-test')
#_response = _k8sclient.createClusterRoleBinding(_response, 'sa-test', 'kube-system', 'cluster-admin')
inputs = {'action':'cluster-findall'}
inputs = {'action':'cluster-find', 'id':'home-tap-1'}
#_response = cluster_abx_actions.abxHandler('', inputs)

#_response = _client.getClusterGroupList()
#_response = _client.getClusterList()
#_response = _client.getClusterGroupList()
#_response = _client.getKubernetesReleases('tkgs', 'supervisor1', 'tap')
#_response = _client.getVirtualMachineClasses('supervisor1', 'tap')
#_response = _client.getStorageClasses('tkgs', 'supervisor1', 'tap')
#_response = _client.getProvisionerList('supervisor1')

#inputs = {'action':'form-getmanagementclusterlist'}
#inputs = {'action':'form-getclustergrouplist'}
#inputs = {'action':'form-getclusterlist'}
#inputs = {'action':'form-getprovisionerlist'}
#inputs = {'action':'form-getnodesizelist','provisioner':'test','managementcluster':'supervisor1'}
#inputs = {'action':'form-storageclasslist','provisioner':'test','managementcluster':'supervisor1'}
#inputs = {'action':'form-getprovisionerlist','provisioner':'test','managementcluster':'supervisor1'}

#_response = cluster_abx.handler('', inputs)

#_response = _client.getManagementClusterList(includeAttached=False)
print(_response)


#'{"error":"failed to update the cluster:(target=mc:01HV0ZQWBT5WE1HVXCPPNJK4CW, intentId=01J1BKRTWYFZG1ZMG1JY47FAQV): admission webhook \\"tkr-resolver-cluster-webhook.tanzu.vmware.com\\" denied the request: could not resolve TKR/OSImage for controlPlane, machineDeployments: [md-0], query: {controlPlane: {k8sVersionPrefix: \'v1.28.8+vmware.1-fips.1-tkg.2\', tkrSelector: \'tkr.tanzu.vmware.com/standard\', osImageSelector: \'os-arch=amd64,os-name=photon,os-version=3,tkr.tanzu.vmware.com/standard\'}, machineDeployments: [{k8sVersionPrefix: \'v1.28.8+vmware.1-fips.1-tkg.2\', tkrSelector: \'tkr.tanzu.vmware.com/standard\', osImageSelector: \'os-arch=amd64,os-name=photon,os-version=3\'}]}, result: {controlPlane: {k8sVersion: \'\', tkrName: \'\', osImagesByTKR: map[]}, machineDeployments: [{k8sVersion: \'\', tkrName: \'\', osImagesByTKR: map[]}]}","code":7,"message":"failed to update the cluster: (target=mc:01HV0ZQWBT5WE1HVXCPPNJK4CW, intentId=01J1BKRTWYFZG1ZMG1JY47FAQV): admission webhook \\"tkr-resolver-cluster-webhook.tanzu.vmware.com\\" denied the request: could not resolve TKR/OSImage for controlPlane, machineDeployments: [md-0], query: {controlPlane: {k8sVersionPrefix: \'v1.28.8+vmware.1-fips.1-tkg.2\', tkrSelector: \'tkr.tanzu.vmware.com/standard\', osImageSelector: \'os-arch=amd64,os-name=photon,os-version=3,tkr.tanzu.vmware.com/standard\'}, machineDeployments: [{k8sVersionPrefix: \'v1.28.8+vmware.1-fips.1-tkg.2\', tkrSelector: \'tkr.tanzu.vmware.com/standard\', osImageSelector: \'os-arch=amd64,os-name=photon,os-version=3\'}]}, result: {controlPlane: {k8sVersion: \'\', tkrName: \'\', osImagesByTKR: map[]}, machineDeployments: [{k8sVersion: \'\', tkrName: \'\', osImagesByTKR: map[]}]}"}'
# '{"error":"failed to update the cluster: (target=mc:01HV0ZQWBT5WE1HVXCPPNJK4CW, intentId=01J1BNV9R9NDNECJCBBT8KQ80C): admission webhook \\"tkr-resolver-cluster-webhook.tanzu.vmware.com\\" denied the request: could not resolve TKR/OSImage for controlPlane, machineDeployments: [md-0], query: {controlPlane: {k8sVersionPrefix: \'v1.28.8+vmware.1-fips.1-tkg.2\', tkrSelector: \'tkr.tanzu.vmware.com/standard\', osImageSelector: \'os-arch=amd64,os-name=photon,os-version=3,tkr.tanzu.vmware.com/standard\'}, machineDeployments: [{k8sVersionPrefix: \'v1.28.8+vmware.1-fips.1-tkg.2\', tkrSelector: \'tkr.tanzu.vmware.com/standard\', osImageSelector: \'os-arch=amd64,os-name=photon,os-version=3\'}]}, result: {controlPlane: {k8sVersion: \'\', tkrName: \'\', osImagesByTKR: map[]}, machineDeployments: [{k8sVersion: \'\', tkrName: \'\', osImagesByTKR: map[]}]}","code":7,"message":"failed to update the cluster: (target=mc:01HV0ZQWBT5WE1HVXCPPNJK4CW, intentId=01J1BNV9R9NDNECJCBBT8KQ80C): admission webhook \\"tkr-resolver-cluster-webhook.tanzu.vmware.com\\" denied the request: could not resolve TKR/OSImage for controlPlane, machineDeployments: [md-0], query: {controlPlane: {k8sVersionPrefix: \'v1.28.8+vmware.1-fips.1-tkg.2\', tkrSelector: \'tkr.tanzu.vmware.com/standard\', osImageSelector: \'os-arch=amd64,os-name=photon,os-version=3,tkr.tanzu.vmware.com/standard\'}, machineDeployments: [{k8sVersionPrefix: \'v1.28.8+vmware.1-fips.1-tkg.2\', tkrSelector: \'tkr.tanzu.vmware.com/standard\', osImageSelector: \'os-arch=amd64,os-name=photon,os-version=3\'}]}, result: {controlPlane: {k8sVersion: \'\', tkrName: \'\', osImagesByTKR: map[]}, machineDeployments: [{k8sVersion: \'\', tkrName: \'\', osImagesByTKR: map[]}]}"}'
# '{"error":"failed to update the cluster: (target=mc:01HV0ZQWBT5WE1HVXCPPNJK4CW, intentId=01J1BPGX2MNMHBV09TF3T675HC): admission webhook \\"tkr-resolver-cluster-webhook.tanzu.vmware.com\\" denied the request: could not resolve TKR/OSImage for controlPlane, machineDeployments: [md-0], query: {controlPlane: {k8sVersionPrefix: \'v1.28.8+vmware.1-fips.1-tkg.2\', tkrSelector: \'tkr.tanzu.vmware.com/standard\', osImageSelector: \'os-arch=amd64,os-name=photon,os-version=3,tkr.tanzu.vmware.com/standard\'}, machineDeployments: [{k8sVersionPrefix: \'v1.28.8+vmware.1-fips.1-tkg.2\', tkrSelector: \'tkr.tanzu.vmware.com/standard\', osImageSelector: \'os-arch=amd64,os-name=photon,os-version=3\'}]}, result: {controlPlane: {k8sVersion: \'\', tkrName: \'\', osImagesByTKR: map[]}, machineDeployments: [{k8sVersion: \'\', tkrName: \'\', osImagesByTKR: map[]}]}","code":7,"message":"failed to update the cluster: (target=mc:01HV0ZQWBT5WE1HVXCPPNJK4CW, intentId=01J1BPGX2MNMHBV09TF3T675HC): admission webhook \\"tkr-resolver-cluster-webhook.tanzu.vmware.com\\" denied the request: could not resolve TKR/OSImage for controlPlane, machineDeployments: [md-0], query: {controlPlane: {k8sVersionPrefix: \'v1.28.8+vmware.1-fips.1-tkg.2\', tkrSelector: \'tkr.tanzu.vmware.com/standard\', osImageSelector: \'os-arch=amd64,os-name=photon,os-version=3,tkr.tanzu.vmware.com/standard\'}, machineDeployments: [{k8sVersionPrefix: \'v1.28.8+vmware.1-fips.1-tkg.2\', tkrSelector: \'tkr.tanzu.vmware.com/standard\', osImageSelector: \'os-arch=amd64,os-name=photon,os-version=3\'}]}, result: {controlPlane: {k8sVersion: \'\', tkrName: \'\', osImagesByTKR: map[]}, machineDeployments: [{k8sVersion: \'\', tkrName: \'\', osImagesByTKR: map[]}]}"}'