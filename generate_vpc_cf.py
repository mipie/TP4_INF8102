#!/usr/bin/env python3
from troposphere import (
    Template, Ref, Parameter, Sub, GetAZs, Select, Tags, Output, Join, GetAtt
)
import troposphere.ec2 as ec2
import troposphere.iam as iam
import troposphere.cloudwatch as cloudwatch

t = Template()
t.set_description("""This deploys a VPC, with a pair of public and private subnets spread
 across two Availability Zones. It deploys an internet gateway, with a default
 route on the public subnets. It deploys a pair of NAT gateways (one in each AZ),
 and default routes for them in the private subnets.""")

# PARAMETERS
EnvironmentName = t.add_parameter(Parameter(
    "EnvironmentName",
    Type="String",
    Description="environment is prefixed to resource names"
))

VpcCIDR = t.add_parameter(Parameter(
    "VpcCIDR",
    Type="String",
    Description="VPC polystudent-vpc",
    Default="10.0.0.0/16"
))

PublicSubnet1CIDR = t.add_parameter(Parameter(
    "PublicSubnet1CIDR",
    Type="String",
    Description="public subnet in Availability Zone 1",
    Default="10.0.0.0/24"
))

PublicSubnet2CIDR = t.add_parameter(Parameter(
    "PublicSubnet2CIDR",
    Type="String",
    Description="public subnet in Availability Zone 2",
    Default="10.0.16.0/24"
))

PrivateSubnet1CIDR = t.add_parameter(Parameter(
    "PrivateSubnet1CIDR",
    Type="String",
    Description="private subnet in Availability Zone 1",
    Default="10.0.128.0/24"
))

PrivateSubnet2CIDR = t.add_parameter(Parameter(
    "PrivateSubnet2CIDR",
    Type="String",
    Description="private subnet in Availability Zone 2",
    Default="10.0.144.0/24"
))

# RESOURCES
VPC = t.add_resource(ec2.VPC(
    "VPC",
    CidrBlock=Ref(VpcCIDR),
    EnableDnsSupport=True,
    EnableDnsHostnames=True,
    Tags=Tags(Name=Ref(EnvironmentName))
))

PublicSubnet1 = t.add_resource(ec2.Subnet(
    "PublicSubnet1",
    VpcId=Ref(VPC),
    AvailabilityZone=Select(0, GetAZs("")),
    CidrBlock=Ref(PublicSubnet1CIDR),
    MapPublicIpOnLaunch=True,
    Tags=Tags(Name=Sub("${EnvironmentName} Public Subnet (AZ1)"))
))

PublicSubnet2 = t.add_resource(ec2.Subnet(
    "PublicSubnet2",
    VpcId=Ref(VPC),
    AvailabilityZone=Select(1, GetAZs("")),
    CidrBlock=Ref(PublicSubnet2CIDR),
    MapPublicIpOnLaunch=True,
    Tags=Tags(Name=Sub("${EnvironmentName} Public Subnet (AZ2)"))
))

PrivateSubnet1 = t.add_resource(ec2.Subnet(
    "PrivateSubnet1",
    VpcId=Ref(VPC),
    AvailabilityZone=Select(0, GetAZs("")),
    CidrBlock=Ref(PrivateSubnet1CIDR),
    MapPublicIpOnLaunch=False,
    Tags=Tags(Name=Sub("${EnvironmentName} Private Subnet (AZ1)"))
))

PrivateSubnet2 = t.add_resource(ec2.Subnet(
    "PrivateSubnet2",
    VpcId=Ref(VPC),
    AvailabilityZone=Select(1, GetAZs("")),
    CidrBlock=Ref(PrivateSubnet2CIDR),
    MapPublicIpOnLaunch=False,
    Tags=Tags(Name=Sub("${EnvironmentName} Private Subnet (AZ2)"))
))

# Internet Gateway
InternetGateway = t.add_resource(ec2.InternetGateway(
    "InternetGateway",
    Tags=Tags(Name=Ref(EnvironmentName))
))

InternetGatewayAttachment = t.add_resource(ec2.VPCGatewayAttachment(
    "InternetGatewayAttachment",
    InternetGatewayId=Ref(InternetGateway),
    VpcId=Ref(VPC)
))

# Route tables
PublicRouteTable = t.add_resource(ec2.RouteTable(
    "PublicRouteTable",
    VpcId=Ref(VPC),
    Tags=Tags(Name=Sub("${EnvironmentName} Public Routes"))
))

t.add_resource(ec2.Route(
    "DefaultPublicRoute",
    RouteTableId=Ref(PublicRouteTable),
    DestinationCidrBlock="0.0.0.0/0",
    GatewayId=Ref(InternetGateway),
    DependsOn="InternetGatewayAttachment"
))

t.add_resource(ec2.SubnetRouteTableAssociation(
    "PublicSubnet1RouteTableAssociation",
    RouteTableId=Ref(PublicRouteTable),
    SubnetId=Ref(PublicSubnet1)
))

t.add_resource(ec2.SubnetRouteTableAssociation(
    "PublicSubnet2RouteTableAssociation",
    RouteTableId=Ref(PublicRouteTable),
    SubnetId=Ref(PublicSubnet2)
))

# NAT Gateways
NatGateway1EIP = t.add_resource(ec2.EIP(
    "NatGateway1EIP",
    Domain="vpc",
    DependsOn="InternetGatewayAttachment"
))

NatGateway2EIP = t.add_resource(ec2.EIP(
    "NatGateway2EIP",
    Domain="vpc",
    DependsOn="InternetGatewayAttachment"
))

NatGateway1 = t.add_resource(ec2.NatGateway(
    "NatGateway1",
    AllocationId=GetAtt(NatGateway1EIP, "AllocationId"),
    SubnetId=Ref(PublicSubnet1)
))

