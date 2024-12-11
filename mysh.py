import signal
import sys
import os
import re
import shlex
import json

# Built-in commands set
builtins = {"cd", "exit", "pwd", "which", "var"}

# Pattern to match valid variable names (letters, digits, and underscores)
valid_variable_pattern = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$')

# DO NOT REMOVE THIS FUNCTION!
# This function is required in order to correctly switch the terminal foreground group to
# that of a child process.
def setup_signals() -> None:
    """
    Setup signals required by this program.
    """
    signal.signal(signal.SIGTTOU, signal.SIG_IGN)

def load_myshrc():
    """Load and parse the .myshrc JSON file for environment variables."""
    myshrc_path = os.path.expanduser("~/.myshrc")
    
    # Check if MYSHDOTDIR environment variable is set, adjust path if necessary
    if 'MYSHDOTDIR' in os.environ:
        myshrc_path = os.path.join(os.environ['MYSHDOTDIR'], '.myshrc')
    
    # Attempt to open and read the .myshrc file
    try:
        with open(myshrc_path, 'r') as file:
            data = json.load(file)
    except FileNotFoundError:
        # If the file doesn't exist, silently continue
        return
    except json.JSONDecodeError:
        # Handle invalid JSON format
        print("mysh: invalid JSON format for .myshrc", file=sys.stderr)
        return
    
    # Process each environment variable from the JSON data
    for key, value in data.items():
        # Check if the key is a valid variable name
        if not valid_variable_pattern.match(key):
            print(f"mysh: .myshrc: {key}: invalid characters for variable name", file=sys.stderr)
            continue
        if not isinstance(value, str):
            print(f"mysh: .myshrc: {key}: not a string", file=sys.stderr)
            continue
        
        # Attempt to resolve any references to other variables within the value
        try:
            resolved_value = os.path.expandvars(value)
            os.environ[key] = resolved_value
        except Exception as e:
            print(f"mysh: .myshrc: {key}: error resolving value: {e}", file=sys.stderr)
            continue

    # Update prompt based on the loaded MYSH_VERSION
    update_prompt_based_on_version()

def update_prompt_based_on_version():
    """Update the shell prompt based on the MYSH_VERSION variable."""
    # Get the MYSH_VERSION environment variable
    version = os.environ.get('MYSH_VERSION', '1.0')

    # If MYSH_VERSION is '1.1.1', set the prompt to 'mysh $ '
    if version == '1.1.1':
        os.environ['PROMPT_DISPLAY'] = 'mysh $ '
    else:
        # Default prompt
        os.environ['PROMPT_DISPLAY'] = '>> '


def exit_command(args: list[str]) -> None:
    """Exit the shell with an optional exit code."""
    if len(args) > 1:
        print("exit: too many arguments", file=sys.stderr)
        return
    if len(args) == 1:
        try:
            exit_code = int(args[0])
        except ValueError:
            print(f"exit: non-integer exit code provided: {args[0]}", file=sys.stderr)
            return
    else:
        exit_code = 0
    sys.exit(exit_code)

# Internal variable to keep track of the current working directory path
current_directory = os.getcwd()

def update_current_directory(path):
    """Update the internal current directory variable and the PWD environment variable."""
    global current_directory
    if os.path.isabs(path):
        current_directory = os.path.normpath(path)
    else:
        current_directory = os.path.normpath(os.path.join(current_directory, path))
    
    # Update the PWD environment variable to match the current directory
    os.environ['PWD'] = current_directory

def pwd_command(args):
    """Handle the built-in pwd command."""
    if len(args) > 1 or (len(args) == 1 and args[0].startswith('-') and args[0] != '-P'):
        for arg in args:
            if arg.startswith('-'):
                for char in arg[1:]:
                    if char != 'P':
                        print(f"pwd: invalid option: -{char}", file=sys.stderr)
                        return
        print("pwd: not expecting any arguments", file=sys.stderr)
        return

    # Print real path if -P is specified, otherwise print the maintained logical path
    if len(args) == 1 and args[0] == '-P':
        print(os.path.realpath(current_directory))
    else:
        print(current_directory)

