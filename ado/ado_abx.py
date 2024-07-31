"""
Service:        Azure DevOps Aria ABX Extension Script
Version:        1.8.8
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
        1.5.0   - Expanded capabitlies around ServiceEndpoint management
        1.6.0   - Environment controls for Orchestrator added
        1.7.0   - Added Kubernetes resource support for Orchestrator
        1.8.0   - Changed delete functions to support both json and boolean responses. Project is the only json dependent service curre
                
"""

import json, time, requests, os
from urllib.error import URLError, HTTPError



"""
A collection of classes that represent each of the managable objects in ADO for Aria
"""
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
    Shared = False


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
    __api_version = "7.0-preview"
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
                    print(f'Error response code: {_response.status_code}, reason: {_response.reason}')
        except HTTPError as e:
            print(f'Error code: {e.code}, Reason: {e.reason}')
        except URLError as e:
            print(f'Url code: {e.code}, Reason: {e.reason}')
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
                if _response.status_code in range(200,205):
                    return json.loads(_response.text)
                else:
                    print(f'POST- Error response code: {_response.status_code}, reason: {_response.reason}')
        except HTTPError as e:
            print(f'POST- Error code: {e.code}, Reason: {e.reason}')
        except URLError as e:
            print(f'POST- Url code: {e.code}, Reason: {e.reason}')
        return None


    # general HTTP delete routine
    def __delete(self, url, jsonResponse=False):
        print(f"Executing HTTP Delete")

        try:
            _headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }

            with requests.delete(url, headers=_headers, auth=('', self.__access_token)) as _response:
                print(f"Status Code: {_response.status_code}")
                if _response.status_code in range(200, 205):
                    if jsonResponse:
                        return json.loads(_response.text)
                    else:
                        return True
                else:
                    print(f'Error response code: {_response.status_code}, reason: {_response.reason}')
        except HTTPError as e:
            print(f'Error code: {e.code}, Reason: {e.reason}')
        except URLError as e:
            print(f'Url code: {e.code}, Reason: {e.reason}')

        if jsonResponse:
            return False
        else:
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
            "visibility": project.Visibility,
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

    # Convert project name to id
    def getProjectId(self, project):
        if not isinstance(project, int):
            if (_response := self.getProject(project)) is not None:
                return _response['id']
            else:
                return None
        else:
            return project

    
    # Delete a project
    def deleteProject(self, projectId):
        print(f"Deleting project {projectId}")

        _id = self.getProjectId(projectId)
        _url = f"{self.__organisation_url}/_apis/projects/{_id}?api-version={self.__api_version}"

        _start = time.time()
        if (_response := self.__delete(_url, True)) is not None:
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
    def getEnvironmentList(self, projectId=None) -> json:
        print(f"Get list of environments from project {projectId} details")

        _envs = []
        if projectId is None:
            for _project in self.getProjectList_dict():
                _url = f"{self.__organisation_url}/{_project}/_apis/pipelines/environments?api-version={self.__api_version}"
                if (_response := self.__get(_url)) is not None:
                    for _env in _response['value']:
                        _envs.append(_env)
        else:        
            _url = f"{self.__organisation_url}/{projectId}/_apis/pipelines/environments?api-version={self.__api_version}"
            if (_response := self.__get(_url)) is not None:
                _envs = _response['value']

        if len(_envs) == 0:
            return None
        else:
            return _envs
 

    # Get the environment id from an environment name
    def getEnvironmentId(self, project, environment):
        if not isinstance(environment, int):
            _url = f"{self.__organisation_url}/{project}/_apis/pipelines/environments?name={environment}&expands=resourceReferences&api-version={self.__api_version}"
            if (_response := self.__get(_url)) is not None:
                if _response['count'] > 0:
                   return _response['value'][0]['id'] 
        return None


    # Get sepcoified environment details
    # requires project name or id and envirnment id
    def getEnvironment(self, project, environment) -> json:
        print(f"Get environment {environment} from project {project} details")


        if (_id := self.getEnvironmentId(project, environment)) is not None:
            _url = f"{self.__organisation_url}/{project}/_apis/pipelines/environments/{_id}?expands=resourceReferences&api-version={self.__api_version}"
            return self.__get(_url)
        else:
            return None


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

        _id = self.getProjectId(projectid)
        if not isinstance(environmentid, int):
            _url = f"{self.__organisation_url}/{projectid}/_apis/pipelines/environments?name={environmentid}&expands=resourceReferences&api-version={self.__api_version}"
            if (_response := self.__get(_url)) is not None:
                environmentid = _response['value'][0]['id'] 
            else:
                return None
        _url = f"{self.__organisation_url}/{projectid}/_apis/pipelines/environments/{environmentid}?api-version={self.__api_version}"        

        return self.__delete(_url)


    # get a list of  a projects service endpoints
    def getServiceEndpointList(self, projectId=None):
        print(f"Get list of all service endpoints or those for a specified project")
        if projectId is None:
            _endpoints = []
            for _project in self.getProjectList_dict():
                _url = f"{self.__organisation_url}/{_project}/_apis/serviceendpoint/endpoints?api-version={self.__api_version}"        
                if (_response := self.__get(_url)) is not None:
                    for _ep in _response['value']:
                        _endpoints.append(_ep)
        else:                           
            _url = f"{self.__organisation_url}/{projectId}/_apis/serviceendpoint/endpoints?api-version={self.__api_version}"        
            if (_response := self.__get(_url)) is not None:
                _endpoints = _response['value']
        return _endpoints


    # Get the endpointid from an endpoint name
    def getServiceEndpointId(self, project, endpoint):
        if not isinstance(endpoint, int):
            for _item in self.getServiceEndpointList(projectId=project):
                if _item['name'] == endpoint:
                    return _item['id']
                    break
        else:
            return endpoint
        return None


    # get a lprojects service endpoint
    def getServiceEndpoint(self, projectid, endpoint, endpointtype='kubernetes'):
        print(f"Get endpoint {endpoint} for project {projectid}")

        _endpoint = None
        if not isinstance(endpoint, int):
            for _item in self.getServiceEndpointList(projectId=projectid):
                if _item['name'] == endpoint:
                    _endpoint = _item
                    break
        else:
            _url = f"{self.__organisation_url}/{projectid}/_apis/serviceendpoint/endpoints/{endpoint}?api-version={self.__api_version}"        
            if (_response := self.__get(_url)) is not None:
                _endpoint = _response['value']
        return _endpoint


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
                "isShared": endpoint.Shared,
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
            return {"status":"FAILED", "message":f"Unable to find project {endpoint.ProjectId}"}


    # Delete the Service Endpoint
    def deleteServiceEndpoint(self, project, endpoint):
        print(f"Deleting endpoint {endpoint} in project {project}")

        _projid = self.getProjectId(project)
        _envid = self.getServiceEndpointId(project, endpoint)

        if _projid is not None and _envid is not None:
            _url = f"{self.__organisation_url}/_apis/serviceendpoint/endpoints/{_envid}?projectIds={_projid}&api-version={self.__api_version}"
            return self.__delete(_url)
        else:
            print("Error: Environment unknown")
            return False


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



    # Get list of an environments resources
    def getKubernetesResourceList(self, project=None):
        print(f"Get list of all resources ")

        _resourcelist = []
        _envlist = self.getEnvironmentList()
        for _item in _envlist:
            _projectid = _item['project']['id']
            _projectname = self.getProject(_projectid)['name']
            _envname = _item['name']
            print(f"Checking project {_projectname} environment {_envname} for resources")
            if _projectname == project or project is None:
                _envid = _item['id']
                _env = self.getEnvironment(_projectname, _envname)
                for _resource in _env['resources']:
                    _resourceid = _resource['id']
                    if (_resource := self.getKubernetesResource(_projectid, _envid, _resourceid)) is not None:
                        _resourcelist.append(processResourceResponse(_resource, _projectname))

        return _resourcelist
    

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

        if (_endpoint := self.getServiceEndpoint(k8sResource.ProjectId, k8sResource.ServiceEndpointId)) is not None:
            _endpointid = _endpoint['id']
        else:
            _endpointid = k8sResource.ServiceEndpointId

        _url = f"{self.__organisation_url}/{k8sResource.ProjectId}/_apis/pipelines/environments/{environmentId}/providers/kubernetes?api-version={self.__api_version}"        
        _data = {
            "name": k8sResource.Name,
            "clusterName": k8sResource.ClusterName,
            "namespace": k8sResource.Namespace,
            "serviceEndpointId": _endpointid
        }
        print(f"Executing resource create function with data {_data}")
        return self.__post(_url, _data)


    # Delete the Kubernetes resource
    def deleteKubernetesResource(self, project, environment, resource):
        print(f"Delete a kubernetes resource")

        if not isinstance(environment, int):
            if(_environment := self.getEnvironment(project, environment)) is not None:
                _envid = _environment['id']
                for _resource in _environment['resources']:
                    if _resource['name'].upper() == resource.upper():
                        _resourceid = _resource['id']
                        break

            else:
                return None
        else:
            _envid = environment
        _url = f"{self.__organisation_url}/{project}/_apis/pipelines/environments/{_envid}/providers/kubernetes/{_resourceid}?api-version={self.__api_version}"
        if (_response := self.__delete(_url)):
            print("Resource deleted successfully")
            return _response
        else:
            print("Resource deletion failed")
            return _response


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
    _status['id'] = response['id']
    _status['name'] = response['name']
    if 'description' in response.keys():
        _status['description'] = response['description']
    else:
        _status['description'] = 'Produced by Aria'
    _status['state'] = response['state']
    #_status['url'] = response['url']
    _status['visbility'] = response['visibility']
    _status['sourcecontroltype'] = response['capabilities']['versioncontrol']['sourceControlType']
    _status['processtemplate'] = response['capabilities']['processTemplate']['templateTypeId']
    _project = json.dumps(_status)
    return _project



