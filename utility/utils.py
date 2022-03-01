
from common.ops.abstract_ops import AbstractOps


class Utils(AbstractOps):
    """
    Utility functions for OCS
    """

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
        version = version or config.RUN["client_version"]
        bin_dir = os.path.expanduser(bin_dir or config.RUN["bin_dir"])
        client_binary_path = os.path.join(bin_dir, "oc")
        kubectl_binary_path = os.path.join(bin_dir, "kubectl")
        download_client = True
        client_version = None
        try:
            version = expose_ocp_version(version)
        except Exception:
            log.exception("Unable to expose OCP version, skipping client download.")
            skip_comparison = True
            download_client = False
            force_download = False

        if force_download:
            log.info("Forcing client download.")
        elif os.path.isfile(client_binary_path) and not skip_comparison:
            current_client_version = get_client_version(client_binary_path)
            if current_client_version != version:
                log.info(
                    f"Existing client version ({current_client_version}) does not match "
                    f"configured version ({version})."
                )
            else:
                log.debug(
                    f"Client exists ({client_binary_path}) and matches configured version, "
                    f"skipping download."
                )
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
            log.info(f"Downloading openshift client ({version}).")
            prepare_bin_dir()
            # record current working directory and switch to BIN_DIR
            previous_dir = os.getcwd()
            os.chdir(bin_dir)
            url = get_openshift_mirror_url("openshift-client", version)
            tarball = "openshift-client.tar.gz"
            download_file(url, tarball)
            run_cmd(f"tar xzvf {tarball} oc kubectl")
            delete_file(tarball)

            try:
                client_version = run_cmd(f"{client_binary_path} version --client")
            except CommandFailed:
                log.error("Unable to get version from downloaded client.")

            if client_version:
                try:
                    delete_file(client_binary_backup)
                    delete_file(kubectl_binary_backup)
                    log.info("Deleted backup binaries.")
                except FileNotFoundError:
                    pass
            else:
                try:
                    os.rename(client_binary_backup, client_binary_path)
                    os.rename(kubectl_binary_backup, kubectl_binary_path)
                    log.info("Restored backup binaries to their original location.")
                except FileNotFoundError:
                    raise ClientDownloadError(
                        "No backups exist and new binary was unable to be verified."
                    )

            # return to the previous working directory
            os.chdir(previous_dir)

        log.info(f"OpenShift Client version: {client_version}")
        return client_binary_path