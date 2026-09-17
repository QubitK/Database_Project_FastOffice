##### ----------------- ENTITIES -----------------

# Entity: Inheritance Structure
```
                        USER
                         |
           +-------------+-------------+
           |   MUTUALLY EXCLUSIVE (d)   |
           v                            v
        CLIENT                      EMPLOYEE
                                       |
                         +-------------+-------------+
                         |   MUTUALLY EXCLUSIVE (d)   |
                         v                            v
                  EMPLOYEE_DRIVER              EMPLOYEE_STAFF

- Single ID for every of these entities.
- A User can be Client OR Employee, never both
- An Employee can be Driver OR Staff, never both
- Admins/Managers exist only in User (no child record)
```

# USER
Base identity for all system users (clients, employees, admins, managers).
# CLIENT
Extension of User for customers who request delivery services.
# EMPLOYEE
Extension of User for post office workers (common to drivers and staff).
# EMPLOYEE_DRIVER
Sub-entity of Employee for drivers. Exclusive with Employee_Staff.
# EMPLOYEE_STAFF
Sub-entity of Employee for office/warehouse staff. Exclusive with Employee_Driver.
# WAREHOUSE
Physical post office locations/warehouses.
# VEHICLE
Fleet vehicles used for deliveries.
# INVOICE
Record of services a client wants to send + payment. Snapshot fields (name, address, contact) preserve client info at creation time for record integrity.
# INVOICE_ITEM
Individual line items within an Invoice.
# ROUTE
A driver's journey from a warehouse carrying deliveries.
# DELIVERY
Individual package to be delivered. Sender/recipient info is stored as flattened snapshot fields because they may not be registered users.
# DELIVERY_TRACKING
Append-only event log recording every status change of a delivery. Each row represents an event — when, where, who, and to which status.
  The DELIVERY table holds only the current status. DELIVERY_TRACKING stores all past statuses, allowing the full journey of a package to be traced.
  How it is populated
  Through the trigger trg_delivery_tracking_log, which fires automatically AFTER INSERT OR UPDATE OF status ON DELIVERY. Whenever a delivery's status changes (via sp_update_delivery_status()), the trigger inserts a new row into DELIVERY_TRACKING with the del_id, new status, staff_id, war_id, and timestamp — with no application-level logic required in Django.

# NOTIFICATION (MongoDB - ignore for PostGreSQL)
Notification records stored in MongoDB.
| Attribute         | Type     | Constraints |
|-------------------|----------|-------------|
| id               | ObjectId | PK (auto)   |
| notification_type | String   | NOT NULL    |
| recipient_contact | String   | NOT NULL    |
| subject           | String   | NULL        |
| message           | String   | NOT NULL    |
| status            | String   | NOT NULL    |
| error_message     | String   | NULL        |
| created_at        | Date     | DEFAULT NOW |



###### ----------------- RELATIONSHIPS -----------------

| #   | Relationship                                         | Cardinality | Participation                                   | Description                                   |
|-----|------------------------------------------------------|-------------|-------------------------------------------------|-----------------------------------------------|
| R1  | User — Client (UserInheritance)                       | 1:1         | User (optional), Client (mandatory)             | A User may be a Client; every Client is a User |
| R2  | User — Employee (UserInheritance)                     | 1:1         | User (optional), Employee (mandatory)           | A User may be an Employee; every Employee is a User |
| R3  | Employee — Employee_Driver (Inheritance)              | 1:1         | Employee (optional), Driver (mandatory)         | An Employee may be a Driver                   |
| R4  | Employee — Employee_Staff (Inheritance)               | 1:1         | Employee (optional), Staff (mandatory)          | An Employee may be Staff                     |
| R5  | Warehouse — Employee (Works_At)                       | 1:N         | Warehouse (optional), Employee (optional)       | A Warehouse has many Employees                |
| R6  | Client — Invoice (Requests)                           | 1:N         | Client (optional), Invoice (optional)           | A Client can have many Invoices               |
| R7  | EmployeeStaff — Invoice (Processes)                   | 1:N         | Employee (optional), Invoice (optional)         | A Staff Employee processes many Invoices      |
| R8  | Warehouse — Invoice (Records)                         | 1:N         | Warehouse (optional), Invoice (optional)        | Invoices are created at a Warehouse           |
| R9  | Invoice — Invoice_Item (Contains)                     | 1:N         | Invoice (mandatory), Item (mandatory)           | An Invoice has many line items                |
| R10 | EmployeeDriver — Route (Is_Assigned_To)               | 1:N         | Employee (optional), Route (optional)           | A Driver is assigned to many Routes           |
| R11 | Vehicle — Route (Uses)                                | 1:N         | Vehicle (optional), Route (optional)            | A Vehicle is assigned to many Routes          |
| R12 | Warehouse — Route (Dispatches)                        | 1:N         | Warehouse (optional), Route (mandatory)         | Routes depart from a Warehouse                |
| R13 | Invoice — Delivery (Generates)                        | 1:N         | Invoice (optional), Delivery (optional)         | An Invoice generates one or more Deliveries   |
| R14 | EmployeeDriver — Delivery (Delivers)                  | 1:N         | Employee (optional), Delivery (optional)        | A Driver delivers many Deliveries             |
| R15 | Client — Delivery (Sent_By)                           | 1:N         | Client (optional), Delivery (optional)          | A Client requests many Deliveries             |
| R16 | Route — Delivery (Belongs_To)                         | 1:N         | Route (optional), Delivery (optional)           | A Route carries many Deliveries               |
| R17 | Warehouse — Delivery (Handles)                        | 1:N         | Warehouse (optional), Delivery (optional)       | Deliveries are dispatched from a Warehouse    |
| R18 | Delivery — Delivery_Tracking (Logs)                   | 1:N         | Delivery (mandatory), Tracking (mandatory)      | A Delivery has many tracking events           |
| R19 | EmployeeStaff — Delivery_Tracking (Registers_Logs)    | 1:N         | Employee (optional), Tracking (optional)        | An Employee logs tracking events              |
| R20 | Warehouse — Delivery_Tracking (Records_Logs)          | 1:N         | Warehouse (optional), Tracking (optional)       | Tracking events record the location           |


## Relationship Diagram

```
                                 WAREHOUSE
                               /    |    \      \
                         R5  /   R8 |  R12\   R17\  R20
                            /      |      \      \    \
    USER ----R1---- CLIENT --R6-- INVOICE  ROUTE  DELIVERY  DELIVERY_TRACKING
      |                |             |       / \      |           |
      R2            R15 \         R9 |  R10/R11\  R16/         R18|
      |                  \           |    /     \  /              |
    EMPLOYEE           DELIVERY  INV_ITEM  VEHICLE           DELIVERY
      |  \               ^
      |   \           R13|  R14
     R3    R4            |  /
      |     \        INVOICE / EMPLOYEE
      v      v
   DRIVER   STAFF
```