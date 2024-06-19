import requests, json, yaml
import base64
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

    _sv_url = context.getSecret(inputs['k8s-sv1-url'])
    _sv_token = context.getSecret(inputs['k8s-sv1-token'])

    _client = TKGSClient(supervisor_url=_sv_url, supervisor_token=_sv_token)

    match op:
        case "kubeconfig-admin":
            outputs['kubeconfig-admin'] = True
            _clustername = inputs['name']
            _provisioner = inputs['provisioner']
            if(_response := _client.getClusterKubeconfig(clustername=_clustername, provisioner=_provisioner)) is not None:
                outputs['kubeconfig'] = _response.kubeconfig



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

        _url = f"{kubeconfig.api_url}/api"
        try:
            _response = requests.get(_url, cert=('tls.crt', 'tls.key'), verify='ca.crt')        
            if _response.status_code == 200:
                return True
            else:
                return False
        except:
            return False


    # Get the kubconfig for the specified cluster
    def getClusterKubeconfig(self, clustername, provisioner):
        print(f'Get cluster {clustername} kubeconfig')
        
        _url = f"{self.__supervisor_url}/api/v1/namespaces/{provisioner}/secrets/{clustername}-kubeconfig"
        if (_response := self.__get(_url)) is not None:
            _data = base64.b64decode(_response['data']['value']).decode("utf-8")
            _kubeconf = Kubeconfig(_data)
            if self.checkClusterAccess(_kubeconf):
                print('Cluster access confirmed')

            return _kubeconf
        else:
            return None


class Kubeconfig:
    kubeconfig = None
    api_url = None
    ca_data = None
    user_cert = None
    user_key = None

    # Class initialising method
    def __init__(self, kubeconfig):
        self.kubeconfig = kubeconfig
        _kube = yaml.safe_load(kubeconfig)
        self.api_url = _kube['clusters'][0]['cluster']['server']
        self.ca_data = base64.b64decode(_kube['clusters'][0]['cluster']['certificate-authority-data']).decode("utf-8")
        self.user_cert = base64.b64decode(_kube['users'][0]['user']['client-certificate-data']).decode("utf-8")
        self.user_key = base64.b64decode(_kube['users'][0]['user']['client-key-data']).decode("utf-8")

        f = open("tls.crt", "w")
        f.write(self.user_cert)
        f.close()
        f = open("tls.key", "w")
        f.write(self.user_key)
        f.close()
        f = open("ca.crt", "w")
        f.write(self.ca_data)
        f.close()

