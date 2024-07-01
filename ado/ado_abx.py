"""
Service:        Azure DevOps Aria ABX Extension Script
Version:        1.4.0
Description:    Through ABX custom objects this script allows for the operational control
                of Azure DevOps objects including
                - projects
                - environments
                - service endpoints
                - repositories
                The purpose of this is to allow ADO to be integrated with systems also managed by Aria
                such as allowing a Kubernetes Cluster to ba assigned as a an endpoint into a ADO project
Changelog:      
        1.1.0   - removed authorization from the Service Endpoint Class
        1.2.0   - Added Orchestrator action support
        1.3.0   - Added supports for environment management with ABX
        1.4.0   - Creating orchestrator actions to manage ADO state
                
"""

import json, time, requests, os
from urllib.error import URLError, HTTPError


"""
Main control class for interacting with Azure DevOps platform
provides project control and associated attributes including
- Environments
- Repositories
- Service Endpoints
- Kubernetes services
"""
class ADOClient:
    __access_token = None
    __organisation_url = None
    __api_version = "7.1-preview"
    __timeout = 900
 
    def __init__(self, organisation_url=None, access_token=None):
        if organisation_url != None:
            self.__organisation_url = organisation_url
        if access_token != None:
            self.__access_token = access_token
        self.__configureclient()

    # Configure the web client to access ADO
    def __configureclient(self) -> json:
        print(f"Intilising Client")


    # Standard set of headers
    def __headers(self):
        return {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }

    # General HTTP Get query
    def __get(self, url):
        print(f"Executing HTTP Get")
        try:
            _headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
            
            with requests.get(url, headers=_headers, auth=('', self.__access_token)) as _response:
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


    # get a list of projects
    def getProjectList(self) -> json:
        print(f"Getting project list")
        _url = f"{self.__organisation_url}/_apis/projects?api-version={self.__api_version}"
        if (_projects := self.__get(_url)) is not None:
            _projects = _projects['value']
        return _projects


    # Project Name list dictionary type
    def getProjectList_dict(self):        
        if (_projects := self.getProjectList()) is not None:
            return [c["name"] for c in _projects]


    # Search for a project by either name of id
    def getProject(self, projectId) -> json:
        print(f"Getting project {projectId} details")
        _url = f"{self.__organisation_url}/_apis/projects/{projectId}?includeCapabilities=true&api-version={self.__api_version}"
        return self.__get(_url)
        

    # Create a project in Azure Devops
    def createProject(self, project) -> json:
        print(f"Creating project {project.Name}")
        _url = f"{self.__organisation_url}/_apis/projects?api-version={self.__api_version}"        
        _project_data = {
            "name": project.Name,
            "description": project.Description,
            "visibility": "private",
            "capabilities": {
                "versioncontrol": {
                "sourceControlType": project.SourceControlType
                },
                "processTemplate": {
                "templateTypeId": project.ProcessTemplateId
                }
            }
        }

        _start = time.time()
        if (_response := self.__post(_url, _project_data)) is not None:
            print(f"Track task request {_response['id']}")
            while (time.time() - _start) < self.__timeout:  
                if _response['status'] == "succeeded":
                    return self.getProject(project.Name)
                elif _response['status'] == "failed" or _response['status'] == "cancelled":
                    return None
                else:
                    time.sleep(10)  # Sleep for 10 seconds before checking again
                    _response = self.__get(_response['url'])
                    print(_response)

    
    # Delete a project
    def deleteProject(self, projectId):
        if not isinstance(projectId, int):
            _response = self.getProject(projectId)
            if _response is None:
                return None
            else:
                _id = _response['id']
        else:
            _id = projectId
        _url = f"{self.__organisation_url}/_apis/projects/{_id}?api-version={self.__api_version}"

        _start = time.time()
        if (_response := self.__delete(_url)) is not None:
            print(f"Track task request {_response['id']}")
            while (time.time() - _start) < self.__timeout:  
                if _response['status'] == "succeeded":
                    return True
                elif _response['status'] == "failed" or _response['status'] == "cancelled":
                    return False
                else:
                    time.sleep(10)  # Sleep for 10 seconds before checking again
                    _response = self.__get(_response['url'])
                    print(_response)

        return False


    # Get a lit of Git Repos for the specified project
    def getRepositoryList(self, projectId) -> json:
        print(f"Get project {projectId} list of Git Repos")
        _url = f"{self.__organisation_url}/{projectId}/_apis/git/repositories?api-version={self.__api_version}"        
        if (_repos := self.__get(_url)) is not None:
            _repos = _repos['value']
        return _repos


    # Get Repo details
    def getRepository(self, projectId, repoid) -> json:
        print(f"Get Repo {repoid} from project {projectId} details")
        _url = f"{self.__organisation_url}/{projectId}/_apis/git/repositories/{repoid}?api-version={self.__api_version}"        
        return self.__get(_url)


    # Create a git repo
    def createRepository(self, repo) -> json:
        print(f"Creating git repo {repo.Name} in project {repo.ProjectId}")
        _url = f"{self.__organisation_url}/{repo.ProjectId}/_apis/git/repositories?api-version={self.__api_version}"        
        _data = {
            "name": repo.Name,
            "project": repo.ProjectId
        }
        # successful post returns new repo object so just returning repsonse direct
        return self.__post(_url, _data)
    
    # Delete a git repo
    def deleteRepository(self):
        return None


    # Get list of environments associated with project
    def getEnvironmentList(self, projectId) -> json:
        print(f"Get list of environments from project {projectId} details")
        _url = f"{self.__organisation_url}/{projectId}/_apis/pipelines/environments?api-version={self.__api_version}"        
        if (_response := self.__get(_url)) is not None:
            _response = _response['value']
        return _response
 

    # Get sepcoified environment details
    # requires project name or id and envirnment id
    def getEnvironment(self, projectId, environmentId) -> json:
        print(f"Get environment {environmentId} from project {projectId} details")
        if not isinstance(environmentId, int):
            _url = f"{self.__organisation_url}/{projectId}/_apis/pipelines/environments?name={environmentId}&expands=resourceReferences&api-version={self.__api_version}"
            if (_response := self.__get(_url)) is not None:
                environmentId = _response['value'][0]['id'] 
            else:
                return None

        _url = f"{self.__organisation_url}/{projectId}/_apis/pipelines/environments/{environmentId}?expands=resourceReferences&api-version={self.__api_version}"
        return self.__get(_url)


    # Create an environment in a project
    def createEnvironment(self, env) -> json:
        print(f"Creating environment {env.Name} in project {env.ProjectId}")
        _url = f"{self.__organisation_url}/{env.ProjectId}/_apis/pipelines/environments?api-version={self.__api_version}"        
        _data = {
            "name": env.Name,
            "description": env.Description
        }
        return self.__post(_url, _data)

    # Delete environment
    def deleteEnvironment(self, projectid, environmentid):
        print(f"Deleting environment {environmentid} in project {projectid}")
        if not isinstance(environmentid, int):
            _url = f"{self.__organisation_url}/{projectid}/_apis/pipelines/environments?name={environmentId}&expands=resourceReferences&api-version={self.__api_version}"
            if (_response := self.__get(_url)) is not None:
                environmentId = _response['value'][0]['id'] 
            else:
                return None
        _url = f"{self.__organisation_url}/{projectid}/_apis/pipelines/environments/{environmentid}?api-version={self.__api_version}"        

        return self.__delete(_url)


    # Get list of an environments resources
    def getResourceList(self, projectId, environmentId):
        print(f"Get list of resources from project {projectId} in environment {environmentId}")
        _environment = self.getEnvironment(projectId, environmentId)
        _resources = _environment['resources']

        return _resources


    # get a list of  a projects service endpoints
    def getServiceEndpointList(self, projectId):
        print(f"Get list of service endpoints for project {projectId}")
        _url = f"{self.__organisation_url}/{projectId}/_apis/serviceendpoint/endpoints?api-version={self.__api_version}"        
        if (_response := self.__get(_url)) is not None:
            _response = _response['value']
        return _response


    # Add a new service endpoint
    def createServiceEndpoint(self, endpoint):
        print(f"Creating  endpoint in project {endpoint.ProjectId}")

        if(_project := self.getProject(endpoint.ProjectId)) is not None:
            _url = f"{self.__organisation_url}/_apis/serviceendpoint/endpoints?api-version={self.__api_version}"        

            _data = {
                "data":{
                    "authorizationType": "ServiceAccount",
                    "acceptUntrustedCerts": True                    
                },
                "name": endpoint.Name,
                "type": endpoint.Type,
                "url": endpoint.Url,
                "authorization": {
                    "parameters": {
                        "apiToken": endpoint.ApiToken,
                        "serviceAccountCertificate": endpoint.Certificate,
                        "isCreatedFromSecretYaml": True
                    },
                    "scheme": "Token"
                },
                "serviceEndpointProjectReferences": [
                    {
                    "projectReference": {
                        "id": _project['id'],
                        "name": _project['name']
                    },
                    "name": endpoint.Name
                    }
                ]
            }
            return self.__post(_url, _data)
        else:
            return None

    # Delete the Service Endpoint
    def deleteServiceEndpoint(self):
        return None

    # Get the kubernetes resource details
    def getKubernetesResource(self, projectId, environmentId, resourceId):
        print(f"Get resource {resourceId} details from environment {environmentId} in project {projectId}")
        if not isinstance(resourceId, int):
            if(_environment := self.getEnvironment(projectId, environmentId)) is not None:
                environmentId = _environment['id']
                for _resource in _environment['resources']:
                    if _resource['name'].upper() == resourceId.upper():
                        resourceId = _resource['id']
                        break
            else:
                return None
            
        _url = f"{self.__organisation_url}/{projectId}/_apis/pipelines/environments/{environmentId}/providers/kubernetes/{resourceId}?api-version={self.__api_version}"        
        if (_response := self.__get(_url)) is None:
            _response = _response['value']
        return _response


    # Add a new Kubernetes endpoint resource
    def createKubernetesResource(self, k8sResource):
        print(f"Creating kubernetes endpoint in environment {k8sResource.EnvironmentId} in project {k8sResource.ProjectId}")
        if not isinstance(k8sResource.EnvironmentId, int):
            if(_environment := self.getEnvironment(k8sResource.ProjectId, k8sResource.EnvironmentId)) is not None:
                environmentId = _environment['id']
            else:
                return None
        else:
            environmentId = k8sResource.EnvironmentId
        _url = f"{self.__organisation_url}/{k8sResource.ProjectId}/_apis/pipelines/environments/{environmentId}/providers/kubernetes?api-version={self.__api_version}"        
        _data = {
            "name": k8sResource.Name,
            "clusterName": k8sResource.ClusterName,
            "namespace": k8sResource.Namespace,
            "serviceEndpointId": k8sResource.ServiceEndpointId
        }
        return self.__post(_url, _data)

    # Delete the Kubernetes resource
    def deleteKubernetesResource(self):
        return None

