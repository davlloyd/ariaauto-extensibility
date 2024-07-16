"""
Service:        Tanzu Mission Controller cluster controller
Version:        1.15.2
Description:    Through ABX custom objects this script allows for the operational control
                of TMC clusters. This is structured to be a universal controller for all support platforms
                in TMC. This includes
                - VMware TKGs (supported)
                - VMware TKGm (to be determined if there is demand)
                - VMware AKS (coming)
                - VMware EKS (coming)
                The purpose of this is to allow TMC cluster consumption to be simplified
Changelog:      
        1.1.0   - Added wait routine for cluster provisioning to complete prior to completing task
                - Added more logging
        1.2.0   - Cleaned up logging and output processing
        1.3.0   - changed field phase to status and added provisioner field
        1.4.0   - Added support for getting admin kubeconfig
        1.5.0   - Added vRO action support
        1.6.0   - Fixed vro action input processing
        1.7.0   - Added management server queries
        1.8.0   - cleaned up form call identifiers
        1.9.0   - added support for vRO custom object
        1.10.0  - Improved exception handling and logging
        1.11.0  - Changed cluster inout/output for vRO for more specific naming instead of attemtoed generalisation
        1.12.0  - Improved security controls for cluster access context
        1.13.0  - Extending clustergroup support to enable control in Orchestrator
        1.14.0  - Added custom disk sizing
        1.15.0  - Extened logging and extended cluster ready determination to include agent health
"""


import json, requests, time, rsa, os
from datetime import timezone, datetime
from urllib.error import URLError, HTTPError

timeout = 2300      # ABX timesout at 900 seconds and Orchestrator at 1800 seconds



# Cluster value class
class Cluster:
    Name = None
    Description = "Cluster created and managed by Aria"
    Provisioner = None
    ClusterGroup = None
    ManagementCluster = 'supervisor1'
    StorageClass = 'general-usage'
    ControlPlaneReplicas = 1
    WorkerNodeCount = 2
    NodeSize = 'best-effort-medium'
    NodeVersion = '3'   # used to define the OS release when required
    FailureDomain = 'zone1'
    Version = 'v1.26.13+vmware.1-fips.1-tkg.3'
    Platform = 'tkgs'
    KubeletDisk = '20G'
    ContainerDisk = '20G'


    def __init__(self, name=None, provisioner=None, clusterGroup=None):
        self.Name = name
        self.Provisioner = provisioner
        self.ClusterGroup = clusterGroup


# TKG Sepcific value class
class TKGValues:
    @staticmethod
    def release(version):
        match (version):
            case '1.26':
                return 'v1.26.13+vmware.1-fips.1-tkg.3'
            case '1.27':
                return 'v1.27.11+vmware.1-fips.1-tkg.2'
            case '1.28':
                return 'v1.28.8+vmware.1-fips.1-tkg.2'
            
    @staticmethod
    def provisioner(clusterGroup):
        match (clusterGroup):
            case 'home-test':
                return 'test'
            case 'home-shared':
                return 'shared-services'
            case 'home-tap':
                return 'tap'
            case 'home-general':
                return 'cloud'
            case 'home-dev':
                return 'beta'
            case _:
                return 'cloud'
    
    @staticmethod
    def vmclass(nodesize):
        match (nodesize):
            case 'small':
                return 'best-effort-small'
            case 'medium':
                return 'best-effort-medium'
            case 'large':
                return 'best-effort-large-cpu'
            case 'tap':
                return 'best-effort-tap-node'
            case _:
                return 'best-effort-medium'


    @staticmethod
    def storageclass(storagetype):
        return 'general-usage'
    
    @staticmethod
    def managementcluster(controller):
        return 'supervisor1'


