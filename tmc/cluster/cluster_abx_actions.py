"""
Service:        Tanzu Mission Controller cluster actions controller
Version:        1.4.1
Description:    Controller for the day 2 actions for the cluster 
Changelog:      
        1.1.0   - Updated to use kubenernetes module
        1.2.0   - added ability to create serviceaccounts and clusterrolebindings
        1.3.0   - Extended to support Orchestrator actions
        1.4.0   - Restructured service account and secret control
                
"""

import requests, json, yaml, base64, os, time
from kubernetes import config, client
from kubernetes.client.rest import ApiException
from urllib.error import URLError, HTTPError


# Kubeconfig controller class
class Kubeconfig:
    kubeconfig = None
    kubeconfig_b64 = None
    kubeconfig_dict = None
    api_url = None
    ca_data = None
    user_cert = None
    user_key = None

    # Class initialising method
    def __init__(self, kubeconfig_b64):
        self.kubeconfig_b64 = kubeconfig_b64
        self.kubeconfig = base64.b64decode(kubeconfig_b64)  #.decode("utf-8")kubeconfig
        _kube = yaml.safe_load(self.kubeconfig)
        self.kubeconfig_dict = _kube 
        self.api_url = _kube['clusters'][0]['cluster']['server']
        self.ca_data = base64.b64decode(_kube['clusters'][0]['cluster']['certificate-authority-data']).decode("utf-8")
        self.user_cert = base64.b64decode(_kube['users'][0]['user']['client-certificate-data']).decode("utf-8")
        self.user_key = base64.b64decode(_kube['users'][0]['user']['client-key-data']).decode("utf-8")


