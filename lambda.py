import json
import boto3
import os
from datetime import datetime
from decimal import Decimal
from botocore.exceptions import ClientError

# Initialize AWS Batch, ECS, and DynamoDB clients
batch_client = boto3.client('batch')
ecs_client = boto3.client('ecs')
dynamodb = boto3.resource('dynamodb')

# DynamoDB Table Name from environment variable
table_name = os.getenv('DYNAMODB_TABLE_NAME')
table = dynamodb.Table(table_name)

# Custom JSON encoder to handle datetime objects and Decimal types
class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)

# Function to extract containerInstanceArn from various event structures
def extract_container_instance_arn(event):
    try:
        if 'containerInstanceArn' in event['detail']:
            return event['detail']['containerInstanceArn']
        elif ('ecsProperties' in event['detail'] and 
              'taskProperties' in event['detail']['ecsProperties'] and
              len(event['detail']['ecsProperties']['taskProperties']) > 0 and
              'containerInstanceArn' in event['detail']['ecsProperties']['taskProperties'][0]):
            return event['detail']['ecsProperties']['taskProperties'][0]['containerInstanceArn']
        elif 'container' in event['detail'] and 'containerInstanceArn' in event['detail']['container']:
            return event['detail']['container']['containerInstanceArn']
        else:
            return 'unknown'
    except (IndexError, KeyError):
        return 'unknown'

def get_ecs_cluster_arn(compute_env_name):
    try:
        response = batch_client.describe_compute_environments(
            computeEnvironments=[compute_env_name]
        )
        return response['computeEnvironments'][0].get('ecsClusterArn', 'unknown')
    except (ClientError, IndexError, KeyError):
        return 'unknown'

# Helper function to fetch EC2 instance ID
def get_ec2_instance_id(cluster_arn, container_instance_arn):
    try:
        container_instance_details = ecs_client.describe_container_instances(
            cluster=cluster_arn,
            containerInstances=[container_instance_arn]
        )
        return container_instance_details['containerInstances'][0].get('ec2InstanceId', 'unknown')
    except (ClientError, IndexError, KeyError):
        return 'unknown'

def get_instance_type_from_ec2(instance_id):
    try:
        ec2_client = boto3.client('ec2', region_name='us-west-2')
        response = ec2_client.describe_instances(InstanceIds=[instance_id])
        if response['Reservations']:
            return response['Reservations'][0]['Instances'][0]['InstanceType']
        else:
            return 'unknown'
    except (ClientError, IndexError, KeyError):
        return 'unknown'

# Update function for DynamoDB with PreviousInstanceIDs handling
def update_dynamodb(job_id, job_queue_name, status, instance_id, instance_type=None, 
                    interruption_time=None, run_duration_seconds=0, total_time_saved=0, 
                    attempts=0, start_time=None, previous_instance_ids=None, instance_map=None):
    # Merge instance_map with the new instance_id and instance_type
    if instance_map is None:
        instance_map = {}
    if instance_id != 'unknown' and instance_type:
        instance_map[instance_id] = instance_type  # Append new instance ID and type
    
    item = {
        'JobID': job_id,
        'JobQueue': job_queue_name,
        'Status': status,
        'InstanceID': instance_id,
        'Attempts': attempts,
        'RunDurationSeconds': run_duration_seconds,
        'TotalTimeSaved': total_time_saved,
        'InstanceMap': instance_map
    }
    if interruption_time:
        item['InterruptionTime'] = interruption_time
    if start_time:
        item['StartTime'] = start_time
    if previous_instance_ids:
        item['PreviousInstanceIDs'] = previous_instance_ids

    try:
        response = table.put_item(Item=item)
        print(f"Successfully updated DynamoDB for JobID {job_id}. Response: {response}")
    except ClientError as e:
        print(f"Error updating DynamoDB for JobID {job_id}: {e}")

