import boto3,os,re
from datetime import datetime

class operation:
    def __init__(self):
        self.AWS_access_key = os.getenv('aws_access_key')
        self.AWS_secrete_access_key = os.getenv('aws_secrete_access_key')
        self.session = 
boto3.Session(aws_access_key_id=self.AWS_access_key,aws_secret_access_key=self.AWS_secrete_access_key)
    
    def get_vpc_id_with_env(self,ec2_client,env):
        vpcs = ec2_client.describe_vpcs()['Vpcs']
        vpc_id = ''
        for vpc in vpcs:
            vpc_tags = vpc['Tags']
            vpc_name = ''
            for tag in vpc_tags:
                if tag['Key'] == 'Name':
                    vpc_name = tag['Value']
            if re.search('.*{}.*'.format(env),vpc_name):
                      vpc_id = vpc['VpcId']
                      return vpc_id
        return vpc_id
            
    def get_all_arn_of_elb(self,elbV2_client,vpcId):
        lst_of_elb_in_vpc = []
        elbs = elbV2_client.describe_load_balancers()
        elbs_config = elbs['LoadBalancers']
        for elb_config in elbs_config:
            vpc_id = elb_config['VpcId']
            load_balancer_arn = elb_config['LoadBalancerArn']
            sg = elb_config['SecurityGroups']
            subnets = []
            for elb_az_config in elb_config['AvailabilityZones']:
                subnets.append(elb_az_config['SubnetId'])
            config = {}
            if vpc_id == vpcId:
                config['vpc_id'] = vpc_id
                config['arn'] = load_balancer_arn
                config['security_group'] = sg
                config['subnets'] = subnets
                lst_of_elb_in_vpc.append(config)
        return lst_of_elb_in_vpc
    
    def create_snapshot_of_rds_instance(self,rds_client,db_identifier):
        snap_identifier = db_identifier + "-" + 
str(datetime.now())[:19].replace(":","-").replace(" ","-")
        response = 
rds_client.create_db_snapshot(DBSnapshotIdentifier=snap_identifier,DBInstanceIdentifier=db_identifier)
        status_code = int(response['ResponseMetadata']['HTTPStatusCode'])
        if status_code == 200:
            return True
        return False
    
    def is_rds_instance_available(self,rds_client,db_identifier):
        try:
            status = 
rds_client.describe_db_instances(DBInstanceIdentifier=db_identifier)['DBInstances'][0]['DBInstanceStatus']
        except:
            return False
        if status == "available":
            return True
        return False
    
    def reboot_with_failover_rds_instance(self,rds_client,db_identifier):
        try:
            response = 
rds_client.reboot_db_instance(DBInstanceIdentifier=db_identifier,ForceFailover=True)
        except:
            return False
        status_code = int(response['ResponseMetadata']['HTTPStatusCode'])
        if status_code == 200:
            return True
        return False
    
    def get_all_subnets_in_vpc(self,vpc_client,vpc_id):
        subnets = vpc_client.describe_subnets(Filters=[{"Name": "vpc-id",
                                                        "Values": 
[vpc_id]}])['Subnets']

        subnets = [subnet['SubnetId'] for subnet in subnets]
        return subnets
    
    def get_ecs_service_in_vpc(self,vpc_client,ecs_client,vpcID):
        clusters = ecs_client.list_clusters(maxResults=100)['clusterArns']
        services_info_lst = []
        for cluster in clusters:
            clusterName = cluster.split('/')[-1]
            lst_services = 
ecs_client.list_services(cluster=clusterName,maxResults=100)['serviceArns']
            for service in lst_services:
                service_json = ecs_client.describe_services( 
cluster=clusterName,services=[service],)
                service_subnets = 
service_json["services"][0]["deployments"][0]["networkConfiguration"]["awsvpcConfiguration"]["subnets"]
                security_group = 
