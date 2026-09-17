/*==============================================================*/
/* DBMS name:      PostgreSQL 9.x                               */
/* Created on:     06/02/2026 19:09:55                          */
/*==============================================================*/


/*==============================================================*/
/* Drop tables (child first, CASCADE handles FKs + indexes)     */
/* NOTE: "USER" is NOT dropped here — it is created and managed */
/*       by Django migrations (see PostOffice_App/models.py).   */
/*       Run 'python manage.py migrate' BEFORE this DDL.        */
/*==============================================================*/
DROP TABLE IF EXISTS DELIVERY_TRACKING CASCADE;
DROP TABLE IF EXISTS DELIVERY CASCADE;
DROP TABLE IF EXISTS INVOICE_ITEM CASCADE;
DROP TABLE IF EXISTS INVOICE CASCADE;
DROP TABLE IF EXISTS ROUTE CASCADE;
DROP TABLE IF EXISTS VEHICLE CASCADE;
DROP TABLE IF EXISTS WAREHOUSE CASCADE;
DROP TABLE IF EXISTS EMPLOYEE_DRIVER CASCADE;
DROP TABLE IF EXISTS EMPLOYEE_STAFF CASCADE;
DROP TABLE IF EXISTS EMPLOYEE CASCADE;
DROP TABLE IF EXISTS CLIENT CASCADE;


-- "USER" table is created by Django migrations (manages auth columns:
-- id, password, username, email, is_superuser, is_staff, is_active,
-- last_login, created_at + business columns: contact, address, role, updated_at).
-- All other tables below reference "USER"(ID) via foreign keys.

-- Includes index creation on FK columns to improve join performance
--  USER.ROLE ->  'admin' || 'client' || 'driver' || 'staff' || 'manager'

/*==============================================================*/
/* Table: CLIENT                                                */
/*==============================================================*/
create table CLIENT (
   ID                   INT4                 not null,
   TAX_ID               VARCHAR(50)          null,
   constraint PK_CLIENT primary key (ID)
);

/*==============================================================*/
/* Table: WAREHOUSE                                             */
/*==============================================================*/
create table WAREHOUSE (
   ID                   SERIAL               not null,
   NAME                 VARCHAR(100)         not null,
   CONTACT              VARCHAR(20)          not null,
   ADDRESS              VARCHAR(255)         not null,
   SCHEDULE_OPEN        TIME                 null,
   SCHEDULE_CLOSE       TIME                 null,
   SCHEDULE             TEXT                 null,
   MAXIMUM_STORAGE_CAPACITY INT4                 not null, -- (>=1)
   IS_ACTIVE            BOOL                 not null,
   CREATED_AT           TIMESTAMPTZ          not null,
   UPDATED_AT           TIMESTAMPTZ          not null,
   constraint PK_WAREHOUSE primary key (ID),
   constraint CHK_WAREHOUSE_CAPACITY CHECK (MAXIMUM_STORAGE_CAPACITY >= 1)
);

/*==============================================================*/
/* Table: EMPLOYEE                                              */
/*==============================================================*/
create table EMPLOYEE (
   ID                   INT4                 not null,
   WAR_ID               INT4                 null,
   EMP_POSITION         VARCHAR(32)          null, --  'driver' || 'staff'
   SCHEDULE             VARCHAR(255)         null,
   WAGE                 DECIMAL(10,2)        null,
   IS_ACTIVE            BOOL                 null,
   HIRE_DATE            DATE                 null,
   constraint PK_EMPLOYEE primary key (ID),
   constraint CHK_EMPLOYEE_POSITION CHECK (EMP_POSITION IN ('driver', 'staff'))
);

create index WORKS_AT_FK on EMPLOYEE (WAR_ID);

