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
"""Base test file for code generation"""
import inspect
import numpy as np
import os
import shutil
import sys
import unittest

from scripts import generate_project as gp
from scripts.pylib.nnlib import NNLib as NNLib
from testcase_dlk_base import TestCaseDLKBase
from tstconf import CURRENT_TEST_LEVEL
from tstutils import updated_dict, run_and_check, FPGA_HOST

sys.path.append("utils")  # PEP8:ignore
import run_test as inference  # PEP8:ignore


def dict_codegen_classification(cpu_name) -> dict:
    """Test parameters for testing code generation for classification on CPU (lmnet_quantize)"""
    return {'model_path': os.path.join('examples', 'classification', 'lmnet_quantize_cifar10_space_to_depth'),
            'expected_output_set_name': '1000_dog.png',
            'prefix': 'cls',
            'input_name': '000_images_placeholder:0.npy',
            'output_npy_name': '133_output:0.npy',
            'cpu_name': cpu_name,
            'hard_quantize': True,
            }


def dict_codegen_classification_resnet(cpu_name) -> dict:
    """Test parameters for testing code generation for classification on CPU (float only)"""
    return {'model_path': os.path.join('examples', 'classification', 'resnet_quantize_cifar10'),
            'expected_output_set_name': '9984_horse.png',
            'prefix': 'cls_resnet',
            'input_name': '000_images_placeholder:0.npy',
            'output_npy_name': '368_output:0.npy',
            'cpu_name': cpu_name,
            'hard_quantize': True,
            }


def dict_codegen_object_detection(cpu_name) -> dict:
    """Test parameters for testing code generation for object detection on CPU"""
    return {'model_path': os.path.join('examples', 'object_detection', 'fyolo_quantize_4_v4'),
            'expected_output_set_name': 'network_input_output',
            'prefix': 'det',
            'input_name': '000_images_placeholder:0.npy',
            'output_npy_name': '317_output:0.npy',
            'cpu_name': cpu_name,
            'hard_quantize': True,
            }


def dict_codegen_segmentation(cpu_name) -> dict:
    """Test parameters for testing code generation for segmentation on CPU"""
    return {'model_path': os.path.join('examples', 'segmentation', 'lm_segnet_v1_quantize_camvid'),
            'expected_output_set_name': 'network_input_output',
            'prefix': 'seg',
            'input_name': '000_images_placeholder:0.npy',
            'output_npy_name': '227_output:0.npy',
            'cpu_name': cpu_name,
            'hard_quantize': True,
            }


def get_configurations_by_test_cases(test_cases, configuration):
    configurations = []
    for test_case in test_cases:
        configurations.append(updated_dict(configuration, test_case))

    return configurations


def get_configurations_by_architecture(test_cases, cpu_name):
    configurations = []
    configurations.extend(get_configurations_by_test_cases(test_cases, dict_codegen_classification(cpu_name)))
    configurations.extend(get_configurations_by_test_cases(test_cases, dict_codegen_classification_resnet(cpu_name)))
    configurations.extend(get_configurations_by_test_cases(test_cases, dict_codegen_object_detection(cpu_name)))
    configurations.extend(get_configurations_by_test_cases(test_cases, dict_codegen_segmentation(cpu_name)))

    return configurations