# Main client for interacting with TKGs Services via Supervisor 
class TKGSClient:
    __supervisor_url ='https://192.168.4.200:6443'
    __supervisor_token = 'eyJhbGciOiJSUzI1NiIsImtpZCI6InF1VlFVSmpmMjRUZm0zdThaUmh3RndFY2o2cFpQVU0wOVA1VGpkaFNrUncifQ.eyJpc3MiOiJrdWJlcm5ldGVzL3NlcnZpY2VhY2NvdW50Iiwia3ViZXJuZXRlcy5pby9zZXJ2aWNlYWNjb3VudC9uYW1lc3BhY2UiOiJrdWJlLXN5c3RlbSIsImt1YmVybmV0ZXMuaW8vc2VydmljZWFjY291bnQvc2VjcmV0Lm5hbWUiOiJhZG1pbi11c2VyLXNlY3JldCIsImt1YmVybmV0ZXMuaW8vc2VydmljZWFjY291bnQvc2VydmljZS1hY2NvdW50Lm5hbWUiOiJhZG1pbi11c2VyIiwia3ViZXJuZXRlcy5pby9zZXJ2aWNlYWNjb3VudC9zZXJ2aWNlLWFjY291bnQudWlkIjoiMmExMjVlM2UtN2IwYi00ZDRhLTk1OTUtNTZhYmZiMWUzMmE2Iiwic3ViIjoic3lzdGVtOnNlcnZpY2VhY2NvdW50Omt1YmUtc3lzdGVtOmFkbWluLXVzZXIifQ.sEAAhfII63rv_amPDQxKmbv3ZYa1nREA_3Z_s9_je7WNsM61-8_If7Bfo6839kWA6gHiV5m_soWBDJXyxa5kTEDjgkIu0QCiooSGbEpR0ZqGTjGVttijnyggM8-hok-IAYaahIV4rzW6XI9EAvswM5NSCPQN-SU8DlLPG3-bt0gWJn69_fMtBdl4cuAdaZzVe0gC4tc3G1m7UklRUTtwEijpswZtMgT1wzmxPbcChOoEIHljbvm5uODILD49TTZT62vdIBXuMl51HbN7EQif9sBEF302w72iVEJFPLUdICDP_9pizR3lUMV2eGE_D9idrbd7aVblvdooV_vrPnOk0Q'

    # Class initialising method
    def __init__(self, supervisor_url=None, supervisor_token=None):
        if supervisor_url is not None:
            self.__supervisor_url=supervisor_url
        if supervisor_token is not None:
            self.__supervisor_token=supervisor_token

    
    # General HTTP Get query
    def __get(self, url):
        print(f"Executing HTTP Get")

        try:
            _headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'Authorization': f'Bearer {self.__supervisor_token}'
            }   
            
            with requests.get(url, headers=_headers, verify=False) as _response:
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


    # Create coreV1 client
    def __get_kubernetes_corev1client(bearer_token, api_server_endpoint):
        try:
            configuration = client.Configuration()
            configuration.host = api_server_endpoint
            configuration.verify_ssl = False
            configuration.api_key = {"authorization": "Bearer " + bearer_token}
            client.Configuration.set_default(configuration)
            client_api = client.CoreV1Api()
            return client_api
        except Exception as e:
            print("Error getting kubernetes client \n{}".format(e))
            return None


    # Check if the API is accessible
    def accessCheck(self):
        print(f'Access check')

        _url = f"{self.__supervisor_url}/api"
        if (_response := self.__get(_url)) is not None:
            print(f"Check result: {_response}")
            return True

        return False


    # client certificate authentication
    def checkClusterAccess(self, kubeconfig):
        print(f'Access check with kubeconfig')

        try:
            config.load_kube_config_from_dict(kubeconfig.kubeconfig_dict)
            _client = client.AppsV1Api()
            if(_response := _client.list_namespaced_deployment('kube-system')) is not None:
                return True
            else:
                return False
        except:
            return False

    # create service account and return associated secret
    def createServiceAccount(self, kubeconfig, namespace='kube-system', accountname='ado-admin'):
        print(f'Create service account and associated secret')

        config.load_kube_config_from_dict(kubeconfig.kubeconfig_dict)
        _client = client.CoreV1Api()
        _body = {'metadata': {'name': accountname} }
        _pretty = 'true'

        try:
            print(f'Create ServiceAccount')
            if(_response := _client.create_namespaced_service_account(namespace, _body, pretty=_pretty)) is not None:
                print(f"ServiceAccount {accountname} created with response: {_response}")
                return _response
        except ApiException as e:
            print(f"API Exception when creatung service account: {e}\n")
            if e.reason == "Conflict" or e.reason == "AlreadyExists":
                print("Service already account already exists")
                return {"status": "AlreadyPresent"}
        except Exception as e:
            print(f"Exception when creating service account: {e}\n")

        _client.api_client.close()
        return None


    # Create a secret
    def createServiceAccountTokenSecret(self, kubeconfig, namespace='kube-system', accountname='ado-admin'):
        print(f'Create ServiceAccount Token Secret')

        config.load_kube_config_from_dict(kubeconfig.kubeconfig_dict)
        _client = client.CoreV1Api()

        _body = client.V1Secret(
            api_version="v1",
            kind="Secret",
            metadata=client.V1ObjectMeta(name=accountname, annotations={'kubernetes.io/service-account.name': accountname}),
            type="kubernetes.io/service-account-token"
        )                

        try:
            print(f'Create ServiceAccount Token Secret')
            _response = _client.create_namespaced_secret(namespace=namespace, body=_body)
            print(f'Secret data returned: {_response}')
            return _response
        except ApiException as e:
            print(f"API Exception when creating service account token: {e}\n")
            if e.reason == "Conflict" or e.reason == "AlreadyExists":
                print(f"AService account token already exists")
                return {"status": "AlreadyPresent"}
        except Exception as e:
            print(f"Exception when creating service account: {e}\n")

        _client.api_client.close()
        return None


    # Read the data from the listed secret
    def readSecretData(self, kubeconfig, namespace, secretname):
        print("Retrieving secret data")

        config.load_kube_config_from_dict(kubeconfig.kubeconfig_dict)
        _client = client.CoreV1Api()

        try:
            if (_secret := _client.read_namespaced_secret(name=secretname, namespace=namespace)) is not None:
                print("Secret retrieved")
                return _secret.data
        except ApiException as e:
            print(f"API Exception when reading xecret data: {e}\n")

        _client.api_client.close()
        return None


    # Create clusterrolebinding
    def createClusterRoleBinding(self, kubeconfig, subject, subjectnamespace, role):
        print(f'Create clusterrolebinding for subject {subject} for role {role}')

        _name = f'{subject}:{role}'
        config.load_kube_config_from_dict(kubeconfig.kubeconfig_dict)
        _client = client.RbacAuthorizationV1Api()
        _body = client.V1ClusterRoleBinding(
            metadata=client.V1ObjectMeta(name=_name),
            subjects=[client.RbacV1Subject(kind='ServiceAccount', name=subject, namespace=subjectnamespace)],
            role_ref=client.V1RoleRef(api_group='rbac.authorization.k8s.io', kind='ClusterRole', name=role))
        try:
            print(f'Create Clusteradmin role binding')
            if(_response := _client.create_cluster_role_binding(body=_body)) is not None:
                return _response
            else:
                if _client.read_cluster_role_binding(name=_name) is None:
                    return {"status":"AlreadyPresent", "comment":"Binding already exists"}
        except ApiException as e:
            print(f'Clusteradmin role binding creation exception caught {e}')
            if e.reason == "Conflict" or e.reason == "AlreadyExists":
                print(f"Cluster role already exists")
                return {"status": "AlreadyPresent"}
        except Exception as e:
            print("Exception when calling create_cluster_role_binding: %s\n" % e)

        _client.api_client.close()
        return None


    # Get the kubconfig for the specified cluster
    def getClusterKubeconfig(self, clustername, provisioner):
        print(f'Get cluster {clustername} kubeconfig')
        
        _url = f"{self.__supervisor_url}/api/v1/namespaces/{provisioner}/secrets/{clustername}-kubeconfig"
        if (_response := self.__get(_url)) is not None:
            print(f'Kubeconfig retrieved')
            _data = _response['data']['value']
            _kubeconf = Kubeconfig(_data)
            if self.checkClusterAccess(_kubeconf):
                print('Cluster access confirmed')

            return _kubeconf
        else:
            return None