def cd_command(args):
    """Handle the built-in cd command."""
    if len(args) > 1:
        print("cd: too many arguments", file=sys.stderr)
        return
    
    # Handle `cd` with no arguments or `cd ~` to navigate to the home directory
    path = args[0] if args else os.path.expanduser("~")
    path = os.path.expanduser(path)  # Expand the tilde to the home directory if present
    
    try:
        os.chdir(path)
        update_current_directory(path)  # Update the current directory and PWD variable
    except FileNotFoundError:
        print(f"cd: no such file or directory: {path}", file=sys.stderr)
    except NotADirectoryError:
        print(f"cd: not a directory: {path}", file=sys.stderr)
    except PermissionError:
        print(f"cd: permission denied: {path}", file=sys.stderr)

def find_executable(cmd):
    """Find the first executable match for a command in the current PATH."""
    # Retrieve the current PATH environment variable or set to None if not present
    path_dirs = os.environ.get("PATH")

    # If PATH is explicitly empty, return None to indicate command not found
    if path_dirs == "":
        return None

    # If PATH is unset (None), fallback to common system paths
    if path_dirs is None:
        path_dirs = ["/bin", "/usr/bin", "/usr/local/bin"]
    else:
        path_dirs = path_dirs.split(os.pathsep)

    # Check each directory in the PATH for the executable command
    for directory in path_dirs:
        if directory:  # Ensure the directory is not empty
            executable_path = os.path.join(directory, cmd)
            if os.path.isfile(executable_path) and os.access(executable_path, os.X_OK):
                return executable_path
    return None



def which_command(args):
    """Handle the built-in which command."""
    if not args:
        print("usage: which command ...", file=sys.stderr)
        return
    
    for cmd in args:
        if cmd in builtins:
            print(f"{cmd}: shell built-in command")
        else:
            path = find_executable(cmd)
            if path:
                print(path)
            else:
                print(f"{cmd} not found")

def is_valid_variable_name(var_name):
    """Check if the provided variable name is valid according to shell rules."""
    return bool(valid_variable_pattern.match(var_name))

def echo_command(args):
    """Handle the echo command with proper escape handling."""
    command = ' '.join(args)

    result = []
    i = 0
    while i < len(command):
        if command[i] == '\\' and i + 1 < len(command):
            if command[i + 1] == '$' and i + 2 < len(command) and command[i + 2] == '{':
                var_end = command.find('}', i + 2)
                if var_end != -1:
                    result.append(command[i + 1:var_end + 1])  # Append ${var} as is without expansion
                    i = var_end + 1
                else:
                    result.append(command[i + 1])
                    i += 2
            else:
                result.append(command[i + 1])
                i += 2
        elif command[i] == '$' and i + 1 < len(command) and command[i + 1] == '{':
            var_end = command.find('}', i + 2)
            if var_end != -1:
                var_name = command[i + 2:var_end]

                # Check for invalid characters in the variable name
                if not is_valid_variable_name(var_name):
                    print(f"mysh: syntax error: invalid characters for variable {var_name}", file=sys.stderr)
                    return

                # Expand the variable if it's defined, otherwise just print a newline
                var_value = os.environ.get(var_name, "")
                
                # If PROMPT is being echoed, simulate the prompt by showing ">>"
                if var_name == 'PROMPT':
                    print(">> \n", end='')  # Display the prompt and keep the cursor at the prompt
                    return  # Exit to prompt for the next command line input

                result.append(var_value)
                i = var_end + 1
            else:
                result.append(command[i])
                i += 1
        else:
            result.append(command[i])
            i += 1

    processed_text = ''.join(result)
    print(processed_text)



