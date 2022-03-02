"""
    Module Name:
    Purpose: Refer to the redhat_mixin.md for more information
"""

from .rexe import Rexe
from .relog import Logger
from .utils import Utils


class RedantMixin(Utils, AbstractOps, Rexe, Logger):
    """
    A mixin class for redant project to encompass all ops, support
    modules and encapsulates the object responsible for the framework
    level data structure for volume and cleanup.
    """

    def __init__(self, es, res):
        self.es = es
        self.TEST_RES = res