# Main TMC REST client for cluster management
class TMCClient:
    __hostname = 'tmc.tanzu.rocks'
    __username = 'david'
    __password = 'B3ach8um!'
    __clientid = 'pinniped-cli'
    __redirect_url = 'http://127.0.0.1/callback'
    __code_challenge = 'vTu6b5Jm2hpi1vjRJw7HB820EYNq7AFT1IHDLBQMc3Q'
    __code_verifier = 'UDABWPiROQh0nfhGzd_7OetrEJZZ7S-Z_H8_ZLB2i8Yc2wix'
    __scope = 'openid+offline_access+username+groups'
    __auth_code = None
    __access_token = None
    __refresh_token = None
    __id_token = None


    def __init__(self, hostname=None, username=None, password=None):
        if hostname != None:
            self.__hostname = hostname
        if username != None:
            self.__username = username
        if password != None:
            self.__password = password

        self.authorizeUser()
        self.obtainToken()

    # General HTTP Get query
    def __get(self, url):
        print(f"Executing HTTP Get with url: {url}")
        self.refreshToken()
        try:
            _headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'Authorization': f'Bearer {self.__access_token}',
                'grpc-metadata-x-user-id': self.__id_token,
                'grpc-metadata-x-refresh-token': self.__refresh_token
            }   
            
            with requests.get(url, headers=_headers) as _response:
                if _response.status_code == 200:
                    _item = json.loads(_response.content)
                    return _item
                else:
                    print(f"Error {_response.status_code} when running http get: {_response.reason} - {_response.text}\n")
                    return None
        except HTTPError as e:
            print(f'HTTP Error code: {e.code} descripton {e.reason}')
        except URLError as e:
            print(f'URL Error code: {e.code} descripton {e.reason}')

        return None
    

    # general HTTP Post. Requires data payload in JSON format
    def __post(self, url, data):
        print(f"Executing HTTP Post with url: {url}")
        self.refreshToken()
        try:
            _body = json.dumps(data).encode('utf-8')
            _headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'Authorization': f'Bearer {self.__access_token}',
                'grpc-metadata-x-user-id': self.__id_token,
                'grpc-metadata-x-refresh-token': self.__refresh_token
            }

            with requests.post(url, headers=_headers, data=_body) as _response:
                if _response.status_code == 200 or _response.status_code == 201 or _response.status_code == 202:
                    _item = json.loads(_response.text)
                    return _item
                else:
                    print(f"Error {_response.status_code} when running http post: {_response.reason} - {_response.text}\n")
                    return None
        except HTTPError as e:
            print(f'HTTP Error code: {e.code} descripton {e.reason}')
            if e.close == 409:
                raise HTTPError("Can not post request as it wold create a conflict", 409)
        except URLError as e:
            print(f'URL Error code: {e.code} descripton {e.reason}')

        return None

    # general HTTP Put. Requires data payload in JSON format
    def __put(self, url, data):
        print(f"Executing HTTP Post with url {url}")
        self.refreshToken()
        try:
            _body = json.dumps(data).encode('utf-8')
            _headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'Authorization': f'Bearer {self.__access_token}',
                'grpc-metadata-x-user-id': self.__id_token,
                'grpc-metadata-x-refresh-token': self.__refresh_token
            }

            with requests.put(url, headers=_headers, data=_body) as _response:
                if _response.status_code == 200 or _response.status_code == 201 or _response.status_code == 202:
                    _item = json.loads(_response.text)
                    return _item
                else:
                    print(f"Error {_response.status_code} when running http put: {_response.reason} - {_response.text}\n")
                    return None
        except HTTPError as e:
            print(f'HTTP Error code: {e.code} descripton {e.reason}')
            if e.close == 409:
                raise HTTPError("Can not post request as it wold create a conflict", 409)
        except URLError as e:
            print(f'URL Error code: {e.code} descripton {e.reason}')

        return None

    # general HTTP delete routine
    def __delete(self, url):
        print(f"Executing HTTP Delete with url {url}")
        self.refreshToken()
        try:
            _headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'Authorization': f'Bearer {self.__access_token}',
                'grpc-metadata-x-user-id': self.__id_token,
                'grpc-metadata-x-refresh-token': self.__refresh_token
            }

            with requests.delete(url, headers=_headers, auth=('', self.__access_token)) as _response:
                if _response.status_code == 200 or _response.status_code == 201 or _response.status_code == 202:
                    return _response.text
                else:
                    print(f"Error {_response.status_code} when running http delete: {_response.reason} - {_response.text}\n")
                    return None
        except HTTPError as e:
            print(f'HTTP Error code: {e.code} descripton {e.reason}')
        except URLError as e:
            print(f'URL Error code: {e.code} descripton {e.reason}')

        return None


    # Initial access authorization for user/password account
    def authorizeUser(self):
        print(f"Authorize User")
        _nonce = '9902045656a1c29b95515f7f45b40773'
        _challenge_method = 'S256'
        _state = 'kj3l2m48'

        _url = f'https://pinniped-supervisor.{self.__hostname}/provider/pinniped/oauth2/authorize?response_type=code&client_id={self.__clientid}&code_challenge={self.__code_challenge}&code_challenge_method={_challenge_method}&nonce={_nonce}&state={_state}&redirect_uri={self.__redirect_url}&scope={self.__scope}'

        _headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Pinniped-Username': self.__username,
            'Pinniped-Password': self.__password
        }

        try:
            with requests.get(_url, headers=_headers, allow_redirects=False) as _response:
                if _response.status_code == 302:
                    _location = _response.headers['location'].split('=')[1]
                    self.__auth_code = _location.split('&')[0]
                    return self.__auth_code
                else:
                    print(f"Error when running delete: {_response}\n")
                    return None

        except HTTPError as e:
            print(f'HTTP Error code: {e.code} descripton {e.reason}')
        except URLError as e:
            print(f'URL Error code: {e.code} descripton {e.reason}')

        return None


    # Get tokens for site access
    def obtainToken(self):
        print(f"Obtain access tokens")

        _url = f'https://pinniped-supervisor.{self.__hostname}/provider/pinniped/oauth2/token'
        _data = {
            'client_id': self.__clientid,
            'grant_type': 'authorization_code',
            'code': self.__auth_code,
            'redirect_uri': self.__redirect_url,
            'code_verifier': self.__code_verifier
        }

        try:
            with requests.post(_url, data=_data, allow_redirects=False) as _response:
                if _response.status_code == 200:
                    _values = json.loads(_response.text)
                    self.__access_token = _values['access_token']
                    self.__refresh_token = _values['refresh_token']
                    self.__id_token = _values['id_token']
                else:
                    print(f"Error when running post: {_response}\n")
        except HTTPError as e:
            print(f'HTTP Error: {e.code} with reason: {e.reason}')
        except URLError as e:
            print(f'URL Error: {e.code} with reason: {e.reason}')

        return None


    # Refresh tokens, needs to be done prior to each call as access token has short expiry
    def refreshToken(self):
        print(f"Refresh access token")

        _url = f'https://pinniped-supervisor.{self.__hostname}/provider/pinniped/oauth2/token'
        _data = {
            'client_id': self.__clientid,
            'grant_type': 'refresh_token',
            'refresh_token': self.__refresh_token
        }

        try:
            with requests.post(_url, data=_data) as _response:
                print(f"Status Code: {_response.status_code}")
                if _response.status_code == 200:
                    _values = json.loads(_response.text)
                    self.__access_token = _values['access_token']
                    self.__refresh_token = _values['refresh_token']
                    self.__id_token = _values['id_token']
                    return True
                else:
                    print(f"Error when running post: {_response}\n")
        except HTTPError as e:
            print(f'HTTP Error: {e.code} with reason: {e.reason}')
        except URLError as e:
            print(f'URL Error: {e.code} with reason: {e.reason}')

        return False


    # Get specified Cluster Details
    def getCluster(self, clusterName, provisionerName, managementCluster):
        print(f"Get cluster details")
        _url = f'https://{self.__hostname}/v1alpha1/clusters/?fullName.name={clusterName}&fullName.provisionerName={provisionerName}&fullName.managementClusterName={managementCluster}'
        if (_response := self.__get(_url)) is not None:
            return _response['cluster']
        else:
            return None


    # Get a list of clusters with filter opton
    def getClusterList(self, managementCluster='*', provisionerName='*', clusterName='*'):
        print(f'Get a list of clusters wth specified filters')
        _url = f'https://{self.__hostname}/v1alpha1/clusters'
        _url += f'?searchScope.name={clusterName}'
        _url += f'&searchScope.provisionerName={provisionerName}'
        _url += f'&searchScope.managementClusterName={managementCluster}'        
        if (_response := self.__get(_url)) is not None:
            return _response["clusters"]
        else:   
            return None
        

    # Create cluster with TMC
    def createCluster(self, cluster):
        print(f"Create new cluster: {cluster.Name}")
        
        match (cluster.Platform):
            case 'tkgs':
                _url = f'https://{self.__hostname}/v1alpha1/managementclusters/{cluster.ManagementCluster}/provisioners/{cluster.Provisioner}/tanzukubernetesclusters'
                _data = self.tkgsClusterTemplate(cluster)
            case 'aws':
                print("eks to be done")
                _url = None
            case 'eks':
                print("aks to be done")
                _url = None
        
        if _url is not None: # no platform specified
            if (_response := self.__post(_url, _data)) is not None:
                if (_cluster := self.waitClusterReady(cluster)) is not None:
                    print('Cluster provision successfully completed')
                    return _cluster
                    
        return None


    # Update existing cluster with TMC
    def updateCluster(self, cluster):
        print(f"Update existing cluster")
        
        match (cluster.Platform):
            case 'tkgs':
                _url = f'https://{self.__hostname}/v1alpha1/managementclusters/{cluster.ManagementCluster}/provisioners/{cluster.Provisioner}/tanzukubernetesclusters/{cluster.Name}'
                _data = self.tkgsClusterTemplate(cluster)
            case 'aws':
                print("eks to be done")
                _url = None
            case 'eks':
                print("aks to be done")
                _url = None
        
        if _url is not None:
            if (_response := self.__put(_url, _data)) is not None:
                return self.waitClusterReady(cluster)
        else:
            raise URLError('Could not define URL as no platform specified')


    # Wait for cluster to reach Ready state
    def waitClusterReady(self, cluster):
        print(f'Waiting for cluster to complete create/update operation')

        _response = None
        _start = time.time() 
        while (time.time() - _start) < timeout:  
            if (time.time() - _start) > 180: # Giving the clusters 3 minutes before polling progress
                _response = self.getCluster(cluster.Name, cluster.Provisioner, cluster.ManagementCluster)
                _status = _response['status']['phase']
                if _status == "READY":
                    print(f"Cluster is now repoerting phase READY")
                    if 'Agent-READY' in _response['status']['conditions']:
                        _agent = _response['status']['conditions']['Agent-READY']['status']
                        print(f"Cluster: READY, Agent Status: {_agent}")
                        if _agent != "FALSE": # CREATING, ATTACH_COMPLETE, AGents healthy
                            print(f'Cluster is fully operationaly ready')
                            return _response
            time.sleep(30)  # Sleep for 30 seconds before checking again

        print(f'Cluster provisioning timeout exceeded')
        raise Exception('Cluster create/update operation timeout exceeded')


    # Delete specified Cluster 
    def deleteCluster(self, clusterName, provisionerName, managementCluster):
        print(f"Get cluster details")
        _url = f'https://{self.__hostname}/v1alpha1/managementclusters/{managementCluster}/provisioners/{provisionerName}/tanzukubernetesclusters/{clusterName}'

        return self.__delete(_url)
    

    # Provides the cluster create and update body payload 
    def tkgsClusterTemplate(self, cluster):
        _template = {
                    "tanzuKubernetesCluster": {
                        "type": {
                            "kind": "Cluster",
                            "version": "v1alpha1",
                            "package": "vmware.tanzu.manage.v1alpha1.cluster"
                        },
                        "fullName": {
                            "name": cluster.Name,
                            "managementClusterName": cluster.ManagementCluster,
                            "provisionerName": cluster.Provisioner
                        },
                        "meta": {
                            "description": cluster.Description,
                            "labels": {
                            }
                        },
                        "spec": {
                            "clusterGroupName": cluster.ClusterGroup,
                            "tmcManaged": True,
                            "tkgServiceVsphere": {
                                "settings": {
                                    "network": {
                                        "pods": {
                                            "cidrBlocks": [
                                                "100.96.0.0/11"
                                            ]
                                        },
                                        "services": {
                                            "cidrBlocks": [
                                                "100.64.0.0/13"
                                            ]
                                        }
                                    },
                                    "storage": {
                                        "classes": [
                                            cluster.StorageClass
                                        ],
                                        "defaultClass": cluster.StorageClass
                                    }
                                }
                            },
                            "topology": {
                                "version": cluster.Version,
                                "clusterClass": "tanzukubernetescluster",
                                "controlPlane": {
                                    "class": cluster.NodeSize,
                                    "storageClass": cluster.StorageClass,
                                    "replicas": cluster.ControlPlaneReplicas,
                                    "osImage": {
                                        "name": "photon",
                                        "version": cluster.NodeVersion,
                                        "arch": "amd64"
                                    }

                                },
                                "nodePools": [
                                    {
                                        "spec": {
                                            "replicas": cluster.WorkerNodeCount,
                                            "class": "node-pool",
                                            "failureDomain": cluster.FailureDomain,
                                            "osImage": {
                                                "name": "photon",
                                                "version": cluster.NodeVersion,
                                                "arch": "amd64"
                                            },
                                            "nodeLabels": {
                                                "myLabel": "myValue"
                                            },
                                            "cloudLabels": {
                                                "myCloudLabel": "mvCloudValue"
                                            },
                                            "tkgServiceVsphere": {
                                                "class": cluster.NodeSize,
                                                "storageClass": cluster.StorageClass,
                                                "failureDomain": cluster.FailureDomain
                                            }
                                        },
                                        "info": {
                                            "name": "md-0"
                                        }
                                    }
                                ],
                                "variables": 
                                [
                                    {
                                        "name": "defaultStorageClass",
                                        "value": cluster.StorageClass
                                    },
                                    {
                                        "name": "vmClass",
                                        "value": cluster.NodeSize
                                    },
                                    {
                                        "name": "storageClass",
                                        "value": cluster.StorageClass
                                    },
                                    {
                                        "name": "ntp",
                                        "value": "au.pool.ntp.org"
                                    },
                        {
                            "name": "nodePoolVolumes",
                            "value": [
                                {
                                    "capacity": {
                                        "storage": cluster.ContainerDisk
                                    },
                                    "mountPath": "/var/lib/containerd",
                                    "name": "containerd",
                                    "storageClass": "general-usage"
                                },
                                {
                                    "capacity": {
                                        "storage": cluster.KubeletDisk
                                    },
                                    "mountPath": "/var/lib/kubelet",
                                    "name": "kubelet",
                                    "storageClass": "general-usage"
                                }
                            ]
                        },

                                ]
                            }
                        }
                    }
                }
        return _template

    # Get clusters admin Kubeconfig file
    def getClusterAdminKubeConfig(self, clustername, provisionerName, managementCluster):
        print(f"Get cluster admin kubeconfig")

        _url = f'https://{self.__hostname}/v1alpha1/clusters/{clustername}/adminkubeconfig'
        _url += f'?fullName.managementClusterName={managementCluster}&fullName.provisionerName={provisionerName}'

        publicKey, privateKey = rsa.newkeys(2048)
        #keytimestamp = datetime.now().isoformat()        
        keytimestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%fZ")

        _url += f'&encryptionKey.PublicKeyPem={publicKey}'
        _url += f'&encryptionKey.timestamp={keytimestamp}'

        if (_response := self.__get(_url)) is not None:
            _kubeconfig = rsa.decrypt(_response['kubeconfig'], privateKey).decode()
            print(f'Key returned {_kubeconfig}')
            return _kubeconfig
        else:
            return None


    # get the specified or a list of the clustergroups
    def getClusterGroupList(self, clustergroup=None):
        if clustergroup is None:
            clustergroup = '*'
        print(f'Getting a list of clustergroups with name {clustergroup}')
        _url = f'https://{self.__hostname}/v1alpha1/clustergroups?searchScope.name={clustergroup}'
        if (_response := self.__get(_url)) is not None:
            _response = _response["clusterGroups"]
        return _response

    # Get a list of clusters within a clustergroup
    def getClusterGroupClusters(self, clustergroup):
        print(f'Getting a list of clusters within clustergroup: {clustergroup}')
        
        _clusterlist = []
        for _cluster in self.getClusterList():
            if _cluster['spec']['clusterGroupName'].lower() == clustergroup.lower():
                _clusterlist.append(_cluster)

        return _clusterlist



    # Get a list of provisioners
    def getProvisionerList(self, managementcluster, provisioner=None):
        print(f'Get a list of provsioners for management cluster {managementcluster}')
        if provisioner is None:
            provisioner = '*'
        _url = f'https://{self.__hostname}/v1alpha1/managementclusters/{managementcluster}/provisioners?searchScope.name={provisioner}'
        if (_response := self.__get(_url)) is not None:
            _response = _response["provisioners"]
        return _response


    # Get a list of Management Clusters
    def getManagementClusterList(self, managementcluster=None, includeAttached=False):
        print(f'Get a list of provsioners for management cluster {managementcluster}')
        if managementcluster is None:
            managementcluster = '*'
        _url = f'https://{self.__hostname}/v1alpha1/managementclusters?searchScope.name={managementcluster}'
        _response = self.__get(_url)
        
        _clusters=[]
        if not includeAttached:
            for _item in _response['managementClusters']:
                if _item['fullName']['name'] != 'attached':
                    _clusters.append(_item)
        else:
            _clusters = _response['managementClusters']

        return _clusters


    # Get a list of cluster options
    def getClusterOptions(self, managementcluster, provisioner):
        print(f'Get a list of cluster options for provisioner {provisioner} in management cluster {managementcluster}')
        _url = f'https://{self.__hostname}/v1alpha1/clusters:options?provisionerName={provisioner}&managementClusterName={managementcluster}'
        return self.__get(_url)


    # Get TKGS virtual machijne class within provisoner in a management cluster
    def getVirtualMachineClasses(self, managementcluster, provisioner):
        print(f'Get a list of virtulmachineclasses assigned to provisioner {provisioner} in management cluster {managementcluster}')
        if (_response := self.getClusterOptions(managementcluster, provisioner)) is not None:
            return [c["name"] for c in _response["tkgServiceVsphereOptions"]["virtualMachineClasses"]]


    # Get K8s Releases, if tkgs includeprovisoner and management cluster names
    def getKubernetesReleases(self, platform=None, managementcluster=None, provisioner=None):
        print(f'Get a list of k8s relesaes')
        if platform is None:
            platform = 'tkgs'

        match platform:
            case 'tkgs':
                if (_response := self.getClusterOptions(managementcluster, provisioner)) is not None:
                    return [c["name"] for c in _response["tkgServiceVsphereOptions"]["virtualMachineImages"]]
            case 'aks':
                print('aks not implemnted')
            case 'eks':
                print('eks not implemnted')


    # Get storage classes assognmed to provisoner in a management cluster
    def getStorageClasses(self, platform=None, managementcluster=None, provisioner=None):
        print(f'Get a list of storage classes assigned to provisioner {provisioner} in management cluster {managementcluster}')
        if platform is None:
            platform = 'tkgs'

        match platform:
            case 'tkgs':
                if (_response := self.getClusterOptions(managementcluster, provisioner)) is not None:
                    return [c["name"] for c in _response["tkgServiceVsphereOptions"]["storageClasses"]]
            case 'aks':
                print('aks not implemnted')
            case 'eks':
                print('eks not implemnted')