class TestCodeGenerationBase(TestCaseDLKBase):
    """Base class for code generation testing."""

    project_name = 'code_generation'

    def run_test_code_generation(self, i, configuration) -> None:

        print(f"\nCode generation test: ID: {i}, Testcase: {configuration}")
        #  TODO consider better implementation
        this_test_level = configuration.get("test_level", 0)
        if this_test_level < CURRENT_TEST_LEVEL:
            self.codegen_cpu(test_id=i, **configuration)
        else:
            raise unittest.SkipTest(
                f'test level of this test: {this_test_level}, current test level: {CURRENT_TEST_LEVEL}')

    def run_test_binary_exec(self, i, configuration) -> None:

        #  TODO consider better implementation
        this_test_level = configuration.get("test_level", 0)
        if this_test_level < CURRENT_TEST_LEVEL:
            self.exec_binary(test_id=i, **configuration)
        else:
            raise unittest.SkipTest(
                f'test level of this test: {this_test_level}, current test level: {CURRENT_TEST_LEVEL}')

    def run_library(self, library, input_npy, expected_output_npy):

        proc_input = np.load(input_npy)
        expected_output = np.load(expected_output_npy)
        # load and initialize the generated shared library
        nn = NNLib()
        nn.load(library)
        nn.init()

        # run the graph
        batched_proc_input = np.expand_dims(proc_input, axis=0)
        output = nn.run(batched_proc_input)

        rtol = atol = 0.0001
        n_failed = expected_output.size - np.count_nonzero(np.isclose(output, expected_output, rtol=rtol, atol=atol))
        percent_failed = (n_failed / expected_output.size) * 100.0

        return percent_failed

    def run_library_using_script(self, library: str, image: str, expected_output_npy: str, from_npy: bool) -> float:

        percent_failed = inference.main_test(image, library, expected_output_npy, from_npy=from_npy)
        return percent_failed

    def run_library_on_remote(self,
                              host: str,
                              output_path: str,
                              library: str,
                              input_npy: str, expected_output_npy: str) -> float:

        run_and_check(["ssh", f"root@{host}", f"rm -rf ~/automated_testing/*"],
                      output_path,
                      os.path.join(output_path, "clean.err"),
                      os.path.join(output_path, "clean.err"),
                      self)

        lib_name = os.path.basename(library)
        input_name = os.path.basename(input_npy)
        output_name = os.path.basename(expected_output_npy)

        run_library_code = "import numpy as np\n"
        run_library_code += "from nnlib import NNLib as NNLib\n"
        run_library_code += "class testing:\n"
        run_library_code += inspect.getsource(self.run_library)
        run_library_code += "if __name__ == '__main__':\n"
        run_library_code += "  t = testing()\n"
        run_library_code += f"  print(t.run_library('./{lib_name}', './{input_name}', './{output_name}'))\n"

        testing_code_name = "testing_code.py"
        testing_code_path = os.path.join(output_path, testing_code_name)
        with open(testing_code_path, "w") as code_file:
            code_file.write(run_library_code)

        run_and_check(["scp", library, input_npy, expected_output_npy, inspect.getfile(NNLib),
                       testing_code_path, f"root@{host}:~/automated_testing/"],
                      output_path,
                      os.path.join(output_path, "scp.out"),
                      os.path.join(output_path, "scp.err"),
                      self)

        remote_output_file = os.path.join(output_path, "remote.out")
        run_and_check(["ssh", f"root@{host}", f"cd ~/automated_testing/; python {testing_code_name}"],
                      output_path,
                      remote_output_file,
                      os.path.join(output_path, "remote.err"),
                      self,
                      keep_outputs=True)

        with open(remote_output_file, "r") as remote_output_file:
            remote_output = remote_output_file.read()

        pf = 100.0
        try:
            pf = float(remote_output)
        except ValueError:
            pf = 100.0

        return pf

    def get_paths(self, model_path, prefix, test_id, cpu_name):
        dir_tags = [str(test_id), prefix, os.path.basename(model_path), cpu_name]
        output_path = os.path.join(self.build_dir, '_'.join(dir_tags))
        input_dir_path = os.path.abspath(
            os.path.join(os.getcwd(),
                         model_path))

        input_path = os.path.join(input_dir_path, 'minimal_graph_with_shape.pb')

        return [output_path, input_path, input_dir_path]

    def codegen_cpu(self,
                    model_path,
                    expected_output_set_name,
                    prefix,
                    input_name,
                    output_npy_name,
                    cpu_name='x86_64',
                    hard_quantize=True,
                    threshold_skipping=False,
                    use_run_test_script=False,
                    max_percent_incorrect_values=0.1,
                    from_npy=False,
                    cache_dma=False,
                    use_avx=False,
                    test_id=0
                    ) -> None:

        """Test code for testing code generation for CPU"""
        output_path, input_path, input_dir_path = self.get_paths(model_path, prefix, test_id, cpu_name)

        gp.run(input_path=input_path,
               dest_dir_path=output_path,
               project_name=self.project_name,
               activate_hard_quantization=hard_quantize,
               threshold_skipping=threshold_skipping,
               num_pe=16,
               debug=False,
               cache_dma=cache_dma,
               )

        lib_name = 'lib_' + cpu_name
        project_dir = os.path.join(output_path, self.project_name + '.prj')
        generated_lib = os.path.join(project_dir, lib_name + '.so')
        npy_targz = os.path.join(input_dir_path, expected_output_set_name + '.tar.gz')

        run_and_check(['tar', 'xvzf', str(npy_targz), '-C', str(output_path)],
                      input_dir_path,
                      os.path.join(output_path, "tar_xvzf.out"),
                      os.path.join(output_path, "tar_xvzf.err"),
                      self,
                      check_stdout_include=[expected_output_set_name + '/raw_image.npy']
                      )

        self.assertTrue(os.path.exists(project_dir))

        cmake_use_aarch64 = '-DTOOLCHAIN_NAME=linux_aarch64'
        cmake_use_arm = '-DTOOLCHAIN_NAME=linux_arm'
        cmake_use_neon = '-DUSE_NEON=1'
        cmake_use_fpga = '-DRUN_ON_FPGA=1'
        cmake_use_avx = '-DUSE_AVX=1'

        cmake_defs = []
        if cpu_name == 'aarch64':
            cmake_defs += [cmake_use_aarch64, cmake_use_neon]
        if cpu_name == 'arm':
            cmake_defs += [cmake_use_arm, cmake_use_neon]
        if cpu_name == 'arm_fpga':
            cmake_defs += [cmake_use_arm, cmake_use_neon, cmake_use_fpga]
        if use_avx is True:
            cmake_defs += [cmake_use_avx]

        run_and_check(['cmake'] + cmake_defs + ['.'],
                      project_dir,
                      os.path.join(output_path, "cmake.out"),
                      os.path.join(output_path, "cmake.err"),
                      self,
                      check_stdout_include=['Generating done'],
                      check_stdout_block=['CMake Error']
                      )

        run_and_check(['make', 'VERBOSE=1', 'lib', '-j8'],
                      project_dir,
                      os.path.join(output_path, "make.out"),
                      os.path.join(output_path, "make.err"),
                      self,
                      check_stdout_include=['Building'],
                      check_stderr_block=['error: ']
                      )
        self.assertTrue(os.path.exists(generated_lib))

    def exec_binary(self,
                    test_id,
                    model_path,
                    expected_output_set_name,
                    prefix,
                    input_name,
                    output_npy_name,
                    cpu_name='x86_64',
                    hard_quantize=True,
                    threshold_skipping=False,
                    use_run_test_script=False,
                    max_percent_incorrect_values=0.1,
                    from_npy=False,
                    cache_dma=False,
                    use_avx=False) -> None:
        output_path, input_path, _ = self.get_paths(model_path, prefix, test_id, cpu_name)

        lib_name = 'lib_' + cpu_name
        project_dir = os.path.join(output_path, self.project_name + '.prj')
        generated_lib = os.path.join(project_dir, lib_name + '.so')
        npy_path = os.path.join(output_path, expected_output_set_name)
        input_path = os.path.join(npy_path, input_name)
        expected_output_path = os.path.join(npy_path, output_npy_name)

        if not use_run_test_script:
            if cpu_name == 'x86_64':
                percent_failed = self.run_library(generated_lib, input_path, expected_output_path)
            else:
                percent_failed = \
                    self.run_library_on_remote(FPGA_HOST, output_path, generated_lib, input_path, expected_output_path)
        else:
            percent_failed = self.run_library_using_script(generated_lib, input_path, expected_output_path,
                                                           from_npy)

        self.assertTrue(percent_failed < max_percent_incorrect_values,
                        msg=f"Test failed: {percent_failed:.3f}% of the values does not match")

        print(f"Binary exec test {prefix}: passed!  {100.0 - percent_failed:.3f}% "
              f"of the output values are correct\n"
              f"[hard quantize == {hard_quantize}, threshold skipping == {threshold_skipping}, cache == {cache_dma}]")


if __name__ == '__main__':
    unittest.main()