class Project:
    Id = None
    Name = None
    Description = None
    State = None
    Visibility = "private"
    ProcessTemplateId = "6b724908-ef14-45cf-84f8-768b5384da45"
    SourceControlType = "Git"

    def __init__(self, id=None, name=None, description=None, state=None, visibility=None, processTemplateId=None, sourceControlType=None):
        self.Id = id
        self.Name = name
        self.Description = description
        self.State = state
        if visibility is not None:
            self.Visibility = visibility
        if processTemplateId is not None:
            self.ProcessTemplateId = processTemplateId
        if sourceControlType is not None:
            self.SourceControlType = sourceControlType

    def __repr__(self):
        return json.dumps(self)

    def __str__(self):
        return f'<Project: {self.Name}>'


class GitRepo:
    Id = None
    Name = None
    Url = None
    RemoteUrl = None
    ProjectId = None
    DefaultBranch = None
    SshUrl = None

    def __init__(self, name=None, projectId=None, id=None, url=None, remoteUrl=None, defaultBranch=None, sshUrl=None):
        self.Id = id
        self.Name = name
        self.ProjectId = projectId
        self.Url = url
        self.RemoteUrl = remoteUrl
        self.DefaultBranch = defaultBranch
        self.SshUrl = sshUrl

    def __repr__(self):
        return json.dumps(self)

    def __str__(self):
        return f'<Project: {self.ProjectId}, GitRepo: {self.Name}>'


