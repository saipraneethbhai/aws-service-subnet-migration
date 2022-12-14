import boto3,re,requests,os

AWS_access_key = os.getenv('aws_access_key')
AWS_secrete_access_key = os.getenv('aws_secrete_access_key')

region = "ap-south-1"
service_name = "elbv2"
stage = "prod"

# boto client config
session = boto3.Session(aws_access_key_id=AWS_access_key,aws_secret_access_key=AWS_secrete_access_key)
elb = session.client(service_name,region_name=region)

def getELBConfig():
    lst_of_elb = elb.describe_load_balancers()['LoadBalancers']
    n = len(lst_of_elb)
    DNS_lst = []
    elb_names = []
    for i in range(n):
        name = lst_of_elb[i]['LoadBalancerName']
        scheme = lst_of_elb[i]['Scheme']
        check = re.search(".*{}.*".format(stage),name)
        if check and scheme=="internet-facing":
            DNS = lst_of_elb[i]['DNSName']
            DNS_lst.append(DNS)
            elb_names.append(name)
    return elb_names,DNS_lst

def getTGConfig():
    lst_of_tg = elb.describe_target_groups()['TargetGroups']
    n = len(lst_of_tg)
    health_check_paths = []
    tg_names = []
    for i in range(n):
        tg_name = lst_of_tg[i]['TargetGroupName']
        check = re.search(".*{}.*".format(stage),tg_name)
        if check:
            path = lst_of_tg[i]['HealthCheckPath']
            health_check_paths.append(path)
            tg_names.append(tg_name)
    return tg_names,health_check_paths

elb_names,DNS_lst = getELBConfig()
tg_names,health_check_paths = getTGConfig()

n = len(elb_names)
Dict = {}
for i in range(n):
    service = elb_names[i][13:-4]
    m = len(tg_names)
    for j in range(m):
        check = re.search(".*{}.*".format(service),tg_names[j])
        if check:
            Dict[elb_names[i]] = {"health_check_path":health_check_paths[j]}

if stage=="prod":
    path = elb.describe_target_groups(Names=["appsforbharat-web-prod-tg"])['TargetGroups'][0]['HealthCheckPath']
    Dict["appsforbhararat-domain-prod-alb"] = {'health_check_path':path}

num = 0
for i in range(n):
    name = elb_names[i]
    path = Dict[name]["health_check_path"]
    print("DNS={}, path={}".format(DNS_lst[i],path))
    response = requests.get("http://"+DNS_lst[i]+path)
    code = response.status_code
    if code != 200:
        print("ALB-name   =  "+name)
        print("StatusCode  =  "+str(code))
        print("path  =  "+path)
        print("===================================")
    else:    
        num += 1
    if num == n:
        print("All services are healthy")
          