service_json["services"][0]["deployments"][0]["networkConfiguration"]["awsvpcConfiguration"]['securityGroups']
                service_name = service_json["services"][0]["serviceName"]
                launch_type = service_json["services"][0]["launchType"]
                subnets = 
self.get_all_subnets_in_vpc(vpc_client=vpc_client,vpc_id=vpcID)
                check = True
                service_info = {}
                for subnet in service_subnets:
                    if subnet not in subnets:
                        check = False
                        break
                    else:
                        check = True
                        break
                if check==True:
                    service_info['cluster_name'] = clusterName
                    service_info['name'] = service_name
                    service_info['subnets'] = service_subnets
                    service_info['sg'] = security_group
                    service_info['launch_type'] = launch_type
                    services_info_lst.append(service_info)
        return services_info_lst
    
    def get_redis_instances_in_vpc(self,elasticache_client,vpc_id):
        clusters = 
elasticache_client.describe_cache_clusters()["CacheClusters"]
        redis_instance_lst = []
        i=0
        for cluster in clusters:
            clusterName = cluster["CacheClusterId"]
            try:
                security_group = 
cluster['SecurityGroups'][0]['SecurityGroupId']
            except:
                security_group = []
            zone = cluster["PreferredAvailabilityZone"]
            subnetGrpName = cluster["CacheSubnetGroupName"]
            subnetGrp = 
elasticache_client.describe_cache_subnet_groups(CacheSubnetGroupName=subnetGrpName)["CacheSubnetGroups"][0]
            vpc = subnetGrp["VpcId"]
            redis_config = {}
            subnet = []
            if vpc == vpc_id:
                for subnetJson in subnetGrp["Subnets"]:
                    if subnetJson['SubnetAvailabilityZone']['Name'] == 
zone:
                        subnet.append(subnetJson["SubnetIdentifier"])
                redis_config['cluster_name'] = clusterName
                redis_config['sg'] = security_group
                redis_config['subnets'] = subnet
                redis_instance_lst.append(redis_config)
            i += 1
        return redis_instance_lst
    
    def is_vpcid_exist(self,ec2_resource,vpc_id):
        vpc_exists = False
        try:
            vpcs = list(ec2_resource.vpcs.filter(Filters=[]))
        except:
            print("Something went wrong while listing vpcs")
        for vpc in vpcs:
            if vpc.id == vpc_id:
                vpc_exists = True
        return vpc_exists
    def get_ec2_instances_in_vpc(self,vpc_client,vpc_id):
        num = 1
        reservations = vpc_client.describe_instances(Filters=[{"Name": 
"vpc-id",
                                                            "Values": 
[vpc_id]}])['Reservations']
        # Get a list of ec2s
        ec2_instances_lst = []
        ec2s_id = [ec2['InstanceId'] for reservation in reservations for 
ec2 in reservation['Instances'] if ec2['State']['Name'] == 'running']
        instanceType = []
        subnetLst = []
        securityGrpLst = []
        for reservation in reservations:
            for ec2 in reservation['Instances']:
                if ec2['State']['Name'] == 'running':
                    
securityGrpLst.append(ec2['SecurityGroups'][0]['GroupName'])
                    instanceType.append(ec2['InstanceType'])
                    subnetLst.append(ec2['SubnetId'])
        for ec2_id in ec2s_id:
            ec2_config = {}
            ec2_config['id'] = ec2_id
            ec2_config['type'] = instanceType[num-1]
            ec2_config['subnet'] = subnetLst[num-1]
            ec2_config['sg'] = securityGrpLst[num-1]
            num += 1
            ec2_instances_lst.append(ec2_config)
        return ec2_instances_lst
    
    def get_lambda_in_vpc(self,lambda_client,vpc_id):
        lmbds = lambda_client.list_functions()['Functions']
        lambdas_list = [lmbd['FunctionName'] for lmbd in lmbds
                        if 'VpcConfig' in lmbd and 
lmbd['VpcConfig']['VpcId'] == vpc_id]
        return lambdas_list
    
    def get_rds_instances_in_vpc(self,rds_client,vpc_id):
        rdss = rds_client.describe_db_instances()['DBInstances']
        rdsss_list = [rds['DBInstanceIdentifier'] for rds in rdss if 
rds['DBSubnetGroup']['VpcId'] == vpc_id]
        rdss_subnets=[]
        subnet_grp = []
        sg = []
        zones = []
        rds_instance_lst = []
        for i in range(len(rdss)):
            rdm = rdss[i]
            instZone = rdm['AvailabilityZone']
            security_grp = 