class Environment:
    Id = None
    Name = None
    Description = None
    ProjectId = None

    def __init__(self, name=None, projectId=None, description=None, id=None):
        self.Id = id
        self.Name = name
        self.ProjectId = projectId
        self.Description = description

    def __repr__(self):
        return json.dumps(self)

    def __str__(self):
        return f'<Project: {self.ProjectId}, Environment: {self.Name}>'


class ServiceEndpoint:
    Id = None
    Name = None
    Type = None
    Url = None
    ProjectId = None
    ApiToken = None
    Certificate = None


class KubernetesResource:
    Id = None
    Name = None
    ClusterName = None
    Namespace = None
    ServiceEndpointId = None
    ProjectId = None
    EnvironmentId = None

    def __init__(self, name=None, projectId=None, environmentId=None, id=None, clustername=None, namespace=None):
        self.Id = id
        self.Name = name
        self.ProjectId = projectId
        self.EnvironmentId = environmentId
        self.ClusterName = clustername
        self.Namespace = namespace

    def __repr__(self):
        return json.dumps(self)


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

    _org_url = context.getSecret(inputs['adOrgUrl'])
    _access_token = context.getSecret(inputs['adAccessToken'])

    _client = ADOClient(organisation_url=_org_url, access_token=_access_token)

    match op:
        case "create":
            outputs['create'] = True
            _project = processProjectInputs(inputs)
            if(_response := _client.createProject(_project)) is not None:
                outputs.update(processProjectResponse(_response))
        case "update":
            # update logic to be added here
            print("update")
        case "read":
            outputs['read'] = True
            if(_response := _client.getProject(inputs['name'])) is not None:
                outputs.update(processProjectResponse(_response))
        case "delete":
            outputs['delete'] = True
            if (_response := _client.deleteProject(inputs['name'])) is None:
                outputs['state'] = False
            else:
                outputs['state'] = True

    return outputs