def var_command(args):
    """Handle the built-in var command including setting variables."""
    if not args or (len(args) == 1 and args[0].startswith('-')):
        print("var: expected 2 arguments, got 0", file=sys.stderr)
        return

    # Check for flags and handle invalid flag characters
    if args[0].startswith('-'):
        for char in args[0][1:]:
            if char != 's':
                print(f"var: invalid option: -{char}", file=sys.stderr)
                return

    # Handle the -s option for command execution
    use_command = args[0] == '-s'
    if use_command:
        if len(args) < 3:
            print(f"var: expected 3 arguments, got {len(args)}", file=sys.stderr)
            return

        variable_name = args[1]
        command_to_run = args[2]

        # Check if variable name is valid without expanding it
        if not is_valid_variable_name(variable_name):
            print(f"mysh: syntax error: invalid characters for variable {variable_name}", file=sys.stderr)
            return

        # Create a pipe to capture the command's output
        read_fd, write_fd = os.pipe()
        pid = os.fork()
        if pid == 0:  # Child process
            os.close(read_fd)  # Close the read end in the child
            os.dup2(write_fd, 1)  # Redirect stdout to the write end of the pipe
            os.dup2(write_fd, 2)  # Redirect stderr to the write end of the pipe
            os.close(write_fd)

            # Use /bin/sh -c to handle complex shell commands with pipes
            try:
                os.execvp("/bin/sh", ["sh", "-c", command_to_run])
            except Exception as e:
                print(f"Error executing {command_to_run}: {e}", file=sys.stderr)
            sys.exit(1)  # Exit if exec fails
        else:  # Parent process
            os.close(write_fd)  # Close the write end in the parent
            output = os.read(read_fd, 4096).decode().strip()  # Read the command's output
            os.close(read_fd)
            os.waitpid(pid, 0)  # Wait for the child process to finish

            # Process output
            multiline_output = len(output.splitlines()) > 1
            formatted_output = '\n'.join([line.rstrip() for line in output.splitlines()])

            # Append newline if output is multiline or commands warrant it
            if multiline_output or command_to_run.startswith(('cat', 'grep', 'sort')):
                formatted_output += '\n'

            os.environ[variable_name] = formatted_output
        return

    # Handle standard var command setting
    if len(args) != 2:
        print(f"var: expected 2 arguments, got {len(args)}", file=sys.stderr)
        return

    variable_name = args[0]
    value = args[1].strip('"').strip("'")

    # Check if the variable name is valid
    if not is_valid_variable_name(variable_name):
        print(f"var: invalid characters for variable {variable_name}", file=sys.stderr)
        return

    # Set the environment variable with correct expansion of any existing variables
    resolved_value = os.path.expandvars(value)
    os.environ[variable_name] = resolved_value

    # Check if the variable being set is PATH to ensure it is correctly updated
    if variable_name == "PATH":
        # Split the updated PATH to update the path directories dynamically
        os.environ["PATH"] = resolved_value

    # Check if the variable being set is PROMPT
    if variable_name == 'PROMPT':
        update_prompt(value)

def update_prompt(value):
    """Update the shell prompt based on the value of the PROMPT variable."""
    # Expand environment variables within the PROMPT value
    expanded_prompt = os.path.expandvars(value)

    # If the prompt is empty, default to '>>'
    if not expanded_prompt:
        os.environ['PROMPT_DISPLAY'] = '>> '
    else:
        os.environ['PROMPT_DISPLAY'] = expanded_prompt



def check_pipe_syntax(commands):
    """Check for syntax errors in piping commands."""
    # Trim whitespace from each command and check if any command is missing
    trimmed_commands = [cmd.strip() for cmd in commands]

    # Check if the first or last command is empty, indicating a missing command
    if not trimmed_commands[0] or not trimmed_commands[-1]:
        print("mysh: syntax error: expected command after pipe", file=sys.stderr)
        return False

    # Check if any intermediate command is empty (between pipes)
    for i, command in enumerate(trimmed_commands):
        if not command:
            print("mysh: syntax error: expected command after pipe", file=sys.stderr)
            return False

    return True

