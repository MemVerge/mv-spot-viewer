#### **`metrics-spot.md`**

```markdown
# `/metrics-spot` API Documentation

## Description
This endpoint provides metrics for AWS Batch users running completely on Spot Instances. It calculates costs, savings, and other metrics based on DynamoDB data.

---

## API: `/metrics-spot`

### Response Format
The API returns the following metrics in JSON format:

| Field                   | Description                                                                                  |
|-------------------------|----------------------------------------------------------------------------------------------|
| `NumberOfJobs`          | Count of all job entries (`JobID`).                                                          |
| `NumberOfRetries`       | Sum of the `Attempts` column.                                                                |
| `TotalRunTime`          | Total run time in seconds (`RunDurationSeconds`).                                            |
| `JobQueueName`          | Unique job queue name(s) from `JobQueue`.                                                    |
| `TotalOnDemandCost`     | Estimated cost of running jobs on On-Demand instances (USD).                                 |
| `TotalSpotCost`         | Total cost of running jobs on Spot Instances (USD).                                          |
| `EstimatedCostSaving`   | Cost savings achieved by using Spot Instances over On-Demand instances (USD).                |

---

### Calculations

#### **1. Total On-Demand Cost (USD) (Estimate)**

Total On-Demand Cost (USD):
Cost = Sum of (On-Demand Price (USD/hour) * (Longest Run Duration (seconds) / 3600)) for all instances.

- Extract **unique `InstanceIDs`** and their corresponding `InstanceTypes` from `InstanceMap`.
- Obtain the **longest `RunDurationSeconds`** for each `InstanceID`.
- Multiply by the **On-Demand price** for the region.

#### **2. Total Spot Cost (USD)**

Total Spot Cost (USD):
Cost = Sum of (Spot Price * (Longest Run Duration (seconds) / 3600)) for all instances.

- Use Spot price history for each `InstanceID` to calculate the cost.
- Multiply the **longest `RunDurationSeconds`** by the **Spot price** for the region.

#### **3. Estimated Cost Saving**

Estimated Cost Savings = Total On-Demand cost - Total Spot cost

---

### Example Response

```json
{
  "NumberOfJobs": 120,
  "NumberOfRetries": 15,
  "TotalRunTime": 240000,
  "JobQueueName": ["DefaultQueue"],
  "TotalOnDemandCost": 100.75,
  "TotalSpotCost": 28.50,
  "EstimatedCostSaving": 72.25
}
```
Notes
	•	Monetary values are rounded to two decimal places for better readability.
	•	Savings are calculated as the difference between On-Demand and Spot costs.
	•	Job Queue Name(s) are returned as a list of unique strings.


---
