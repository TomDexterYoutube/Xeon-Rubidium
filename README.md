# Xeon-Rubidium

**The official project, build, and package manager for the Rubidium programming language.**

Xeon is the complete command-line toolchain for Rubidium. It handles project creation, static analysis, debugging, compilation, package management, and execution from a single command.

Designed to work on **Windows**, **Linux**, and **macOS**, Xeon automatically detects your project root and provides a workflow similar to Cargo, while remaining tailored specifically for Rubidium.

> **Rubidium Source Code:** https://github.com/TomDexterYoutube/Rubidium

---

# Features

- Create new Rubidium projects
- Static code analysis
- Integrated debugger
- Native executable compilation
- Shared library compilation (.so/.dll/.dylib)
- Automatic FFI library bundling
- Package manager
- Automatic package updates
- Cross-platform support
- Zero configuration

---

# Installation

Run the installer for your operating system.

### Windows

```powershell
install.ps1
```

### Linux / macOS

```bash
bash install.sh
```

The installer automatically:

- Installs Python 3 (if required)
- Installs Clang (if required)
- Creates the `~/.xeon` directory
- Installs the Rubidium compiler
- Installs the debugger
- Adds `xeon` to your system PATH

There is no complicated setup.

---

# Basic Workflow

Create a project

```bash
mkdir MyProject
cd MyProject

xeon init
```

Edit:

```
src/main.rub
```

Build

```bash
xeon build
```

Run

```bash
xeon run
```

That's it.

---

# Commands

## xeon init

Creates a new Rubidium project.

Creates:

```
src/
└── main.rub
```

Example

```bash
xeon init
```

---

## xeon check

Runs the Rubidium static analyzer without compiling.

Useful for CI, quick validation, or checking code before a build.

```bash
xeon check
```

---

## xeon build

Runs:

1. Static checks
2. Debugger
3. Compiler

Produces a native executable inside:

```
build/
```

Example

```bash
xeon build
```

---

## xeon run

Builds the project and immediately runs the generated executable.

```bash
xeon run
```

---

# Build Options

## Skip debugger

If you don't want debugger validation:

```bash
xeon build --no-debug
```

or

```bash
xeon run --no-debug
```

---

## Build as a Shared Library

Instead of creating an executable, compile a shared library.

Linux

```
.so
```

Windows

```
.dll
```

macOS

```
.dylib
```

Example

```bash
xeon build -s
```

Shared libraries are intended to be loaded from another language through Rubidium's FFI system.

Since shared libraries have no program entry point:

```bash
xeon run -s
```

is intentionally not supported.

---

# Automatic FFI Bundling

When building a project, Xeon automatically copies any FFI libraries found inside your source directory into the build folder.

Supported files include:

```
.so
.dll
.dylib
```

No additional configuration is required.

---

# Package Manager

Xeon includes an integrated package manager.

```
xeon pkg
```

Packages are installed into

```
~/.xeon/packages/
```

---

## Package Commands

### Show Help

```bash
xeon pkg help
```

---

### Fetch Package Index

Downloads the latest package list.

```bash
xeon pkg fetch
```

---

### Install a Package

```bash
xeon pkg pull <package>
```

Example

```bash
xeon pkg pull math
```

If your local package list is missing or more than 24 hours old, Xeon automatically refreshes it before installing.

No need to remember to run `fetch`.

---

### Remove a Package

```bash
xeon pkg purge <package>
```

Example

```bash
xeon pkg purge math
```

---

### Upgrade Installed Packages

Updates every installed package to the newest available version.

```bash
xeon pkg upgrade
```

Like `pull`, this automatically refreshes the package list when necessary.

---

# Using Packages

After installing a package:

```bash
xeon math
```

Access its members normally.

```rubidium
print(math.pi)
```

Packages can also be imported with aliases.

```rubidium
xeon math as m

print(m.pi)
```

---

# Package Repository

Current package repository:

https://github.com/TomDexterYoutube/xeon-pkgs

---

# Project Layout

A typical project looks like:

```
MyProject/
│
├── src/
│   ├── main.rub
│   └── ...
│
└── build/
```

The build directory is recreated every compilation.

---

# Example Workflow

```bash
mkdir Calculator
cd Calculator

xeon init

# edit src/main.rub

xeon check

xeon build

xeon run
```

---

# Command Summary

| Command | Description |
|----------|-------------|
| `xeon init` | Create a new project |
| `xeon check` | Run the static analyzer |
| `xeon build` | Build the project |
| `xeon run` | Build and run |
| `xeon build -s` | Build as shared library |
| `xeon build --no-debug` | Skip debugger |
| `xeon run --no-debug` | Run without debugger |
| `xeon pkg help` | Package manager help |
| `xeon pkg fetch` | Download package list |
| `xeon pkg pull <name>` | Install package |
| `xeon pkg purge <name>` | Remove package |
| `xeon pkg upgrade` | Upgrade installed packages |

---

# Contributing

Found a bug?

Have an idea?

Think something could be improved?

Open an issue on GitHub.

Feature suggestions and bug reports are greatly appreciated.

---

# Support

Xeon and Rubidium are completely free.

There are no paid editions or subscriptions.

If you'd like to support development, the best way is to:

- Report bugs
- Suggest features
- Improve documentation
- Share the project
- Contribute packages

Every report helps make Rubidium better.
