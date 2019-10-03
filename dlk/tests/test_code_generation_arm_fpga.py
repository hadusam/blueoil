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
"""Test file for code generation"""
from nose2.tools import params
from test_code_generation_base import TestCodeGenerationBase, get_configurations_by_architecture
from testcase_dlk_base import TestCaseFPGABase
import unittest


def get_configurations():
    cpu_name = "arm_fpga"
    test_cases = [
        {'hard_quantize': True, 'need_arm_compiler': True, 'cache_dma': True, 'threshold_skipping': True},
        {'hard_quantize': True, 'need_arm_compiler': True, 'cache_dma': True, 'threshold_skipping': False},
        {'hard_quantize': True, 'need_arm_compiler': True, 'cache_dma': False, 'threshold_skipping': True},
        {'hard_quantize': True, 'need_arm_compiler': True, 'cache_dma': False, 'threshold_skipping': False},
    ]
    configurations = get_configurations_by_architecture(test_cases, cpu_name)

    return [(i, configuration) for i, configuration in enumerate(configurations)]


class TestCodeGenerationArmFpga(TestCodeGenerationBase, TestCaseFPGABase):
    """Test class for code generation testing of arm_fpga."""

    @params(*get_configurations())
    def test_code_generation(self, i, configuration) -> None:
        self.run_test_code_generation(i, configuration)
        self.run_test_binary_exec(i, configuration)
