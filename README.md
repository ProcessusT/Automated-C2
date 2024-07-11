# Automated-C2


## Description

This project provides a sophisticated mechanism for setting up a command and control (C2) server on Azure, equipped with a frontdoor redirector to legitimize outbound traffic from the implant. The Python script automates the deployment of an Azure VM, configures the frontdoor, and installs the Havoc C2 server with randomly generated URIs and connection ports to enhance operational security.

## Features

- **Automated Azure VM Deployment**: Utilizes Azure's API to create a virtual machine tailored for C2 operations.
- **Azure Frontdoor Configuration**: Sets up Azure Frontdoor to act as a traffic redirector, masking C2 traffic and ensuring it appears legitimate.
- **Havoc C2 Installation**: Deploys the Havoc C2 server on the created VM, configuring it for secure and efficient command and control operations.
- **Randomized URIs and Ports**: Implements random generation of URIs and communication ports for the Havoc C2 server, increasing the difficulty of detection and analysis.

<br>
<img src="https://github.com/ProcessusT/Automated-C2/raw/main/.assets/c2.png" width="100%;"><br>
<br>
<img src="https://github.com/ProcessusT/Automated-C2/raw/main/.assets/demo.png" width="100%;"><br>


## Prerequisites

- **Azure Account**: Ensure you have an active Azure account with sufficient permissions to create resources.
- **Python 3.x**: The script is written in Python and requires Python3 to run.
- **Azure CLI**: Install the Azure CLI tool for interacting with Azure resources.


## Technical Details

### Azure VM Deployment

The script leverages Azure's SDK to create a virtual machine with the specified configurations. It ensures the VM is provisioned with adequate resources and network settings to support C2 activities.

### Azure Frontdoor Configuration

Azure Frontdoor is configured as a redirector, providing an additional layer of obfuscation. The script sets up the frontdoor to route traffic from legitimate-looking domains to the C2 server, minimizing the risk of detection.

### Randomized URIs and Ports

To prevent pattern-based detection, the script generates random URIs and ports for the Havoc C2 server. This dynamic approach complicates traffic analysis and signature-based detection mechanisms employed by security solutions.

### Havoc C2 Installation

The Havoc C2 server is installed on the VM using a series of automated steps. The script ensures the server is configured to use the randomized URIs and ports, establishing a secure and flexible C2 infrastructure.


## Contributing

Contributions to this project are welcome. Please fork the repository and submit pull requests for any enhancements or bug fixes.


## Acknowledgements

- **Havoc Framework**: Special thanks to the developers of the Havoc C2 framework for their powerful and flexible tool.


---

**Disclaimer**: This project is intended for educational and research purposes only. The author is not responsible for any misuse or damage caused by this project.