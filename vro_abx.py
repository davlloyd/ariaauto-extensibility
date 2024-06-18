import json
from urllib.request import urlopen
from urllib.parse import urlparse
import urllib.request
import urllib.error
import ssl
import time
import os
import base64
import random
import string

# Aria has a max timeout of 900 seconds (15 minutes).
# If an action doesn't complete its execution within 15 minutes, then it is marked as failed.
# Specifying the timeout value to be 14 minutes, so we try to complete the deployment request (create db) operation within the max timeout of Aria which is 15 minutes.
# If the create db operation takes longer, then we don't want to let vRA think it failed.
timeout = 3500

class DsmClient:
    """
        A client class for interacting with the DSM (Data Services Manager) API.

        Args:
            server (str): The DSM server URL.
            username (str): The username for authentication.
            password (str): The password for authentication.
            skip_certificate_check (str): True/False If certificate should be used for authentication
            root_ca (str): DSM root CA
    """

    GROUP_INFRA = "infrastructure.dataservices.vmware.com"
    GROUP_INFRAVER = "v1alpha1"
    GROUP_DB = "databases.dataservices.vmware.com"
    GROUP_DBVER = "v1alpha1"

    def __init__(self, server, username, password, skip_certificate_check, root_ca) -> None:
        """
            Initializes a new instance of the DsmClient class.

            Args:
                server (str): The DSM server URL.
                username (str): The username for authentication.
                password (str): The password for authentication.
                skip_certificate_check (str): True/False If certificate should be used for authentication
                root_ca (str): DSM root CA
        """

        # Store the server URL, username, and password
        self.server = server
        self.username = username
        self.password = password
        self.root_ca = root_ca

        if skip_certificate_check == "True":
            # Create an SSL context to allow unverified connections
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            self.httpCtx = context
        else:
            # Create an SSL context to allow verified connections using certificates
            self.httpCtx = self.getSSLContext()

        # Call the login method to authenticate and retrieve the token
        self.login()

    def getSSLContext(self):
        """
            This function creates and returns an SSL context.
        """
        cert_content = self.root_ca

        # Create an SSLContext instance by specifying the client TLS protocol
        sslSettings = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        sslSettings.verify_mode = ssl.CERT_REQUIRED
        sslSettings.check_hostname = True

        # Load the CA certificates used for validating the peer's certificate
        sslSettings.load_verify_locations(cadata=cert_content)

        return sslSettings

    def headers(self):
        """
            Returns the headers for API requests.

            Returns:
                dict: The headers dictionary.
        """

        return {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.token}',
            'Accept': 'application/json, text/plain, */*'
        }

    def login(self):
        """
            Logs in to the DSM server and retrieves the authentication token.
            Raises an exception if the login fails.
        """

        # Convert the login information to JSON format
        loginInfo = json.dumps({
            "email": self.username,
            "password": self.password,
        }).encode('utf-8')

        # Construct the login URL
        url = f"https://{self.server}/provider/session"

        # Set the headers for the login request
        headers = {
            'Content-Type': 'application/json',
        }

        # Send the login request and retrieve the response
        request = urllib.request.Request(url, headers=headers, data=loginInfo)
        with urlopen(request, context=self.httpCtx) as response:
            # Extract the authentication token from the response headers
            auth = response.headers.get("Authorization")
            prefix = 'Bearer '
            if not auth.startswith(prefix):
                raise Exception("Login didn't return a Bearer token")
            self.token = auth[len(prefix):]

    def get(self, path):
        """
            Sends a GET request to the specified path and returns the response as a JSON object.

            Args:
                path (str): The path to send the GET request to.

            Returns:
                dict: The response as a JSON object.
        """

        # Construct the URL using the server and path
        url = f"https://{self.server}{path}"

        # Create a request object with the URL and headers
        request = urllib.request.Request(url, headers=self.headers())

        # Send the GET request and retrieve the response
        with urlopen(request, context=self.httpCtx) as response:
            # Load the response as a JSON object
            return json.load(response)

    def delete(self, path):
        """
            Sends a DELETE request to the specified path on the server.

            Args:
                path (str): The path to send the DELETE request to.

            Returns:
                dict: The JSON response from the server.
        """

        # Construct the URL
        url = f"https://{self.server}{path}"

        # Create a DELETE request with the specified URL and headers
        request = urllib.request.Request(url, headers=self.headers(), method="DELETE")

        # Send the request and handle the response
        with urlopen(request, context=self.httpCtx) as response:
            # Load the response as a JSON object
            return json.load(response)

    def postOrPut(self, path, jsonData, method):
        """
            Sends a POST or PUT request to the specified path with the given JSON data.

            Args:
                path (str): The path to send the request to.
                jsonData (dict): The JSON data to send in the request body.
                method (str): The HTTP method to use (either "POST" or "PUT").

            Returns:
                dict: The JSON response from the server.
        """

        # Construct the URL
        url = f"https://{self.server}{path}"

        # Encode the JSON data as bytes
        body = json.dumps(jsonData).encode('utf-8')

        # Create a request object with the URL, headers, and data
        request = urllib.request.Request(url, headers=self.headers(), data=body, method=method)

        # Send the request and handle the response
        with urlopen(request, context=self.httpCtx) as response:
            # Load the response as a JSON object
            return json.load(response)
    
    def k8sClusterList(self, group, version, kindplural):
        """
            Retrieves a kubernetes list of DB clusters.

            Args:
                group (str): The group name.
                version (str): The version.
                kindplural (str): The plural form of the kind.

            Returns:
                dict: The JSON response.
        """
        path = f"/apis/{group}/{version}/{kindplural}?limit=50&observe=response"
        return self.get(path)

    def listInfraPolicies(self):
        """
            Retrieves a list of infrastructure policies.

            Returns:
                dict: The JSON response
        """
        return self.k8sClusterList(self.GROUP_INFRA, self.GROUP_INFRAVER, "infrastructurepolicies")

    def k8sListDict(self, response):
        """
            Converts a Kubernetes response to a dictionary.

            Args:
                response (dict): The Kubernetes response.

            Returns:
                dict: The converted dictionary.
        """
        return dict([(x["metadata"]["name"], x) for x in response["items"]])

    def listInfraPoliciesDict(self):
        """
            Retrieves a dictionary of infrastructure policies.

            Returns:
                dict: The dictionary of infrastructure policies.
        """
        return self.k8sListDict(self.listInfraPolicies())

    def listBackupLocations(self):
        """
            Retrieves a list of backup locations.

            Returns:
                list: The list of backup locations.
        """
        backuplocation_names = []
        path = f"/provider/s3storages"
        backuplocation_out = self.get(path)
        for content in backuplocation_out["content"]:
            backuplocation_names.append(content["name"])
        return backuplocation_names

    def listVmClasses(self):
        """
            Retrieves a list of VM classes.

            Returns:
                dict: The JSON response.
        """
        return self.k8sClusterList(self.GROUP_INFRA, self.GROUP_INFRAVER, "vmclasses")

    def listDbVersions(self, dbengine):
        """
            Retrieves a list of database versions.

            Args:
                dbengine (str): The database engine.

            Returns:
                list: The list of database versions.
        """

        path = f"/apis/internal.dataservices.vmware.com/v1alpha1/dataservicesreleases"
        ds_out = self.get(path)
        db_versions = []

        if self.isDataServiceReleaseReady(ds_out, "Ready"):
            for item in ds_out["items"]:
                data_service_version = item["spec"]["version"]
                for service in item["spec"]["services"]:
                    if dbengine == "Postgres":
                        if service["name"] == "vmware-sql-postgres":
                            for version in service["supportedVersions"]:
                                version_val = version + "+vmware." + data_service_version
                                db_versions.append(version_val)
                            return db_versions
                    if dbengine == "MySQL":
                        if service["name"] == "vmware-sql-mysql":
                            for version in service["supportedVersions"]:
                                version_val = version + "+vmware." + data_service_version
                                db_versions.append(version_val)
                            return db_versions
        return db_versions

    def listClusterTopologies(self, dbengine, replicamode):
        """
            Returns a list of cluster topologies based on the specified database engine and replica mode.

            Args:
                dbengine (str): The database engine. Valid values are "Postgres" and "MySQL".
                replicamode (str): The replica mode. Valid values depend on the database engine.

            Returns:
                list: A list of cluster topologies.
        """

        topologies = []
        if dbengine == "Postgres":
            path = f"/provider/deployment-topology"
            topology_out = self.get(path)
            for topology_details in topology_out:
                if replicamode == topology_details["replicaMode"]:
                    for value in topology_details["topologies"]:
                        topology_value = str(value["totalNodes"]) + " (" + value["nodesDescription"] + ")"
                        topologies.append(topology_value)
        elif dbengine == "MySQL":
            if replicamode == "Single Server":
                topologies = ['1 (1 Primary, 0 Replica)']
            elif replicamode == "Single vSphere Cluster":
                topologies = ['3 (1 Primary, 2 Replicas)', '5 (1 Primary, 4 Replicas)']
        return topologies
    
    def createPg(self, data):
        """
            Creates a PostgreSQL cluster.

            Args:
                data (dict): The data to be sent in the request body.

            Returns:
                None
        """

        # Construct the path for creating a PostgreSQL cluster
        path = f"/apis/{self.GROUP_DB}/{self.GROUP_DBVER}/namespaces/default/postgresclusters"

        # Send a POST request with the specified path, data, and method
        self.postOrPut(path, data, "POST")

    def createDatabaseConfig(self, data):
        """
            Creates a database configuration.

            Args:
                data (dict): The data to be sent in the request body.

            Returns:
                None
        """
        # Construct the path for creating a database configuration
        path = f"/apis/{self.GROUP_DB}/{self.GROUP_DBVER}/namespaces/default/databaseconfigs"

        # Send a POST request with the specified path, data, and method
        self.postOrPut(path, data, "POST")

    def pgPath(self, name):
        """
            Constructs the path for a PostgreSQL cluster.

            Args:
                name (str): The name of the PostgreSQL cluster.

            Returns:
                str: The constructed path.
        """
        return f"/apis/{self.GROUP_DB}/{self.GROUP_DBVER}/namespaces/default/postgresclusters/{name}"

    def deletePg(self, name):
        """
            Deletes a PostgreSQL cluster.

            Args:
                name (str): The name of the PostgreSQL cluster.

            Returns:
                None
        """
        return self.delete(self.pgPath(name))
    
    def getPg(self, name):
        """
            Retrieves information about a PostgreSQL cluster.

            Args:
                name (str): The name of the PostgreSQL cluster.

            Returns:
                dict: The information about the PostgreSQL cluster.
        """
        return self.get(self.pgPath(name))
    
    def updatePg(self, pg):
        """
            Updates a PostgreSQL cluster.

            Args:
                pg (dict): The updated data for the PostgreSQL cluster.

            Returns:
                None
        """
        path = self.pgPath(pg["metadata"]["name"])
        return self.postOrPut(path, pg, "PUT")

    def createMysql(self, data):
        """
            Creates a MySQL cluster.

            Args:
                data (dict): The data to be sent in the request body.

            Returns:
                None
        """
        path = f"/apis/{self.GROUP_DB}/{self.GROUP_DBVER}/namespaces/default/mysqlclusters"
        self.postOrPut(path, data, "POST")

    def mysqlPath(self, name):
        """
            Constructs the path for a MySQL cluster.

            Args:
                name (str): The name of the MySQL cluster.

            Returns:
                str: The constructed path.
        """
        return f"/apis/{self.GROUP_DB}/{self.GROUP_DBVER}/namespaces/default/mysqlclusters/{name}"

    def deleteMysql(self, name):
        """
            Deletes a MySQL cluster.

            Args:
                name (str): The name of the MySQL cluster.

            Returns:
                None
        """
        return self.delete(self.mysqlPath(name))

    def getMysql(self, name):
        """
            Retrieves information about a MySQL cluster.

            Args:
                name (str): The name of the MySQL cluster.

            Returns:
                dict: The information about the MySQL cluster.
        """
        return self.get(self.mysqlPath(name))

    def updateMysql(self, mysql):
        """
            Updates a MySQL cluster.

            Args:
                mysql (dict): The updated data for the MySQL cluster.

            Returns:
                None
        """
        path = self.mysqlPath(mysql["metadata"]["name"])
        return self.postOrPut(path, mysql, "PUT")

    def deleteDatabaseConfig(self, name):
        """
            Deletes a database configuration.

            Args:
                name (str): The name of the database configuration.

            Returns:
                None
        """
        path = f"/apis/{self.GROUP_DB}/{self.GROUP_DBVER}/namespaces/default/databaseconfigs/{name}"
        return self.delete(path)

    def isDataServiceReleaseReady(self, ds, condType):
        """
            Checks if the data service release is ready based on the specified condition type.

            Args:
                ds (dict): The data service object.
                condType (str): The condition type to check.

            Returns:
                bool: True if the data service release is ready, False otherwise.
        """
        for item in ds["items"]:
            condList = item.get('status', {}).get('conditions', [])
            for cond in condList:
                if cond.get('type') == condType and cond.get('status') == "True":
                    return True
            return False

    def getDBConnectionString(self, inputs):
        """
            Retrieves the database connection string.

            Args:
                inputs (dict): The input parameters for the connection string.

            Returns:
                str: The database connection string.
        """
        dbengine = (inputs["dbengine"]).lower()
        admin_username = inputs["adminUsername"]
        conn_host = inputs["conn_host"]
        conn_port = str(inputs["conn_port"]).split(".")[0]
        deployment_name = inputs["deploymentName"]
        database_name = inputs["databaseName"]

        path = f"/api/v1/namespaces/default/secrets/{deployment_name}"
        out = self.get(path)

        if dbengine == "postgres":
            db_name = database_name
        else:
            db_name = "mysqlappuser_data"

        password = out["data"]["password"]
        decoded_password = base64.b64decode(password)
        db_password = decoded_password.decode("utf-8")

        connection_string = dbengine+"://"+admin_username+":"+db_password+"@"+conn_host+":"+conn_port+"/"+db_name
        return connection_string