/*==============================================================*/
/* Table: EMPLOYEE_DRIVER                                       */
/*==============================================================*/
create table EMPLOYEE_DRIVER (
   ID                   INT4                 not null,
   LICENSE_NUMBER       VARCHAR(50)          null,
   LICENSE_CATEGORY     VARCHAR(20)          null, -- 'A' ||'B' ||'C' ||'D'
   LICENSE_EXPIRY_DATE  DATE                 null,
   DRIVING_EXPERIENCE_YEARS INT4                 null,
   DRIVER_STATUS        VARCHAR(20)          null, -- 'available' || 'on_duty' || 'off_duty' || 'on_break'
   constraint PK_EMPLOYEE_DRIVER primary key (ID),
   constraint CHK_DRIVER_LICENSE_CAT CHECK (LICENSE_CATEGORY IN ('A', 'B', 'C', 'D')),
   constraint CHK_DRIVER_STATUS CHECK (DRIVER_STATUS IN ('available', 'on_duty', 'off_duty', 'on_break'))
);

/*==============================================================*/
/* Table: EMPLOYEE_STAFF                                        */
/*==============================================================*/
create table EMPLOYEE_STAFF (
   ID                   INT4                 not null,
   DEPARTMENT           VARCHAR(32)          null, -- 'customer_service' || 'sorting' || 'administration'
   constraint PK_EMPLOYEE_STAFF primary key (ID),
   constraint CHK_STAFF_DEPARTMENT CHECK (DEPARTMENT IN ('customer_service', 'sorting', 'administration'))
);

/*==============================================================*/
/* Table: VEHICLE                                               */
/*==============================================================*/
create table VEHICLE (
   ID                   SERIAL               not null,
   VEHICLE_TYPE         VARCHAR(50)          null, -- 'van' || 'truck' || 'motorcycle' || 'bicycle' || 'car'
   PLATE_NUMBER         VARCHAR(20)          null,
   CAPACITY             DECIMAL(10,2)        null,
   BRAND                VARCHAR(50)          null,
   MODEL                VARCHAR(50)          null,
   VEHICLE_STATUS       VARCHAR(20)          null, -- 'available' || 'in_use' || 'maintenance' || 'out_of_service'
   YEAR                 INT4                 null,
   FUEL_TYPE            VARCHAR(30)          null, -- 'diesel' || 'petrol' || 'electric' || 'hybrid'
   LAST_MAINTENANCE_DATE DATE                null,
   IS_ACTIVE            BOOL                 null,
   CREATED_AT           TIMESTAMPTZ          null,
   UPDATED_AT           TIMESTAMPTZ          null,
   constraint PK_VEHICLE primary key (ID),
   constraint CHK_VEHICLE_TYPE CHECK (VEHICLE_TYPE IN ('van', 'truck', 'motorcycle', 'bicycle', 'car')),
   constraint CHK_VEHICLE_STATUS CHECK (VEHICLE_STATUS IN ('available', 'in_use', 'maintenance', 'out_of_service')),
   constraint CHK_VEHICLE_FUEL CHECK (FUEL_TYPE IN ('diesel', 'petrol', 'electric', 'hybrid'))
);

/*==============================================================*/
/* Table: INVOICE                                               */
/*==============================================================*/
create table INVOICE (
   ID                   SERIAL               not null,
   WAR_ID               INT4                 null,
   STAFF_ID             INT4                 null,
   CLIENT_ID            INT4                 null,
   STATUS               VARCHAR(30)          null, -- 'pending' || 'completed' || 'cancelled' || 'refunded'
   TYPE                 VARCHAR(30)          null, --  'paid_on_send' || 'paid_on_delivery'
   QUANTITY             INT4                 null,
   COST                 DECIMAL(10,2)        null,
   PAID                 BOOL                 null,
   PAY_METHOD           VARCHAR(30)          null, -- 'cash' || 'card' || 'mobile_payment' || 'account'
   NAME                 TEXT                 null,
   ADDRESS              TEXT                 null,
   CONTACT              TEXT                 null,
   CREATED_AT           TIMESTAMPTZ          not null,
   UPDATED_AT           TIMESTAMPTZ          not null,
   constraint PK_INVOICE primary key (ID),
   constraint CHK_INVOICE_STATUS CHECK (STATUS IN ('pending', 'completed', 'cancelled', 'refunded')),
   constraint CHK_INVOICE_TYPE CHECK (TYPE IN ('paid_on_send', 'paid_on_delivery')),
   constraint CHK_INVOICE_PAY_METHOD CHECK (PAY_METHOD IN ('cash', 'card', 'mobile_payment', 'account'))
);