def run_command_with_pipes(command):
    """Run a shell-like command with pipes, handling SIGINT correctly."""
    # Split commands by pipe while preserving quoted pipes
    commands = [shlex.split(cmd.strip()) for cmd in re.split(r'\s*\|\s*(?=(?:[^\'"]*[\'"][^\'"]*[\'"])*[^\'"]*$)', command)]

    # Check for missing command syntax error
    if not check_pipe_syntax(command.split('|')):
        return

    num_commands = len(commands)
    pipe_fds = []

    # Setup pipes between processes
    for _ in range(num_commands - 1):
        pipe_fds.append(os.pipe())

    processes = []
    pgid = None  # Process Group ID of the first command

    for i, cmd in enumerate(commands):
        # Skip if command is empty after splitting (this case should already be caught by check_pipe_syntax)
        if not cmd:
            print("mysh: syntax error: expected command after pipe", file=sys.stderr)
            return

        # Expand the tilde (~) manually
        cmd = [os.path.expanduser(arg) for arg in cmd]

        pid = os.fork()
        if pid == 0:  # Child process
            # Set the process group; for the first process, make it the group leader
            if i == 0:
                os.setpgrp()  # Create a new process group with the first command as the leader
            else:
                try:
                    os.setpgid(0, pgid)  # Set subsequent processes to the first process's group
                except PermissionError:
                    pass  # Ignore permission errors when setting process group

            # Setup input from the previous pipe, if not the first command
            if i > 0:
                os.dup2(pipe_fds[i - 1][0], 0)  # Redirect stdin to the read end of the previous pipe
            # Setup output to the next pipe, if not the last command
            if i < num_commands - 1:
                os.dup2(pipe_fds[i][1], 1)  # Redirect stdout to the write end of the current pipe

            # Close all pipe fds in the child process
            for fd_pair in pipe_fds:
                os.close(fd_pair[0])
                os.close(fd_pair[1])

            # Execute the command
            try:
                os.execvp(cmd[0], cmd)
            except BrokenPipeError:
                sys.exit(0)  # Silently exit if there's a broken pipe error
            except FileNotFoundError:
                print(f"{cmd[0]}: command not found", file=sys.stderr)
            except IndexError:
                # Handle case where no command exists after a pipe
                print("mysh: syntax error: expected command after pipe", file=sys.stderr)
            except Exception as e:
                print(f"Error executing {cmd[0]}: {e}", file=sys.stderr)
            sys.exit(1)  # Exit the child process if exec fails
        else:  # Parent process
            if pgid is None:
                pgid = pid  # Set the process group ID to the first child PID
                try:
                    os.setpgid(pid, pgid)  # Set the group ID for the first process
                except PermissionError:
                    pass  # Ignore permission errors when setting process group
            else:
                try:
                    os.setpgid(pid, pgid)  # Set subsequent processes to the same group
                except PermissionError:
                    pass  # Ignore permission errors when setting process group

            processes.append(pid)

    # Close all pipe fds in the parent process
    for fd_pair in pipe_fds:
        os.close(fd_pair[0])
        os.close(fd_pair[1])

    # Ignore SIGINT in the shell; the child process group handles it
    old_handler = signal.signal(signal.SIGINT, signal.SIG_IGN)

    try:
        # Wait for all child processes to finish
        for pid in processes:
            os.waitpid(pid, 0)
    except KeyboardInterrupt:
        # Send SIGINT to the entire process group to terminate all piped commands
        os.killpg(pgid, signal.SIGINT)
    finally:
        # Restore the previous SIGINT handler
        signal.signal(signal.SIGINT, old_handler)



def parse_command(cmd):
    """Parse the command string into arguments, preserving escape sequences."""
    lexer = shlex.shlex(cmd, posix=True)
    lexer.whitespace_split = True
    lexer.escape = ''  # Disable shlex's escape handling to preserve backslashes
    lexer.quotes = "'\""  # Allow both single and double quotes

    try:
        args = []
        current_arg = ''
        in_quotes = False
        quote_char = ''

        for token in lexer:
            if not in_quotes and (token.startswith("'") or token.startswith('"')):
                # Starting a new quoted string
                in_quotes = True
                quote_char = token[0]
                current_arg = token
            elif in_quotes and token.endswith(quote_char):
                # Ending the quoted string
                in_quotes = False
                current_arg += ' ' + token
                args.append(current_arg)
                current_arg = ''
                quote_char = ''
            elif in_quotes:
                # Inside a quoted string, accumulate tokens
                current_arg += ' ' + token
            else:
                # Regular token outside of quotes
                args.append(token)

        # If still inside quotes after processing all tokens, it's an unterminated quote error
        if in_quotes:
            print("mysh: syntax error: unterminated quote", file=sys.stderr)
            return None

        processed_args = []
        for arg in args:
            # Check if the argument is a variable with invalid characters
            if arg.startswith('${') and arg.endswith('}'):
                var_name = arg[2:-1]
                if not is_valid_variable_name(var_name):
                    print(f"mysh: syntax error: invalid characters for variable {var_name}", file=sys.stderr)
                    return None
            processed_args.append(re.sub(r'\\\$', r'\\$', arg))
        return processed_args
    except ValueError:
        print("mysh: syntax error: unterminated quote", file=sys.stderr)
        return None




