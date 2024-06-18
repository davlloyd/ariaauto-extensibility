import json, time, requests
from urllib.error import URLError, HTTPError

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



    # General HTTP Get query
    def __get(self, url, headers=None):
        print(f"Executing HTTP Get")
        try:
            if headers is None:
                headers = {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                }
            
            with requests.get(url, headers=headers, auth=('', self.__access_token)) as _response:
                print(f"Status Code: {_response.status_code}")
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
        try:
            _body = json.dumps(data).encode('utf-8')
            _headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }

            with requests.post(url, headers=_headers, data=_body, auth=('', self.__access_token)) as _response:
                print(f"Status Code: {_response.status_code}")
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
        try:
            _headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }

            with requests.delete(url, headers=_headers, auth=('', self.__access_token)) as _response:
                print(f"Status Code: {_response.status_code}")
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
            print(f'URL Error: {e.reason}')

        return None

    # Get tokens for site access
    def obtainToken(self):
        print(f"Obtain access tokens")

        return None


    # Refresh tokens, needs to be done prior to each call as access token has short expiry
    def refreshToken(self):
        print(f"Refresh access token")
        return None


    def createCluster(self, cluster):
        _time = time.time()
        _data = {
                    "tanzuKubernetesCluster": {
                        "type": {
                            "kind": "Cluster",
                            "version": "v1alpha1",
                            "package": "vmware.tanzu.manage.v1alpha1.cluster"
                        },
                        "fullName": {
                            "name": {cluster.Name},
                            "managementClusterName": {cluster.ManagementCluster},
                            "provisionerName": {cluster.Provisioner}
                        },
                        "meta": {
                            "description": "Aria created cluster with TMC",
                            "labels": {
                                "timeCreated": {_time}
                            }
                        },
                        "spec": {
                            "clusterGroupName": {cluster.ClusterGroup},
                            "tmcManaged": true,
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
                                            {cluster.StorageClass}
                                        ],
                                        "defaultClass": {cluster.StorageClass}
                                    }
                                }
                            },
                            "topology": {
                                "version": {cluster.Version},
                                "clusterClass": "tanzukubernetescluster",
                                "controlPlane": {
                                    "class": {cluster.VMClass},
                                    "storageClass": {cluster.StorageClass},
                                    "replicas": {cluster.ControlPlaneReplicas},
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
                                            "failureDomain": {cluster.FailureDomain},
                                            "nodeLabels": {
                                                "myLabel": "myValue"
                                            },
                                            "cloudLabels": {
                                                "myCloudLabel": "mvCloudValue"
                                            },
                                            "tkgServiceVsphere": {
                                                "class": {cluster.VMClass},
                                                "storageClass": {cluster.StorageClass},
                                                "failureDomain": {cluster.FailureDomain}
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
                                        "value": {cluster.StorageClass}
                                    },
                                    {
                                        "name": "vmClass",
                                        "value": {cluster.VMClass}
                                    },
                                    {
                                        "name": "storageClass",
                                        "value": {cluster.StorageClass}
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



class Cluster:
    Name = None
    Provisioner = None
    ClusterGroup = None
    ManagementCluster = 'supervisor1'
    StorageClass = 'general-usage'
    ControlPlaneReplicas = 1
    WorkerNodeCount = 2
    VMClass = 'best-effort-medium'
    FailureDomain = 'zone1'
    Version = 'v1.26.13+vmware.1-fips.1-tkg.3'


    def __init__(self, name, provisioner, clusterGroup):
        self.Name = name
        self.Provisioner = provisioner
        self.ClusterGroup = clusterGroup


