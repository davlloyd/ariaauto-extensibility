"""
Service:        Tanzu Mission Controller cluster controller
Version:        1.0.6
Description:    Through ABX custom objects this script allows for the operational control
                of TMC clusters. This is structured to be a universal controller for all support platforms
                in TMC. This includes
                - VMware TKGs (supported)
                - VMware TKGm (to be determined if there is demand)
                - VMware AKS (coming)
                - VMware EKS (coming)
                The purpose of this is to allow TMC cluster consumption to be simplified
Changelog:      
        1.0.1   - Added wait routine for cluster provisioning to complete prior to completing task
                - Added more logging
        1.0.2   - Cleaned up logging and output processing
        1.0.3   - changed field phase to status and added provisioner field
        1.0.4   - Added support for getting admin kubeconfig
        1.0.5   - Added vRO action support
        1.0.6   - Fixed vro action input processing
"""


import json, requests, time, rsa, os
from datetime import timezone, datetime
from urllib.error import URLError, HTTPError

timeout = 885


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
    FailureDomain = 'zone1'
    Version = 'v1.26.13+vmware.1-fips.1-tkg.3'
    Platform = 'tkgs'


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
    __hostname = 'tmc.home.tanzu.rocks'
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
                    print(f"Status Code issue: {_response.status_code}")
                    return None

        except HTTPError as e:
            print(f'Error code: {e.code}')
        except URLError as e:
            print(f'URL Error: {e.reason}')

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
                    print(f"Status Code issue: {_response.status_code}")
                    return None

        except HTTPError as e:
            print(f'Error code: {e.code}')
        except URLError as e:
            print(f'URL Error: {e.reason}')

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
                    print(f"Status Code issue: {_response.status_code}")
                    return None

        except HTTPError as e:
            print(f'Error code: {e.code}')
        except URLError as e:
            print(f'URL Error: {e.reason}')

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
                    _item = json.loads(_response.text)
                    return _item
                else:
                    print(f"Status Code issue: {_response.status_code}")
                    return None
        except HTTPError as e:
            print(f'Error code: {e.code}')
        except URLError as e:
            print(f'URL Error: {e.reason}')

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
                    print(f"Status Code Issue: {_response.status_code}")
                    return None

        except HTTPError as e:
            print(f'HTTP Error: {e.code} with reason: {e.reason}')
        except URLError as e:
            print(f'URL Error: {e.code} with reason: {e.reason}')

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
                   print(f"Status Code issue: {_response.status_code}")
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
        except HTTPError as e:
            print(f'HTTP Error: {e.code} with reason: {e.reason}')
        except URLError as e:
            print(f'URL Error: {e.code} with reason: {e.reason}')

        return None

    # Get specified Cluster Details
    def getCluster(self, clusterName, provisionerName, managementCluster):
        print(f"Get cluster details")
        _url = f'https://{self.__hostname}/v1alpha1/clusters/?fullName.name={clusterName}&fullName.provisionerName={provisionerName}&fullName.managementClusterName={managementCluster}'
        return self.__get(_url)


    # Get a list of clusters with filter opton
    def getClusterList(self, filter=None):
        if filter is None:
            filter = '*'
        print(f'Get a list of clusters wth filter {filter}')
        _url = f'https://{self.__hostname}/v1alpha1/clusters?searchScope.name={filter}'
        return self.__get(_url)
        

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
        
        if _url is not None:
            
            print('Waiting for cluster provisioning to complete')
            _start = time.time() 
            if (_response := self.__post(_url, _data)) is not None:
                while (time.time() - _start) < timeout:  
                    _response = self.getCluster(cluster.Name, cluster.Provisioner, cluster.ManagementCluster)
                    _status = _response['cluster']['status']['phase']
                    if _status != "READY": # CREATING, ATTACH_COMPLETE
                        time.sleep(15)  # Sleep for 15 seconds before checking again
                    else:
                        print(f'Cluster ready /n{_response}')
                        return _response

                print(f'Cluster provisioning timeout exceed')
                return _response
        else:
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
            return self.__put(_url, _data)
        else:
            return None


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
                                        "version": "3",
                                        "arch": "amd64"
                                    }

                                },
                                "nodePools": [
                                    {
                                        "spec": {
                                            "replicas": cluster.WorkerNodeCount,
                                            "class": "node-pool",
                                            "failureDomain": cluster.FailureDomain,
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
                                    }
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

    # get a list of the clustergroups
    def getClusterGroupList(self):
        print(f'Getting a list of clustergroups')
        _url = f'https://{self.__hostname}/v1alpha1/clustergroups?searchScope.name=*'
        return self.__get(_url)


    # Get a list of provisioners
    def getProvisionerList(self, managementcluster, provisioner=None):
        print(f'Get a list of provsioners for management cluster {managementcluster}')
        if provisioner is None:
            provisioner = '*'
        _url = f'https://{self.__hostname}/v1alpha1/managementclusters/{managementcluster}/provisioners?searchScope.name={provisioner}'
        return self.__get(_url)


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

    outputs = inputs
    op = inputs["__metadata"]["operation"]
    print (f"Running operational request type: {op}")

    _tmc_host = context.getSecret(inputs['tmc_host'])
    _tmc_username = context.getSecret(inputs['tmc_username'])
    _tmc_password = context.getSecret(inputs['tmc_password'])

    _client = TMCClient(hostname=_tmc_host, username=_tmc_username, password=_tmc_password)

    match op:
        case "create":
            outputs['create'] = True
            _cluster = processInputs(inputs)
            if(_response := _client.createCluster(_cluster)) is not None:
                outputs.update(processClusterResponse(inputs, _response))
        case "update":
            outputs['create'] = True
            _cluster = processInputs(inputs)
            if(_response := _client.updateCluster(_cluster)) is not None:
                outputs.update(processClusterResponse(inputs, _response))
        case "read":
            outputs['read'] = True
            if(_response := _client.getCluster(inputs['name'], inputs['provisioner'], inputs['managementcluster'])) is not None:
                outputs.update(processClusterResponse(inputs, _response))
        case "delete":
            outputs['delete'] = True
            _response = _client.deleteCluster(inputs['name'], inputs['provisioner'], inputs['managementcluster'])

    return outputs


# process inputs into platform specific settings
def processInputs(inputs):    
    print(f"Processing inputs")
    _cluster = Cluster()
    _cluster.Name = inputs['name']
    _cluster.Description = inputs['description']
    _cluster.ClusterGroup = inputs['clustergroup']
    _cluster.WorkerNodeCount = inputs['workernodecount']
    _cluster.Platform = inputs['platform']

    if inputs['highavailability']:
        _cluster.ControlPlaneReplicas = 3
    else:
        _cluster.ControlPlaneReplicas = 1

    match (inputs['platform']):
        case 'tkgs':
            print('tkg values processing')
            _cluster.Provisioner = TKGValues.provisioner(inputs['clustergroup'])
            _cluster.Version = TKGValues.release(inputs['version'])            
            _cluster.NodeSize = TKGValues.vmclass(inputs['nodesize'])
            _cluster.ManagementCluster = TKGValues.managementcluster(inputs['controller'])
            _cluster.StorageClass = TKGValues.storageclass(inputs['storagetype'])
        case 'eks':
            print('eks to be done')
        case 'aks':
            print('aks to be done')
    return _cluster


# extracts current cluster data to feed into the abx output variable
def processClusterResponse(inputs, response):
    print('Processing cluster response')
    _status = {}
    match (inputs['platform']):        
        case 'tkgs':
            _status['name'] = response['cluster']['fullName']['name']
            _status['managementcluster'] = response['cluster']['fullName']['managementClusterName']
            _status['description'] = response['cluster']['meta']['description']
            _status['clustergroup'] = response['cluster']['spec']['clusterGroupName']
            _status['controlplanereplicas'] = response['cluster']['spec']['topology']['controlPlane']['replicas']
            _status['workernodecount'] = response['cluster']['spec']['topology']['nodePools'][0]['spec']['replicas']
            _status['tkr'] = response['cluster']['spec']['topology']['version'] # platform specific value so not in cluster schema
            _status['provisioner'] = response['cluster']['fullName']['provisionerName'] # platform specific value so not in cluster schema
            for _entry in response['cluster']['spec']['topology']['variables']:
                match _entry['name']:
                    case "storageClass":
                        _status['storageclass'] = _entry['value'] # platform specific value so not in cluster schema
                    case "vmClass":
                        _status['vmclass'] = _entry['value'] # platform specific value so not in cluster schema
            _status['status'] = response['cluster']['status']['phase']
        case 'eks':
            print('eks to be done')
        case 'aks':
            print('aks to be done')

    return _status


# Handler for vRO Actions
def handler(context, inputs):
    print('Execurint vRO Action')

    _action = inputs["action"]
    print (f"Running orchestrator action: {_action}")

    _outputs = []

    _host = os.environ.get("host") or 'tmc.home.tanzu.rocks'
    _username = os.environ.get("username") or 'david'
    _password = os.environ.get("password") or 'B3ach8um!'

    _platform = inputs.get('platform') or 'tkgs'
    _managementcluster = inputs.get('managementcluster') or 'supervisor1'
    _provisioner = inputs.get('provisioner') or '*'

    _client = TMCClient(hostname=_host, username=_username, password=_password)

    match _action:
        case "form-getclustergrouplist":
            if(_response := _client.getClusterGroupList()) is not None:
                _outputs = [c["fullName"]["name"] for c in _response["clusterGroups"]]
        case "form-getclusterlist":
            if(_response := _client.getClusterList()) is not None:
                _outputs = [c["fullName"]["name"] for c in _response["clusters"]]
        case "form-getprovisionerlist":
            if (_response := _client.getProvisionerList(_managementcluster)) is not None:        
                _outputs = [c["fullName"]["name"] for c in _response["provisioners"]]
        case "form-getversionlist":
            _outputs =  _client.getKubernetesReleases(_platform, _managementcluster, _provisioner)
        case "form-getnodesizelist":
            _outputs = _client.getVirtualMachineClasses(_managementcluster, _provisioner)
        case "form-storageclasslist":
            _outputs = _client.getStorageClasses(_platform, _managementcluster, _provisioner)

    return _outputs