# Main handler for ABX actions
def abxHandler(context, inputs):
    """
        Handles the ABX event and performs the necessary operations based on the inputs.

        Args:
            context: The context object containing information about the ABX event.
            inputs: The inputs provided for the ABX event.

        Returns:
            outputs: The outputs generated by the ABX handler.
    """

    _outputs = inputs
    _op = inputs["__metadata"]["operation"]
    _platform = inputs.get('platform') or 'tkgs'

    print (f"Running operational request type: {_op}")

    _tmc_host = context.getSecret(inputs['tmc_host'])
    _tmc_username = context.getSecret(inputs['tmc_username'])
    _tmc_password = context.getSecret(inputs['tmc_password'])

    _client = TMCClient(hostname=_tmc_host, username=_tmc_username, password=_tmc_password)

    match _op:
        case "create":
            _outputs['create'] = True
            _cluster = processInputs(inputs)
            if(_response := _client.createCluster(_cluster)) is not None:
                _outputs.update(processClusterResponse(_platform, _response))
        case "update":
            _outputs['update'] = True
            _cluster = processInputs(inputs)
            if(_response := _client.updateCluster(_cluster)) is not None:
                _outputs.update(processClusterResponse(_platform, _response))
        case "read":
            _outputs['read'] = True
            if(_response := _client.getCluster(inputs['name'], inputs['provisioner'], inputs['managementcluster'])) is not None:
                _outputs.update(processClusterResponse(_platform, _response))
        case "delete":
            _outputs['delete'] = True
            _response = _client.deleteCluster(inputs['name'], inputs['provisioner'], inputs['managementcluster'])

    return _outputs


