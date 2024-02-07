import click
from click.testing import CliRunner
import sys
import pytest
from io import StringIO
from unittest.mock import patch, MagicMock, call

from snaketool_utils.cli_utils import (
    OrderedCommands,
    echo_click,
    msg,
    msg_box,
    read_config,
    recursive_merge_config,
    initialise_config,
    write_config,
    update_config,
    copy_config,
    run_snakemake,
    tuple_to_list,
)


def test_list_commands_preserves_order():
    class TestCLI(OrderedCommands):
        pass

    @click.command()
    def command1():
        pass

    @click.command()
    def command2():
        pass

    @click.command()
    def command3():
        pass

    test_cli = TestCLI()
    test_cli.add_command(command1)
    test_cli.add_command(command2)
    test_cli.add_command(command3)

    runner = CliRunner()
    result = runner.invoke(test_cli, ["--help"])
    print(result.output)
    assert result.exit_code == 0
    assert "Commands:\n  command1\n  command2\n  command3" in result.output


def test_echo_click(capsys, tmp_path):
    # Redirect stderr to capture the output
    sys.stderr = StringIO()

    # Define the error message and create a temporary log file
    msg = "This is an error message"
    log_file = tmp_path / "log.txt"

    # Call the echo_click function
    echo_click(msg, log=str(log_file))

    # Get the captured stderr output
    captured_stderr = sys.stderr.getvalue()

    # Assert that the error message is printed to stderr
    assert captured_stderr == msg

    # Assert that the error message is written to the log file
    with open(log_file, "r") as log:
        log_content = log.read()
        assert log_content == msg

    # Clean up and restore stderr
    sys.stderr = sys.__stderr__


def test_msg(capsys, tmp_path):
    # Define the error message and log file path
    err_message = "This is an error message"
    log_file = tmp_path / "log.txt"

    # Patch the strftime function to return a fixed timestamp
    fixed_timestamp = "[2022:01:01 00:00:00] "
    with patch("snaketool_utils.cli_utils.strftime", return_value=fixed_timestamp):
        # Call the msg function
        msg(err_message, log=log_file)

    # Capture the printed output
    captured = capsys.readouterr()

    # Assert that the output contains the formatted error message
    expected_output = fixed_timestamp + err_message + "\n"
    assert captured.err == expected_output

    # Assert that the error message is written to the log file
    with open(log_file, "r") as log:
        log_content = log.read()
        assert log_content == expected_output


def test_msg_box(capsys, tmp_path):
    splash = "Error!"
    errmsg = "This is a multi-line error message\nwith multiple lines"
    log_file = tmp_path / "log.txt"

    msg_box(splash, errmsg=errmsg, log=log_file)

    captured = capsys.readouterr()

    assert splash in captured.err
    assert errmsg in captured.err


@pytest.fixture(scope="function")
def temp_left_config(tmp_path):
    file_path = tmp_path / "config.yaml"
    config_content = """
            key1: value1
            key2: value2
            key3:
                - item1
                - item2
        """

    with open(file_path, "w") as f:
        f.write(config_content)

    expected_config = {"key1": "value1", "key2": "value2", "key3": ["item1", "item2"]}

    yield str(file_path), expected_config


def test_read_config(temp_left_config):
    file_path, expected_config = temp_left_config

    config = read_config(file_path)

    assert config == expected_config


@pytest.fixture(scope="function")
def left_config():
    return {
        "key1": "value1",
        "key2": {"nested_key1": "nested_value1", "nested_key2": "nested_value2"},
        "key3": ["item1", "item2"],
    }


@pytest.fixture(scope="function")
def left_yaml():
    return (
        "key1: value1\n"
        "key2:\n"
        "  nested_key1: nested_value1\n"
        "  nested_key2: nested_value2\n"
        "key3:\n"
        "- item1\n"
        "- item2\n"
    )


@pytest.fixture(scope="function")
def left_path(tmp_path, left_yaml):
    file_path = tmp_path / "left_config.yaml"
    with open(file_path, "w") as f:
        f.write(left_yaml)
    return file_path


@pytest.fixture(scope="function")
def right_config():
    return {
        "key1": "new_value1",
        "key2": {"nested_key2": "new_nested_value2", "nested_key3": "nested_value3"},
        "key4": "value4",
    }