create index PROCESSES_FK on INVOICE (STAFF_ID);
create index RECORDS_FK on INVOICE (WAR_ID);
create index REQUESTS_FK on INVOICE (CLIENT_ID);

/*==============================================================*/
/* Table: INVOICE_ITEM                                          */
/*==============================================================*/
create table INVOICE_ITEM (
   ID                   SERIAL               not null,
   INV_ID               INT4                 not null,
   SHIPMENT_TYPE        VARCHAR(50)          null,
   WEIGHT               DECIMAL(10,2)        null,
   DELIVERY_SPEED       VARCHAR(50)          null,
   QUANTITY             INT4                 null,
   UNIT_PRICE           DECIMAL(10,2)        null,
   TOTAL_ITEM_COST      DECIMAL(10,2)        null,
   NOTES                TEXT                 null,
   CREATED_AT           TIMESTAMPTZ          null,
   UPDATED_AT           TIMESTAMPTZ          null,
   constraint PK_INVOICE_ITEM primary key (ID)
);

create index CONTAINS_FK on INVOICE_ITEM (INV_ID);

/*==============================================================*/
/* Table: ROUTE                                                 */
/*==============================================================*/
create table ROUTE (
   ID                   SERIAL               not null,
   DRIVER_ID            INT4                 null,
   VEHICLE_ID           INT4                 null,
   WAR_ID               INT4                 null,
   DESCRIPTION          TEXT                 null,
   DELIVERY_STATUS      VARCHAR(20)          null, -- 'not_started' || 'on_going' || 'finished' || 'cancelled'
   DELIVERY_DATE        DATE                 null,
   DELIVERY_START_TIME  TIMESTAMPTZ          null,
   DELIVERY_END_TIME    TIMESTAMPTZ          null,
   EXPECTED_DURATION    TIME                 null,
   KMS_TRAVELLED        DECIMAL(8,2)         null,
   DRIVER_NOTES         TEXT                 null,
   IS_ACTIVE            BOOL                 null,
   CREATED_AT           TIMESTAMPTZ          null,
   UPDATED_AT           TIMESTAMPTZ          null,
   constraint PK_ROUTE primary key (ID),
   constraint CHK_ROUTE_STATUS CHECK (DELIVERY_STATUS IN ('not_started', 'on_going', 'finished', 'cancelled'))
);

create index IS_ASSIGNED_TO_FK on ROUTE (DRIVER_ID);
create index DISPATCHES_FK on ROUTE (WAR_ID);
create index USES_FK on ROUTE (VEHICLE_ID);