# Lambda handler function
def lambda_handler(event, context):
    print("Received Event:", json.dumps(event, indent=4, cls=CustomJSONEncoder))

    # Extract job details
    job_id = event.get('detail', {}).get('jobId', 'unknown')
    job_queue_arn = event.get('detail', {}).get('jobQueue', 'unknown')
    status = event.get('detail', {}).get('status', 'unknown')
    container_instance_arn = extract_container_instance_arn(event)
    compute_env_name = os.getenv('COMPUTE_ENV_NAME')
    job_queue_name = job_queue_arn.split('/')[-1] if job_queue_arn != 'unknown' else 'unknown'
    cluster_arn = get_ecs_cluster_arn(compute_env_name)
    
    response = table.get_item(Key={'JobID': job_id})
    item = response.get('Item', {})
    
    # Initialize fields
    attempts = item.get('Attempts', 0)
    run_duration_seconds = item.get('RunDurationSeconds', 0)
    total_time_saved = item.get('TotalTimeSaved', []) or []
    start_time = item.get('StartTime')
    instance_id = item.get('InstanceID', 'unknown')
    instance_map = item.get('InstanceMap', {})
    previous_instance_ids = item.get('PreviousInstanceIDs', []) or []
    interruption_time = None
    current_time = datetime.utcnow()
    
    # Logic for job status
    if status == "RUNNING":
        if start_time is None:  # This is either the first start or a retry after interruption
            start_time = current_time.isoformat()
        if container_instance_arn and container_instance_arn != 'unknown':
            new_instance_id = get_ec2_instance_id(cluster_arn, container_instance_arn)
            if new_instance_id != 'unknown' and new_instance_id != instance_id:
                if instance_id != 'unknown':
                    previous_instance_ids.append(instance_id)
                instance_id = new_instance_id
                
                # Fetch instance type
                instance_type = get_instance_type_from_ec2(instance_id)
                instance_map[instance_id] = instance_type
                update_dynamodb(
                    job_id=job_id,
                    job_queue_name=job_queue_name,
                    status=status,
                    instance_id=instance_id,
                    instance_type=instance_type, 
                    interruption_time=interruption_time,
                    run_duration_seconds=Decimal(run_duration_seconds),
                    total_time_saved=total_time_saved,
                    attempts=attempts,
                    start_time=start_time,
                    previous_instance_ids=previous_instance_ids
                )
    elif status == "RUNNABLE" and start_time:  # Job is interrupted, switch to RUNNABLE
        # Increment attempts as the job is interrupted and may retry
        attempts += 1
        last_run_duration = int((current_time - datetime.fromisoformat(start_time)).total_seconds())
        run_duration_seconds += last_run_duration
        total_time_saved.append(last_run_duration)  # Record time spent on this attempt
        interruption_time = current_time.isoformat()
        start_time = None  # Reset start_time to mark interruption

    elif status in ["SUCCEEDED", "FAILED"] and start_time:  # Job is complete
        last_run_duration = int((current_time - datetime.fromisoformat(start_time)).total_seconds())
        run_duration_seconds += last_run_duration
        start_time = None

    # Update DynamoDB
    update_dynamodb(
        job_id=job_id,
        job_queue_name=job_queue_name,
        status=status,
        instance_id=instance_id,
        instance_type=instance_map.get(instance_id),
        interruption_time=interruption_time,
        run_duration_seconds=Decimal(run_duration_seconds),
        total_time_saved=total_time_saved,
        attempts=attempts,
        start_time=start_time,
        previous_instance_ids=previous_instance_ids,
        instance_map=instance_map
    )

    # Return success response
    return {
        'statusCode': 200,
        'body': json.dumps({
            'JobID': job_id,
            'JobQueue': job_queue_name,
            'Status': status,
            'InstanceID': instance_id,
            'Attempts': attempts,
            'RunDurationSeconds': run_duration_seconds,
            'TotalTimeSaved': total_time_saved,
            'InterruptionTime': interruption_time,
            'StartTime': start_time,
            'PreviousInstanceIDs': previous_instance_ids if attempts > 1 else None,
            'InstanceMap': instance_map
        }, cls=CustomJSONEncoder)
    }