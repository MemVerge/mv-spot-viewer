from flask import Flask, jsonify
import boto3
import json
import logging
from decimal import Decimal

app = Flask(__name__)

# Boto3 Clients
dynamodb = boto3.resource('dynamodb', region_name='us-west-2')
table = dynamodb.Table("jobTracker-spot-1")

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


@app.route('/metrics-on-demand', methods=['GET'])
def metrics_on_demand():
    """Metrics for On-Demand usage."""
    data = fetch_dynamodb_data()
    metrics = calculate_metrics(data, "us-west-2", "OnDemand")
    return jsonify(metrics)


@app.route('/metrics-spot', methods=['GET'])
def metrics_spot():
    """Metrics for Spot usage."""
    data = fetch_dynamodb_data()
    metrics = calculate_metrics(data, "us-west-2", "Spot")
    return jsonify(metrics)


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5005)