@pytest.fixture(scope="function")
def right_yaml():
    return (
        "key1: value1\n"
        "key2:\n"
        "  nested_key2: new_nested_value2\n"
        "  nested_key3: nested_value3\n"
        "key4: value4\n"
    )


@pytest.fixture(scope="function")
def right_path(tmp_path, right_yaml):
    file_path = tmp_path / "right_config.yaml"
    with open(file_path, "w") as f:
        f.write(right_yaml)
    return file_path


@pytest.fixture(scope="function")
def merged_config():
    return {
        "key1": "new_value1",
        "key2": {
            "nested_key1": "nested_value1",
            "nested_key2": "new_nested_value2",
            "nested_key3": "nested_value3",
        },
        "key3": ["item1", "item2"],
        "key4": "value4",
    }


@pytest.fixture(scope="function")
def merged_yaml():
    return (
        "key1: new_value1\n"
        "key2:\n"
        "  nested_key1: nested_value1\n"
        "  nested_key2: new_nested_value2\n"
        "  nested_key3: nested_value3\n"
        "key3:\n"
        "- item1\n"
        "- item2\n"
        "key4: value4\n"
    )


@pytest.fixture(scope="function")
def merged_path(tmp_path, merged_yaml):
    file_path = tmp_path / "merge_config.yaml"
    with open(file_path, "w") as f:
        f.write(merged_yaml)
    return file_path


def test_recursive_merge_config(left_config, right_config, merged_config):
    recursive_merge_config(left_config, right_config)
    assert left_config == merged_config


def test_write_config(left_config, left_yaml, tmp_path):
    file_path = tmp_path / "config.yaml"
    write_config(left_config, file_path)
    with open(file_path, "r") as f:
        assert f.read() == left_yaml


def test_update_config(tmp_path, left_path, right_config, merged_yaml):
    file_path = tmp_path / "config.yaml"
    update_config(in_config=left_path, merge=right_config, output_config=file_path)
    with open(file_path, "r") as f:
        assert f.read() == merged_yaml


def test_copy_config(tmp_path, left_path, right_config, merged_yaml):
    file_path = tmp_path / "config.yaml"
    copy_config(file_path, merge_config=right_config, system_config=left_path)
    with open(file_path, "r") as f:
        assert f.read() == merged_yaml


def test_initialise_config(tmp_path, left_path, left_yaml, right_path, right_yaml):
    config_out = tmp_path / "config.yaml"
    profile_out = tmp_path / "profile"
    profile_out_yaml = tmp_path / "profile" / "config.yaml"
    initialise_config(
        configfile=config_out,
        system_config=left_path,
        workflow_profile=profile_out,
        system_workflow_profile=right_path
    )
    with open(config_out, "r") as f:
        assert f.read() == left_yaml
    with open(profile_out_yaml, "r") as f:
        assert f.read() == right_yaml