def checkDsmParams(envlist):
    """
        Validate the length of envlist and also the length of
        individual items in the env list
        Args:
            envlist
        Returns: True or False(if envList is not proper)
        Valid env list is [dsmHost,dsmUserID,dsmPassword,dsmSkipCertificateCheck,dsmRootCA]
    """
    if len(envlist) == 5:
        if all(len(element) > 0 for element in envlist):
            return True
        else:
            return False
    else:
        return False


def getDsmConnectionConfig(input):
    """
        Returns a dictionary containing the DSM connection configuration.

        Args:
            input (list): A list containing the DSM host, user ID, password, certificate check and root ca.

        Returns:
            dict: A dictionary containing the DSM connection configuration with keys 'dsmHost', 'dsmUserID', 'dsmPassword', 'dsmSkipCertificateCheck' and 'dsmRootCA'.
    """
    connectionConfig = {"dsmHost":input[0],"dsmUserID":input[1],"dsmPassword":input[2],"dsmSkipCertificateCheck":input[3],"dsmRootCA":input[4]}
    return connectionConfig


def getDsmParamsForAbx(context,inputs):
    """
        Retrieves the DSM connection parameters for ABX.

        Args:
            inputs (list): A list containing the DSM host, user ID, password, certificate check and root CA.

        Returns:
            dict: A dictionary containing the DSM connection configuration.
    """
    try:
         dsmUserID = context.getSecret(inputs['dsmUserID'])
         dsmPassword = context.getSecret(inputs['dsmPassword'])
         dsmHost = context.getSecret(inputs['dsmHost'])
         dsmSkipCertificateCheck = context.getSecret(inputs['dsmSkipCertificateCheck'])
         dsmRootCA = context.getSecret(inputs['dsmRootCA'])
         envList = [dsmHost, dsmUserID, dsmPassword, dsmSkipCertificateCheck, dsmRootCA]
    except Exception as e:
            raise ValueError("Unable to retrieve DSM connection params, Check "
                             "[dsmHost,dsmUserID,dsmPassword,dsmSkipCertificateCheck,dsmRootCA] secrets configuration in Aria/Vra.")
    if not checkDsmParams(envList):
        raise ValueError("Dsm Connection parameters are invalid, Check "
                            "[dsmHost,dsmUserID,dsmPassword,dsmSkipCertificateCheck,dsmRootCA] secrets configuration.")

    return getDsmConnectionConfig(envList)

