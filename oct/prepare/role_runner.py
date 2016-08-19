from collections import namedtuple

from ansible.executor.task_queue_manager import TaskQueueManager
from ansible.inventory import Inventory
from ansible.parsing.dataloader import DataLoader
from ansible.playbook import Play
from ansible.vars import VariableManager


class RoleRunner:
    '''
    This class allows for a simple abstraction around the loading
    and execution of an Ansible role or roles given an inventory
    and variables to expose to the roles.
    '''

    def __init__(self,
                 variable_manager=VariableManager(), data_loader=DataLoader(), host_list=None, passwords=None,
                 connection='local', module_path='', forks=5, become=None, become_method=None, become_user=None, check=False
                 ):
        """
        Initialize a RoleRunner.

        :param variable_manager: instance of an Ansible variable manager
        :param data_loader: instance of an Ansible data loader
        :param host_list: either a literal list of hosts or the path to an inventory file
        :param passwords: passwords to use when connection to remote hosts
        :param connection: what type of connection to use to connect to the host, one of ssh, local, docker
        :param module_path: path to third-party modules to load
        :param forks: number of parallel processes to spawn when communicating with remote hosts
        :param become: determine if privilege escalation should be activated
        :param become_method: method to use for privilege escalation
        :param become_user: user to assume in order to escalate priviliges
        :param check: do a dry run, simulating actions Ansible would take on a remote host
        """
        self._variable_manager = variable_manager
        self._data_loader = data_loader

        ansible_play_options = namedtuple(
            'Options', [
                'connection',
                'module_path',
                'forks',
                'become',
                'become_method',
                'become_user',
                'check'
            ]
        )

        self._ansible_play_options = ansible_play_options(
            connection=connection,
            module_path=module_path,
            forks=forks,
            become=become,
            become_method=become_method,
            become_user=become_user,
            check=check
        )

        self._passwords = passwords
        self._inventory = Inventory(loader=data_loader, variable_manager=variable_manager, host_list=host_list)
        self._variable_manager.set_inventory(self._inventory)

        pass

    def run_role(self, name, role, vars=None, hosts='all', gather_facts='yes'):
        """
        Run a play that includes the role specified with the variables
        provided.

        :param name: name of the play
        :param role: name of the role to run
        :param vars: variables to pass to the role
        :param hosts: remote hosts or groups on which the role should be run
        :param gather_facts: whether or not to gather facts on the remote hosts
        """
        play_raw = dict(
            name=name,
            hosts=hosts,
            gather_facts=gather_facts,
            roles=[
                dict(
                    role=role,
                    vars=vars
                )
            ]
        )
        play = Play().load(play_raw, variable_manager=self._variable_manager, loader=self._data_loader)

        tqm = None
        try:
            tqm = TaskQueueManager(
                inventory=self._inventory,
                variable_manager=self._variable_manager,
                loader=self._data_loader,
                options=self._ansible_play_options,
                passwords=self._passwords,
            )
            result = tqm.run(play)
        finally:
            if tqm is not None:
                tqm.cleanup()
