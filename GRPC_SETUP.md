# gRPC Proto Files - Updated for Donation System

## Proto Files Created/Updated

### 1. Campaign Service Proto
**Location**: `campaign-service/app/proto/campaign.proto`

```proto
service CampaignService {
  rpc GetCampaign(GetCampaignRequest) returns (GetCampaignResponse);
  rpc CheckCampaignActive(CheckCampaignActiveRequest) returns (CheckCampaignActiveResponse);
}
```

**Methods**:
- `GetCampaign`: Retrieves campaign details (title, name, description, dates, active status)
- `CheckCampaignActive`: Checks if a campaign is currently active for donations

---

### 2. Donation Service Proto (Client)
**Location**: `donation-service/proto/donation.proto`

```proto
service DonationService {
  rpc CreateDonation(CreateDonationRequest) returns (CreateDonationResponse);
  rpc GetDonation(GetDonationRequest) returns (GetDonationResponse);
}
```

---

### 3. Campaign Proto for Donation Service (Client)
**Location**: `donation-service/proto/campaign/campaign.proto`

This is the campaign proto that donation-service will use to make gRPC calls to campaign-service.

---

## Generate gRPC Code

### For Campaign Service:
```bash
cd campaign-service/app/proto
python -m grpc_tools.protoc -I. --python_out=../grpc/campaign --grpc_python_out=../grpc/campaign campaign.proto
```

### For Donation Service:
```bash
cd donation-service/proto

# Generate campaign client code
python -m grpc_tools.protoc -I. --python_out=../app/grpc/campaign --grpc_python_out=../app/grpc/campaign campaign/campaign.proto

# Generate donation service code
python -m grpc_tools.protoc -I. --python_out=../app/grpc/donation --grpc_python_out=../app/grpc/donation donation.proto
```

---

## Next Steps

1. **Generate gRPC code** using the commands above
2. **Update donation service** to use CampaignGRPCClient instead of ProductGRPCClient
3. **Implement gRPC server** in campaign-service
4. **Update create_donation endpoint** to:
   - Check if campaign is active (via gRPC)
   - Get campaign details (via gRPC)
   - Create donation record
   - Publish donation events to Kafka

---

## Key Changes from Order → Donation

### Data Model:
- `product_id` + `quantity` → `campaign_id` + `amount`
- `CheckAvailability` → `CheckCampaignActive`
- `GetProduct` → `GetCampaign`
- Added donation-specific fields: `donor_name`, `donor_email`, `message`, `is_anonymous`

### Status Flow:
- Order: `PENDING → PAID → FAILED → CANCELLED`
- Donation: `INITIATED → AUTHORIZED → CAPTURED → FAILED → REFUNDED → CANCELLED`
