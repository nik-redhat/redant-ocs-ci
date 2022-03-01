"""
This file contains one class - AbstractOps which
is inherited by the ops library and the ops library
call the functions in the AbstractOps which in turn
call the funtions in the remote executioner which is
responsible for executing commands on the nodes or execute
commands locally.
"""
import subprocess
from collections import OrderedDict


class AbstractOps:
    """
    This class contains functions which is responsible for
    executing commands on remote node or local machine.
    """

    def remote_exec_cmd_abstract_op(self, cmd: str, node: str = None,
                                    excep: bool = True):
        """
        Calls the function in the remote executioner to execute
        commands on the nodes. Logging is also performed along
        with handling exceptions while executng the commands.
        Args:
            cmd  (str): the command to be executed by the rexe
        Kwargs:
            node (str): the node on which the command as to be executed.
                        If the node is None then the rexe chooses the
                        node randomly and executes the command on it.
            excep (bool): exception flag to bypass the exception if the
                          cmd fails. If set to False the exception is
                          bypassed and value from remote executioner is
                          returned. Defaults to True

        """
        self.logger.info(f"Running {cmd} on {node}")

        ret = self.remote_exec_cmd(cmd, node)

        if not excep:
            return ret

        if ret['error_code'] != 0:
            self.logger.error(ret['error_msg'])
            raise Exception(ret['error_msg'])
        elif isinstance(ret['msg'], (OrderedDict, dict)):
            if int(ret['msg']['opRet']) != 0:
                self.logger.error(ret['msg']['opErrstr'])
                raise Exception(ret['msg']['opErrstr'])

        return ret

    def remote_exec_cmd_multinode_abstract_op(self, cmd: str,
                                              node: list = None,
                                              excep: bool = True):
        """
        Calls the function in the remote executioner to execute
        commands on the nodes. Logging is also performed along
        with handling exceptions while executng the commands.
        Args:
            cmd  (str): the command to be executed by the rexe
            node (list): the list of nodes on which the command as to be
                         executed. If the node is None then the rexe chooses
                         the node randomly and executes the command on it.

            excep (bool): exception flag to bypass the exception if the
                          cmd fails. If set to False the exception is
                          bypassed and value from remote executioner is
                          returned. Defaults to True
        """
        self.logger.info(f"Running {cmd} on {node}")

        ret = self.remote_exec_cmd_multinode(cmd, node)

        if not excep:
            return ret

        for each_ret in ret:
            if each_ret['error_code'] != 0:
                self.logger.error(each_ret['error_msg'])
                raise Exception(each_ret['error_msg'])
            elif isinstance(each_ret['msg'], (OrderedDict, dict)):
                if int(each_ret['msg']['opRet']) != 0:
                    self.logger.error(each_ret['msg']['opErrstr'])
                    raise Exception(each_ret['msg']['opErrstr'])

        return ret

    def exec_cmd(self, cmd: str, secrets: list = None, timeout: int = 600,
                 excep: bool = True, **kwargs):
        """
        Run an arbitrary command locally

        Args:
            cmd (str): command to run
            secrets (list): A list of secrets to be masked with asterisks
                            This kwarg is popped in order to not interfere
                            with subprocess.run(``**kwargs``)
            timeout (int): Timeout for the command, defaults to 600 seconds.
            excep (bool): True if handle exceptions here in the op.
                          Else, False to handle errors manually

        Returns:
            (CompletedProcess) A CompletedProcess object of the command that was executed
            CompletedProcess attributes:
            args: The list or str args passed to run().
            returncode (str): The exit code of the process, negative for signals.
            stdout     (str): The standard output (None if not captured).
            stderr     (str): The standard error (None if not captured).

        """
        # masked_cmd = mask_secrets(cmd, secrets)
        self.logger.info(f"Executing command: {cmd}")
        if isinstance(cmd, str):
            cmd = shlex.split(cmd)
        completed_process = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.PIPE,
            timeout=timeout,
            **kwargs,
        )
        # masked_stdout = mask_secrets(completed_process.stdout.decode(), secrets)
        # if len(completed_process.stdout) > 0:
        #     log.debug(f"Command stdout: {masked_stdout}")
        # else:
        #     log.debug("Command stdout is empty")

        # masked_stderr = mask_secrets(completed_process.stderr.decode(), secrets)
        # if len(completed_process.stderr) > 0:
        #     log.warning(f"Command stderr: {masked_stderr}")
        # else:
        #     log.debug("Command stderr is empty")
        self.logger.debug(f"Command return code: {completed_process.returncode}")
        if completed_process.returncode and excep:
            raise Exception(f"Error during execution of command: {cmd}."
                            f"\nError is {completed_process.stderr}")
        return completed_process