# extracts current environment data to feed into the abx output variable
def processEnvironmentInputs(inputs):
    _env = Environment()
    _env.Name = inputs['name']
    _env.Description = inputs['description']
    _env.ProjectId = inputs['project']
    return _env


# extracts current environment data to feed into the abx output variable
def processEnvironmentResponse(response):
    _status = {}
    _status['id'] = response['id']
    _status['name'] = response['name']
    _status['description'] = response['description']
    _status['project'] = response['project']['name']
    _status = json.dumps(_status)
    return _status


# Process the inputs for the endpoints
def processEndpointInputs(inputs):
    _endpoint = ServiceEndpoint()
    _endpoint.Name = inputs['name']
    _endpoint.ProjectId = inputs['project']
    _endpoint.Type = inputs['type']
    _endpoint.Url = inputs['apiurl']
    _endpoint.ApiToken = inputs['token']
    _endpoint.Certificate = inputs['certificate']
    return _endpoint


# extracts current project data to feed into the abx output variable
def processEndpointResponse(response):
    _status = {}
    _status['name'] = response['name']
    _status['id'] = response['id']
    _status['project'] = response['serviceEndpointProjectReferences'][0]['projectReference']['name']
    _status['ready'] = response['isReady']
    _status['apiurl'] = response['url']
    _status['type'] = response['type']
    _status = json.dumps(_status)
    return _status


