import boto3,os

AWS_access_key = os.getenv('aws_access_key')
AWS_secrete_access_key = os.getenv('aws_secrete_access_key')

region = "ap-south-1"
service_name = "ec2"

# boto client config
session = boto3.Session(aws_access_key_id=AWS_access_key,aws_secret_access_key=AWS_secrete_access_key)
ec2 = session.client(service_name,region_name=region)
sgs = ec2.describe_security_groups(Filters=[{
        'Name':'vpc-id',
        'Values':['vpc-07fd58568009ddcc4']
    }])['SecurityGroups']
num = 1
atleast_one_exist = False
for sg in sgs:
    sg_ID = sg["GroupId"]
    sg_Name = sg["GroupName"]
    NI = ec2.describe_network_interfaces(Filters=[{
        'Name':'group-id',
        'Values':[sg_ID]
    }])
    if len(NI['NetworkInterfaces']) == 0:
        atleast_one_exist = True
        print("=====================================")
        print("{}) {}, {}".format(num,sg_Name,sg_ID))
        num += 1
if atleast_one_exist==False:
    print("All security groups are associated with services")
else:
    print("Above security groups are not associated with any network interface")

