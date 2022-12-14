from operations import operation
import time,threading

class update_services(operation):
    def __init__(self,vpc_id,region):
        super().__init__()
        self.vpc_id = vpc_id
        self.region = region
        self.ec2_client = self.session.client('ec2',region_name=self.region)
        self.ec2_resource = self.session.resource('ec2', region_name=self.region)
        self.elbV2_client = self.session.client('elbv2',region_name=self.region)
        self.lambda_client = self.session.client('lambda', region_name=self.region)
        self.ecs_client = self.session.client('ecs',region_name=self.region)
        self.elb_client = self.session.client('elb', region_name=self.region)
        self.eks_client = self.session.client('eks', region_name=self.region)
        self.asg_client = self.session.client('autoscaling', region_name=self.region)
        self.rds_client = self.session.client('rds', region_name=self.region)
        self.elasticache_client = self.session.client('elasticache', region_name=self.region)
        
    def update_all_elb_subnets(self,subnets_lst):
        elbs_config = operation.get_all_arn_of_elb(elb_client=self.elbV2_client,vpcId=self.vpc_id)
        for elb_config in elbs_config:
            if elb_config['subnets'] != subnets_lst:
                alb_arn = elb_config['arn']
                res = self.elbV2_client.set_subnets(LoadBalancerArn=alb_arn,Subnets=subnets_lst)
                print(alb_arn," subnets are updated to",subnets_lst)
    def update_all_elb_security_groups(self,security_group_lst):
        elbs_config = operation.get_all_arn_of_elb(elb_client=self.elbV2_client,vpcId=self.vpc_id)
        for elb_config in elbs_config:
            if elb_config['security_group'] != security_group_lst:
                alb_arn = elb_config['arn']
                res = self.elbV2_client.set_subnets(LoadBalancerArn=alb_arn,Subnets=security_group_lst)
                print(alb_arn," security groups are updated to",security_group_lst)
    def update_rds_instance(self,db_identifier,multi_az=True,public_access=False):
        try:
            response =self.rds_client.modify_db_instance(DBInstanceIdentifier=db_identifier,MultiAZ=multi_az,PubliclyAccessible=public_access,ApplyImmediately=True)
        except:
            print("Unable to update db instance {}".format(db_identifier))
            return False
        status_code = int(response['ResponseMetadata']['HTTPStatusCode'])
        if status_code == 200:
            return True
        print("Unable to update db instance {}".format(db_identifier))
        return False
    #This below function is used to change subnet. Like If A-RDS is in ap-south-1a if we want to migrate to ap-south-1b or ap-south-1c we can use this function.
    def change_rds_instance_az(self,db_identifier):
        done = operation.create_snapshot(db_identifier) #creating a snapshot of a db instance for rollback
        created = False
        if done:
            created = True
            print("Creating "+db_identifier+" snapshot")
        else:
            print("Unable to create snashot for "+db_identifier)
        time.sleep(60)
        while(True):
            if operation.is_available(db_identifier):
                break
            time.sleep(2)
        if created:
            print(db_identifier+" snapshot is created")
        modified = False
        done = operation.modify(db_identifier,multi_az=True)
        if done:
            modified = True
            print(db_identifier+" is modifying...")
        else:
            print("Unable to modify "+db_identifier)
        time.sleep(60)
        while(True):
            if operation.is_available(db_identifier):
                break
            time.sleep(2)
        if modified:
            print(db_identifier+" Mulit_AZ is turned on")
        rebooted = False
        time.sleep(10)
        done = operation.reboot_with_failover(db_identifier)
        if done:
            rebooted = True
            print(db_identifier+" is rebooting with failover...")
        else:
            print("Unable to reboot "+db_identifier)
        time.sleep(60)
        while(True):
            if operation.is_available(db_identifier):
                break
            time.sleep(2)
        if rebooted:
            print(db_identifier+" is rebooted")
        time.sleep(10)
        modified = False
        done = operation.modify(db_identifier,multi_az=False)
        if done:
            modified = True
            print(db_identifier+" is modifying...")
        else:
            print("Unable to modify "+db_identifier)
        time.sleep(60)
        while(True):
            if operation.is_available(db_identifier):
                break
            time.sleep(2)
        if modified:
            print(db_identifier+" Mulit_AZ is turned off")
            
    def change_rds_instances_az(self,lst_db_identifier):
        threads = []
        for db_identifier in lst_db_identifier:
            threads.append(threading.Thread(target=self.change_rds_instance_az,args=(db_identifier,)))
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
    
    def change_ecs_service_subnets_sg(self,cluster_name,service_name,subnets,security_groups,public_ip="ENABLED"):
        network_config = {
			'awsvpcConfiguration': 
					{
	            		'subnets': subnets,
						'securityGroups': security_groups,
	            		'assignPublicIp': public_ip
	        		}
			 }
        response = self.ecs_client.update_service(cluster=cluster_name,service=service_name,networkConfiguration=network_config)
        print("{} service subnet={} and security_group={}".format(service_name,subnets,security_groups))
    
    def change_all_ecs_service_subnets_sg_in_vpc(self,subnets,security_groups):
        ecs_services = operation.get_ecs_service_in_vpc(self,vpc_client=self.ec2_client,ecs_client=self.ecs_client,vpcID=self.vpc_id)
        for ecs_service in ecs_services:
            cluster_name = ecs_service['cluster_name']
            service_name = ecs_service['name']
            self.change_ecs_service_subnets_sg(cluster_name=cluster_name,service_name=service_name,subnets=subnets,security_groups=security_groups)

vpc_id = "VPC ID"
region = "ap-south-1"
us = update_services(vpc_id,region)
ecs = us.ecs_client
vpc = us.ec2_client
rds = us.rds_client
redis = us.elasticache_client
elb = us.elbV2_client
us.get_all_resources_in_vpc(vpc_client=vpc,ecs_client=ecs,elbV2_client=elb,elasticache_client=redis,rds_client=rds,vpc_id=us.vpc_id)


