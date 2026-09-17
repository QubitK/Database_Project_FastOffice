###### Entities
# USER -> (Super Entity) Stores all people common Info
ID_USER                   -> INT (PK, Auto-increment)
USERNAME                  -> VARCHAR(150) [UNIQUE, NOT NULL]
PASSWORD                  -> VARCHAR(128) [Django hashed password]
FULL_NAME                 -> VARCHAR(150)
CONTACT                   -> VARCHAR(50)
ADDRESS                   -> VARCHAR(255)
EMAIL                     -> VARCHAR(254)
TAX_ID                    -> VARCHAR(50) [For business clients]
ROLE                      -> VARCHAR(20) [admin, client, driver, staff, manager]
CREATED_AT                -> TIMESTAMP [Default CURRENT_TIMESTAMP]
UPDATED_AT                -> TIMESTAMP [Default CURRENT_TIMESTAMP ON UPDATE]
IS_ACTIVE                 -> BOOLEAN [Django User field]
IS_STAFF                  -> BOOLEAN [Django User field]
IS_SUPERUSER              -> BOOLEAN [Django User field]
DATE_JOINED               -> TIMESTAMP [Django User field]
FIRST_NAME                -> VARCHAR(150) [Django User field]
LAST_NAME                 -> VARCHAR(150) [Django User field]

# EMPLOYEE -> (Super Entity) Stores all employee common Info
ID_EMPLOYEE               -> INT (PK, Auto-increment)
USER_ID                   -> INT (FK to USER, UNIQUE)
POSITION                  -> VARCHAR(20) [Driver, Staff]
SCHEDULE                  -> VARCHAR(50) [e.g., "08:00-16:00"]
WAGE                      -> DECIMAL(8,2) [Hourly or monthly rate]
IS_ACTIVE                 -> BOOLEAN [True/False]
HIRE_DATE                 -> DATE

# EMPLOYEE_DRIVER -> (Sub Entity) Inherits all info from EMPLOYEE
# Only for drivers
ID                        -> INT (PK, Auto-increment)
EMPLOYEE_ID               -> INT (FK to EMPLOYEE, UNIQUE)
LICENSE_NUMBER            -> VARCHAR(50)
LICENSE_CATEGORY          -> VARCHAR(10) [Category A, B, C, D - for different vehicle types]
LICENSE_EXPIRY_DATE       -> DATE
DRIVING_EXPERIENCE_YEARS  -> INT
DRIVER_STATUS             -> VARCHAR(50) [Available, OnDuty, Off_Duty, On_Break]

# EMPLOYEE_STAFF -> (Sub Entity) Inherits all info from EMPLOYEE
# Only for employees that work inside the PO
ID                        -> INT (PK, Auto-increment)
EMPLOYEE_ID               -> INT (FK to EMPLOYEE, UNIQUE)
DEPARTMENT                -> VARCHAR(100) [Customer_Service, Sorting, Administration]

# INVOICE -> Registry of the items a client wants to send
ID_INVOICE                -> INT (PK, Auto-increment)
USER_ID                   -> INT (FK to USER, NULLABLE) [Optional link to client]
INVOICE_STATUS            -> VARCHAR(20) [Pending, Completed, Cancelled, Refunded]
INVOICE_TYPE              -> VARCHAR(50) [Paid_on_Send, Paid_On_Delivery]
QUANTITY                  -> INT [Number of items/stamps/services]
INVOICE_DATETIME          -> TIMESTAMP [When transaction occurred]
COST                      -> DECIMAL(10,2) [Total cost]
PAID                      -> BOOLEAN [True/False]
PAYMENT_METHOD            -> VARCHAR(50) [Cash, Card, Mobile_Payment, Account]
NAME                      -> VARCHAR(100)
ADDRESS                   -> VARCHAR(200)
CONTACT                   -> VARCHAR(50)

# INVOICE_ITEM -> Individual items within an invoice
ID_ITEM                   -> INT (PK, Auto-increment)
INVOICE_ID                -> INT (FK to INVOICE)
SHIPMENT_TYPE             -> VARCHAR(50)
WEIGHT                    -> DECIMAL(10,2)
DELIVERY_SPEED            -> VARCHAR(50)
QUANTITY                  -> INT [Default 1]
UNIT_PRICE                -> DECIMAL(10,2)
NOTES                     -> TEXT