rdm['VpcSecurityGroups'][0]['VpcSecurityGroupId']
            lstSubnets=rdm['DBSubnetGroup']['Subnets']
            subnetGrp = rdm['DBSubnetGroup']['DBSubnetGroupName']
            tmp = []
            zone = []
            if rdm['DBSubnetGroup']['VpcId'] == vpc_id:
                for subnet in lstSubnets:
                    if subnet['SubnetAvailabilityZone']['Name']==instZone:
                        tmp.append(subnet["SubnetIdentifier"])
                        
zone.append(subnet['SubnetAvailabilityZone']['Name'])
                sg.append(security_grp)
                subnet_grp.append(subnetGrp)
                rdss_subnets.append(tmp)
                zones.append(zone)
        num = 1
        for rds in rdsss_list:
            rds_config = {}
            rds_config['id'] = rds
            rds_config['subnet_grp'] = subnet_grp[num-1]
            rds_config['subnets'] = rdss_subnets[num-1]
            rds_config['sg'] = sg[num-1]
            rds_instance_lst.append(rds_config)
            num+=1
        return rds_instance_lst
    
    def get_elbV2_in_vpc(self,elbV2_client,vpc_id):
        num=1
        elb_lst = []
        elbs = elbV2_client.describe_load_balancers()['LoadBalancers']
        elbs_list = [elb['LoadBalancerName'] for elb in elbs if 
elb['VpcId'] == vpc_id]
        elbs_scheme = [elb['Scheme'] for elb in elbs if elb['VpcId'] == 
vpc_id]
        elbs_subnet = []
        elbs_sg = []
        for elb in elbs:
            if elb['VpcId'] == vpc_id:
                tmp = []
                for subnet in elb['AvailabilityZones']:
                    tmp.append(subnet['SubnetId'])
                elbs_sg.append(elb['SecurityGroups'][0])
                elbs_subnet.append(tmp)
        for elb in elbs_list:
            elb_config = {}
            elb_config['name'] = elb
            elb_config['subnet'] = elbs_subnet[num-1]
            elb_config['sg'] = elbs_sg[num-1]
            elb_config['scheme'] = elbs_scheme[num-1]
            num+=1
            elb_lst.append(elb_config)
        return elb_lst
    
    def get_nat_in_vpc(self,vpc_client,vpc_id):
        nats = vpc_client.describe_nat_gateways(Filters=[{"Name": 
"vpc-id",
                                                        "Values": 
[vpc_id]}])['NatGateways']

        nat_lst = 
