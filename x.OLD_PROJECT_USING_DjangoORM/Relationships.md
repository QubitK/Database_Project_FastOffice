###### Relationship Verification Report

## IMPLEMENTED RELATIONSHIPS

### USER
- USER inheritance to EMPLOYEE/CLIENT - Implemented via role field and OneToOne relationships

### EMPLOYEE
- EMPLOYEE (1) ────── (1) EMPLOYEE_DRIVER - Implemented via employee.driver_info
- EMPLOYEE (1) ────── (1) EMPLOYEE_STAFF - Implemented via employee.staff_info

### EMPLOYEE_DRIVER
- EMPLOYEE_DRIVER (1) ────── (N) ROUTE - Implemented via Route.driver FK

### CLIENT
- CLIENT (1) ────── (N) INVOICE - Implemented via Invoice.user FK
- CLIENT (1) ────── (N) DELIVERY (as client) - Implemented via Delivery.client FK

### INVOICE
- INVOICE (1) ────── (N) DELIVERY - Implemented via Delivery.invoice FK
- INVOICE (1) ────── (N) INVOICE_ITEM - Implemented via InvoiceItem.invoice FK

### DELIVERY
- DELIVERY (N) ────── (1) ROUTE - Implemented via Delivery.route FK
- DELIVERY (N) ────── (1) EMPLOYEE_DRIVER - Implemented via Delivery.driver FK

### ROUTE
- ROUTE (N) ────── (1) VEHICLE - Implemented via Route.vehicle FK

## MISSING RELATIONSHIPS

### EMPLOYEE
- EMPLOYEE (N) ────── Works_At ────── (1) POST_OFFICE_STORE
  Missing FK: No warehouse field in Employee model

### EMPLOYEE_STAFF
- EMPLOYEE_STAFF (1) ────── Processes ────── (N) INVOICE
  Missing FK: No processed_by_staff field in Invoice model

### CLIENT
- CLIENT (1) ────── Picks_Up_At ────── (N) POST_OFFICE_STORE
  Missing relationship: Would need ManyToMany table

### POST_OFFICE_STORE (WAREHOUSE)
- POST_OFFICE_STORE (1) ────── Records ────── (N) INVOICE
  Missing FK: No warehouse field in Invoice model

- POST_OFFICE_STORE (1) ────── Dispatches ────── (N) ROUTE
  Missing FK: No origin_warehouse or dispatch_warehouse field in Route model

### DELIVERY
- DELIVERY (N) ────── Sent_By ────── (1) CLIENT (as Sender)
  Partially implemented: Has sender name/address/phone/email as TEXT fields, but no FK to User/Client

- DELIVERY (N) ────── Addressed_To ────── (1) CLIENT (as Recipient)
  Partially implemented: Has recipient name/address/phone/email as TEXT fields, but no FK to User/Client

- DELIVERY (1) ────── Triggers ────── (N) NOTIFICATION
  Missing: No Notification model exists at all, and no FK from Notification to Delivery
