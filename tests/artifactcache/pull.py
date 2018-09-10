import hashlib
import multiprocessing
import os
import signal

import pytest

from buildstream import _yaml, _signals, utils
from buildstream._artifactcache.cascache import CASCache
from buildstream._context import Context
from buildstream._project import Project
from buildstream._protos.build.bazel.remote.execution.v2 import remote_execution_pb2

from tests.testutils import cli, create_artifact_share


# Project directory
DATA_DIR = os.path.join(
    os.path.dirname(os.path.realpath(__file__)),
    "project",
)


# Handle messages from the pipeline
def message_handler(message, context):
    pass


def tree_maker(cas, tree, directory):
    if tree.root.ByteSize() == 0:
        tree.root.CopyFrom(directory)

    for directory_node in directory.directories:
        child_directory = tree.children.add()

        with open(cas.objpath(directory_node.digest), 'rb') as f:
            child_directory.ParseFromString(f.read())

        tree_maker(cas, tree, child_directory)


@pytest.mark.datafiles(DATA_DIR)
def test_pull(cli, tmpdir, datafiles):
    project_dir = str(datafiles)

    # Set up an artifact cache.
    with create_artifact_share(os.path.join(str(tmpdir), 'artifactshare')) as share:
        # Configure artifact share
        artifact_dir = os.path.join(str(tmpdir), 'cache', 'artifacts')
        user_config_file = str(tmpdir.join('buildstream.conf'))
        user_config = {
            'scheduler': {
                'pushers': 1
            },
            'artifacts': {
                'url': share.repo,
                'push': True,
            }
        }

        # Write down the user configuration file
        _yaml.dump(_yaml.node_sanitize(user_config), filename=user_config_file)
        # Ensure CLI calls will use it
        cli.configure(user_config)

        # First build the project with the artifact cache configured
        result = cli.run(project=project_dir, args=['build', 'target.bst'])
        result.assert_success()

        # Assert that we are now cached locally
        assert cli.get_element_state(project_dir, 'target.bst') == 'cached'
        # Assert that we shared/pushed the cached artifact
        element_key = cli.get_element_key(project_dir, 'target.bst')
        assert share.has_artifact('test', 'target.bst', element_key)

        # Delete the artifact locally
        cli.remove_artifact_from_cache(project_dir, 'target.bst')

        # Assert that we are not cached locally anymore
        assert cli.get_element_state(project_dir, 'target.bst') != 'cached'

        # Fake minimal context
        context = Context()
        context.load(config=user_config_file)
        context.artifactdir = os.path.join(str(tmpdir), 'cache', 'artifacts')
        context.set_message_handler(message_handler)

        # Load the project and CAS cache
        project = Project(project_dir, context)
        project.ensure_fully_loaded()
        cas = CASCache(context)

        # Assert that the element's artifact is **not** cached
        element = project.load_elements(['target.bst'], cas)[0]
        element_key = cli.get_element_key(project_dir, 'target.bst')
        assert not cas.contains(element, element_key)

        queue = multiprocessing.Queue()
        # Use subprocess to avoid creation of gRPC threads in main BuildStream process
        # See https://github.com/grpc/grpc/blob/master/doc/fork_support.md for details
        process = multiprocessing.Process(target=_test_pull,
                                          args=(user_config_file, project_dir, artifact_dir,
                                                'target.bst', element_key, queue))

        try:
            # Keep SIGINT blocked in the child process
            with _signals.blocked([signal.SIGINT], ignore=False):
                process.start()

            error = queue.get()
            process.join()
        except KeyboardInterrupt:
            utils._kill_process_tree(process.pid)
            raise

        assert not error
        assert cas.contains(element, element_key)


def _test_pull(user_config_file, project_dir, artifact_dir,
               element_name, element_key, queue):
    # Fake minimal context
    context = Context()
    context.load(config=user_config_file)
    context.artifactdir = artifact_dir
    context.set_message_handler(message_handler)

    # Load the project manually
    project = Project(project_dir, context)
    project.ensure_fully_loaded()

    # Create a local CAS cache handle
    cas = CASCache(context)

    # Load the target element
    element = project.load_elements([element_name], cas)[0]

    # Manually setup the CAS remote
    cas.setup_remotes(use_config=True)
    cas.initialize_remotes()

    if cas.has_push_remotes(element=element):
        # Push the element's artifact
        if not cas.pull(element, element_key):
            queue.put("Pull operation failed")
        else:
            queue.put(None)
    else:
        queue.put("No remote configured for element {}".format(element_name))