# Secondary handler for day two ops of projects
def actionHandler(context, inputs):
    """
        This function handles various actions based on the input parameters.

        Args:
            context: The context object.
            inputs: The input parameters.

        Returns:
            The outputs based on the specified action.
    """

    action = inputs.get("action")
    outputs = []
    _client = ADOClient()

# Envirnonment CRUD handler
def abxHandler_Environments(context, inputs):
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

    _org_url = context.getSecret(inputs['adOrgUrl'])
    _access_token = context.getSecret(inputs['adAccessToken'])

    _client = ADOClient(organisation_url=_org_url, access_token=_access_token)

    match op:
        case "create":
            outputs['create'] = True
            _env = Environment()
            _env.Name = inputs['name']
            _env.Description = inputs['description']
            _env.ProjectId = inputs['projectid']
            if (_response := _client.createEnvironment(_env)) is not None:
                outputs.update(processEnvironmentResponse(_response))
            else:
                outputs['state'] = False
        case "read":
            outputs['read'] = True
            if(_response := _client.getEnvironment(inputs['projectid'], inputs['name'])) is not None:
                outputs.update(processProjectResponse(_response))
            else:
                outputs['state'] = False
        case "delete":
            outputs['delete'] = True
            if (_response := _client.deleteEnvironment(inputs['projectid'], inputs['environmentid'])) is None:
                outputs['state'] = False
            else:
                outputs['state'] = True

    return outputs


# Popeulate inouts into project class
def processProjectInputs(inputs):
    _project = Project()
    _project.Name = inputs['name']
    _project.Description = inputs['description']
    _project.ProcessTemplateId = inputs['processtemplate']
    _project.SourceControlType = inputs['sourcecontroltype']
    _project.Visibility = inputs['visibility']
    return _project


