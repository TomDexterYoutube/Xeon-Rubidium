Markdown

# Xeon-Rubidium

**The official project and build manager for the Rubidium programming language.**

Xeon streamlines the process of initializing, building, and running your Rubidium applications. It acts as your primary toolchain, working seamlessly across Windows, Linux, and macOS, and natively handling project roots just like Cargo.

---

## Installation Setup

To get started with Xeon, you need to link it with the core Rubidium compiler files.

1. **Download the Compiler:** Retrieve the latest version of the Rubidium compiler from the official repository:
   [https://github.com/TomDexterYoutube/Rubidium](https://github.com/TomDexterYoutube/Rubidium)
2. **Prepare the Directory:** Extract the downloaded files and place them directly into the `rubidium/` folder within your downloaded Xeon directory.
3. **Execute the Installer:** Run the appropriate installation script for your operating system to install Xeon globally. **The script will automatically detect and install required dependencies like Python 3 and Clang.**
   * **Windows:** Run `install.bat`
   * **Linux / macOS:** Run `bash install.sh`

> **Note:** The installer will automatically configure your `~/.xeon` directory and add the `xeon` command to your system path. You can update your compiler version at any time by simply replacing the files inside the `~/.xeon` folder.

---

## Usage Guide

Once installed, you can manage your Rubidium projects using the `xeon` command line interface. Here are the core commands to drive your development:

### 1. Initialize a New Project
Creates a new project structure in your current directory, generating a `src/` folder and a boilerplate `main.rub` file.

```bash

xeon init

```

2. Build the Project

Compiles your application starting from src/main.rub. The resulting runnable binary executable will be placed inside a generated build/ directory.
Bash

```bash

xeon build

```

3. Run the Project

Automatically builds your project and immediately executes the resulting binary in one continuous step.
Bash

```bash

xeon run

```

Example Workflow

Here is what a standard development session looks like from your terminal

```bash

# Create a new folder for your application
mkdir my_application
cd my_application

# Initialize the Rubidium project
xeon init

# (Edit your src/main.rub file here)

# Build and execute the code
xeon run

```