@pytest.mark.datafiles(DATA_DIR)
def test_pull_tree(cli, tmpdir, datafiles):
    project_dir = str(datafiles)

    # Set up an artifact cache.
    with create_artifact_share(os.path.join(str(tmpdir), 'artifactshare')) as share:
        # Configure artifact share
        artifact_dir = os.path.join(str(tmpdir), 'cache', 'artifacts')
        user_config_file = str(tmpdir.join('buildstream.conf'))
        user_config = {
            'scheduler': {
                'pushers': 1
            },
            'artifacts': {
                'url': share.repo,
                'push': True,
            }
        }

        # Write down the user configuration file
        _yaml.dump(_yaml.node_sanitize(user_config), filename=user_config_file)
        # Ensure CLI calls will use it
        cli.configure(user_config)

        # First build the project with the artifact cache configured
        result = cli.run(project=project_dir, args=['build', 'target.bst'])
        result.assert_success()

        # Assert that we are now cached locally
        assert cli.get_element_state(project_dir, 'target.bst') == 'cached'
        # Assert that we shared/pushed the cached artifact
        element_key = cli.get_element_key(project_dir, 'target.bst')
        assert share.has_artifact('test', 'target.bst', element_key)

        # Fake minimal context
        context = Context()
        context.load(config=user_config_file)
        context.artifactdir = os.path.join(str(tmpdir), 'cache', 'artifacts')
        context.set_message_handler(message_handler)

        # Load the project and CAS cache
        project = Project(project_dir, context)
        project.ensure_fully_loaded()
        cas = CASCache(context)

        # Assert that the element's artifact is cached
        element = project.load_elements(['target.bst'], cas)[0]
        element_key = cli.get_element_key(project_dir, 'target.bst')
        assert cas.contains(element, element_key)

        # Retrieve the Directory object from the cached artifact
        artifact_ref = cas.get_artifact_fullname(element, element_key)
        artifact_digest = cas.resolve_ref(artifact_ref)

        queue = multiprocessing.Queue()
        # Use subprocess to avoid creation of gRPC threads in main BuildStream process
        # See https://github.com/grpc/grpc/blob/master/doc/fork_support.md for details
        process = multiprocessing.Process(target=_test_push_tree,
                                          args=(user_config_file, project_dir, artifact_dir,
                                                artifact_digest, queue))

        try:
            # Keep SIGINT blocked in the child process
            with _signals.blocked([signal.SIGINT], ignore=False):
                process.start()

            tree_hash, tree_size = queue.get()
            process.join()
        except KeyboardInterrupt:
            utils._kill_process_tree(process.pid)
            raise

        assert tree_hash and tree_size

        # Now delete the artifact locally
        cli.remove_artifact_from_cache(project_dir, 'target.bst')

        # Assert that we are not cached locally anymore
        assert cli.get_element_state(project_dir, 'target.bst') != 'cached'

        tree_digest = remote_execution_pb2.Digest(hash=tree_hash,
                                                  size_bytes=tree_size)

        queue = multiprocessing.Queue()
        # Use subprocess to avoid creation of gRPC threads in main BuildStream process
        process = multiprocessing.Process(target=_test_pull_tree,
                                          args=(user_config_file, project_dir, artifact_dir,
                                                tree_digest, queue))

        try:
            # Keep SIGINT blocked in the child process
            with _signals.blocked([signal.SIGINT], ignore=False):
                process.start()

            directory_hash, directory_size = queue.get()
            process.join()
        except KeyboardInterrupt:
            utils._kill_process_tree(process.pid)
            raise

        assert directory_hash and directory_size

        directory_digest = remote_execution_pb2.Digest(hash=directory_hash,
                                                       size_bytes=directory_size)

        # Ensure the entire Tree stucture has been pulled
        assert os.path.exists(cas.objpath(directory_digest))


def _test_push_tree(user_config_file, project_dir, artifact_dir, artifact_digest, queue):
    # Fake minimal context
    context = Context()
    context.load(config=user_config_file)
    context.artifactdir = artifact_dir
    context.set_message_handler(message_handler)

    # Load the project manually
    project = Project(project_dir, context)
    project.ensure_fully_loaded()

    # Create a local CAS cache handle
    cas = CASCache(context)

    # Manually setup the CAS remote
    cas.setup_remotes(use_config=True)
    cas.initialize_remotes()

    if cas.has_push_remotes():
        directory = remote_execution_pb2.Directory()

        with open(cas.objpath(artifact_digest), 'rb') as f:
            directory.ParseFromString(f.read())

        # Build the Tree object while we are still cached
        tree = remote_execution_pb2.Tree()
        tree_maker(cas, tree, directory)

        # Push the Tree as a regular message
        tree_digest = cas.push_message(project, tree)

        queue.put((tree_digest.hash, tree_digest.size_bytes))
    else:
        queue.put("No remote configured")


def _test_pull_tree(user_config_file, project_dir, artifact_dir, artifact_digest, queue):
    # Fake minimal context
    context = Context()
    context.load(config=user_config_file)
    context.artifactdir = artifact_dir
    context.set_message_handler(message_handler)

    # Load the project manually
    project = Project(project_dir, context)
    project.ensure_fully_loaded()

    # Create a local CAS cache handle
    cas = CASCache(context)

    # Manually setup the CAS remote
    cas.setup_remotes(use_config=True)
    cas.initialize_remotes()

    if cas.has_push_remotes():
        # Pull the artifact using the Tree object
        directory_digest = cas.pull_tree(project, artifact_digest)
        queue.put((directory_digest.hash, directory_digest.size_bytes))
    else:
        queue.put("No remote configured")