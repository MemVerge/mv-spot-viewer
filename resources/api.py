from flask import Flask, jsonify
import boto3
import json
import logging
from decimal import Decimal
import pandas as pd
from flask import send_from_directory

app = Flask(__name__)

# Boto3 Clients
dynamodb = boto3.resource('dynamodb', region_name='us-west-2')
table = dynamodb.Table("jobTracker-${UniquePrefix}")

# Logger
logging.basicConfig(level=logging.INFO)


def fetch_dynamodb_data():
    """Fetch all job data from DynamoDB."""
    return table.scan()["Items"]


def get_pricing(instance_type, region, price_type="OnDemand"):
    """Fetch pricing information for On-Demand or Spot pricing."""
    region_mapping = {
        "us-east-1": "US East (N. Virginia)",
        "us-east-2": "US East (Ohio)",
        "us-west-1": "US West (N. California)",
        "us-west-2": "US West (Oregon)"
    }

    if price_type == "Spot":
        ec2_client = boto3.client('ec2', region_name=region)
        try:
            response = ec2_client.describe_spot_price_history(
                InstanceTypes=[instance_type],
                ProductDescriptions=["Linux/UNIX"],
                MaxResults=1
            )
            if response.get('SpotPriceHistory'):
                return float(response['SpotPriceHistory'][0]['SpotPrice'])
            else:
                logging.warning(f"No spot price data found for instance_type: {instance_type}, region: {region}")
                return 0
        except Exception as e:
            logging.error(f"Error fetching Spot price: {e}")
            return 0
    else:  # On-Demand pricing
        pricing_client = boto3.client('pricing', region_name="us-east-1")
        try:
            response = pricing_client.get_products(
                ServiceCode="AmazonEC2",
                Filters=[
                    {"Type": "TERM_MATCH", "Field": "instanceType", "Value": instance_type},
                    {"Type": "TERM_MATCH", "Field": "location", "Value": region_mapping.get(region, "")},
                ]
            )
            if response['PriceList']:
                price_list = json.loads(response['PriceList'][0])
                price_dimensions = list(price_list['terms']['OnDemand'].values())[0]['priceDimensions']
                return float(list(price_dimensions.values())[0]['pricePerUnit']['USD'])
            else:
                logging.warning(f"No On-Demand pricing data found for instance_type: {instance_type}, region: {region}")
                return 0
        except Exception as e:
            logging.error(f"Error fetching On-Demand pricing: {e}")
            return 0
def calculate_metrics(data, region, cost_type):
    """Calculate metrics for jobs based on type (On-Demand or Spot)."""
    metrics = {
        "NumberOfJobs": len(data),
        "NumberOfRetries": 0,
        "TotalRunTime": 0,
        "JobQueueName": set(),
        "TotalOnDemandCost": 0,
        "TotalSpotCost": 0,
        "EstimatedSavings": 0,
    }
    unique_instances = {}

    # Aggregate job metrics
    for job in data:
        metrics["NumberOfRetries"] += int(job.get("Attempts", 0))
        metrics["TotalRunTime"] += int(job.get("RunDurationSeconds", 0))
        metrics["JobQueueName"].add(job.get("JobQueue", "Unknown"))

        # Process instance data
        instance_map = job["InstanceMap"] if isinstance(job["InstanceMap"], dict) else json.loads(job["InstanceMap"])
        for instance_id, instance_type in instance_map.items():
            if instance_id not in unique_instances:
                unique_instances[instance_id] = {"type": instance_type, "longest_time": 0}
            unique_instances[instance_id]["longest_time"] = max(
                unique_instances[instance_id]["longest_time"],
                int(job["RunDurationSeconds"])
            )

    # Calculate costs
    for instance_id, details in unique_instances.items():
        instance_type = details["type"]
        longest_time = details["longest_time"]
        on_demand_price = get_pricing(instance_type, region, "OnDemand")
        spot_price = get_pricing(instance_type, region, "Spot")

        metrics["TotalOnDemandCost"] += on_demand_price * (longest_time / 3600)
        metrics["TotalSpotCost"] += spot_price * (longest_time / 3600)

    # Calculate savings
    metrics["EstimatedSavings"] = metrics["TotalOnDemandCost"] - metrics["TotalSpotCost"]
    metrics["JobQueueName"] = list(metrics["JobQueueName"])  # Convert set to list for JSON serialization

    return metrics