def execute_command(args):
    """Execute external commands with arguments using the current PATH."""
    # Expand tilde (~) in the command arguments
    args = [os.path.expanduser(arg) for arg in args]

    # Check if the command is a local file or executable in PATH
    cmd = args[0]

    # Check if the command is a built-in and if it should be handled
    if cmd in builtins:
        # Only execute built-ins if PATH is not explicitly empty
        if os.environ.get("PATH") == "":
            print(f"mysh: command not found: {cmd}", file=sys.stderr)
            return

        # Otherwise, run the built-in command directly
        if cmd == "echo":
            echo_command(args[1:])
            return
        elif cmd == "pwd":
            pwd_command(args[1:])
            return
        elif cmd == "cd":
            cd_command(args[1:])
            return
        elif cmd == "which":
            which_command(args[1:])
            return
        elif cmd == "var":
            var_command(args[1:])
            return

    # Check if the command is a local file
    if os.path.isfile(cmd):
        # Check if the file has executable permissions
        if not os.access(cmd, os.X_OK):
            print(f"mysh: permission denied: {cmd}", file=sys.stderr)
            return
        # If it's a local executable file, use it directly
        executable = cmd
    else:
        # Find executable in PATH if it's not a local command with a specified path
        executable = find_executable(cmd)

    # Handle command not found error
    if executable is None:
        print(f"mysh: command not found: {cmd}", file=sys.stderr)
        return

    pid = os.fork()
    if pid == 0:  # Child process
        os.setpgrp()  # Set the child as the leader of a new process group
        try:
            # Execute the command using the executable found or provided path
            os.execvp(executable, args)
        except FileNotFoundError:
            print(f"mysh: command not found: {cmd}", file=sys.stderr)
        except PermissionError:
            print(f"mysh: permission denied: {cmd}", file=sys.stderr)
        except Exception as e:
            print(f"Error executing {cmd}: {e}", file=sys.stderr)
        sys.exit(1)  # Exit the child process if exec fails
    else:  # Parent process
        # Ignore SIGINT in the shell and pass it to the child process group
        old_handler = signal.signal(signal.SIGINT, signal.SIG_IGN)
        try:
            # Wait for the child process to finish
            os.waitpid(pid, 0)
        except KeyboardInterrupt:
            # Send SIGINT to the process group of the child
            os.killpg(pid, signal.SIGINT)
        finally:
            # Restore the previous SIGINT handler
            signal.signal(signal.SIGINT, old_handler)



def initialize_default_environment():
    """Initialize default environment variables for the shell."""
    # Set the default prompt variable; it prompts the next input
    if 'PROMPT' not in os.environ:
        os.environ['PROMPT'] = ''
    # Set the default version for the shell only if not already set
    if 'MYSH_VERSION' not in os.environ:
        os.environ['MYSH_VERSION'] = '1.0'


def main() -> None:
    # DO NOT REMOVE THIS FUNCTION CALL!
    setup_signals()

    # Load the .myshrc configuration at shell startup
    load_myshrc()

    # Initialize default environment variables
    initialize_default_environment()

    # Set the initial prompt display based on the MYSH_VERSION
    update_prompt_based_on_version()

    while True:
        try:
            # Use the dynamic prompt display
            cmd = input(os.environ.get('PROMPT_DISPLAY', '>> ')).strip()
            if not cmd:
                continue

            # Check for syntax error if there is a missing command after a pipe
            if '|' in cmd and not check_pipe_syntax(cmd.split('|')):
                continue  # Skip further execution if there's a pipe syntax error

            # Handle piping separately
            if '|' in cmd:
                run_command_with_pipes(cmd)
                continue

            args = parse_command(cmd)
            if args is None:
                continue

            command = args[0]
            if command == "exit":
                exit_command(args[1:])
            elif command == "pwd":
                pwd_command(args[1:])
            elif command == "cd":
                cd_command(args[1:])
            elif command == "which":
                which_command(args[1:])
            elif command == "var":
                var_command(args[1:])
            elif command == "echo":
                echo_command(args[1:])
            else:
                execute_command(args)  # Execute non-built-in commands
        except EOFError:
            print()  # Final newline after EOF
            sys.exit(0)


if __name__ == "__main__":
    main()
