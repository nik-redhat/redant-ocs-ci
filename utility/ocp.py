"""
This module provides base class for OCP deployment.
"""
import os
import json

import yaml

from utility import constants
from templating import Templating


class OCPDeployment:
    def __init__(self):
        """
        Constructor for OCPDeployment class
        """
        self.pull_secret = {}
        self.metadata = {}
        self.config = self.get_config_hashmap()
        self.deployment_platform = self.config['ENV_DATA']["platform"].lower()
        self.deployment_type = config['ENV_DATA']["deployment_type"].lower()
        if not hasattr(self, "flexy_deployment"):
            self.flexy_deployment = False
        if (not self.flexy_deployment
            and self.deployment_platform != constants.IBMCLOUD_PLATFORM):
            self.installer = self.download_installer()
        self.cluster_path = self.config['ENV_DATA']["cluster_path"]
        self.cluster_name = self.config['ENV_DATA']["cluster_name"]

    def download_installer(self):
        """
        Method to download installer

        Returns:
            str: path to the installer
        """
        force_download = (
            self.config['RUN']["cli_params"].get("deploy")
            and self.config['DEPLOYMENT']["force_download_installer"]
        )
        return self.get_openshift_installer(
            self.config['DEPLOYMENT']["installer_version"], force_download=force_download
        )

    def get_pull_secret(self):
        """
        Load pull secret file

        Returns:
            dict: content of pull secret
        """
        pull_secret_path = os.path.join(constants.TOP_DIR, "data", "pull-secret")
        with open(pull_secret_path, "r") as f:
            # Parse, then unparse, the JSON file.
            # We do this for two reasons: to ensure it is well-formatted, and
            # also to ensure it ends up as a single line.
            return json.dumps(json.loads(f.read()))

    def get_ssh_key(self):
        """
        Loads public ssh to be used for deployment

        Returns:
            str: public ssh key or empty string if not found

        """
        ssh_key = os.path.expanduser(self.config['DEPLOYMENT'].get("ssh_key"))
        if not os.path.isfile(ssh_key):
            return ""
        with open(ssh_key, "r") as fs:
            lines = fs.readlines()
            return lines[0].rstrip("\n") if lines else ""

    def deploy_prereq(self):
        """
        Perform generic prereq before calling openshift-installer
        This method performs all the basic steps necessary before invoking the
        installer
        """
        deploy = self.config['RUN']["cli_params"]["deploy"]
        teardown = self.config['RUN']["cli_params"]["teardown"]
        if teardown and not deploy:
            msg = "Attempting teardown of non-accessible cluster: "
            msg += f"{self.cluster_path}"
            raise Exception(msg)
        elif not deploy and not teardown:
            msg = ("The given cluster can not be connected to: "
                   f"{self.cluster_path}")
            msg += ("Provide a valid --cluster-path or use --deploy to "
                    "deploy a new cluster")
            raise Exception(msg)
        elif not system.is_path_empty(self.cluster_path) and deploy:
            msg = f"The given cluster path is not empty: {self.cluster_path}"
            msg += ("Provide an empty --cluster-path and --deploy to deploy "
                    "a new cluster")
            raise Exception(msg)
        else:
            self.logger.info("A testing cluster will be deployed and cluster"
                             f" information stored at: {self.cluster_path}")
        if (
            not self.flexy_deployment
            and self.config['ENV_DATA']["deployment_type"] != "managed"
        ):
            self.create_config()

    def create_config(self):
        """
        Create the OCP deploy config, if something needs to be changed for
        specific platform you can overload this method in child class.
        """
        # Generate install-config from template
        self.logger.info("Generating install-config")
        _templating = templating.Templating()
        ocp_install_template = (
            f"install-config-{self.deployment_platform}-"
            f"{self.deployment_type}.yaml.j2"
        )
        ocp_install_template_path = os.path.join("ocp-deployment", ocp_install_template)
        install_config_str = _templating.render_template(
            ocp_install_template_path, config.ENV_DATA
        )
        # Log the install config *before* adding the pull secret,
        # so we don't leak sensitive data.
        self.logger.info(f"Install config: \n{install_config_str}")
        # Parse the rendered YAML so that we can manipulate the object directly
        install_config_obj = yaml.safe_load(install_config_str)
        install_config_obj["pullSecret"] = self.get_pull_secret()
        ssh_key = self.get_ssh_key()
        if ssh_key:
            install_config_obj["sshKey"] = ssh_key
        install_config_str = yaml.safe_dump(install_config_obj)
        install_config = os.path.join(self.cluster_path, "install-config.yaml")
        with open(install_config, "w") as f:
            f.write(install_config_str)

    def deploy(self, log_cli_level="DEBUG"):
        """
        Implement ocp deploy in specific child class
        """
        raise Exception("deploy_ocp functionality not implemented")

    # def test_cluster(self):
    #     """
    #     Test if OCP cluster installed successfuly
    #     """
    #     # Test cluster access
    #     if not OCP.set_kubeconfig(
    #         os.path.join(
    #             self.cluster_path,
    #             config.RUN.get("kubeconfig_location"),
    #         )
    #     ):
    #         pytest.fai("Cluster is not available!")

    def destroy(self, log_level="DEBUG"):
        """
        Destroy OCP cluster specific

        Args:
            log_level (str): log level openshift-installer (default: DEBUG)

        """
        # Retrieve cluster metadata
        metadata_file = os.path.join(self.cluster_path, "metadata.json")
        with open(metadata_file) as f:
            self.metadata = json.loads(f.read())
        self.destroy_cluster(
            installer=self.installer,
            cluster_path=self.cluster_path,
            log_level=log_level,
        )
