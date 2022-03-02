
import os
import json
import requests
import platform
from jinja2 import Template
import yaml
from copy import deepcopy
from semantic_version import Version
from utility import constants
from timeout import TimeoutSampler
from abstract_ops import AbstractOps


class Utils(AbstractOps):
    """
    Utility functions for OCS
    """

    @staticmethod
    def get_url_content(url: str, **kwargs: dict):
        """
        Return URL content

        Args:
            url (str): URL address to return
            kwargs (dict): additional keyword arguments passed to requests.get(...)
        Returns:
            str: Content of URL
        """
        r = requests.get(url, **kwargs)
        if not r.ok:
            raise Exception(f"Couldn't load URL: {url} content!"
                            f" Status: {r.status_code}.")
        return r.content

    @staticmethod
    def get_available_ocp_versions(channel: str):
        """
        Find all available OCP versions for specific channel.

        Args:
            channel (str): Channel of OCP (e.g. stable-4.2 or fast-4.2)

        Returns
            list: Sorted list with OCP versions for specified channel.

        """
        headers = {"Accept": "application/json"}
        req = requests.get(
            constants.OPENSHIFT_UPGRADE_INFO_API.format(channel=channel), headers=headers
        )
        data = req.json()
        versions = [Version(node["version"]) for node in data["nodes"]]
        versions.sort()
        return versions

    @staticmethod
    def get_latest_ocp_version(channel: str, index: int = -1):
        """
        Find latest OCP version for specific channel.

        Args:
            channel (str): Channel of OCP (e.g. stable-4.2 or fast-4.2)
            index (int): Index to get from all available versions list
                e.g. default -1 is latest version (version[-1]). If you want to get
                previous version pass index -2 and so on.

        Returns
            str: Latest OCP version for specified channel.

        """
        versions = get_available_ocp_versions(channel)
        return str(versions[index])

    @staticmethod
    def download_file(url: str, filename: str, **kwargs):
        """
        Download a file from a specified url

        Args:
            url (str): URL of the file to download
            filename (str): Name of the file to write the download to
            kwargs (dict): additional keyword arguments passed to requests.get(...)

        """
        with open(filename, "wb") as f:
            r = requests.get(url, **kwargs)
            if not r.ok:
                raise Exception(f"The URL {url} is not available! "
                                f"Status: {r.status_code}.")
            f.write(r.content)

    @staticmethod
    def delete_file(file_name: str):
        """
        Delete file_name

        Args:
            file_name (str): Path to the file you want to delete
        """
        os.remove(file_name)

    @staticmethod
    def generate_yaml_from_jinja2_template_with_data(file_, **kwargs):
        """
        Generate yaml fron jinja2 yaml with processed data

        Args:
            file_ (str): Template Yaml file path

        Keyword Args:
            All jinja2 attributes

        Returns:
            dict: Generated from template file

        Examples:
            generate_yaml_from_template(file_='path/to/file/name', pv_data_dict')
        """
        with open(file_, "r") as stream:
            data = stream.read()
        template = Template(data)
        out = template.render(**kwargs)
        return yaml.safe_load(out)

    @staticmethod
    def dump_to_temp_yaml(src_file, dst_file, **kwargs):
        """
        Dump a jinja2 template file content into a yaml file
         Args:
            src_file (str): Template Yaml file path
            dst_file: the path to the destination Yaml file
        """
        data = generate_yaml_from_jinja2_template_with_data(src_file, **kwargs)
        with open(dst_file, "w") as yaml_file:
            yaml.dump(data, yaml_file)

    @staticmethod
    def load_yaml(file, multi_document=False):
        """
        Load yaml file (local or from URL) and convert it to dictionary

        Args:
            file (str): Path to the file or URL address
            multi_document (bool): True if yaml contains more documents

        Returns:
            dict: If multi_document == False, returns loaded data from yaml file
                with one document.
            generator: If multi_document == True, returns generator which each
                iteration returns dict from one loaded document from a file.

        """
        loader = yaml.safe_load_all if multi_document else yaml.safe_load
        if file.startswith("http"):
            return loader(get_url_content(file))
        else:
            with open(file, "r") as fs:
                return loader(fs.read())

    @staticmethod
    def get_n_document_from_yaml(yaml_generator, index=0):
        """
        Returns n document from yaml generator loaded by load_yaml with
        multi_document = True.

        Args:
            yaml_generator (generator): Generator from yaml.safe_load_all
            index (int): Index of document to return. (0 - 1st, 1 - 2nd document)

        Returns:
            dict: Data from n document from yaml file.

        Raises:
            IndexError: In case that yaml generator doesn't have such index.

        """
        for idx, document in enumerate(yaml_generator):
            if index == idx:
                return document
        raise IndexError(f"Passed yaml generator doesn't have index {index}")

    @staticmethod
    def dump_data_to_temp_yaml(data, temp_yaml):
        """
        Dump data to temporary yaml file

        Args:
            data (dict or list): dict or list (in case of multi_document) with
                data to dump to the yaml file.
            temp_yaml (str): file path of yaml file

        Returns:
            str: dumped yaml data

        """
        dumper = yaml.dump if isinstance(data, dict) else yaml.dump_all
        yaml_data = dumper(data)
        with open(temp_yaml, "w") as yaml_file:
            yaml_file.write(yaml_data)
        if isinstance(data, dict):
            yaml_data_censored = dumper(censor_values(deepcopy(data)))
        else:
            yaml_data_censored = [dumper(censor_values(deepcopy(doc))) for doc in data]
        logger.info(yaml_data_censored)
        return yaml_data

    @staticmethod
    def dump_data_to_json(data, json_file):
        """
        Dump data to json file

        Args:
            data (dict): dictionary with data to dump to the json file.
            json_file (str): file path to json file

        """
        with open(json_file, "w") as fd:
            json.dump(data, fd)

    @staticmethod
    def json_to_dict(json_file):
        """
        Converts JSON to dictionary format

        Args:
            json_file (str): file path to json file

        Returns:
             dict: JSON data in dictionary format

        """
        with open(json_file, "r") as fd:
            return json.loads(fd.read())

    @staticmethod
    def load_config_data(data_path):
        """
        Loads YAML data from the specified path

        Args:
            data_path: location of the YAML data file

        Returns: loaded YAML data

        """
        with open(data_path, "r") as data_descriptor:
            return yaml.load(data_descriptor, Loader=yaml.FullLoader)

    @staticmethod
    def to_nice_yaml(a, indent=2, *args, **kw):
        """
        This is a j2 filter which allows you from dictionary to print nice human
        readable yaml.

        Args:
            a (dict): dictionary with data to print as yaml
            indent (int): number of spaces for indent to be applied for whole
                dumped yaml. First line is not indented! (default: 2)
            *args: Other positional arguments which will be passed to yaml.dump
            *args: Other keywords arguments which will be passed to yaml.dump

        Returns:
            str: transformed yaml data in string format
        """
        transformed = yaml.dump(
            a,
            Dumper=yaml.Dumper,
            indent=indent,
            allow_unicode=True,
            default_flow_style=False,
            **kw,
        )
        return transformed

    @staticmethod
    def censor_values(data_to_censor):
        """
        This function censor string and numeric values in dictionary based on
        keys that match pattern defined in config_keys_patterns_to_censor in
        constants. It is performed recursively for nested dictionaries.

        Args:
            data_to_censor (dict): Data to censor.

        Returns:
            dict: filtered data

        """
        for key in data_to_censor:
            if isinstance(data_to_censor[key], dict):
                censor_values(data_to_censor[key])
            elif isinstance(data_to_censor[key], (str, int, float)):
                for pattern in constants.config_keys_patterns_to_censor:
                    if pattern in key.lower():
                        data_to_censor[key] = "*" * 5
        return data_to_censor

    def ocsci_log_path(self):
        """
        Construct the full path for the log directory.

        Returns:
            str: full path for ocs-ci log directory

        """
        return os.path.expanduser(
            os.path.join(self.config['RUN']["log_dir"], f"ocs-ci-logs")
        )

    def get_client_version(self, client_binary_path: str):
        """
        Get version reported by `oc version`.

        Args:
            client_binary_path (str): path to `oc` binary

        Returns:
            str: version reported by `oc version`.
                None if the client does not exist at the provided path.

        """
        if os.path.isfile(client_binary_path):
            cmd = f"{client_binary_path} version --client -o json"
            resp = self.exec_cmd(cmd)
            stdout = json.loads(resp.stdout.decode())
            return stdout["releaseClientVersion"]

    def prepare_bin_dir(self, bin_dir: str = None):
        """
        Prepare bin directory for OpenShift client and installer

        Args:
            bin_dir (str): Path to bin directory (default: config.RUN['bin_dir'])
        """
        bin_dir = os.path.expanduser(bin_dir)
        try:
            os.mkdir(bin_dir)
            self.logger.info(f"Directory '{bin_dir}' successfully created.")
        except FileExistsError:
            self.logger.debug(f"Directory '{bin_dir}' already exists.")

    def get_openshift_mirror_url(self, file_name: str, version: str):
        """
        Format url to OpenShift mirror (for client and installer download).

        Args:
            file_name (str): Name of file
            version (str): Version of the installer or client to download

        Returns:
            str: Url of the desired file (installer or client)

        Raises:
            UnsupportedOSType: In case the OS type is not supported
            UnavailableBuildException: In case the build url is not reachable
        """
        if platform.system() == "Darwin":
            os_type = "mac"
        elif platform.system() == "Linux":
            os_type = "linux"
        else:
            raise Exception("Unsupported OS type")

        url_template = self.config['DEPLOYMENT'].get(
            "ocp_url_template",
            "https://openshift-release-artifacts.apps.ci.l2s4.p1.openshiftapps.com/"
            "{version}/{file_name}-{os_type}-{version}.tar.gz",
        )
        url = url_template.format(version=version, file_name=file_name,
                                  os_type=os_type)
        logger_obj = self.get_framework_logger()
        sample = TimeoutSampler(
            timeout=540,
            sleep=5,
            log_obj = logger_obj,
            func=ensure_nightly_build_availability,
            build_url=url
        )
        if not sample.wait_for_func_status(result=True):
            raise Exception(f"The build url {url} is not reachable")
        return url

    def expose_ocp_version(self, version: str):
        """
        This helper function exposes latest nightly version or GA version of OCP.
        When the version string ends with .nightly (e.g. 4.2.0-0.nightly) it will
        expose the version to latest accepted OCP build
        (e.g. 4.2.0-0.nightly-2019-08-08-103722)
        If the version ends with -ga than it will find the latest GA OCP version
        and will expose 4.2-ga to for example 4.2.22.

        Args:
            version (str): Verison of OCP

        Returns:
            str: Version of OCP exposed to full version if latest nighly passed

        """
        if version.endswith(".nightly"):
            latest_nightly_url = (
                f"https://amd64.ocp.releases.ci.openshift.org/api/v1/"
                f"releasestream/{version}/latest"
            )
            version_url_content = get_url_content(latest_nightly_url)
            version_json = json.loads(version_url_content)
            return version_json["name"]
        if version.endswith("-ga"):
            channel = self.config['DEPLOYMENT'].get("ocp_channel", "stable")
            ocp_version = version.rstrip("-ga")
            index = self.config['DEPLOYMENT'].get("ocp_version_index", -1)
            return get_latest_ocp_version(f"{channel}-{ocp_version}", index)
        else:
            return version

    def get_openshift_client(self, version: str = None, bin_dir: str = None,
                             force_download: bool = False,
                             skip_comparison: bool = False):
        """
        Download the OpenShift client binary, if not already present.
        Update env. PATH and get path of the oc binary.

        Args:
            version (str): Version of the client to download
                (default: config.RUN['client_version'])
            bin_dir (str): Path to bin directory (default: config.RUN['bin_dir'])
            force_download (bool): Force client download even if already present
            skip_comparison (bool): Skip the comparison between the existing OCP client
                version and the configured one.

        Returns:
            str: Path to the client binary

        """
        version = version or self.config['RUN']['client_version']
        bin_dir = bin_dir or self.config['RUN']["bin_dir"]
        client_binary_path = os.path.join(bin_dir, "oc")
        kubectl_binary_path = os.path.join(bin_dir, "kubectl")
        download_client = True
        client_version = None
        try:
            version = self.expose_ocp_version(version)
        except Exception:
            self.logger.error("Unable to expose OCP version, "
                              "skipping client download.")
            skip_comparison = True
            download_client = False
            force_download = False

        if force_download:
            self.logger.info("Forcing client download.")
        elif os.path.isfile(client_binary_path) and not skip_comparison:
            current_client_version = self.get_client_version(client_binary_path)
            if current_client_version != version:
                self.logger.info("Existing client version "
                                 f"({current_client_version}) does not match"
                                 f"configured version ({version}).")
            else:
                self.logger.debug(f"Client exists ({client_binary_path})"
                                  " and matches configured version, "
                                  "skipping download.")
                download_client = False

        if download_client:
            # Move existing client binaries to backup location
            client_binary_backup = f"{client_binary_path}.bak"
            kubectl_binary_backup = f"{kubectl_binary_path}.bak"

            try:
                os.rename(client_binary_path, client_binary_backup)
                os.rename(kubectl_binary_path, kubectl_binary_backup)
            except FileNotFoundError:
                pass

            # Download the client
            self.logger.info(f"Downloading openshift client ({version}).")
            self.prepare_bin_dir(bin_dir)
            # record current working directory and switch to BIN_DIR
            previous_dir = os.getcwd()
            os.chdir(bin_dir)
            url = self.get_openshift_mirror_url("openshift-client", version)
            tarball = "openshift-client.tar.gz"
            download_file(url, tarball)
            self.exec_cmd(f"tar xzvf {tarball} oc kubectl")
            delete_file(tarball)

            try:
                client_version = self.exec_cmd(f"{client_binary_path} version --client")
            except CommandFailed:
                self.logger.error("Unable to get version from downloaded client.")

            if client_version:
                try:
                    delete_file(client_binary_backup)
                    delete_file(kubectl_binary_backup)
                    self.logger.info("Deleted backup binaries.")
                except FileNotFoundError:
                    pass
            else:
                try:
                    os.rename(client_binary_backup, client_binary_path)
                    os.rename(kubectl_binary_backup, kubectl_binary_path)
                    self.logger.info("Restored backup binaries to their original location.")
                except FileNotFoundError:
                    raise Exception("No backups exist and new binary was"
                                    " unable to be verified.")

            # return to the previous working directory
            os.chdir(previous_dir)

        self.logger.info(f"OpenShift Client version: {client_version}")
        return client_binary_path

    def get_openshift_installer(version: str = None, bin_dir: str = None,
                                force_download: bool = False,):
        """
        Download the OpenShift installer binary, if not already present.
        Update env. PATH and get path of the openshift installer binary.

        Args:
            version (str): Version of the installer to download
            bin_dir (str): Path to bin directory (default: config.RUN['bin_dir'])
            force_download (bool): Force installer download even if already present

        Returns:
            str: Path to the installer binary

        """
        version = version or self.config['DEPLOYMENT']["installer_version"]
        bin_dir = os.path.expanduser(bin_dir or config['RUN']["bin_dir"])
        installer_filename = "openshift-install"
        installer_binary_path = os.path.join(bin_dir, installer_filename)
        if os.path.isfile(installer_binary_path) and force_download:
            delete_file(installer_binary_path)
        if os.path.isfile(installer_binary_path):
            self.logger.debug(f"Installer exists ({installer_binary_path})"
                              ", skipping download.")
            # TODO: check installer version
        else:
            version = self.expose_ocp_version(version)
            self.logger.info(f"Downloading openshift installer ({version}).")
            self.prepare_bin_dir()
            # record current working directory and switch to BIN_DIR
            previous_dir = os.getcwd()
            os.chdir(bin_dir)
            tarball = f"{installer_filename}.tar.gz"
            url = self.get_openshift_mirror_url(installer_filename, version)
            download_file(url, tarball)
            self.exec_cmd(f"tar xzvf {tarball} {installer_filename}")
            delete_file(tarball)
            # return to the previous working directory
            os.chdir(previous_dir)

        installer_version = self.exec_cmd(f"{installer_binary_path} version")
        self.logger.info(f"OpenShift Installer version: {installer_version}")
        return installer_binary_path

    def log_ocs_version(self):
        """
        Fixture handling version reporting for OCS.

        This fixture handles alignment of the version reporting, so that we:

         * report version for each test run (no matter if just deployment, just
           test or both deployment and tests are executed)
         * prevent conflict of version reporting with deployment/teardown (eg. we
           should not run the version logging before actual deployment, or after
           a teardown)

        Version is reported in:

         * log entries of INFO log level during test setup phase
         * ocs_version file in cluster path directory (for copy pasting into bug
           reports)
        """
        teardown = self.config['RUN']["cli_params"].get("teardown")
        deploy = self.config['RUN']["cli_params"].get("deploy")
        dev_mode = self.config['RUN']["cli_params"].get("dev_mode")
        skip_ocs_deployment = self.config['ENV_DATA']["skip_ocs_deployment"]
        if teardown and not deploy:
            self.logger.info("Skipping version reporting for teardown.")
            return
        elif dev_mode:
            self.logger.info("Skipping version reporting for development mode.")
            return
        elif skip_ocs_deployment:
            self.logger.info("Skipping version reporting since OCS deployment is skipped.")
            return
        elif deploy:
            self.logger.info("Deploying OCP")
        # cluster_version = get_ocp_version_dict()
        # image_dict = get_ocs_version()
        # file_name = os.path.join(self.config['ENV_DATA']["cluster_path"],
        #                          "ocs_version." + datetime.now().isoformat())
        # with open(file_name, "w") as file_obj:
        #     report_ocs_version(cluster_version, image_dict, file_obj)
        # self.logger.info("human readable ocs version info written into %s", file_name)

    def cluster(self):
        """
        This fixture initiates deployment for both OCP and OCS clusters.
        Specific platform deployment classes will handle the fine details
        of action
        """
        self.logger.info(f"All logs located at {self.ocsci_log_path()}")

        teardown = self.config['RUN']["cli_params"]["teardown"]
        deploy = self.config['RUN']["cli_params"]["deploy"]
        if teardown or deploy:
            factory = dep_factory.DeploymentFactory()
            deployer = factory.get_deployment()

        # Add a finalizer to teardown the cluster after test execution is finished
        if teardown:
            deployer.destroy_cluster()
            self.logger.info("Will teardown cluster because --teardown was provided")

        # Download client
        if config.DEPLOYMENT["skip_download_client"]:
            self.logger.info("Skipping client download")
        else:
            force_download = (
                self.config['RUN']["cli_params"].get("deploy")
                and self.config['DEPLOYMENT']["force_download_client"]
            )
            self.get_openshift_client(force_download=force_download)

        # # set environment variable for early testing of RHCOS
        # if config.ENV_DATA.get("early_testing"):
        #     release_img = config.ENV_DATA["RELEASE_IMG"]
        #     log.info(f"Running early testing of RHCOS with release image: {release_img}")
        #     os.environ["RELEASE_IMG"] = release_img
        #     os.environ["OPENSHIFT_INSTALL_RELEASE_IMAGE_OVERRIDE"] = release_img

        if deploy:
            # Deploy cluster
            deployer.deploy_cluster()
        # else:
        #     if config.ENV_DATA["platform"] == constants.IBMCLOUD_PLATFORM:
        #         ibmcloud.login()
        # if not config.ENV_DATA["skip_ocs_deployment"]:
        #     record_testsuite_property("rp_ocs_build", get_ocs_build_number())