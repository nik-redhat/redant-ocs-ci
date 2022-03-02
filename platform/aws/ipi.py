"""
This module contains platform specific methods and classes for deployment
on AWS platform
"""
import logging
import os
import shutil
from subprocess import PIPE, Popen

import boto3

from ocs_ci.cleanup.aws.defaults import CLUSTER_PREFIXES_SPECIAL_RULES
from ocs_ci.deployment.ocp import OCPDeployment as BaseOCPDeployment
from ocs_ci.framework import config
from ocs_ci.ocs import constants, exceptions, ocp, machine
from ocs_ci.ocs.resources import pod
from ocs_ci.utility import templating, version
from ocs_ci.utility.aws import (
    AWS as AWSUtil,
    create_and_attach_volume_for_all_workers,
    delete_cluster_buckets,
    destroy_volumes,
    get_rhel_worker_instances,
    terminate_rhel_workers,
)
from ocs_ci.utility.bootstrap import gather_bootstrap
from ocs_ci.utility.mirror_openshift import prepare_mirror_openshift_credential_files
from ocs_ci.utility.retry import retry
from ocs_ci.utility.utils import (
    clone_repo,
    create_rhelpod,
    delete_file,
    get_cluster_name,
    get_infra_id,
    get_ocp_repo,
    run_cmd,
    TimeoutSampler,
    get_ocp_version,
)
from semantic_version import Version
from .cloud import CloudDeploymentBase
from .cloud import IPIOCPDeployment
from .flexy import FlexyAWSUPI

class AWSIPI(AWSBase):
    """
    A class to handle AWS IPI specific deployment
    """

    OCPDeployment = IPIOCPDeployment

    def __init__(self):
        self.name = self.__class__.__name__
        super(AWSIPI, self).__init__()

    def deploy_ocp(self, log_cli_level="DEBUG"):
        """
        Deployment specific to OCP cluster on this platform

        Args:
            log_cli_level (str): openshift installer's log level
                (default: "DEBUG")
        """
        super(AWSIPI, self).deploy_ocp(log_cli_level)
        if config.DEPLOYMENT.get("infra_nodes"):
            num_nodes = config.ENV_DATA.get("infra_replicas", 3)
            ms_list = machine.create_ocs_infra_nodes(num_nodes)
            for node in ms_list:
                machine.wait_for_new_node_to_be_ready(node)
        if config.DEPLOYMENT.get("host_network"):
            self.host_network_update()
        lso_type = config.DEPLOYMENT.get("type")
        if lso_type == constants.AWS_EBS:
            create_and_attach_volume_for_all_workers()

    def destroy_cluster(self, log_level="DEBUG"):
        """
        Destroy OCP cluster specific to AWS IPI

        Args:
            log_level (str): log level openshift-installer (default: DEBUG)
        """
        destroy_volumes(self.cluster_name)
        delete_cluster_buckets(self.cluster_name)
        super(AWSIPI, self).destroy_cluster(log_level)