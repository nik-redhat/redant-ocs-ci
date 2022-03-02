import os
import sys
from socket import timeout
import copy
import traceback
import paramiko
from halo import Halo
from shutil import which
sys.path.insert(1, ".")
from utility.mixin import RedantMixin


class Environ:
    """
    Framework level control on the gluster environment. Controlling both
    the setup and the cleanup.
    """

    def __init__(self, param_obj, es, error_handler,
                 log_path: str, log_level: str):
        """
        Redant mixin obj to be used for server setup and teardown operations
        has to be created.
        """
        self.spinner = Halo(spinner='dots')
        self.redant = RedantMixin(es, [True])
        self.redant.init_logger("environ", log_path, log_level)
        self.config = param_obj.get_config_hashmap()

    def get_framework_logger(self):
        """
        To return the framework logger object
        """
        return self.redant.logger

    def set_kubeconfig(self, kubeconfig_path):
        """
        Export environment variable KUBECONFIG for future calls of OC commands
        or other API calls

        Args:
            kubeconfig_path (str): path to kubeconfig file to be exported

        Returns:
            boolean: True if successfully connected to cluster, False otherwise
        """
        # Test cluster access
        print("Testing access to cluster with %s", kubeconfig_path)
        if not os.path.isfile(kubeconfig_path):
            # log.warning("The kubeconfig file %s doesn't exist!", kubeconfig_path)
            return False
        os.environ["KUBECONFIG"] = kubeconfig_path
        if not which("oc"):
            self.redant.get_openshift_client()
        try:
            self.redant.exec_cmd("oc cluster-info")
        except CommandFailed as ex:
            print("Cluster is not ready to use: %s", ex)
            return False
        print("Access to cluster is OK!")
        return True

    def setup_env(self, kubeconfig_path):
        """
        Setting up of the environment before the TC execution begins.
        """
        # invoke the hard reset or hard terminate.
        self.spinner.start("Setting up environment")
        self.redant.set_kubeconfig(kubeconfig_path)
        self.redant.log_ocs_version()
        self.redant.deploy_cluster()
        try:
            self.redant.start_glusterd(self.server_list)
            self.redant.create_cluster(self.server_list)
            self.redant.wait_till_all_peers_connected(self.server_list)
            self._check_and_copy_scripts()
            self._check_and_install_scripts()
            self.redant.logger.info("Environment setup success.")
            self.spinner.succeed("Environment setup successful.")
        except Exception as error:
            tb = traceback.format_exc()
            self.redant.logger.error(f"Environment setup failure : {error}")
            self.redant.logger.error(tb)
            self.spinner.fail("Environment setup failed.")
            sys.exit(0)

    def teardown_env(self):
        """
        The teardown of the complete environment once the test framework
        ends.
        """
        self.spinner.start("Tearing down environment.")
        try:
            self.redant.hard_terminate(self.server_list, self.client_list,
                                       self.brick_root)
            self.redant.logger.info("Environment teardown success.")
            self.spinner.succeed("Tearing down successful.")
        except Exception as error:
            tb = traceback.format_exc()
            self.redant.logger.error(f"Environment teardown failure : {error}")
            self.redant.logger.error(tb)
            self.spinner.fail("Environment Teardown failed.")


# class FrameworkEnv:
#     """
#     A class for handling the framework environemnt details. This won't
#     affect the environment directly. It is more of a data store.
#     """

#     __instance = None

#     @staticmethod
#     def getInstance():
#         """ Static access method """
#         if FrameworkEnv.__instance is None:
#             FrameworkEnv()
#         return FrameworkEnv.__instance

#     def __init__(self):
#         """ vpc """
#         if FrameworkEnv.__instance is not None:
#             raise Exception("Singleton class can have only one Instance.")
#         else:
#             FrameworkEnv.__instance = self

#     def init_ds(self):
#         """
#         Method to handle the creation of data structures to store the
#         current state of the environment used to run the framework.
#         """
#         self.volds = {}
#         self.clusteropt = {}
#         self.snapm = {}

#     def _validate_volname(self, volname: str):
#         """
#         A helper function to validate incoming volname parameters if
#         its valid.
#         Arg:
#             volname (str)
#         """
#         if volname not in self.volds.keys():
#             raise Exception(f"No such volume called {volname}")

#     def set_new_volume(self, volname: str, brickdata: dict):
#         """
#         Add a new volume when created to volds.
#         Args:
#             volname (str)
#             brickdata (dict) : dictionary containing objects with key as
#                                node ip and values as list of bricks lying
#                                under the said node.
#         """
#         self.volds[volname] = {"started": False, "options": {},
#                                "mountpath": {}, "brickdata": brickdata,
#                                "voltype": {"dist_count": 0,
#                                            "replica_count": 0,
#                                            "disperse_count": 0,
#                                            "arbiter_count": 0,
#                                            "redundancy_count": 0,
#                                            "transport": ""}}

#     def reset_ds(self):
#         """
#         Method to reset the DSs.
#         """
#         self.volds = {}
#         self.clusteropt = {}
#         self.snapm = {}

#     def get_volnames(self) -> list:
#         """
#         Method returns a list of existing volume names
#         Returns:
#             list : list of volume names
#         """
#         return list(self.volds.keys())

#     def does_volume_exists(self, volname: str) -> bool:
#         """
#         Method checks if the said volume already exists.
#         Arg:
#             volname (str)
#         Returns:
#             True: If volume exists, else False
#         """
#         if volname in list(self.volds.keys()):
#             return True
#         return False

#     def remove_volume_data(self, volname: str):
#         """
#         Removing a volume's data from the volds.
#         Arg:
#             volname (str)
#         """
#         self._validate_volname(volname)
#         del self.volds[volname]

#     def get_volume_dict(self, volname: str) -> dict:
#         """
#         Get the volume dictionary for requested volume.
#         Arg:
#             volname (str)
#         Returns:
#             volds dictionary specific to given volume.
#         """
#         self._validate_volname(volname)
#         return self.volds[volname]

#     def get_volds(self) -> dict:
#         """
#         Get the volds.
#         Returns:
#             volds dictionary as a whole.
#         """
#         return copy.deepcopy(self.volds)
