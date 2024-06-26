import json, time, requests
from datetime import datetime
from urllib.error import URLError, HTTPError


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

    _tmc_host = context.getSecret(inputs['tmc_host'])
    _tmc_username = context.getSecret(inputs['tmc_username'])
    _tmc_password = context.getSecret(inputs['tmc_password'])

    _client = TMCClient(hostname=_tmc_host, username=_tmc_username, password=_tmc_password)

    match op:
        case "create":
            outputs['create'] = True
            _cluster = Cluster()
            _cluster.Name = inputs['name']
            _cluster.Description = inputs['description']
            _cluster.Provisioner = inputs['provisioner']
            _cluster.ClusterGroup = inputs['clustergroup']
            _cluster.ManagementCluster = inputs['managementcluster']
            _cluster.StorageClass = inputs['storageclass']
            _cluster.Version = inputs['version']
            _cluster.VMClass = inputs['vmclass']
            _cluster.ControlPlaneReplicas = inputs['controlplanereplicas']
            _cluster.WorkerNodeCount = inputs['workernodecount']
            if(_response := _client.createCluster(_cluster)) is not None:
                outputs.update(processClusterResponse(_response))
        case "update":
            # update logic to be added here
            print("update")
        case "read":
            outputs['read'] = True
            if(_response := _client.getCluster(inputs['name'], inputs['provisioner'], inputs['managementcluster'])) is not None:
                outputs.update(processClusterResponse(_response))
        case "delete":
            outputs['delete'] = True
            _response = _client.deleteCluster(inputs['name'], inputs['provisioner'], inputs['managementcluster'])

    return outputs


# extracts current cluster data to feed into the abx output variable
def processClusterResponse(response):
    _status = {}
    _status['name'] = response['tanzuKubernetesCluster']['fullName']['name']
    _status['provisioner'] = response['tanzuKubernetesCluster']['fullName']['provisionerName']
    _status['managementcluster'] = response['tanzuKubernetesCluster']['fullName']['managementClusterName']
    _status['description'] = response['tanzuKubernetesCluster']['meta']['description']
    _status['clustergroup'] = response['tanzuKubernetesCluster']['spec']['clusterGroupName']
    _status['version'] = response['tanzuKubernetesCluster']['spec']['topology']['version']
    _status['controlplanereplicas'] = response['tanzuKubernetesCluster']['spec']['topology']['controlPlane']['replicas']
    _status['workernodecount'] = response['tanzuKubernetesCluster']['spec']['topology']['nodePools'][0]['spec']['replicas']
    for _entry in response['tanzuKubernetesCluster']['spec']['topology']['variables']:
        match _entry['name']:
            case "storageClass":
                _status['storageclass'] = _entry['value']
            case "vmClass":
                _status['vmclass'] = _entry['value']

    _status['phase'] = response['tanzuKubernetesCluster']['status']['phase']
    #_status['health'] = response['tanzuKubernetesCluster']['status']['health']
    _status['health'] = 'unset'

    return _status



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
        print(f"Executing HTTP Get")
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
                print(f"Status: {_response.status_code}")
                if _response.status_code == 200:
                    _item = json.loads(_response.content)
                    return _item
                else:
                    return None

        except HTTPError as e:
            print(f'Error code: {e.code}')
        except URLError as e:
            print(f'URL Error: {e.reason}')

        return None
    
    
    # general HTTP Post. Requires data payload in JSON format
    def __post(self, url, data):
        print(f"Executing HTTP Post")
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
                print(f"Status: {_response.status_code}")
                if _response.status_code == 200 or _response.status_code == 201 or _response.status_code == 202:
                    _item = json.loads(_response.text)
                    return _item
                else:
                    return None

        except HTTPError as e:
            print(f'Error code: {e.code}')
        except URLError as e:
            print(f'URL Error: {e.reason}')

        return None


    # general HTTP delete routine
    def __delete(self, url):
        print(f"Executing HTTP Delete")
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
                print(f"Status: {_response.status_code}")
                if _response.status_code == 200 or _response.status_code == 201 or _response.status_code == 202:
                    _item = json.loads(_response.text)
                    return _item
                else:
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
                print(f"Status Code: {_response.status_code}")
                if _response.status_code == 302:
                    _location = _response.headers['location'].split('=')[1]
                    self.__auth_code = _location.split('&')[0]
                    return self.__auth_code
                else:
                    return None

        except HTTPError as e:
            print(f'Error code: {e.code}')
        except URLError as e:
            print(f'URL Error: client_id{e.reason}')

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
                print(f"Status Code: {_response.status_code}")
                if _response.status_code == 200:
                    _values = json.loads(_response.text)
                    self.__access_token = _values['access_token']
                    self.__refresh_token = _values['refresh_token']
                    self.__id_token = _values['id_token']
        except HTTPError as e:
            print(f'Error code: {e.code}')
        except URLError as e:
            print(f'URL Error: client_id{e.reason}')

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
            print(f'Error code: {e.code}')
        except URLError as e:
            print(f'URL Error: client_id{e.reason}')

        return None

    # Get specified Cluster Details
    def getCluster(self, clusterName, provisionerName, managementCluster):
        print(f"Get cluster details")
        _url = f'https://{self.__hostname}/v1alpha1/clusters/?fullName.name={clusterName}&fullName.provisionerName={provisionerName}&fullName.managementClusterName={managementCluster}'
        return self.__get(_url)


    # Create cluster with TMC
    def createCluster(self, cluster):
        print(f"Create new cluster")
        _url = f'https://{self.__hostname}/v1alpha1/managementclusters/{cluster.ManagementCluster}/provisioners/{cluster.Provisioner}/tanzukubernetesclusters'
        _data = {
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
                                    "class": cluster.VMClass,
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
                                                "class": cluster.VMClass,
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
                                        "value": cluster.VMClass
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
        
        return self.__post(_url, _data)


    # Delete specified Cluster 
    def deleteCluster(self, clusterName, provisionerName, managementCluster):
        print(f"Get cluster details")
        _url = f'https://{self.__hostname}/v1alpha1/managementclusters/{managementCluster}/provisioners/{provisionerName}/tanzukubernetesclusters/{clusterName}'

        return self.__delete(_url)




class Cluster:
    Name = None
    Description = "Cluster created and managed by Aria"
    Provisioner = None
    ClusterGroup = None
    ManagementCluster = 'supervisor1'
    StorageClass = 'general-usage'
    ControlPlaneReplicas = 1
    WorkerNodeCount = 2
    VMClass = 'best-effort-medium'
    FailureDomain = 'zone1'
    Version = 'v1.26.13+vmware.1-fips.1-tkg.3'


    def __init__(self, name=None, provisioner=None, clusterGroup=None):
        self.Name = name
        self.Provisioner = provisioner
        self.ClusterGroup = clusterGroup


