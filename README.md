# Unix Shell Implementation (`mysh`) 🚀

### Duration: August 2024 to September 2024
This project is a custom Unix shell written in Python. The shell replicates and extends basic Unix shell functionalities, supporting custom commands, piping, environment variables, and initialization from configuration files.

## Features ✨

### Core Functionalities:
- **Execute Commands**: Supports running system commands available in the `PATH`.
- **Built-in Commands**:
  - `pwd`: Prints the current working directory.
  - `cd`: Changes the current working directory.
  - `which`: Identifies if a command is built-in or finds its path in `PATH`.
  - `var`: Manages shell environment variables.
  - `exit`: Exits the shell.
  - `echo`: Prints text to the console, with support for environment variable expansion.

### Advanced Features:
- **Piping**: Redirects the output of one command to the input of another using `|`.
- **Custom Initialization**: Reads environment variables from a `.myshrc` JSON file located in the user's home directory or a custom directory specified by `MYSHDOTDIR`.
- **Error Handling**:
  - Detects syntax errors (e.g., unclosed quotes, missing commands after pipes).
  - Handles invalid commands gracefully with descriptive error messages.
- **Signal Management**: Ignores `SIGTTOU` to ensure smooth foreground process group management.

---

## Project Structure 📂

```plaintext
mysh/
├── mysh.py                 
├── parsing.py                      
├── tests/                 
├── README.md    
```
## Setup and Running 🛠️
### Prerequisites:
1. Python 3.8+
2. Unix-based environment (Linux/macOS).

### Steps to Run:
1. Clone the Repository:
```bash
git clone https://github.com/yourusername/mysh.git
cd mysh
```
2. Create `.myshrc` file in home directory
```json
{    "PROMPT": "mysh $ ",
    "MYSH_VERSION": "1.0"}
```
3. Run the shell
```bash
python3 mysh.py
```
4. Type exit to terminate the shell.

## Testing 🧪
### Test Directory Structure:
1. Input/Output Files:
Input files (*.in) contain shell commands to test specific functionalities.
Expected output files (*.out) store the corresponding expected results.

2. Test Script:
The `run_tests.sh` script automates testing by comparing the output of mysh with the expected results.


3. Running Tests:
Ensure the `tests/` directory contains your test cases.
```bash
./run_tests.sh
```

## Technical Details 🔍
### Command Parsing:
Utilizes shlex for splitting input into arguments while respecting quoted strings and escaped characters.
Supports pipes (|) and environment variable substitutions (e.g., ${VAR}).

### Piping:
Implements os.pipe and process forking to connect multiple commands in a pipeline.
Ensures all piped commands are part of the same process group, allowing Ctrl+C to terminate the entire pipeline.

### Environment Variables:
Managed via the var command and stored in the process's os.environ.
Supports substitution within command arguments using ${VAR} syntax.

### Initialization:
Reads .myshrc JSON files to load default environment variables.
Gracefully handles missing or invalid .myshrc files.

## Example Usage 📋
### Commands:
1. Change Directory
```bash
cd /path/to/directory
```
2. Print current directory
```bash
pwd
```
3. Define variable
```bash
var GREETING "Hello, world!"
echo ${GREETING}
```
4. Pipe Commands
```bash
ls | grep "mysh"
```
### Error Cases:
1. Missing command after pipe
```bash
ls | 
# Output: mysh: syntax error: expected command after pipe
```

## Technologies Used 🛠️
### Python:
`os`, `signal`, and `shlex` modules for command execution and piping.

`json` for parsing initialization files.

## Contact 📬
For questions or collaboration:

Email: ashish.shiju@outlook.com

GitHub: [ashish-shiju](https://github.com/ashish-shiju)