# process inputs into platform specific settings
def processInputs(inputs):    
    print(f"Processing inputs")
    _cluster = Cluster()
    _cluster.Name = inputs['name']
    _cluster.Description = inputs['description']
    _cluster.ClusterGroup = inputs['clustergroup']
    _cluster.WorkerNodeCount = inputs['workernodecount']
    _cluster.Platform = inputs['platform']
    _cluster.Version = inputs['version']
    _cluster.NodeSize = inputs['nodesize']
    _cluster.StorageClass = inputs['storageclass']
    _cluster.ControlPlaneReplicas = inputs['controlplanereplicas']
    _cluster.ContainerDisk = inputs['containerdisk']
    _cluster.KubeletDisk = inputs['kubeletdisk']
    match (inputs['platform']):
        case 'tkgs':
            print('tkg values processing')
            _cluster.ManagementCluster = inputs['controller']
            if inputs['clustergroup'] != "unset":
                _cluster.Provisioner = inputs['provisioner']
            else:
                _cluster.Provisioner = TKGValues.provisioner(inputs['clustergroup'])
            if '1.25' in _cluster.Version or '1.26' in _cluster.Version or '1.27' in _cluster.Version:
                _cluster.NodeVersion = '3'
            else:
                _cluster.NodeVersion = '5'
        case 'eks':
            print('eks to be done')
        case 'aks':
            print('aks to be done')
    return _cluster


