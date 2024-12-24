/metrics-spot API Documentation

Description

The /metrics-spot endpoint provides metrics for AWS Batch jobs running on Spot Instances. It calculates runtime, costs, and potential savings using DynamoDB job data and AWS pricing APIs.

API: /metrics-spot

Response Format

The API returns the following metrics:
NumberOfJobs-Count of all job entries (JobID).
TotalRetries-Sum of the Attempts column.
TotalRunTimeSpot-Total runtime of all jobs in seconds (RunDurationSeconds).
TotalTimeWastedSpot-Time lost due to Spot interruptions in seconds.
TotalRunTimeWithMemVergeSpot-Adjusted runtime with MemVerge optimizations (checkpointing).
JobQueueName-Unique job queue name(s) from JobQueue.
CostWithoutMemVerge-Total cost for running jobs on Spot Instances without MemVerge (USD).
CostWithMemVerge-Total cost for running jobs on Spot Instances with MemVerge (USD).
SavingsWithMemVerge-Cost savings achieved using MemVerge optimization (USD).


Key Calculations

1. Total Runtime Without MemVerge

The total runtime is the sum of RunDurationSeconds for all jobs.

2. Time Wasted Due to Interruptions

Time lost is derived from the TotalTimeSaved field, which tracks how much time was checkpointed and restored.

Formula:
TotalTimeWastedSpot = TotalRunTimeSpot - TotalRunTimeWithMemVergeSpot

3. Cost Without MemVerge

The cost without MemVerge is calculated using the Spot pricing for the region.

Formula:
CostWithoutMemVerge = SpotPrice * (TotalRunTimeSpot / 3600)

4. Cost With MemVerge

MemVerge optimizations reduce runtime by restoring jobs from checkpoints.

Formula:
CostWithMemVerge = SpotPrice * (TotalRunTimeWithMemVergeSpot / 3600)

5. Savings With MemVerge

The cost savings achieved using MemVerge optimizations are calculated as the difference between the cost without and with MemVerge.

Formula:
SavingsWithMemVerge = CostWithoutMemVerge - CostWithMemVerge

```sh
{
  "NumberOfJobs": 419,
  "TotalRetries": 45,
  "TotalRunTimeSpot": 9959,
  "TotalTimeWastedSpot": 4857,
  "TotalRunTimeWithMemVergeSpot": 5102,
  "JobQueueName": ["jq-mm-batch-nih"],
  "CostWithoutMemVerge": 0.9132,
  "CostWithMemVerge": 0.5047,
  "SavingsWithMemVerge": 0.4085
}
```
Notes
	•	Monetary values are rounded to 4 decimal places for clarity.
	•	Savings calculations rely on accurate pricing from AWS Spot Price APIs.
	•	Job queue names are returned as a list of unique values.


/metrics-on-demand API Documentation

Description

The /metrics-on-demand endpoint provides metrics for AWS Batch jobs running on On-Demand Instances. It calculates runtime, costs, and potential savings.

API: /metrics-on-demand

Response Format

The API returns the following metrics:

NumberOfJobs-Count of all job entries (JobID).
NumberOfRetries-Sum of the Attempts column.
TotalRunTime-Total runtime of all jobs in seconds (RunDurationSeconds).
JobQueueName-Unique job queue name(s) from JobQueue.
TotalOnDemandCost-Total cost for running jobs on On-Demand Instances (USD).
TotalSpotCost-Estimated cost for running jobs on Spot Instances (USD).
EstimatedSavings-Cost savings achieved by using Spot Instances over On-Demand (USD).

Key Calculations

1. Total Runtime

The total runtime is the sum of RunDurationSeconds for all jobs.

2. Total On-Demand Cost

Cost is calculated based on the On-Demand pricing for the region.

Formula:
TotalOnDemandCost = OnDemandPrice * (LongestRuntime / 3600)

3. Total Spot Cost Estimate

The Spot cost estimate is based on Spot pricing for the region.

Formula:
TotalSpotCost = SpotPrice * (LongestRuntime / 3600)

4. Estimated Savings

Savings are calculated as the difference between On-Demand and Spot costs.

Formula:
EstimatedSavings = TotalOnDemandCost - TotalSpotCost

Example Response

```sh
{
  "NumberOfJobs": 419,
  "NumberOfRetries": 45,
  "TotalRunTime": 6933,
  "JobQueueName": ["jq-mm-batch-nih"],
  "TotalOnDemandCost": 1.3258,
  "TotalSpotCost": 0.1887,
  "EstimatedSavings": 1.1371
}
```
Notes
	•	Monetary values are rounded to 4 decimal places for clarity.
	•	Savings are calculated assuming 100% Spot capacity availability.
	•	Job queue names are returned as a list of unique values.