# extracts current project data to feed into the abx output variable
def processProjectResponse(response):
    _status = {}
    _status['name'] = response['name']
    _status['description'] = response['description']
    _status['projectid'] = response['id']
    _status['state'] = response['state']
    _status['url'] = response['url']
    _status['description'] = response['description']
    _status['visbility'] = response['visibility']
    _status['sourcecontroltype'] = response['capabilities']['versioncontrol']['sourceControlType']
    _status['processtemplate'] = response['capabilities']['processTemplate']['templateTypeId']
    return _status


# extracts current environment data to feed into the abx output variable
def processEnvironmentResponse(response):
    _status = {}
    _status['name'] = response['name']
    _status['type'] = response['type']
    _status['url'] = response['url']
    _status['state'] = True
    return _status


# extracts current project data to feed into the abx output variable
def processEndpointResponse(response):
    _status = {}
    _status['name'] = response['name']
    _status['id'] = response['id']
    _status['projectid'] = response['serviceEndpointProjectReferences']['name']
    _status['ready'] = response['isReady']
    _status['state'] = response['operationStatus']
    return _status


# Endpoint CRUD handler
def abxHandler_Endpoint(content, inputs):
    action = inputs.get("action")
    outputs = []



# Kubernetes Resource CRUD handler
def abxHandler_KubernetesResource(content, inputs):
    action = inputs.get("action")
    outputs = []


# Repository CRUD handler
def abxHandler_Repository(content, inputs):
    action = inputs.get("action")
    outputs = []



# Handler for vRO Actions
def handler(context, inputs):
    print('Executing vRO Action')

    _action = inputs["action"]
    print (f"Running orchestrator action: {_action}")

    _outputs = []

    _token = os.environ.get("adAccessToken") or 'e4t7gerblbfziblu4y7lzdjccvsmkdnzehymnczbz4odctb6rzuq'
    _url = os.environ.get("adOrgUrl") or 'http://azuredevops.ad.home.local/DefaultCollection'

    _project = inputs.get('projectname') or 'alpha'

    _client = ADOClient(organisation_url=_url, access_token=_token)

    match _action:
        case "form-projectlist":
            print (f"Getting project list")
            _outputs = _client.getProjectList_dict
        case "project-create":
            _project = processProjectInputs(inputs)
            if(_response := _client.createProject(_project)) is not None:
                _outputs.update(processProjectResponse(_response))
            else:
                _outputs['state'] = False
        case "project-read":
            if(_response := _client.getProject(inputs['name'])) is not None:
                _outputs.update(processProjectResponse(_response))
        case "project-delete":
            if (_response := _client.deleteProject(inputs['name'])) is not None:
                print(f'project {inputs['name']} deleted')
            else:
                print(f'project {inputs['name']} deletion failed')
            _outputs['state'] = _response
        case "environment-create":
            _env = Environment()
            _env.Name = inputs['name']
            _env.Description = inputs['description']
            _env.ProjectId = inputs['projectid']
            if (_response := _client.createEnvironment(_env)) is not None:
                _outputs.update(processEnvironmentResponse(_response))
            else:
                _outputs['state'] = False
        case "environment-delete":
            _project = inputs['project']
            _env = inputs['environment']
            if (_response := _client.deleteEnvironment(_project, _env)) is not None:
                print(f'Environment {_env} connected to project {(_project)} has been deleted')
            else:
                print(f'Environment {_env} deletion failed')
            _outputs['state'] = _response
        case "endpoint-create":
            _endpoint = ServiceEndpoint()
            _endpoint.Name = inputs['name']
            _endpoint.ProjectId = inputs['project']
            _endpoint.Type = 'kubernetes'
            _endpoint.Url = inputs['apiurl']
            _endpoint.ApiToken = inputs['token']
            _endpoint.Certificate = inputs['cert']
            if (_response := _client.createServiceEndpoint(_endpoint)) is not None:
                _outputs.update(processEndpointResponse(_response))
            else:
                _outputs['state'] = False

    return _outputs