# extracts current cluster data to feed into the abx output variable
def processClusterResponse(platform, response):
    print('Processing cluster response')
    _status = {}
    _status['name'] = response['fullName']['name']
    _status['controller'] = response['fullName']['managementClusterName']
    _status['uid'] = response['meta']['uid']
    if 'description' in response['meta']:
        _status['description'] = response['meta']['description']
    else:
        _status['description'] = ''
    _status['clustergroup'] = response['spec']['clusterGroupName']
    _status['controlplanereplicas'] = response['spec']['topology']['controlPlane']['replicas']
    _status['workernodecount'] = response['spec']['topology']['nodePools'][0]['spec']['replicas']
    _status['version'] = response['spec']['topology']['version'] # platform specific value so not in cluster schema
    _status['platform'] = platform
    _status['status'] = response['status']['phase']

    match (platform):        
        case 'tkgs':
            _status['provisioner'] = response['fullName']['provisionerName'] # platform specific value so not in cluster schema
            for _entry in response['spec']['topology']['variables']:
                match _entry['name']:
                    case "storageClass":
                        _status['storageclass'] = _entry['value'] # platform specific value so not in cluster schema
                    case "vmClass":
                        _status['nodesize'] = _entry['value'] # platform specific value so not in cluster schema
        case 'eks':
            print('eks to be done')
        case 'aks':
            print('aks to be done')
    
    return json.dumps(_status)