[{'id':nat['NatGatewayId'],'subnet':nat['SubnetId'],'connectivity':nat['ConnectivityType']} 
for nat in nats]
        return nat_lst
    
    def get_enis_in_vpc(self,vpc_client,vpc_id):
        enis = vpc_client.describe_network_interfaces(Filters=[{"Name": 
"vpc-id", "Values": [vpc_id]}])['NetworkInterfaces']
        enis = [{'id':eni['NetworkInterfaceId'],'subnet':eni['SubnetId']} 
for eni in enis]
        return enis
    
    def get_igws_in_vpc(self,vpc_client,vpc_id):
        num=1
        # Get list of dicts
        igws = vpc_client.describe_internet_gateways(
            Filters=[{"Name": "attachment.vpc-id",
                    "Values": [vpc_id]}])['InternetGateways']
        igws = [igw['InternetGatewayId'] for igw in igws]
        return igws
    
    def get_acls_in_vpc(self,vpc_client,vpc_id):
        acls = vpc_client.describe_network_acls(Filters=[{"Name": 
"vpc-id",
                                                          "Values": 
[vpc_id]}])['NetworkAcls']
        acls_lst = []
        for acl in acls:
            id = acl['NetworkAclId']
            subnets = []
            for subnet in acl['Associations']:
                subnets.append(subnet['SubnetId'])
            acls_lst.append({'id':id,'subnet':subnets})
        return acls_lst
    
    def get_ecs_tasks_in_vpc(self,ecs_client,vpc_client,vpc_id):
        num=1
        tasks_lst = []
        clusters = ecs_client.list_clusters()['clusterArns']
        for cluster in clusters:
            clusterName = cluster.split('/')[-1]
            lst_tasks = ecs_client.list_tasks(cluster=clusterName)
            for tsk in lst_tasks["taskArns"]:
                infoTask = 
ecs_client.describe_tasks(cluster=clusterName,tasks=[tsk])
                subnetID = 
infoTask['tasks'][0]['attachments'][0]['details'][0]['value']
                service1 = infoTask['tasks'][0]['group']
                subnets = 
self.get_all_subnets_in_vpc(vpc_client=vpc_client,vpc_id=vpc_id)
                if subnetID in subnets:
                    
tasks_lst.append({'id':tsk.split("/")[-1],'service':service1,'subnet':subnetID})
                    num+=1
        return tasks_lst
    
    def 
get_all_resources_in_vpc(self,vpc_client,ecs_client,elbV2_client,elasticache_client,rds_client,vpc_id):
        vpc = vpc_id
        print("VPC-ID is",vpc)
        redis = self.get_redis_instances_in_vpc(elasticache_client,vpc_id)
        print("--------------------------------------------------------")
        print("REDIS CLUSTERS IN VPC",vpc)
        for i in range(len(redis)):
            print("{})name={}, subnet={}, 
security_group={}".format(i+1,redis[i]['cluster_name'],redis[i]['subnets'],redis[i]['sg']))
        print("--------------------------------------------------------")
        rds = self.get_rds_instances_in_vpc(rds_client,vpc_id)
        print("RDS INSTANCES IN VPC",vpc)
        for i in range(len(rds)):
            print("{})id={}, subnet_grp={}, subnets={}, 
security_grp={}".format(i+1,rds[i]['id'],rds[i]['subnet_grp'],rds[i]['subnets'],rds[i]['sg']))
        print("--------------------------------------------------------")
        ec2 = self.get_ec2_instances_in_vpc(vpc_client,vpc_id)
        print("EC2 INSTANCES IN VPC",vpc)
        for i in range(len(ec2)):
            print("{})id={}, type={}, subnet={}, 
security_group={}".format(i+1,ec2[i]['id'],ec2[i]['type'],ec2[i]['subnet'],ec2[i]['sg']))
        print("--------------------------------------------------------")
        ecs = self.get_ecs_service_in_vpc(vpc_client,ecs_client,vpc_id)
        print("ECS SERVICES IN VPC",vpc)
        for i in range(len(ecs)):
            print("{})name={}, launch_type={}, subnets={}, 
security_group={}".format(i+1,ecs[i]['name'],ecs[i]['launch_type'],ecs[i]['subnets'],ecs[i]['sg']))
        print("--------------------------------------------------------")
        elbv2 = self.get_elbV2_in_vpc(elbV2_client,vpc_id)
        print("ELB IN VPC",vpc)
        for i in range(len(elbv2)):
            print("{})name={}, scheme={}, subnet={}, 
security_grp={}".format(i+1,elbv2[i]['name'],elbv2[i]['scheme'],elbv2[i]['subnet'],elbv2[i]['sg']))
        print("--------------------------------------------------------")
        