NatGateway2 = t.add_resource(ec2.NatGateway(
    "NatGateway2",
    AllocationId=GetAtt(NatGateway2EIP, "AllocationId"),
    SubnetId=Ref(PublicSubnet2)
))

# PRIVATE ROUTES
PrivateRouteTable1 = t.add_resource(ec2.RouteTable(
    "PrivateRouteTable1",
    VpcId=Ref(VPC),
    Tags=Tags(Name=Sub("${EnvironmentName} Private Routes (AZ1)"))
))

t.add_resource(ec2.Route(
    "DefaultPrivateRoute1",
    RouteTableId=Ref(PrivateRouteTable1),
    DestinationCidrBlock="0.0.0.0/0",
    NatGatewayId=Ref(NatGateway1)
))

t.add_resource(ec2.SubnetRouteTableAssociation(
    "PrivateSubnet1RouteTableAssociation",
    RouteTableId=Ref(PrivateRouteTable1),
    SubnetId=Ref(PrivateSubnet1)
))

PrivateRouteTable2 = t.add_resource(ec2.RouteTable(
    "PrivateRouteTable2",
    VpcId=Ref(VPC),
    Tags=Tags(Name=Sub("${EnvironmentName} Private Routes (AZ2)"))
))

t.add_resource(ec2.Route(
    "DefaultPrivateRoute2",
    RouteTableId=Ref(PrivateRouteTable2),
    DestinationCidrBlock="0.0.0.0/0",
    NatGatewayId=Ref(NatGateway2)
))

t.add_resource(ec2.SubnetRouteTableAssociation(
    "PrivateSubnet2RouteTableAssociation",
    RouteTableId=Ref(PrivateRouteTable2),
    SubnetId=Ref(PrivateSubnet2)
))

# Security group
IngressSecurityGroup = t.add_resource(
    ec2.SecurityGroup(
        "IngressSecurityGroup",
        GroupName="polystudent-sg",
        GroupDescription="Security group allows SSH, HTTP, HTTPS, MSSQL, PostgreSQL, MySQL, RDP, OSSEC, ElasticSearch, DNS...",
        VpcId=Ref(VPC),
        SecurityGroupIngress=[
            # SSH
            ec2.SecurityGroupRule(IpProtocol="tcp", FromPort=22, ToPort=22, CidrIp="0.0.0.0/0"),

            # HTTP
            ec2.SecurityGroupRule(IpProtocol="tcp", FromPort=80, ToPort=80, CidrIp="0.0.0.0/0"),

            # HTTPS
            ec2.SecurityGroupRule(IpProtocol="tcp", FromPort=443, ToPort=443, CidrIp="0.0.0.0/0"),

            # DNS TCP
            ec2.SecurityGroupRule(IpProtocol="tcp", FromPort=53, ToPort=53, CidrIp="0.0.0.0/0"),

            # DNS UDP
            ec2.SecurityGroupRule(IpProtocol="udp", FromPort=53, ToPort=53, CidrIp="0.0.0.0/0"),

            # MSSQL
            ec2.SecurityGroupRule(IpProtocol="tcp", FromPort=1433, ToPort=1433, CidrIp="0.0.0.0/0"),

            # PostgreSQL
            ec2.SecurityGroupRule(IpProtocol="tcp", FromPort=5432, ToPort=5432, CidrIp="0.0.0.0/0"),

            # MySQL
            ec2.SecurityGroupRule(IpProtocol="tcp", FromPort=3306, ToPort=3306, CidrIp="0.0.0.0/0"),

            # RDP
            ec2.SecurityGroupRule(IpProtocol="tcp", FromPort=3389, ToPort=3389, CidrIp="0.0.0.0/0"),

            # OSSEC (Agent)
            ec2.SecurityGroupRule(IpProtocol="udp", FromPort=1514, ToPort=1514, CidrIp="0.0.0.0/0"),

            # ElasticSearch REST API
            ec2.SecurityGroupRule(IpProtocol="tcp", FromPort=9200, ToPort=9200, CidrIp="0.0.0.0/0"),

            # Elasticsearch cluster transport
            ec2.SecurityGroupRule(IpProtocol="tcp", FromPort=9300, ToPort=9300, CidrIp="0.0.0.0/0"),
        ],
    )
)

# OUTPUTS
t.add_output(Output(
    "VPC",
    Value=Ref(VPC),
    Description="A reference to the created VPC"
))
t.add_output(Output(
    "PublicSubnets",
    Description="A list of the public subnets",
    Value=Join(",", [Ref(PublicSubnet1), Ref(PublicSubnet2)])
))
t.add_output(Output(
    "PrivateSubnets",
    Description="A list of the private subnets",
    Value=Join(",", [Ref(PrivateSubnet1), Ref(PrivateSubnet2)])
))
t.add_output(Output(
    "PublicSubnet1",
    Description="A reference to the public subnet in Availability Zone 1",
    Value=Ref(PublicSubnet1)
))
t.add_output(Output(
    "PublicSubnet2",
    Description="A reference to the public subnet in Availability Zone 2",
    Value=Ref(PublicSubnet2)
))
t.add_output(Output(
    "PrivateSubnet1",
    Description="A reference to the private subnet in Availability Zone 1",
    Value=Ref(PrivateSubnet1)
))
t.add_output(Output(
    "PrivateSubnet2",
    Description="A reference to the private subnet in Availability Zone 2",
    Value=Ref(PrivateSubnet2)
))

# WRITE TEMPLATE
with open("tp4_vpc.yaml", "w") as f:
    f.write(t.to_yaml())

print("Generated tp4_vpc.yaml")