/*==============================================================*/
/* Table: DELIVERY                                              */
/*==============================================================*/
create table DELIVERY (
   ID                   SERIAL               not null,
   DRIVER_ID            INT4                 null,
   ROUTE_ID             INT4                 null,
   INV_ID               INT4                 null,
   CLIENT_ID            INT4                 null,
   WAR_ID               INT4                 null,
   TRACKING_NUMBER      VARCHAR(50)          null,
   DESCRIPTION          TEXT                 null,
   SENDER_NAME          VARCHAR(100)         null,
   SENDER_ADDRESS       TEXT                 null,
   SENDER_PHONE         VARCHAR(20)          null,
   SENDER_EMAIL         VARCHAR(100)         null,
   RECIPIENT_NAME       VARCHAR(100)         null,
   RECIPIENT_ADDRESS    TEXT                 null,
   RECIPIENT_PHONE      VARCHAR(20)          null,
   RECIPIENT_EMAIL      VARCHAR(100)         null,
   ITEM_TYPE            VARCHAR(20)          null,
   WEIGHT               INT4                 null, -- (>=1)
   DIMENSIONS           VARCHAR(50)          null,
   STATUS               VARCHAR(20)          null, -- 'registered' || 'ready' || 'pending' || 'in_transit' || 'completed' || 'cancelled'
   PRIORITY             VARCHAR(20)          null, -- 'normal' || 'urgent'
   IN_TRANSITION        BOOL                 null,
   DELIVERY_DATE        TIMESTAMPTZ          null,
   CREATED_AT           TIMESTAMPTZ          null,
   UPDATED_AT           TIMESTAMPTZ          null,
   constraint PK_DELIVERY primary key (ID),
   constraint CHK_DELIVERY_WEIGHT CHECK (WEIGHT >= 1),
   constraint CHK_DELIVERY_STATUS CHECK (STATUS IN ('registered', 'ready', 'pending', 'in_transit', 'completed', 'cancelled')),
   constraint CHK_DELIVERY_PRIORITY CHECK (PRIORITY IN ('normal', 'urgent'))
);

create index DELIVERS_FK on DELIVERY (DRIVER_ID);
create index BELONGS_TO_FK on DELIVERY (ROUTE_ID);
create index GENERATES_FK on DELIVERY (INV_ID);
create index SENT_BY_FK on DELIVERY (CLIENT_ID);
create index HANDLES_FK on DELIVERY (WAR_ID);

/*==============================================================*/
/* Table: DELIVERY_TRACKING                                     */
/*==============================================================*/
create table DELIVERY_TRACKING (
   ID                   SERIAL               not null,
   STAFF_ID             INT4                 null,
   WAR_ID               INT4                 null,
   DEL_ID               INT4                 not null,
   STATUS               VARCHAR(20)          null, -- 'registered' || 'ready' || 'pending' || 'in_transit' || 'completed' || 'cancelled'
   NOTES                TEXT                 null,
   CREATED_AT           TIMESTAMPTZ          null,
   constraint PK_DELIVERY_TRACKING primary key (ID),
   constraint CHK_TRACKING_STATUS CHECK (STATUS IN ('registered', 'ready', 'pending', 'in_transit', 'completed', 'cancelled'))
);

create index LOGS_FK on DELIVERY_TRACKING (DEL_ID);
create index REGISTERS_LOGS_FK on DELIVERY_TRACKING (STAFF_ID);
create index RECORDS_LOGS_FK on DELIVERY_TRACKING (WAR_ID);


/*==============================================================*/
/* Foreign Key Constraints (R1-R20)                             */
/*==============================================================*/

-- CHK: User.role (Django-managed table, applied via ALTER)
alter table "USER" add constraint CHK_USER_ROLE
   CHECK (role IN ('admin', 'client', 'driver', 'staff', 'manager'));

-- R1: User -> Client (UserInheritance)
alter table CLIENT add constraint FK_CLIENT_INHERITS_USER
   foreign key (ID) references "USER" (ID);

-- R2: User -> Employee (UserInheritance)
alter table EMPLOYEE add constraint FK_EMPLOYEE_INHERITS_USER
   foreign key (ID) references "USER" (ID);

-- R3: Employee -> Employee_Driver (EmployeeInheritance)
alter table EMPLOYEE_DRIVER add constraint FK_DRIVER_INHERITS_EMPLOYEE
   foreign key (ID) references EMPLOYEE (ID);

-- R4: Employee -> Employee_Staff (EmployeeInheritance)
alter table EMPLOYEE_STAFF add constraint FK_STAFF_INHERITS_EMPLOYEE
   foreign key (ID) references EMPLOYEE (ID);

-- R5: Warehouse -> Employee (Works_At)
alter table EMPLOYEE add constraint FK_EMPLOYEE_WORKS_AT
   foreign key (WAR_ID) references WAREHOUSE (ID);