def getDsmParamsForVro():
    """
        Retrieves the DSM connection parameters for VRO.

        Args:
            None

        Returns:
            dict: A dictionary containing the DSM connection configuration.
    """
    dsmUserID = os.environ["dsmUserID"]
    dsmPassword = os.environ["dsmPassword"]
    dsmHost = os.environ["dsmHost"]
    dsmSkipCertificateCheck = os.environ["dsmSkipCertificateCheck"]
    dsmRootCA = os.environ["dsmRootCA"]
    envList = [dsmHost, dsmUserID, dsmPassword, dsmSkipCertificateCheck, dsmRootCA]
    if not checkDsmParams(envList):
        raise ValueError("Dsm Connection parameters are invalid, Check action's environment")

    return getDsmConnectionConfig(envList)

def getAriaInstanceID():
    """
        This function gets aria instance ID  by accessing raw
        input file and obtains aria instance ID/url from system inputs dictionary
        Args:
            None
        Returns:
            str: The aria instance id
    """
    inputs_file = open(os.getenv('INPUTS_FILE'))
    decoded_inputs = base64.b64decode(inputs_file.read()).decode('utf-8')
    inputs = json.loads(decoded_inputs)
    url = inputs["__system.inputs"]["__callback.url"]
    parsed_url = urlparse(url)
    ariaInstanceID = parsed_url.netloc
    return ariaInstanceID


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
    createdIn = "aria"
    dsmConnConfig = getDsmParamsForAbx(context, inputs)
    ariaInstanceID = getAriaInstanceID()

    # Initialize DSM client
    dsmClient = DsmClient(dsmConnConfig["dsmHost"],dsmConnConfig["dsmUserID"],dsmConnConfig["dsmPassword"],dsmConnConfig["dsmSkipCertificateCheck"],dsmConnConfig["dsmRootCA"])

    def defByPg(inputs):
        """
            Constructs the request body for creating a PostgresCluster in DSM.

            Args:
                inputs (dict): A dictionary containing the input parameters for creating the PostgresCluster.

            Returns:
                dict: The request body for creating the PostgresCluster.
        """
        request_body = {
            "metadata": {
                "name": inputs["deploymentName"],
                "labels": {
                    "dsm.vmware.com/aria-automation-instance": ariaInstanceID,
                    "dsm.vmware.com/aria-automation-project": inputs["ariaProject"],
                    "dsm.vmware.com/created-in": createdIn
                }
            },
            "spec": {
                "version": inputs["dbversion"],
                "vmClass": {
                    "name": inputs["vmClass"]
                },
                "adminUsername": inputs["adminUsername"],
                "databaseName": inputs["databaseName"],
                "storageSpace": f'{inputs["storageSpace"]}Gi',
                "infrastructurePolicy": {
                    "name": inputs["infraPolicy"]
                },
                "storagePolicyName": inputs["storagePolicy"],
                "replicas": getReplicaCount(inputs)
            },
            "apiVersion": f"{dsmClient.GROUP_DB}/{dsmClient.GROUP_DBVER}",
            "kind": "PostgresCluster"
        }

        if inputs["enableBackups"]:
            # Configure backup settings if enabled
            backup_config = {
                    "backupRetentionDays": inputs["backupRetentionDays"],
                    "schedules": [{"name": "default-full-backup", "type": "full", "schedule": "59 23 * * 6"},
                                  {"name": "default-incremental-backup", "type": "incremental", "schedule": "59 23 1/1 * *"}]
            }
            backup_location = {
                "name": inputs["backupLocation"]
            }

            request_body["spec"]["backupConfig"] = backup_config
            request_body["spec"]["backupLocation"] = backup_location

        if inputs["enableMaintenanceWindow"]:
            # Configure maintenance window settings if enabled
            maintenance_window = {
                "duration": f'{inputs["maintenanceDuration"]}h',
                "startDay": inputs["maintenanceDayOfWeek"],
                "startTime": inputs["maintenanceWindowHours"] + ":" + inputs["maintenanceWindowMins"]
            }
            request_body["spec"]["maintenanceWindow"] = maintenance_window

        if inputs["enableDbOptions"]:
            # Configure custom database options if enabled
            request_body["spec"]["databaseConfig"] = {
                "name": createAndGetDbConfig(inputs)
            }

        return request_body

    def defByMysql(inputs):
        """
            Constructs the request body for creating a MySQLCluster in DSM.

            Args:
                inputs (dict): A dictionary containing the input parameters for creating the MySQLCluster.

            Returns:
                dict: The request body for creating a MySQLCluster.
        """
        request_body = {
            "metadata": {
                "name": inputs["deploymentName"],
                "labels": {
                    "dsm.vmware.com/aria-automation-instance": ariaInstanceID,
                    "dsm.vmware.com/aria-automation-project": inputs["ariaProject"],
                    "dsm.vmware.com/created-in": createdIn
                }
            },
            "spec": {
                "version": inputs["dbversion"],
                "vmClass": {
                    "name": inputs["vmClass"]
                },
                "storageSpace": f'{inputs["storageSpace"]}Gi',
                "infrastructurePolicy": {
                    "name": inputs["infraPolicy"]
                },
                "storagePolicyName": inputs["storagePolicy"],
                "members": getReplicaCount(inputs)
            },
            "apiVersion": f"{dsmClient.GROUP_DB}/{dsmClient.GROUP_DBVER}",
            "kind": "MySQLCluster"
        }

        if inputs["enableBackups"]:
            # Configure backup settings if enabled
            backup_config = {
                    "backupRetentionDays": inputs["backupRetentionDays"],
                    "schedules": [{"name": "default-full-backup", "type": "full", "schedule": "59 23 * * 6"}]
            }
            backup_location = {
                "name": inputs["backupLocation"]
            }

            request_body["spec"]["backupConfig"] = backup_config
            request_body["spec"]["backupLocation"] = backup_location

        if inputs["enableMaintenanceWindow"]:
            # Configure maintenance window settings if enabled
            maintenance_window = {
                "duration": f'{inputs["maintenanceDuration"]}h',
                "startDay": inputs["maintenanceDayOfWeek"],
                "startTime": inputs["maintenanceWindowHours"] + ":" + inputs["maintenanceWindowMins"]
            }
            request_body["spec"]["maintenanceWindow"] = maintenance_window

        if inputs["enableDbOptions"]:
            # Configure custom database options if enabled
            request_body["spec"]["databaseConfig"] = {
                "name": createAndGetDbConfig(inputs)
            }

        return request_body

    def getCondition(db: object, condType: str) -> object:
        """
            Retrieves a condition from the database based on the condition type.

            Args:
                db (object): The database object.
                condType (str): The type of condition to retrieve.

            Returns:
                object: The condition object if found, None otherwise.
        """
        condList = db.get('status', {}).get('conditions', [])  # Get the list of conditions from the database object
        for cond in condList:  # Iterate through each condition
            if cond.get('type') == condType:  # Check if the condition type matches the desired condition type
                return cond  # Return the condition object if found
        return None  # Return None if the condition is not found

    def isDBReady(db: object) -> bool:
        """
            Check if the database is ready.

            Args:
                db (object): The database object.

            Returns:
                bool: True if the database is ready, False otherwise.
        """

        # Get the "Ready" condition from the database object
        cond = getCondition(db, "Ready")

        # If the "Ready" condition is not found, return False
        if cond is None:
            return False

        # Return True if the status of the "Ready" condition is "True", False otherwise
        return cond.get('status') == "True"

    def extractStatusInfo(pg):
        """
            Extracts status information from a given PostgreSQL connection.

            Args:
                pg (dict): A dictionary containing the PostgreSQL connection information.

            Returns:
                dict: A dictionary containing the extracted status information.
                      - conn_host (str): The host of the PostgreSQL connection.
                      - conn_dbname (str): The name of the PostgreSQL database.
                      - conn_username (str): The username used for the PostgreSQL connection.
                      - conn_port (int): The port number of the PostgreSQL connection.
                      - ready (str): Indicates whether the database is ready or not ("True" or "False").
        """
        statusInfo = {}
        pgStatus = pg["status"]
        pgConn = pgStatus.get("connection", {})
        statusInfo["conn_host"] = pgConn.get("host")  # Extract the host of the PostgreSQL connection
        statusInfo["conn_dbname"] = pgConn.get("dbname")  # Extract the name of the PostgreSQL database
        statusInfo["conn_username"] = pgConn.get("username")  # Extract the username used for the PostgreSQL connection
        statusInfo["conn_port"] = pgConn.get("port")  # Extract the port number of the PostgreSQL connection
        statusInfo["ready"] = "True" if isDBReady(pg) else "False"  # Check if the database is ready and set the "ready" flag accordingly
        return statusInfo

    def extractStatusInfoMysql(mysql):
        """
            Extracts status information from a MySQL object.

            Args:
                mysql (dict): The MySQL object containing status information.

            Returns:
                dict: A dictionary containing the extracted status information.
                      - conn_host (str): The host of the MySQL connection.
                      - conn_dbname (str): The name of the MySQL database.
                      - conn_username (str): The username used for the MySQL connection.
                      - conn_port (int): The port used for the MySQL connection.
                      - ready (str): Indicates whether the MySQL database is ready or not.
        """
        statusInfo = {}
        mysqlStatus = mysql["status"]
        mysqlConn = mysqlStatus.get("connection",{})
        statusInfo["conn_host"] = mysqlConn.get("host")  # Extract the host of the MySQL connection
        statusInfo["conn_dbname"] = mysqlConn.get("dbname")  # Extract the name of the MySQL database
        statusInfo["conn_username"] = mysqlConn.get("username")  # Extract the username used for the MySQL connection
        statusInfo["conn_port"] = mysqlConn.get("port")  # Extract the port used for the MySQL connection
        statusInfo["ready"] = "True" if isDBReady(mysql) else "False"  # Check if the MySQL database is ready and set the "ready" flag accordingly
        return statusInfo
    
    def waitForDBReady(dbName: str, timeout: int, dbEngine: str):
        """
            Waits for the specified database to be ready within the given timeout period.

            Args:
                dbName (str): The name of the database.
                timeout (int): The maximum time to wait for the database to be ready, in seconds.
                dbEngine (str): The type of database engine (e.g., "Postgres", "MySQL").

            Raises:
                Exception: If the timeout period has exceeded and the database is still not ready.
        """
        now = time.time()  # Get the current time
        while (time.time() - now) < timeout:  # Loop until the timeout period has exceeded
            if dbEngine == "Postgres":
                db_object = dsmClient.getPg(dbName)  # Get the Postgres database object
            if dbEngine == "MySQL":
                db_object = dsmClient.getMysql(dbName)  # Get the MySQL database object
            if isDBReady(db_object):  # Check if the database is ready
                return db_object  # If the database is ready, return the database object
            cond = getCondition(db_object, "Ready")  # Get the "Ready" condition from the database object
            time.sleep(10)  # Sleep for 10 seconds before checking again
        raise Exception("Timed out waiting for DB to be Ready: %s" % cond)  # If the timeout period has exceeded, raise an exception

    def getReplicaCount(inputs):
        """
            Returns the replica count based on the inputs.

            Parameters:
            inputs (dict): A dictionary containing the input values.

            Returns:
            int: The replica count.
        """
        if inputs["dbengine"] == "Postgres":
            # For Postgres, the topology value will be of the format: '1 (1 (Primary + Monitor), 0 Replica)'.
            replica_val = inputs["topology"].split(",")[1]  # Split on comma and get the replica details
            replica_count = int(replica_val.split(" ")[1])  # Split on space and get the replica count
            return replica_count
        else:
            # For Mysql, the topology value will be of the format: '5 (1 Primary, 4 Replicas)'.
            # The first integer denotes the member count in a Mysql cluster.
            member_count = int(inputs["topology"].split(" ")[0])
            return member_count

    def createAndGetDbConfig(inputs):
        """
            Creates a database configuration based on the provided inputs (db options) and returns its metadata name.

            Args:
                inputs (dict): A dictionary containing the input parameters (db options) for creating the database configuration.

            Returns:
                str: The metadata name of the created database configuration.
        """
        dboptions_dict = {}
        params_dict = {}

        # Parse the dbOptions and create a dictionary
        for option in inputs["dbOptions"]:
            key = option.split("=")[0]
            val = option.split("=")[1]
            dboptions_dict[key] = val

        # Generate a random alphanumeric string and epoch time for metadata name
        random_alphanum_str = ''.join(random.choices(string.ascii_lowercase + string.digits, k=5))
        epoch_time = int(time.time())
        metadata_name = "db-config-" + random_alphanum_str + "-" + str(epoch_time)

        # Create the request body for creating the database configuration
        request_body = {
            "metadata": {
                "name": metadata_name
            },
            "apiVersion": "databases.dataservices.vmware.com/v1alpha1",
            "kind": "DatabaseConfig"
        }

        params_dict["params"] = dboptions_dict
        request_body["spec"] = params_dict

        # Call the DSM client to create the database configuration
        dsmClient.createDatabaseConfig(request_body)

        # Return the metadata name of the created database configuration
        return metadata_name

    if op == "create":
        outputs['create'] = True

        if inputs["dbengine"] == "Postgres":
            data = defByPg(inputs)
            outputs['id'] = data["metadata"]["name"]
            dsmClient.createPg(data)
        if inputs["dbengine"] == "MySQL":
            data = defByMysql(inputs)
            outputs['id'] = data["metadata"]["name"]
            dsmClient.createMysql(data)
        db_object = waitForDBReady(outputs["id"], timeout, inputs["dbengine"])

        # Reaching here indicates that the database creation had completed within the specified timeout period.
        # Update the latest status information of the database.
        if inputs["dbengine"] == "Postgres":
            outputs.update(extractStatusInfo(db_object))
        if inputs["dbengine"] == "MySQL":
            outputs.update(extractStatusInfoMysql(db_object))
    elif op == "update":
        origDbConfigName = ""

        if inputs["dbengine"] == "Postgres":
            db = dsmClient.getPg(inputs["id"])
            modifiedDb = defByPg(inputs)
        if inputs["dbengine"] == "MySQL":
            db = dsmClient.getMysql(inputs["id"])
            modifiedDb = defByMysql(inputs)

        # Get the original databaseConfig name in order to perform the necessary cleanup.
        if "databaseConfig" in db["spec"]:
            origDbConfigName = db["spec"]["databaseConfig"]["name"]

        modifiedSpec = modifiedDb["spec"]
        db["spec"]["vmClass"] = modifiedSpec["vmClass"]

        # Only allow the increase of the storage space.
        if modifiedSpec["storageSpace"] >= db["spec"]["storageSpace"]:
            db["spec"]["storageSpace"] = modifiedSpec["storageSpace"]

        if "maintenanceWindow" in modifiedDb["spec"]:
            db["spec"]["maintenanceWindow"] = modifiedSpec["maintenanceWindow"]
        else:
            # If the user is disabling the maintenance-window, then remove the maintenanceWindow key from the request-body.
            if "maintenanceWindow" in db["spec"]:
                del db["spec"]["maintenanceWindow"]

        if "databaseConfig" in modifiedDb["spec"]:
            db["spec"]["databaseConfig"] = modifiedSpec["databaseConfig"]
        else:
            # If the user is disabling the db-options, then remove the databaseConfig key from the request-body.
            if "databaseConfig" in db["spec"]:
                del db["spec"]["databaseConfig"]

        if ("backupConfig" in modifiedDb["spec"]) and ("backupLocation" in modifiedDb["spec"]):
            db["spec"]["backupConfig"] = modifiedSpec["backupConfig"]
            db["spec"]["backupLocation"] = modifiedSpec["backupLocation"]

        if inputs["dbengine"] == "Postgres":
            # Only allow the scale up of the replicas.
            if modifiedSpec["replicas"] >= db["spec"]["replicas"]:
                db["spec"]["replicas"] = modifiedSpec["replicas"]
            dsmClient.updatePg(db)
        if inputs["dbengine"] == "MySQL":
            # Only allow the scale up of the members
            if modifiedSpec["members"] >= db["spec"]["members"]:
                db["spec"]["members"] = modifiedSpec["members"]
            dsmClient.updateMysql(db)

        # If the original request-body had an entry for 'databaseconfig', then perform the necessary cleanup.
        if origDbConfigName != "":
            dsmClient.deleteDatabaseConfig(origDbConfigName)
        # XXX: Wait
    elif op == "read":
        if inputs["dbengine"] == "Postgres":
            pg = dsmClient.getPg(inputs["id"])
            pgSpec = pg["spec"]
            outputs["infraPolicy"] = pgSpec["infrastructurePolicy"]["name"]
            outputs.update(extractStatusInfo(pg))
        if inputs["dbengine"] == "MySQL":
            mysql = dsmClient.getMysql(inputs["id"])
            mysqlSpec = mysql["spec"]
            outputs["infraPolicy"] = mysqlSpec["infrastructurePolicy"]["name"]
            outputs.update(extractStatusInfoMysql(mysql))
    elif op == "delete":
        if inputs["dbengine"] == "Postgres":
            db = dsmClient.getPg(inputs["id"])
            dsmClient.deletePg(inputs["id"])
        if inputs["dbengine"] == "MySQL":
            db = dsmClient.getMysql(inputs["id"])
            dsmClient.deleteMysql(inputs["id"])

        # If the request body had an entry for 'databaseconfig', then perform the necessary cleanup.
        if "databaseConfig" in db["spec"]:
            dbConfigName = db["spec"]["databaseConfig"]["name"]
            dsmClient.deleteDatabaseConfig(dbConfigName)
        # XXX: Wait

    return outputs


