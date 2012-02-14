#!/usr/bin/env python
# Software License Agreement (BSD License)
#
# Copyright (c) 2009, Willow Garage, Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above
#    copyright notice, this list of conditions and the following
#    disclaimer in the documentation and/or other materials provided
#    with the distribution.
#  * Neither the name of Willow Garage, Inc. nor the names of its
#    contributors may be used to endorse or promote products derived
#    from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

import os
import io
import copy
import stat
import struct
import sys
import unittest
import subprocess
import tempfile
import urllib
import shutil

import rosinstall
import rosinstall.helpers

def _add_to_file(path, content):
     """Util function to append to file to get a modification"""
     f = io.open(path, 'a')
     f.write(content)
     f.close()

def _create_fake_ros_dir(root_path):
     """setup fake ros root within root_path/ros"""
     ros_path = os.path.join(root_path, "ros")
     os.makedirs(ros_path)
     subprocess.check_call(["git", "init"], cwd=ros_path)
     _add_to_file(os.path.join(ros_path, "stack.xml"), u'<stack></stack>')
     _add_to_file(os.path.join(ros_path, "setup.sh"), u'export ROS_ROOT=`pwd`')
     subprocess.check_call(["git", "add", "*"], cwd=ros_path)
     subprocess.check_call(["git", "commit", "-m", "initial"], cwd=ros_path)

def _create_yaml_file(config_elements, path):
     content = ''
     for elt in list(config_elements):
          content += "- %s:\n"%elt["type"]
          if elt["uri"] is not None:
               content += "    uri: '%s'\n"%elt["uri"]
          content += "    local-name: '%s'\n"%elt["local-name"]
          if elt["version"] is not None:
               content += "    version: '%s'\n"%elt["version"]
     _add_to_file(path, unicode(content))

def _create_config_elt_dict(scmtype, localname, uri=None, version=None):
     element = {}
     element["type"]       = scmtype
     element["uri"]        = uri
     element["local-name"] = localname
     element["version"]    = version
     return element

def _create_git_repo(git_path):
    os.makedirs(git_path)
    subprocess.check_call(["git", "init"], cwd=git_path)
    subprocess.check_call(["touch", "gitfixed.txt"], cwd=git_path)
    subprocess.check_call(["git", "add", "*"], cwd=git_path)
    subprocess.check_call(["git", "commit", "-m", "initial"], cwd=git_path)

def _create_hg_repo(hg_path):
    os.makedirs(hg_path)
    subprocess.check_call(["hg", "init"], cwd=hg_path)
    subprocess.check_call(["touch", "hgfixed.txt"], cwd=hg_path)
    subprocess.check_call(["hg", "add", "hgfixed.txt"], cwd=hg_path)
    subprocess.check_call(["hg", "commit", "-m", "initial"], cwd=hg_path)
               
ROSINSTALL_CMD = os.path.join(os.getcwd(), 'scripts/rosinstall')



class AbstractRosinstallCLITest(unittest.TestCase):

     """Base class for cli tests"""
     @classmethod
     def setUpClass(self):
          self.new_environ = os.environ
          self.new_environ["PYTHONPATH"] = os.path.join(os.getcwd(), "src")



class AbstractRosinstallBaseDirTest(AbstractRosinstallCLITest):
     """test class where each test method get its own fresh tempdir named self.directory"""
     
     def setUp(self):
          self.directories = {}
          self.directory = tempfile.mkdtemp()
          self.directories["base"] = self.directory
          self.rosinstall_fn = [ROSINSTALL_CMD, "-n"]

     def tearDown(self):
        for d in self.directories:
            shutil.rmtree(self.directories[d])
        self.directories = {}

class AbstractFakeRosBasedTest(AbstractRosinstallBaseDirTest):
     """creates some larger infrastructure for testing locally"""
     
     @classmethod
     def setUpClass(self):
          AbstractRosinstallBaseDirTest.setUpClass()
          # create a dir mimicking ros
          self.test_root_path = tempfile.mkdtemp()
          _create_fake_ros_dir(self.test_root_path)
          # create a repo in git
          self.ros_path = os.path.join(self.test_root_path, "ros")
          self.git_path = os.path.join(self.test_root_path, "gitrepo")
          _create_git_repo(self.git_path)
          # create a repo in hg
          self.hg_path = os.path.join(self.test_root_path, "hgrepo")
          _create_hg_repo(self.hg_path)
          # create custom rosinstall files to use as input
          self.simple_rosinstall = os.path.join(self.test_root_path, "simple.rosinstall")
          _create_yaml_file([_create_config_elt_dict("git", "ros", self.ros_path),
                             _create_config_elt_dict("git", "gitrepo", self.git_path)],
                            self.simple_rosinstall)
          self.simple_changed_vcs_rosinstall = os.path.join(self.test_root_path, "simple_changed_vcs.rosinstall")
          _create_yaml_file([_create_config_elt_dict("git", "ros", self.ros_path),
                             _create_config_elt_dict("hg", "hgrepo", self.hg_path)],
                            self.simple_changed_vcs_rosinstall)

     @classmethod
     def tearDownClass(self):
          shutil.rmtree(self.test_root_path)
          
class AbstractSCMTest(AbstractRosinstallCLITest):
     """Base class for diff tests, setting up a tempdir self.test_root_path for a whole class"""
     @classmethod
     def setUpClass(self):
          """creates a directory 'ros' mimicking to be a ROS root to rosinstall"""
          AbstractRosinstallCLITest.setUpClass()
          self.test_root_path = tempfile.mkdtemp()
          self.directories = {}
          self.directories["root"] = self.test_root_path

          _create_fake_ros_dir(self.test_root_path)
          self.local_path = os.path.join(self.test_root_path, "ws")
          os.makedirs(self.local_path)

     @classmethod
     def tearDownClass(self):
          for d in self.directories:
               shutil.rmtree(self.directories[d])
        