-- R6: Client -> Invoice (Requests)
alter table INVOICE add constraint FK_INVOICE_REQUESTS
   foreign key (CLIENT_ID) references CLIENT (ID);

-- R7: EmployeeStaff -> Invoice (Processes)
alter table INVOICE add constraint FK_INVOICE_PROCESSES
   foreign key (STAFF_ID) references EMPLOYEE_STAFF (ID);

-- R8: Warehouse -> Invoice (Records)
alter table INVOICE add constraint FK_INVOICE_RECORDS
   foreign key (WAR_ID) references WAREHOUSE (ID);

-- R9: Invoice -> Invoice_Item (Contains)
alter table INVOICE_ITEM add constraint FK_ITEM_CONTAINS
   foreign key (INV_ID) references INVOICE (ID);

-- R10: EmployeeDriver -> Route (Is_Assigned_To)
alter table ROUTE add constraint FK_ROUTE_IS_ASSIGNED_TO
   foreign key (DRIVER_ID) references EMPLOYEE_DRIVER (ID);

-- R11: Vehicle -> Route (Uses)
alter table ROUTE add constraint FK_ROUTE_USES
   foreign key (VEHICLE_ID) references VEHICLE (ID);

-- R12: Warehouse -> Route (Dispatches)
alter table ROUTE add constraint FK_ROUTE_DISPATCHES
   foreign key (WAR_ID) references WAREHOUSE (ID);

-- R13: Invoice -> Delivery (Generates)
alter table DELIVERY add constraint FK_DELIVERY_GENERATES
   foreign key (INV_ID) references INVOICE (ID);

-- R14: EmployeeDriver -> Delivery (Delivers)
alter table DELIVERY add constraint FK_DELIVERY_DELIVERS
   foreign key (DRIVER_ID) references EMPLOYEE_DRIVER (ID);

-- R15: Client -> Delivery (Sent_By)
alter table DELIVERY add constraint FK_DELIVERY_SENT_BY
   foreign key (CLIENT_ID) references CLIENT (ID);

-- R16: Route -> Delivery (Belongs_To)
alter table DELIVERY add constraint FK_DELIVERY_BELONGS_TO
   foreign key (ROUTE_ID) references ROUTE (ID);

-- R17: Warehouse -> Delivery (Handles)
alter table DELIVERY add constraint FK_DELIVERY_HANDLES
   foreign key (WAR_ID) references WAREHOUSE (ID);

-- R18: Delivery -> Delivery_Tracking (Logs)
alter table DELIVERY_TRACKING add constraint FK_TRACKING_LOGS
   foreign key (DEL_ID) references DELIVERY (ID);

-- R19: EmployeeStaff -> Delivery_Tracking (Registers_Logs)
alter table DELIVERY_TRACKING add constraint FK_TRACKING_REGISTERS_LOGS
   foreign key (STAFF_ID) references EMPLOYEE_STAFF (ID);

-- R20: Warehouse -> Delivery_Tracking (Records_Logs)
alter table DELIVERY_TRACKING add constraint FK_TRACKING_RECORDS_LOGS
   foreign key (WAR_ID) references WAREHOUSE (ID);


-- FOR MongoDB:
-- /*==============================================================*/
-- /* Table: NOTIFICATION                                          */
-- /*==============================================================*/
-- create table NOTIFICATION (
--    NOTIFICATION_ID      SERIAL               not null,
--    ID                   INT4                 not null,
--    NOTIFICATION_TYPE    VARCHAR(20)          null,
--    RECIPIENT_CONTACT    VARCHAR(100)         null,
--    SUBJECT              VARCHAR(255)         null,
--    MESSAGE              TEXT                 null,
--    STATUS               VARCHAR(20)          null,
--    CREATED_AT           TIMESTAMPTZ          null,
--    ERROR_MESSAGE        TEXT                 null,
--    constraint PK_NOTIFICATION primary key (NOTIFICATION_ID)
-- );