def handler(context, inputs):
    """
        This function handles various actions based on the input parameters.

        Args:
            context: The context object.
            inputs: The input parameters.

        Returns:
            The outputs based on the specified action.
    """

    # Get DSM connection configuration for VRO
    dsmConnConfig = getDsmParamsForVro()
    action = inputs.get("action")
    outputs = []
    dsmClient = DsmClient(dsmConnConfig["dsmHost"],dsmConnConfig["dsmUserID"],dsmConnConfig["dsmPassword"],dsmConnConfig["dsmSkipCertificateCheck"],dsmConnConfig["dsmRootCA"])

    def getReplicaType(input_string):
        """
            Returns the replica type based on the input string.

            Args:
                input_string: The input string.

            Returns:
                The replica type (Single Server/Single vSphere Cluster).
        """
        if input_string is None:
            return "Single Server"
        parts = input_string.split('-')
        return parts[0].strip()

    if action == "form-infrapolicy":
        outputs = ["Prod", "Dev"]
        # Get list of infrastructure policies
        infraPolicyDict = dsmClient.listInfraPoliciesDict()
        outputs = list(infraPolicyDict.keys())
    elif action == "form-dbversion":
        # Get list of database versions based on the selected database engine
        dbengine = inputs.get("dbengine")
        outputs = dsmClient.listDbVersions(dbengine)
    elif action == "form-topology":
        # Get list of cluster topologies based on the selected database engine and replica mode
        dbengine = inputs.get("dbengine")
        replicamode = inputs.get("replicamode")
        outputs = dsmClient.listClusterTopologies(dbengine, getReplicaType(replicamode))
    elif action == "form-storagepolicy":
        # Get list of storage policies based on the selected infrastructure policy
        infraPolicyDict = dsmClient.listInfraPoliciesDict()
        infraPolicyName = inputs.get('infraPolicy')
        infraPolicy = infraPolicyDict.get(infraPolicyName)
        if infraPolicy is not None:
            outputs = infraPolicy["spec"]["storagePolicies"]
    elif action == "form-vmclass":
        # Get list of VM classes based on the selected infrastructure policy
        infraPolicyDict = dsmClient.listInfraPoliciesDict()
        infraPolicyName = inputs.get('infraPolicy')
        infraPolicy = infraPolicyDict.get(infraPolicyName)
        if infraPolicy is not None:
            outputs = [c["name"] for c in infraPolicy["spec"]["vmClasses"]]
    elif action == "form-backuplocation":
        # Get list of backup locations
        outputs = dsmClient.listBackupLocations()
    elif action == "form-replicamode":
        # Get list of replica modes based on the selected database engine
        dbengine = inputs.get("dbengine")
        if dbengine == "Postgres":
           outputs = ["Single Server - No Replica, protected by vSphere HA",
               "Single vSphere Cluster - Multiple nodes co-located on the same vSphere cluster."
               " Non-disruptive upgrades, and the ability to scale read heavy workloads"]
        if dbengine == "MySQL":
            outputs = ["Single Server - No Replica, protected by vSphere HA"]
    elif action == "form-connectionstring":
        # Get the database connection string
        outputs = dsmClient.getDBConnectionString(inputs)
    return outputs