def calculate_spot_metrics(data):
    """Calculate Spot metrics with MemVerge enhancements."""
    df = pd.DataFrame(data)
    df["RunDurationSeconds"] = df["RunDurationSeconds"].astype(int)
    df["TotalTimeSaved"] = df["TotalTimeSaved"].fillna("[]")

    # Parse TotalTimeSaved
    df["ParsedTimeSaved"] = df["TotalTimeSaved"].apply(sum_time_saved)

    # Aggregate metrics for each unique instance
    unique_instances = {}
    total_retries = 0
    job_queues = set()

    for _, row in df.iterrows():
        instance_map = json.loads(row["InstanceMap"]) if isinstance(row["InstanceMap"], str) else row["InstanceMap"]
        runtime = row["RunDurationSeconds"]
        time_saved = row["ParsedTimeSaved"]
        retries = int(row.get("Attempts", 0))
        total_retries += retries

        job_queue = row.get("JobQueue", "Unknown")
        job_queues.add(job_queue)

        for instance_id, instance_type in instance_map.items():
            if instance_id not in unique_instances:
                unique_instances[instance_id] = {"type": instance_type, "total_runtime": 0, "saved_time": 0}
            unique_instances[instance_id]["total_runtime"] += runtime
            unique_instances[instance_id]["saved_time"] += time_saved

    # Calculate costs and runtimes
    cost_without_memverge = 0
    cost_with_memverge = 0
    total_runtime_spot = 0
    total_runtime_with_memverge = 0

    for instance_id, details in unique_instances.items():
        instance_type = details["type"]
        total_runtime = details["total_runtime"]
        saved_time = details["saved_time"]

        spot_price = get_pricing(instance_type, "us-west-2", "Spot")

        # Calculate runtimes
        adjusted_runtime = max(total_runtime - saved_time, 0)
        total_runtime_spot += total_runtime
        total_runtime_with_memverge += adjusted_runtime

        # Calculate costs
        cost_without_memverge += spot_price * (total_runtime / 3600)
        cost_with_memverge += spot_price * (adjusted_runtime / 3600)

    return {
        "NumberOfJobs": len(df),
        "TotalRetries": total_retries,
        "TotalRunTimeSpot": total_runtime_spot,
        "TotalTimeWastedSpot": total_runtime_spot - total_runtime_with_memverge,
        "TotalRunTimeWithMemVergeSpot": total_runtime_with_memverge,
        "JobQueueName": list(job_queues),
        "CostWithoutMemVerge": cost_without_memverge,
        "CostWithMemVerge": cost_with_memverge,
        "SavingsWithMemVerge": cost_without_memverge - cost_with_memverge,
    }


def sum_time_saved(time_saved_list):
    """Sum time saved from TotalTimeSaved column."""
    try:
        # If it's a string, try to parse it as JSON
        if isinstance(time_saved_list, str):
            parsed_list = json.loads(time_saved_list)
            if isinstance(parsed_list, list):
                return sum(int(item["N"]) for item in parsed_list if isinstance(item, dict) and "N" in item)
        elif isinstance(time_saved_list, list):
            return sum(
                int(item["N"]) if isinstance(item, dict) and "N" in item else int(item)
                for item in time_saved_list
                if isinstance(item, (dict, Decimal, int))
            )
        elif isinstance(time_saved_list, Decimal):
            return int(time_saved_list)
        elif isinstance(time_saved_list, int):
            return time_saved_list
    except Exception as e:
        logging.error(f"Unexpected error while summing TotalTimeSaved: {time_saved_list}, Error: {e}")
    return 0

@app.route('/metrics-on-demand', methods=['GET'])
def metrics_on_demand():
    """Metrics for On-Demand usage."""
    data = fetch_dynamodb_data()
    metrics = calculate_metrics(data, "us-west-2", "OnDemand")
    return jsonify(metrics)

@app.route('/metrics-spot', methods=['GET'])
def metrics_spot():
    """Metrics for Spot usage with MemVerge enhancements."""
    data = fetch_dynamodb_data()
    spot_metrics = calculate_spot_metrics(data)
    return jsonify(spot_metrics)


@app.route('/<path:filename>')
def serve_static(filename):
    return send_from_directory('/home/ubuntu/mv-spot-viewer', filename)


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5005)