# Process the response from a clustergroup query
def processClusterGroupResponse(response):
    print('Processing clustergroup response')
    _status = {}
    _status['name'] = response['fullName']['name']
    if 'description' in response['meta']:
        _status['description'] = response['meta']['description']
    else:
        _status['description'] = ''

    return json.dumps(_status)



# Handler for vRO Actions
def handler(context, inputs):
    print('Executing vRO Action')

    _action = inputs["action"]
    print (f"Running orchestrator action: {_action}")

    outputs = []
    _host = os.environ.get("host") or 'tmc.tanzu.rocks'
    _username = os.environ.get("username") or 'david'
    _password = os.environ.get("password") or 'B3ach8um!'

    _platform = inputs.get('platform') or 'tkgs'
    _managementcluster = inputs.get('managementcluster') or 'supervisor1'
    _provisioner = inputs.get('provisioner') or '*'

    _client = TMCClient(hostname=_host, username=_username, password=_password)

    match _action:
        case "cluster-create":
            _cluster = processInputs(inputs)
            if(_response := _client.createCluster(_cluster)) is not None:
                print(f'Cluster creation result: {_response}')
                outputs = processClusterResponse(_platform, _response)
        case "cluster-update":
            _cluster = processInputs(inputs)
            if(_response := _client.updateCluster(_cluster)) is not None:
                outputs = processClusterResponse(_platform, _response)
        case "cluster-delete":
            if(_response := _client.deleteCluster(clusterName=inputs['name'], provisionerName=_provisioner, managementCluster=_managementcluster)) is not None:
                outputs = _response
        case "cluster-findall":
            if(_response := _client.getClusterList()) is not None:
                for _item in _response:
                    outputs.append(processClusterResponse(_platform, _item))
        case "cluster-find":
            if(_response := _client.getClusterList(clusterName=inputs['name'])) is not None:
                outputs = processClusterResponse(_platform, _response[0])
        case "clustergroup-find":
            if(_response := _client.getClusterGroupList(inputs['name'])) is not None:
                outputs.append(processClusterGroupResponse(_response[0]))
        case "clustergroup-findall":
            if(_response := _client.getClusterGroupList()) is not None:
                for _item in _response:
                    outputs.append(processClusterGroupResponse(_item))
        case "clustergroup-cluster-list":
            if(_response := _client.getClusterGroupClusters(inputs['name'])) is not None:
                for _item in _response:
                    outputs.append(processClusterResponse(_platform, _item))
        case "form-managementclusterlist":
            if(_response := _client.getManagementClusterList()) is not None:
                outputs = [c["fullName"]["name"] for c in _response]
        case "form-clustergrouplist":
            if(_response := _client.getClusterGroupList()) is not None:
                outputs = [c["fullName"]["name"] for c in _response]
        case "form-clusterlist":
            if(_response := _client.getClusterList()) is not None:
                outputs = [c["fullName"]["name"] for c in _response]
        case "form-provisionerlist":
            if (_response := _client.getProvisionerList(_managementcluster)) is not None:        
                outputs = [c["fullName"]["name"] for c in _response]
        case "form-versionlist":
            outputs =  _client.getKubernetesReleases(_platform, _managementcluster, _provisioner)
        case "form-nodesizelist":
            outputs = _client.getVirtualMachineClasses(_managementcluster, _provisioner)
        case "form-storageclasslist":
            outputs = _client.getStorageClasses(_platform, _managementcluster, _provisioner)

    return outputs
