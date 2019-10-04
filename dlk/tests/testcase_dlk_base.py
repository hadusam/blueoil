# -*- coding: utf-8 -*-
# Copyright 2018 The Blueoil Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# =============================================================================
import os
import shutil
import tempfile
import time
from datetime import datetime
from glob import glob
from unittest import TestCase

from tstconf import DO_CLEANUP, DO_CLEANUP_OLDBUILD, FPGA_FILES, HOURS_ELAPSED_TO_ERASE, PROJECT_TAG
from tstutils import setup_de10nano

SECOND_PER_HOUR = 3600


def rmdir(path) -> None:
    try:
        shutil.rmtree(path)
    except FileNotFoundError:
        pass


class TestCaseDLKBase(TestCase):
    """
    This is base class TestCase which have
    Setup and TearDown method which is common in dlk project.
    """
    build_dir = None

    @classmethod
    def setUpClass(cls):
        """ Make build directory """

        if DO_CLEANUP_OLDBUILD:
            build_dir = cls.getClassDir()
            rmdir(build_dir)
            print(f'Old directory {build_dir} deleted')

        if not os.path.exists(build_dir):
            os.mkdir(build_dir)


    @classmethod
    def getClassDir(self):
        """ Get build directory """

        base_dir = os.path.join(os.getcwd(), "outputs")
        prefix = "-".join(["test", PROJECT_TAG])
        classtag = self.__class__.__name__
        build_dir = "-".join([prefix, classtag])

        return os.path.join(base_dir, build_dir)


    def setUp(self):
        """ Set build directory """

        self.build_dir = self.getClassDir()


    def tearDownClass(self) -> None:
        if DO_CLEANUP:
            rmdir(self.build_dir)


class TestCaseFPGABase(TestCaseDLKBase):
    """
    This is base class for FPGA TestCase which have
    Setup and TearDown method.
    """

    @classmethod
    def setUpClass(TestCaseDLKBase):
        super().setUpClass()
        # Setup the board. For now, DE10 Nano board
        output_path = '/tmp'
        hw_path = os.path.abspath(os.path.join('..', FPGA_FILES))

        board_available = setup_de10nano(hw_path, output_path)

        if not board_available:
            raise Exception('Not FPGA found: cannot test')