# ROUTE -> Trip containing delivery packages
ID_ROUTE                  -> INT (PK, Auto-increment)
DESCRIPTION               -> TEXT [Route details, area covered, special instructions]
DELIVERY_STATUS           -> VARCHAR(50) [NotStarted, On_Going, Finished, Cancelled]
DELIVERY_DATE             -> DATE
DELIVERY_START_TIME       -> TIME
DELIVERY_END_TIME         -> TIME
EXPECTED_DURATION         -> INTERVAL [Expected duration of route]
KMS_TRAVELLED             -> FLOAT [Default 0]
DRIVER_NOTES              -> TEXT [Driver notes about the delivery]
DRIVER_ID                 -> INT (FK to EMPLOYEE, NULLABLE)
VEHICLE_ID                -> INT (FK to VEHICLE, NULLABLE)
ORIGIN_NAME               -> VARCHAR(200)
ORIGIN_ADDRESS            -> VARCHAR(255)
ORIGIN_CONTACT            -> VARCHAR(50)
DESTINATION_NAME          -> VARCHAR(200)
DESTINATION_ADDRESS       -> VARCHAR(255)
DESTINATION_CONTACT       -> VARCHAR(50)
[UNIQUE CONSTRAINT: (DRIVER_ID, VEHICLE_ID, DELIVERY_DATE)]

# DELIVERY -> Each Package to be delivered
ID_DELIVERY               -> INT (PK, Auto-increment)
INVOICE_ID                -> INT (FK to INVOICE, NULLABLE)
TRACKING_NUMBER           -> VARCHAR(50) [UNIQUE]
DESCRIPTION               -> TEXT [Special instructions]
SENDER_NAME               -> VARCHAR(100)
SENDER_ADDRESS            -> VARCHAR(255)
SENDER_PHONE              -> VARCHAR(50)
SENDER_EMAIL              -> VARCHAR(254)
RECIPIENT_NAME            -> VARCHAR(100)
RECIPIENT_ADDRESS         -> VARCHAR(255)
RECIPIENT_PHONE           -> VARCHAR(50)
RECIPIENT_EMAIL           -> VARCHAR(254)
ITEM_TYPE                 -> VARCHAR(50)
WEIGHT                    -> INT [grams, minimum 1]
DIMENSIONS                -> VARCHAR(100) ["30x20x10 cm"]
STATUS                    -> VARCHAR(20) [Registered, Ready, Pending, In Transit, Completed, Cancelled]
PRIORITY                  -> VARCHAR(10) [normal, urgent] [Default 'normal']
REGISTERED_AT             -> TIMESTAMP
UPDATED_AT                -> TIMESTAMP
IN_TRANSITION             -> BOOLEAN [True/False]
DESTINATION               -> VARCHAR(255)
DELIVERY_DATE             -> DATE
DRIVER_ID                 -> INT (FK to EMPLOYEE, NULLABLE)
CLIENT_ID                 -> INT (FK to USER, NULLABLE)
ROUTE_ID                  -> INT (FK to ROUTE, NULLABLE)

# WAREHOUSE -> Physical storage zones/warehouses within a Post Office
ID_WAREHOUSE              -> INT (PK, Auto-increment)
NAME                      -> VARCHAR(100)
ADDRESS                   -> VARCHAR(200)
CONTACT                   -> VARCHAR(50)
PO_SCHEDULE_OPEN          -> TIME
PO_SCHEDULE_CLOSE         -> TIME
MAXIMUM_STORAGE_CAPACITY  -> INT [Minimum 1]

# VEHICLE -> Register each vehicle of the PO info
ID_VEHICLE                -> INT (PK, Auto-increment)
VEHICLE_TYPE              -> VARCHAR(100) [Van, Truck, Motorcycle, Bicycle, Car]
PLATE_NUMBER              -> VARCHAR(20) [UNIQUE]
CAPACITY                  -> FLOAT [Weight in kg or volume in m³]
BRAND                     -> VARCHAR(100) [Ford, Mercedes, Honda, etc.]
MODEL                     -> VARCHAR(100)
VEHICLE_STATUS            -> VARCHAR(50) [Available, In_Use, Maintenance, Out_of_Service]
YEAR                      -> INT [1900-2100]
FUEL_TYPE                 -> VARCHAR(50) [Diesel, Petrol, Electric, Hybrid]
LAST_MAINTENANCE_DATE     -> DATE

# NOTIFICATION
NOTIFICATION_ID           -> INT (PK, Auto-increment)
NOTIFICATION_TYPE         -> VARCHAR(20) [sms, email, push, whatsapp] [Not Null]
RECIPIENT_CONTACT         -> VARCHAR(100) [Not Null] [Phone number for SMS/WhatsApp or email]
SUBJECT                   -> VARCHAR(200) [Nullable] [Email subject line or notification title]
MESSAGE                   -> TEXT [Not Null] [Full notification message content]
STATUS                    -> VARCHAR(20) [pending, sent, delivered, failed] [Not Null]
ERROR_MESSAGE             -> TEXT [Nullable] [Error details if status=failed]
CREATED_AT                -> TIMESTAMP [Default CURRENT_TIMESTAMP]