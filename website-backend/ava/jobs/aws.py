
import boto3

REGIONS = ['us-east-1', 'us-west-1', 'us-west-2']

def state_to_string(instance):
    state = instance.get('State')
    if state:
        code = state.get('Code', 0)
        name = state.get('Name', 'error')
        return '(%d) %s' % (code, name)
    return 'ERROR'

def instance_id_from_private_ip(private_ip):

    for region in REGIONS:

        try:
            ec2 = boto3.client('ec2', region_name=region)

            response = ec2.describe_instances(Filters=[
                {
                    'Name': 'private-ip-address',
                    'Values': [private_ip,]
                },
            ])
            for reservation in response.get('Reservations', []):
                for instance in reservation.get('Instances', []):
                    instance_id = instance.get('InstanceId')
                    state = instance.get('State').get('Name')
                    return (instance_id, region, state)
                
        except Exception as e:
            print('AWS Error: ' + e.message)

    return (None, None, 'none')

def instance_state(instance_id, region):

    try:
        ec2 = boto3.client('ec2', region_name=region)
        response = ec2.describe_instances(Filters=[
            {
                'Name': 'instance-id',
                'Values': [instance_id,]
            },
        ])
        for reservation in response.get('Reservations', []):
            for instance in reservation.get('Instances', []):
                if instance_id == instance.get('InstanceId'):
                    return instance.get('State').get('Name')
                
    except Exception as e:
        print('AWS Error: ' + e.message)

    return None

def start_instance(instance_id, region):
    ec2 = boto3.client('ec2', region_name=region)
    response = ec2.start_instances(
        InstanceIds=[instance_id],
        DryRun=False
    )
    for instance in response.get('StartingInstances', []):
        if instance_id == instance.get('InstanceId'):
            # Return new state of the instance
            return instance.get('CurrentState').get('Name')

def stop_instance(instance_id, region):
    ec2 = boto3.client('ec2', region_name=region)
    response = ec2.stop_instances(
        InstanceIds=[instance_id],
        Hibernate=False,
        DryRun=False,
        Force=False
    )
    for instance in response.get('StoppingInstances', []):
        if instance_id == instance.get('InstanceId'):
            # Return new state of the instance
            return instance.get('CurrentState').get('Name')
                
