# Architecture Diagram (Mermaid)

```mermaid
flowchart TB
    EB[Amazon EventBridge<br/>Hourly Schedule]
    Lambda[AWS Lambda<br/>cost-detective<br/>Python 3.12<br/>1024MB / 5min]
    
    subgraph "Data Sources"
        CE[AWS Cost Explorer<br/>GetCostAndUsage]
        CT[AWS CloudTrail<br/>LookupEvents]
        Config[AWS Config<br/>GetConfigHistory]
    end
    
    Bedrock[Amazon Bedrock<br/>Claude Sonnet 4.6<br/>AI Analysis]
    
    subgraph "Storage & Alerts"
        DDB[(DynamoDB<br/>cost-anomalies<br/>Store history)]
        S3[S3 Bucket<br/>Detailed reports]
        SNS[Amazon SNS<br/>Email alerts]
        CW[CloudWatch Logs<br/>Execution logs]
    end
    
    EB -->|Trigger| Lambda
    Lambda -->|Query costs| CE
    Lambda -->|Get API calls| CT
    Lambda -->|Get changes| Config
    Lambda -->|Analyze with AI| Bedrock
    Lambda -->|Store| DDB
    Lambda -->|Save reports| S3
    Lambda -->|Send alerts| SNS
    Lambda -->|Log| CW
    
    style Lambda fill:#FF9900
    style Bedrock fill:#00A4A6
    style EB fill:#FF4F8B
    style DDB fill:#4053D6
    style S3 fill:#569A31
    style SNS fill:#FF4F8B
```

## Component Description

| Component | Purpose | Key Details |
|-----------|---------|-------------|
| **EventBridge** | Scheduled trigger | Hourly (configurable) |
| **Lambda** | Orchestrator | Python 3.12, 1024MB, 5min timeout |
| **Cost Explorer** | Fetch costs | Current vs baseline (1 week ago) |
| **CloudTrail** | API activity | Who made what changes |
| **Config** | Resource changes | Instance types, sizes, configs |
| **Bedrock** | AI analysis | Root cause + recommendations |
| **DynamoDB** | Anomaly history | Store for trending |
| **S3** | Detailed reports | JSON format, 90-day retention |
| **SNS** | Email alerts | Real-time notifications |
| **CloudWatch** | Logs | Execution tracking |

## Data Flow

1. **EventBridge** triggers Lambda every hour
2. **Lambda** queries Cost Explorer for current & baseline costs
3. If spike detected (>50%):
   - Query **CloudTrail** for recent API calls
   - Query **Config** for resource changes
   - Query **CloudWatch** for metrics
4. Send context to **Bedrock** for AI analysis
5. Store anomaly in **DynamoDB**
6. Save detailed report to **S3**
7. Send alert via **SNS**
8. Log execution to **CloudWatch**

**Execution time:** ~30-60 seconds  
**Cost per run:** ~$0.01  
**Monthly cost:** ~$30

---

## Simplified Flow Diagram

```mermaid
sequenceDiagram
    participant EB as EventBridge
    participant L as Lambda
    participant CE as Cost Explorer
    participant AI as Bedrock AI
    participant SNS as SNS Alerts
    
    EB->>L: Trigger (hourly)
    L->>CE: Get current costs
    L->>CE: Get baseline costs (1 week ago)
    
    alt Spike detected
        L->>L: Enrich with CloudTrail + Config
        L->>AI: Analyze with context
        AI-->>L: Root cause + recommendations
        L->>SNS: Send alert
    else No spike
        L->>L: Log "no anomalies"
    end
```

---

## Multi-Account Deployment

```mermaid
flowchart TB
    subgraph "Management Account"
        CD[Cost Anomaly Detective<br/>Has org-wide Cost Explorer access]
    end
    
    subgraph "Member Accounts"
        Dev[Dev Account]
        Prod[Prod Account]
        Stage[Staging Account]
    end
    
    CD -->|Monitors costs| Dev
    CD -->|Monitors costs| Prod
    CD -->|Monitors costs| Stage
    
    style CD fill:#FF9900
```

**Key:** Deploy in **management account** for org-wide visibility.

---

For the interactive Draw.io diagram, open: [`architecture-diagram.drawio`](architecture-diagram.drawio)