# Get cluster access details
def getSecurityContexts(client, inputs):
    _creds = {}
    _clustername = inputs['name']
    print(f'Requesting kubeconfig admin for cluster {_clustername}')
    _provisioner = inputs['provisioner']
    _accountname = 'token-admin'
    _namespace = 'kube-system'
    _creds['cluster'] = _clustername
    _creds["provisioner"] = _provisioner
    _creds['serviceaccountnamespace'] = _namespace
    _creds['serviceaccountname'] = _accountname

    print(f'Calling Kubeconfig retriever function')
    if(_kubeconfig := client.getClusterKubeconfig(clustername=_clustername, provisioner=_provisioner)) is not None:
        _creds['kubeconfig'] = _kubeconfig.kubeconfig_b64
        _creds['apiurl'] = _kubeconfig.api_url

        print(f'Calling service account creation function')
        if (_response := client.createServiceAccount(_kubeconfig, _namespace, _accountname)) is  None:
            print(f'Service account creation returned nothing')
        else:
            print(f"Service account {_accountname} created")

        print(f'Calling service account token secret creation')
        if (_response := client.createServiceAccountTokenSecret(_kubeconfig, _namespace, _accountname)) is  None:
            print(f'Service account token creation returned nothing')
        else:
            print(f"Service account token {_accountname} created with the data {_response}")


        print(f'Reading service account token secret')
        if (_response := client.readSecretData(_kubeconfig, _namespace, _accountname)) is  None:
            print(f'Could not read service account token details')
        else:
            print(f"Service account token {_accountname} read with the data {_response}")
            _creds['serviceaccounttoken'] = _response['token']
            _creds['serviceaccountcertificate'] = _response['ca.crt']

        print(f'Creating service account Cluster rolebindung for clusteradmin')
        if (_response := client.createClusterRoleBinding(_kubeconfig, _accountname, _namespace, 'cluster-admin')) is  None:
            print(f'Could not create the cluster role')
        else:
            print(f"Cluster role created created with the response: {_response}")

        return _creds
    else:
        print(f"Unable to retrieve cluster credentials")
        return None



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
    print(f'request metadata: {inputs["__metadata"]}')
    op = inputs["__metadata"]["operation"]

    _sv_url = context.getSecret(inputs['k8s-sv1-url'])
    _sv_token = context.getSecret(inputs['k8s-sv1-token'])

    _client = TKGSClient(supervisor_url=_sv_url, supervisor_token=_sv_token)

    match op:
        case "kubeconfig-admin":
            outputs = getSecurityContexts(_client, inputs)            

    return outputs


# Main entry point for orchestrator actions
def handler(context, inputs):
    print('Executing vRO Action')

    _action = inputs["action"]
    print (f"Running orchestrator action: {_action}")

    outputs = []
    _sv_url = os.getenv('supervisorUrl')
    _sv_token = os.getenv('supervisorToken')

    _client = TKGSClient(supervisor_url=_sv_url, supervisor_token=_sv_token)

    match _action:
        case "kubeconfig-admin":
            outputs = getSecurityContexts(_client, inputs)

    print(f'Response complete')
    return json.dumps(outputs)

