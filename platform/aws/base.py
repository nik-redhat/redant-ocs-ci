class AWSBase(CloudDeploymentBase):

    # default storage class for StorageCluster CRD on AWS platform
    DEFAULT_STORAGECLASS = "gp2"

    def __init__(self):
        """
        This would be base for both IPI and UPI deployment
        """
        super(AWSBase, self).__init__()
        self.aws = AWSUtil(self.region)
        # dict of cluster prefixes with special handling rules (for existence
        # check or during a cluster cleanup)
        self.cluster_prefixes_special_rules = CLUSTER_PREFIXES_SPECIAL_RULES

    def deploy_ocp(self, log_cli_level="DEBUG"):
        super(AWSBase, self).deploy_ocp(log_cli_level)
        ocp_version = version.get_semantic_ocp_version_from_config()
        ocs_version = version.get_semantic_ocs_version_from_config()

        if ocs_version >= version.VERSION_4_10 and ocp_version >= version.VERSION_4_9:
            # If we don't customize the storage class, we will use the default one
            self.DEFAULT_STORAGECLASS = config.DEPLOYMENT.get(
                "customized_deployment_storage_class", self.DEFAULT_STORAGECLASS
            )

    def host_network_update(self):
        """
        Update security group rules for HostNetwork
        """
        cluster_id = get_infra_id(self.cluster_path)
        worker_pattern = f"{cluster_id}-worker*"
        worker_instances = self.aws.get_instances_by_name_pattern(worker_pattern)
        security_groups = worker_instances[0]["security_groups"]
        sg_id = security_groups[0]["GroupId"]
        security_group = self.aws.ec2_resource.SecurityGroup(sg_id)
        # The ports are not 100 % clear yet. Taken from doc:
        # https://docs.google.com/document/d/1c23ooTkW7cdbHNRbCTztprVU6leDqJxcvFZ1ZvK2qtU/edit#
        security_group.authorize_ingress(
            DryRun=False,
            IpPermissions=[
                {
                    "FromPort": 6800,
                    "ToPort": 7300,
                    "IpProtocol": "tcp",
                    "UserIdGroupPairs": [
                        {
                            "Description": "Ceph OSDs",
                            "GroupId": sg_id,
                        },
                    ],
                },
                {
                    "FromPort": 3300,
                    "ToPort": 3300,
                    "IpProtocol": "tcp",
                    "UserIdGroupPairs": [
                        {
                            "Description": "Ceph MONs rule1",
                            "GroupId": sg_id,
                        },
                    ],
                },
                {
                    "FromPort": 6789,
                    "ToPort": 6789,
                    "IpProtocol": "tcp",
                    "UserIdGroupPairs": [
                        {
                            "Description": "Ceph MONs rule2",
                            "GroupId": sg_id,
                        },
                    ],
                },
                {
                    "FromPort": 8443,
                    "ToPort": 8443,
                    "IpProtocol": "tcp",
                    "UserIdGroupPairs": [
                        {
                            "Description": "Ceph Dashboard rule1",
                            "GroupId": sg_id,
                        },
                    ],
                },
                {
                    "FromPort": 8080,
                    "ToPort": 8080,
                    "IpProtocol": "tcp",
                    "UserIdGroupPairs": [
                        {
                            "Description": "Ceph Dashboard rule2",
                            "GroupId": sg_id,
                        },
                    ],
                },
            ],
        )

    def add_node(self):
        # TODO: Implement later
        super(AWSBase, self).add_node()

    def check_cluster_existence(self, cluster_name_prefix):
        """
        Check cluster existence according to cluster name prefix

        Returns:
            bool: True if a cluster with the same name prefix already exists,
                False otherwise

        """
        cluster_name_pattern = cluster_name_prefix + "*"
        instances = self.aws.get_instances_by_name_pattern(cluster_name_pattern)
        instance_objs = [self.aws.get_ec2_instance(ins.get("id")) for ins in instances]
        non_terminated_instances = [
            ins
            for ins in instance_objs
            if ins.state.get("Code") != constants.INSTANCE_TERMINATED
        ]
        if non_terminated_instances:
            logger.error(
                f"Non terminated EC2 instances with the same name prefix were"
                f" found: {[ins.id for ins in non_terminated_instances]}"
            )
            return True
        return False