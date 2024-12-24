# mv-spot-viewer


## Overview

This project provides a two-step process to analyze and visualize AWS Batch workloads. It includes:
1. **Analytics Stack**: Captures job metrics and insights from AWS Batch and stores them in DynamoDB.
2. **Spot Viewer Stack (Optional)**: Visualizes On-Demand vs. Spot cost insights for AWS Batch jobs, helping optimize workloads.

---

## **Stack 1: Analytics for AWS Batch**

### Purpose:
- Monitor AWS Batch jobs and collect insights such as instance IDs, retries, interruptions, and runtime into DynamoDB.

### Features:
- **EventBridge Rule**: Triggers a Lambda function for Batch job state changes.
- **Lambda Function**: Processes job data from AWS Batch and ECS, then stores it in DynamoDB.

### Deployment Parameters:
- **`UniquePrefix`**: A unique prefix for resource naming (e.g., `project-name` or a random string).
- **`BatchComputeEnvironmentName`**: Name of the AWS Batch Compute Environment to monitor.

### Outputs:
- **`DynamoDBTableName`**: Name of the DynamoDB table storing job metrics.
- **`LambdaFunctionName`**: Name of the Lambda function processing job state changes.

---

## **Stack 2: Spot Viewer (Optional)**

### Purpose:
- Provides visual insights into AWS Batch workloads, comparing On-Demand and Spot costs with MemVerge enhancements.

### Features:
- Deploys an EC2 instance hosting a Flask-based web application.
- Two visualization options:
  - **On-Demand Metrics**: `/on-demand.html`
  - **Spot Metrics with MemVerge Enhancements**: `/spot.html`
- Cost analysis for AWS Batch jobs:
  - On-Demand vs. Spot.
  - Savings potential with MemVerge.

### Deployment Parameters:
- **`UniquePrefix`**: The same prefix used in Stack 1 for consistent integration.
- **`VpcId`**: VPC ID for the EC2 instance.
- **`SubnetId`**: Subnet ID for the EC2 instance.
- **`KeyName`**: Key Pair for SSH access.

### Outputs:
- **`SpotViewerEC2InstanceId`**: ID of the EC2 instance hosting the Spot Viewer.
- **`PublicIP`**: Public IP of the EC2 instance for accessing the web interface.

---

## **Steps to Use**

1. **Deploy Stack 1**:
   - Use AWS CloudFormation to deploy the Analytics stack.
   - Provide the required parameters: `UniquePrefix` and `BatchComputeEnvironmentName`.

2. **Deploy Stack 2** (Optional):
   - Use AWS CloudFormation to deploy the Spot Viewer stack.
   - Provide the required parameters: `UniquePrefix`, `VpcId`, `SubnetId`, and `KeyName`.

3. **Access Spot Viewer**:
   - Get the **Public IP** from the stack outputs or EC2 dashboard.
   - Open the following URLs in a browser:
     - **On-Demand Metrics**: `http://<ip_address>:5005/on-demand.html`
     - **Spot Metrics**: `http://<ip_address>:5005/spot.html`

---

## Additional Information

- **Source Code**:
  - API-level details: `doc/`
  - Lambda and HTML code: `resources/`

- **Note**: Make sure to use the same `UniquePrefix` across both stacks to ensure proper integration.


## License
This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details