# Process the inputs for the endpoints
def processResourceInputs(inputs):
    _resource = KubernetesResource()
    _resource.Name = inputs['name']
    _resource.ProjectId = inputs['project']
    _resource.EnvironmentId = inputs['environment']
    _resource.ServiceEndpointId = inputs['serviceendpoint']
    _resource.ClusterName = inputs['cluster']
    _resource.Namespace = inputs['namespace']
    return _resource


# Extracts the resource details froo the response)
def processResourceResponse(response, project=None):
    _status = {}
    _status['name'] = response['name']
    _status['resourceid'] = response['id']
    _status['environment'] = response['environmentReference']['name']
    _status['cluster'] = response['clusterName']
    _status['namespace'] = response['namespace']
    _status['serviceendpoint'] = response['serviceEndpointId']
    _status['resourcetype'] = response['type']
    if project is not None:
        _status['project'] = project
    _status = json.dumps(_status)
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
        case "project-create":
            print(f"Creating project")
            _project = processProjectInputs(inputs)
            if(_response := _client.createProject(_project)) is not None:
                _outputs = processProjectResponse(_response)
            else:
                _outputs = None
        case "project-get":
            print(f"retrieving project {inputs['name']}")
            if(_response := _client.getProject(inputs['name'])) is not None:
                _outputs = processProjectResponse(_response)
        case "project-list":
            print(f"Getting project list")
            _outputs = _client.getProjectList_dict()
        case "project-delete":
            print(f"Deleting project {inputs['name']}")
            if (_response := _client.deleteProject(inputs['name'])):
                print(f"project {inputs['name']} deleted")
                _outputs = {'status':'succeeded','comment':'delete task completed successfully'}
            else:
                print(f"project {inputs['name']} deletion failed")
                _outputs = None
        case "environment-create":
            print (f"Creating an environment")
            _env = processEnvironmentInputs(inputs)
            if (_response := _client.createEnvironment(_env)) is not None:
                _outputs = processEnvironmentResponse(_response)
            else:
                _outputs = None
        case "environment-get":
            _project = inputs['project']
            _env = inputs['environment']
            print(f"retrieving environment {_env} for project {_project}")
            if (_response := _client.getEnvironment(project=_project, environment=_env)) is not None:
                if _response['project']['name'] is None:
                    _response['project']['name'] = _client.getProject(_response['project']['id'])['name']
                _outputs = processEnvironmentResponse(_response)
            else:
                _outputs = {"status":"failed","comment":"Unable to rerieve environment"}
        case "environment-list":
            if 'project' in inputs.keys():
                _project = inputs['project']
                print (f"Getting project {_project} environment list")
                _response = _client.getEnvironmentList(_project)
            else:
                print (f"Getting environment list")
                _response = _client.getEnvironmentList()

            if _response is not None:
                for _item in _response:
                    if _item['project']['name'] is None:
                        _item['project']['name'] = _client.getProject(_item['project']['id'])['name']
                    _outputs.append(processEnvironmentResponse(_item))
        case "environment-delete":
            _project = inputs['project']
            _env = inputs['environment']
            print(f"Deleting environment {_env} for project {_project}")
            if (_response := _client.deleteEnvironment(_project, _env)):
                print(f'Environment {_env} connected to project {_project} has been deleted')
                _outputs = {'status':'succeeded','comment':'delete task completed successfully'}
            else:
                print(f'Environment {_env} deletion failed')
                _outputs = None
        case "endpoint-create":
            print(f"Creating endpoint")
            _endpoint = processEndpointInputs(inputs)
            if (_response := _client.createServiceEndpoint(_endpoint)) is not None:
                _outputs = processEndpointResponse(_response)
            else:
                _outputs = None
        case "endpoint-get":
            _project = inputs['project']
            _endpoint = inputs['name']
            print(f"Getting Project {_project} endpoint {_endpoint}")
            if (_response := _client.getServiceEndpoint(_project, _endpoint)) is not None:
                _outputs = processEndpointResponse(_response)
        case "endpoint-list":
            print(f"Retrieving endpoint")
            if 'project' in inputs.keys():
                _response = _client.getServiceEndpointList(inputs['project'])
            else:
                _response = _client.getServiceEndpointList() 
            
            if _response is not None:
                for _ep in _response:
                    _outputs.append(processEndpointResponse(_ep))
        case "endpoint-delete":
            _project = inputs['project']
            _endpoint = inputs['name']
            print(f"Deleting endpoint {_endpoint} from Project {_project}")
            if(_response := _client.deleteServiceEndpoint(_project, _endpoint)):
                print(f"project {inputs['name']} deleted")
                _outputs = {'status':'succeeded','comment':'delete task completed successfully'}
            else:
                print(f"project {inputs['name']} deletion failed")
                _outputs = None
        case "resource-list":
            print(f"Retrieving environment resource list")
            if 'project' in inputs.keys():
                _project = inputs['project']
            else:
                _project = None
            if (_response := _client.getKubernetesResourceList(_project)) is not None:
                _outputs = _response
            else:
                print("Resource list not returned")
        case "resource-get":
            _project = inputs['project']
            _env = inputs['environment']
            _resource = inputs['name']
            print(f"Retrieving resource {_resource} details for proejct {_project} in environment {_env}")
            if (_response := _client.getKubernetesResource(_project, _env, _resource)) is not None:
                print(f"Resource created successfully")
                _outputs.append(processResourceResponse(_response, _project))
        case "resource-create":
            print(f"Creating environment resource")
            _resource = processResourceInputs(inputs)
            if (_response := _client.createKubernetesResource(_resource)) is not None:
                _outputs = processResourceResponse(_response, inputs['project'])
            else:
                _outputs = None
        case "resource-delete":
            print(f"Deleting environment resource")
            _project = inputs['project']
            _environment = inputs['environment']
            _resource = inputs['name']
            print(f"Deleting resource {_resource} in environment {_environment} from Project {_project}")
            if(_response := _client.deleteKubernetesResource(_project, _environment, _resource)):
                print(f"resource {_resource} deleted")
                _outputs = {'status':'succeeded','comment':'delete task completed successfully'}
            else:
                print(f"resource {_resource} deletion failed")
                _outputs = None

    return _outputs
