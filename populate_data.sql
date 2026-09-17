    /*==============================================================*/
    /* 1. "USER" — 7 rows: 1 admin, 2 clients, 2 drivers, 2 staff  */
    /*    Password for all: testpass123                             */
    /*==============================================================*/
    INSERT INTO "USER" (id, password, username, first_name, last_name, email, is_superuser, is_staff, is_active, last_login, created_at, contact, address, role, updated_at) VALUES
    (1, 'pbkdf2_sha256$1000000$B0pbeOll2M3egGRXS7DOE4$T/jjF5201VFh5aKYDxs6aii8A1iSSHeuxmOfI1Ceh7c=', 'ana.silva',      'Ana',    'Silva',    'ana.silva@email.com',    false, false, true, NULL, NOW(), '912000001', 'Rua das Flores 10, Lisboa',     'client',   NOW()),
    (2, 'pbkdf2_sha256$1000000$B0pbeOll2M3egGRXS7DOE4$T/jjF5201VFh5aKYDxs6aii8A1iSSHeuxmOfI1Ceh7c=', 'bruno.santos',   'Bruno',  'Santos',   'bruno.santos@email.com', false, false, true, NULL, NOW(), '912000002', 'Av. da Liberdade 55, Porto',    'client',   NOW()),
    (3, 'pbkdf2_sha256$1000000$B0pbeOll2M3egGRXS7DOE4$T/jjF5201VFh5aKYDxs6aii8A1iSSHeuxmOfI1Ceh7c=', 'carlos.ferreira','Carlos', 'Ferreira', 'carlos.f@email.com',     false, false, true, NULL, NOW(), '913000001', 'Rua do Carmo 22, Coimbra',      'driver',   NOW()),
    (4, 'pbkdf2_sha256$1000000$B0pbeOll2M3egGRXS7DOE4$T/jjF5201VFh5aKYDxs6aii8A1iSSHeuxmOfI1Ceh7c=', 'diana.costa',    'Diana',  'Costa',    'diana.costa@email.com',  false, false, true, NULL, NOW(), '913000002', 'Rua Augusta 100, Lisboa',       'driver',   NOW()),
    (5, 'pbkdf2_sha256$1000000$B0pbeOll2M3egGRXS7DOE4$T/jjF5201VFh5aKYDxs6aii8A1iSSHeuxmOfI1Ceh7c=', 'eduardo.lopes',  'Eduardo','Lopes',    'eduardo.l@email.com',    false, true,  true, NULL, NOW(), '914000001', 'Praça do Comércio 5, Lisboa',   'staff',    NOW()),
    (6, 'pbkdf2_sha256$1000000$B0pbeOll2M3egGRXS7DOE4$T/jjF5201VFh5aKYDxs6aii8A1iSSHeuxmOfI1Ceh7c=', 'filipa.mendes',  'Filipa', 'Mendes',   'filipa.m@email.com',     false, true,  true, NULL, NOW(), '914000002', 'Rua de Santa Catarina 8, Porto','staff',    NOW()),
    (7, 'pbkdf2_sha256$1000000$B0pbeOll2M3egGRXS7DOE4$T/jjF5201VFh5aKYDxs6aii8A1iSSHeuxmOfI1Ceh7c=', 'gabriel.rodrigues','Gabriel','Rodrigues','gabriel.r@email.com',   true,  true,  true, NULL, NOW(), '915000001', 'Rua do Ouro 30, Lisboa',        'admin',    NOW());
    -- Reset the serial sequence after raw SQL inserts
    SELECT setval(pg_get_serial_sequence('"USER"', 'id'), (SELECT MAX(id) FROM "USER"));


    /*==============================================================*/
    /* 2. CLIENT — 2 rows (shared PK with USER 1, 2)               */
    /*==============================================================*/
    INSERT INTO CLIENT (ID, TAX_ID) VALUES
    (1, 'PT123456789'),
    (2, 'PT987654321');

    /*==============================================================*/
    /* 3. WAREHOUSE — 2 rows                                        */
    /*==============================================================*/
    INSERT INTO WAREHOUSE (ID, NAME, CONTACT, ADDRESS, SCHEDULE_OPEN, SCHEDULE_CLOSE, SCHEDULE, MAXIMUM_STORAGE_CAPACITY, IS_ACTIVE, CREATED_AT, UPDATED_AT) VALUES
    (1, 'Armazém Central Lisboa', '210000001', 'Zona Industrial Alverca, Lote 12, Lisboa',  '06:00', '22:00', 'Mon-Sat', 5000, true, NOW(), NOW()),
    (2, 'Armazém Norte Porto',   '220000002', 'Parque Empresarial Maia, Nave 3, Porto',    '07:00', '20:00', 'Mon-Fri', 3000, true, NOW(), NOW());

    SELECT setval(pg_get_serial_sequence('warehouse', 'id'), (SELECT MAX(ID) FROM WAREHOUSE));


    /*==============================================================*/
    /* 4. EMPLOYEE — 4 rows (shared PK with USER 3,4,5,6)          */
    /*    2 will be drivers, 2 will be staff                        */
    /*==============================================================*/
    INSERT INTO EMPLOYEE (ID, WAR_ID, EMP_POSITION, SCHEDULE, WAGE, IS_ACTIVE, HIRE_DATE) VALUES
    (3, 1, 'driver',          '08:00-17:00 Mon-Fri', 1350.00, true, '2024-03-15'),
    (4, 2, 'driver',          '09:00-18:00 Mon-Fri', 1400.00, true, '2024-06-01'),
    (5, 1, 'staff',  '07:00-16:00 Mon-Fri', 1200.00, true, '2023-11-10'),
    (6, 2, 'staff',  '08:00-17:00 Mon-Sat', 1250.00, true, '2024-01-20');


    /*==============================================================*/
    /* 5. EMPLOYEE_DRIVER — 2 rows (shared PK with EMPLOYEE 3, 4)  */
    /*==============================================================*/
    INSERT INTO EMPLOYEE_DRIVER (ID, LICENSE_NUMBER, LICENSE_CATEGORY, LICENSE_EXPIRY_DATE, DRIVING_EXPERIENCE_YEARS, DRIVER_STATUS) VALUES
    (3, 'DL-2024-00123', 'C',  '2029-03-15', 8,  'available'),
    (4, 'DL-2024-00456', 'C',  '2028-06-01', 12, 'available');


    /*==============================================================*/
    /* 6. EMPLOYEE_STAFF — 2 rows (shared PK with EMPLOYEE 5, 6)   */
    /*==============================================================*/
    INSERT INTO EMPLOYEE_STAFF (ID, DEPARTMENT) VALUES
    (5, 'sorting'),
    (6, 'administration');


    /*==============================================================*/
    /* 7. VEHICLE — 2 rows                                          */
    /*==============================================================*/
    INSERT INTO VEHICLE (ID, VEHICLE_TYPE, PLATE_NUMBER, CAPACITY, BRAND, MODEL, VEHICLE_STATUS, YEAR, FUEL_TYPE, LAST_MAINTENANCE_DATE, IS_ACTIVE, CREATED_AT, UPDATED_AT) VALUES
    (1, 'van',   'AA-12-BB', 1500.00, 'Mercedes-Benz', 'Sprinter 314', 'available', 2023, 'diesel',   '2025-12-01', true, NOW(), NOW()),
    (2, 'truck', 'CC-34-DD', 5000.00, 'Volvo',         'FH 460',       'available', 2022, 'diesel',   '2025-11-15', true, NOW(), NOW());

    SELECT setval(pg_get_serial_sequence('vehicle', 'id'), (SELECT MAX(ID) FROM VEHICLE));


    /*==============================================================*/
    /* 8. INVOICE — 2 rows                                          */
    /*    FK → WAREHOUSE, EMPLOYEE_STAFF (as STAFF_ID), CLIENT      */
    /*==============================================================*/
    INSERT INTO INVOICE (ID, WAR_ID, STAFF_ID, CLIENT_ID, STATUS, TYPE, QUANTITY, COST, PAID, PAY_METHOD, NAME, ADDRESS, CONTACT, CREATED_AT, UPDATED_AT) VALUES
    (1, 1, 5, 1, 'completed', 'paid_on_send',     2, 30.00,  true,  'card',           'Ana Silva',    'Rua das Flores 10, Lisboa',  '912000001', NOW(), NOW()),
    (2, 2, 6, 2, 'pending',   'paid_on_delivery', 1, 32.00,  false, 'mobile_payment', 'Bruno Santos', 'Av. da Liberdade 55, Porto', '912000002', NOW(), NOW());

    SELECT setval(pg_get_serial_sequence('invoice', 'id'), (SELECT MAX(ID) FROM INVOICE));


    /*==============================================================*/
    /* 9. INVOICE_ITEM — 2 rows                                     */
    /*    FK → INVOICE                                              */
    /*==============================================================*/
    INSERT INTO INVOICE_ITEM (ID, INV_ID, SHIPMENT_TYPE, WEIGHT, DELIVERY_SPEED, QUANTITY, UNIT_PRICE, TOTAL_ITEM_COST, NOTES, CREATED_AT, UPDATED_AT) VALUES
    (1, 1, 'parcel',   2.50,  'standard', 2, 15.00, 30.00, 'Fragile - handle with care',  NOW(), NOW()),
    (2, 2, 'document', 0.30,  'express',  1, 32.00, 32.00, 'Urgent legal documents',      NOW(), NOW());

    SELECT setval(pg_get_serial_sequence('invoice_item', 'id'), (SELECT MAX(ID) FROM INVOICE_ITEM));


    /*==============================================================*/
    /* 10. ROUTE — 2 rows                                           */
    /*     FK → EMPLOYEE_DRIVER, VEHICLE, WAREHOUSE                 */
    /*==============================================================*/
    INSERT INTO ROUTE (ID, DRIVER_ID, VEHICLE_ID, WAR_ID, DESCRIPTION, DELIVERY_STATUS, DELIVERY_DATE, DELIVERY_START_TIME, DELIVERY_END_TIME, EXPECTED_DURATION, KMS_TRAVELLED, DRIVER_NOTES, IS_ACTIVE, CREATED_AT, UPDATED_AT) VALUES
    (1, 3, 1, 1, 'Lisboa Centro - Zona Sul',   'finished',   '2026-02-05', '2026-02-05 08:00:00+00', '2026-02-05 14:30:00+00', '06:30', 85.40,  'Traffic on A2 southbound',       true, NOW(), NOW()),
    (2, 4, 2, 2, 'Porto - Braga - Guimarães',  'on_going',   '2026-02-07', '2026-02-07 09:00:00+00', NULL,                     '05:00', NULL,   'Departure delayed 15 min (fog)', true, NOW(), NOW());

    SELECT setval(pg_get_serial_sequence('route', 'id'), (SELECT MAX(ID) FROM ROUTE));


    /*==============================================================*/
    /* 11. DELIVERY — 2 rows                                        */
    /*     FK → EMPLOYEE_DRIVER, ROUTE, INVOICE, CLIENT, WAREHOUSE  */
    /*==============================================================*/
    INSERT INTO DELIVERY (ID, DRIVER_ID, ROUTE_ID, INV_ID, CLIENT_ID, WAR_ID, TRACKING_NUMBER, DESCRIPTION, SENDER_NAME, SENDER_ADDRESS, SENDER_PHONE, SENDER_EMAIL, RECIPIENT_NAME, RECIPIENT_ADDRESS, RECIPIENT_PHONE, RECIPIENT_EMAIL, ITEM_TYPE, WEIGHT, DIMENSIONS, STATUS, PRIORITY, IN_TRANSITION, DELIVERY_DATE, CREATED_AT, UPDATED_AT) VALUES
    (1, 3, 1, 1, 1, 1, 'TRK-2026-000001', 'Electronics package', 'Ana Silva', 'Rua das Flores 10, Lisboa', '912000001', 'ana.silva@email.com', 'Maria Oliveira', 'Rua do Alecrim 40, Setúbal', '915000001', 'maria.o@email.com', 'parcel', 3, '30x20x15', 'completed',  'normal', false, '2026-02-05 14:00:00+00', NOW(), NOW()),
    (2, 4, 2, 2, 2, 2, 'TRK-2026-000002', 'Legal documents',     'Bruno Santos', 'Av. da Liberdade 55, Porto', '912000002', 'bruno.santos@email.com', 'João Pereira', 'Largo do Toural 12, Guimarães', '916000002', 'joao.p@email.com', 'document', 1, '35x25x5', 'in_transit', 'urgent', true, NULL, NOW(), NOW());

    SELECT setval(pg_get_serial_sequence('delivery', 'id'), (SELECT MAX(ID) FROM DELIVERY));


    /*==============================================================*/
    /* 12. DELIVERY_TRACKING — 2 rows                               */
    /*     FK → DELIVERY, EMPLOYEE_STAFF, WAREHOUSE                 */
    /*==============================================================*/
    INSERT INTO DELIVERY_TRACKING (ID, STAFF_ID, WAR_ID, DEL_ID, STATUS, NOTES, CREATED_AT) VALUES
    (1, 5, 1, 1, 'completed',   'Package delivered and signed by recipient',                      NOW()),
    (2, 6, 2, 2, 'in_transit',  'Departed Porto warehouse, next stop Braga sorting center',       NOW());

    SELECT setval(pg_get_serial_sequence('delivery_tracking', 'id'), (SELECT MAX(ID) FROM DELIVERY_TRACKING));


    /*==============================================================*/
    /* Summary:                                                     */
    /*   USER              = 7 rows (1 admin + 2 clients + 2 drivers + 2 staff) */
    /*   CLIENT            = 2 rows                                 */
    /*   WAREHOUSE         = 2 rows                                 */
    /*   EMPLOYEE          = 4 rows (2 drivers + 2 staff)           */
    /*   EMPLOYEE_DRIVER   = 2 rows                                 */
    /*   EMPLOYEE_STAFF    = 2 rows                                 */
    /*   VEHICLE           = 2 rows                                 */
    /*   INVOICE           = 2 rows                                 */
    /*   INVOICE_ITEM      = 2 rows                                 */
    /*   ROUTE             = 2 rows                                 */
    /*   DELIVERY          = 2 rows                                 */
    /*   DELIVERY_TRACKING = 2 rows                                 */
    /*                                                              */
    /*   Total: 29 rows across 12 tables                            */
    /*==============================================================*/