def test_run_snakemake(tmp_path):
    # Create temporary files for the configfile, system config, and Snakefile
    configfile = str(tmp_path / "config.yaml")
    system_config = str(tmp_path / "system_config.yaml")
    system_workflow_profile = str(tmp_path / "system_profile.yaml")
    workflow_profile = str(tmp_path / "profile")
    workflow_profile_config = str(tmp_path / "profile" / "config.yaml")
    snakefile_path = str(tmp_path / "Snakefile")
    log_file = str(tmp_path / "log")

    # Write the system config content to the system config file
    with open(system_config, "w") as f:
        f.write("key: value")

    with open(system_workflow_profile, "w") as f:
        f.write("key2: value2")

    # Write the Snakefile content to the Snakefile
    with open(snakefile_path, "w") as f:
        f.write("rule all:\n  input: 'output.txt'")

    # Patch the copy_config, update_config, read_config, and subprocess.run functions
    with patch("snaketool_utils.cli_utils.copy_config") as mock_copy_config, patch(
        "snaketool_utils.cli_utils.update_config"
    ) as mock_update_config, patch(
        "snaketool_utils.cli_utils.read_config"
    ) as mock_read_config, patch(
        "subprocess.run"
    ) as mock_run:
        # Set the return values and side effects of the mocked functions
        mock_read_config.return_value = {"key": "value"}

        # Create a MagicMock object to use as the return value of subprocess.run
        mock_run_result = MagicMock()
        mock_run_result.returncode = 0

        # Set the return value of subprocess.run to the MagicMock object
        mock_run.return_value = mock_run_result

        # Call the run_snakemake function
        exit_code = run_snakemake(
            configfile=configfile,
            system_config=system_config,
            snakefile_path=snakefile_path,
            system_workflow_profile=system_workflow_profile,
            workflow_profile=workflow_profile,
        )

        # Assert that the copy_config function was called with the expected arguments
        mock_copy_config.assert_has_calls([
            call(configfile, system_config=system_config, log=None),
            call(workflow_profile_config, system_config=system_workflow_profile, log=None)
        ])

        # Assert that the update_config function was not called
        mock_update_config.assert_not_called()

        # Assert that the read_config function was called with the configfile
        mock_read_config.assert_called_once_with(configfile)

        # Assert that the subprocess.run function was called with the expected command
        mock_run.assert_called_once_with(
            "snakemake -s {} --configfile {} --cores 1 --workflow-profile {}".format(
                snakefile_path, configfile, workflow_profile
            ),
            shell=True,
        )

        # Assert that the exit code is 0
        assert exit_code == 0

    # Patch the copy_config, update_config, read_config, and subprocess.run functions
    with patch("snaketool_utils.cli_utils.copy_config") as mock_copy_config, patch(
        "snaketool_utils.cli_utils.update_config"
    ) as mock_update_config, patch(
        "snaketool_utils.cli_utils.read_config"
    ) as mock_read_config, patch(
        "subprocess.run"
    ) as mock_run:
        # Set the return values and side effects of the mocked functions
        mock_read_config.return_value = {"key": "value"}

        # Create a MagicMock object to use as the return value of subprocess.run
        mock_run_result = MagicMock()
        mock_run_result.returncode = 0

        # Set the return value of subprocess.run to the MagicMock object
        mock_run.return_value = mock_run_result

        # Call the run_snakemake function again with additional arguments
        exit_code = run_snakemake(
            configfile=configfile,
            system_config=system_config,
            snakefile_path=snakefile_path,
            merge_config={"key2": "value2"},
            threads=4,
            use_conda=True,
            conda_prefix="/path/to/conda",
            snake_default=["--verbose"],
            snake_args=["--dry-run"],
            profile="my_profile",
            workflow_profile=workflow_profile,
            system_workflow_profile=system_workflow_profile,
            log=log_file,
            additional_arg="value",
        )

        # Assert that the copy_config function was called with the expected arguments
        mock_copy_config.assert_has_calls([
            call(configfile, system_config=system_config, log=log_file),
            call(workflow_profile_config, system_config=system_workflow_profile, log=log_file)
        ])

        # Assert that the update_config function was called with the expected arguments
        # mock_update_config.assert_called_once_with(configfile, merge={"key2": "value2"}, log=log_file)

        # Assert that the read_config function was called with the configfile
        mock_read_config.assert_called_once_with(configfile)

        # Assert that the subprocess.run function was called with the expected command
        expected_command = "snakemake -s {} --configfile {} --use-conda --conda-prefix /path/to/conda --verbose " \
                           "--dry-run --profile my_profile --workflow-profile {}".format(
            snakefile_path, configfile, workflow_profile
        )
        mock_run.assert_called_once_with(expected_command, shell=True)

        # Assert that the exit code is 0
        assert exit_code == 0


def test_tuple_to_list_single_tuple():
    input_dict = {'a': (1, 2, 3)}
    expected_output = {'a': [1, 2, 3]}
    assert tuple_to_list(input_dict) == expected_output


def test_tuple_to_list_nested_tuples():
    input_dict = {'a': (1, 2, 3), 'b': {'c': (4, 5)}}
    expected_output = {'a': [1, 2, 3], 'b': {'c': [4, 5]}}
    assert tuple_to_list(input_dict) == expected_output


def test_tuple_to_list_no_tuples():
    input_dict = {'a': 1, 'b': {'c': 2}}
    expected_output = {'a': 1, 'b': {'c': 2}}
    assert tuple_to_list(input_dict) == expected_output


def test_tuple_to_list_empty_dict():
    input_dict = {}
    expected_output = {}
    assert tuple_to_list(input_dict) == expected_output


def test_tuple_to_list_mixed_types():
    input_dict = {'a': (1, 2, 3), 'b': 'string', 'c': {'d': (4, 5)}, 'e': 6}
    expected_output = {'a': [1, 2, 3], 'b': 'string', 'c': {'d': [4, 5]}, 'e': 6}
    assert tuple_to_list(input_dict) == expected_output