-- Sample data for the refactored Post Office application
-- Automatically assigns IDs to avoid conflicts

-- -------------------------------------------------------------------------
-- USERS
-- -------------------------------------------------------------------------
INSERT INTO "PostOffice_App_user"
    (username, password, first_name, last_name, email, full_name,
     contact, address, tax_id, role,
     is_staff, is_superuser, is_active, date_joined, created_at, updated_at)
VALUES
    ('adminuser',
     'pbkdf2_sha256$260000$d1efc05cb8989bf667cc8cc5ef59fc58$U1d/CEFQ+3q0fs/6zdTZW7ck+VVeCzIbdPCtFnhPkJU=',
     'Admin', 'User', 'admin@example.com', 'Admin User', '912345678',
     'Admin Street', '111111111', 'admin',
     TRUE, TRUE, TRUE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    ('clientuser',
     'pbkdf2_sha256$260000$ddec894eb0962f566dea445f26c08d2a$uBUdpYyeB/zHMZh16IzYE3YaMdyUgBsAFbxPFlX9Ihc=',
     'Client', 'User', 'client@example.com', 'Client User', '912345679',
     'Client Street', '222222222', 'client',
     FALSE, FALSE, TRUE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    ('driveruser',
     'pbkdf2_sha256$260000$b90027de35d054c47a06b17265c13d85$5eXZjE9TKhF6QuB/aBz709wfwa/Ql39fgmhEbT9a/H8=',
     'Driver', 'User', 'driver@example.com', 'Driver User', '912345680',
     'Driver Street', '333333333', 'driver',
     FALSE, FALSE, TRUE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    ('staffuser',
     'pbkdf2_sha256$260000$e1209424fb48a7e3b1632a913b157e74$N0ImlO46O1ExY+dC2YyqrBy/QNjV6nzcVdgmFQyx0sQ=',
     'Staff', 'User', 'staff@example.com', 'Staff User', '912345681',
     'Staff Street', '444444444', 'staff',
     FALSE, FALSE, TRUE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    ('manageruser',
     'pbkdf2_sha256$260000$525349438fc22cc89959166ad21afd3a$eGuHuyvcuR319Ln/saf/SOsGfar0c/ApyP7cGkXNd5o=',
     'Manager', 'User', 'manager@example.com', 'Manager User', '912345682',
     'Manager Street', '555555555', 'manager',
     TRUE, FALSE, TRUE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);

-- -------------------------------------------------------------------------
-- EMPLOYEES
-- -------------------------------------------------------------------------
INSERT INTO "PostOffice_App_employee"
    (user_id, position, schedule, wage, is_active, hire_date)
VALUES
    ((SELECT id FROM "PostOffice_App_user" WHERE username='driveruser'), 'Driver', '08:00-16:00', 1500.00, TRUE, '2024-01-15'),
    ((SELECT id FROM "PostOffice_App_user" WHERE username='staffuser'),  'Staff',  '09:00-17:00', 1200.00, TRUE, '2023-11-20');

-- Driver details
INSERT INTO "PostOffice_App_employeedriver"
    (employee_id, license_number, license_category, license_expiry_date,
     driving_experience_years, driver_status)
VALUES
    ((SELECT id FROM "PostOffice_App_employee" WHERE position='Driver'), 'PT-45678901', 'C', '2026-12-31', 8, 'Available');

-- Staff details
INSERT INTO "PostOffice_App_employeestaff"
    (employee_id, department)
VALUES
    ((SELECT id FROM "PostOffice_App_employee" WHERE position='Staff'), 'Atendimento ao Cliente');

-- -------------------------------------------------------------------------
-- WAREHOUSES
-- -------------------------------------------------------------------------
INSERT INTO "PostOffice_App_warehouse"
    (name, address, contact, po_schedule_open, po_schedule_close, maximum_storage_capacity)
VALUES
    ('Armazém Central Lisboa', 'Zona Industrial de Alcântara, 1300-001 Lisboa', '211234567', '08:00:00', '18:00:00', 500),
    ('Depósito Porto Norte', 'Parque Industrial da Maia, 4425-001 Maia', '229876543', '09:00:00', '17:00:00', 300),
    ('Centro Logístico Coimbra', 'Zona Industrial Taveiro, 3045-001 Coimbra', '239456789', '07:30:00', '19:00:00', 400);

-- -------------------------------------------------------------------------
-- VEHICLES
-- -------------------------------------------------------------------------
INSERT INTO "PostOffice_App_vehicle"
    (vehicle_type, plate_number, capacity, brand, model, vehicle_status,
     year, fuel_type, last_maintenance_date)
VALUES
    ('Carrinha', 'AB-12-CD', 1200.0, 'Ford', 'Transit', 'Available', 2020, 'Diesel', '2024-06-01'),
    ('Camião',  'EF-34-GH', 5000.0, 'Mercedes', 'Actros', 'In Service', 2019, 'Diesel', '2024-05-15'),
    ('Carro',   'IJ-56-KL', 500.0, 'Renault', 'Kangoo Z.E.', 'Available', 2021, 'Eléctrico', '2024-04-20');

-- -------------------------------------------------------------------------
-- INVOICES
-- -------------------------------------------------------------------------
INSERT INTO "PostOffice_App_invoice"
    (user_id, invoice_status, invoice_type, quantity, invoice_datetime, cost, paid, payment_method, name, address, contact)
VALUES
    ((SELECT id FROM "PostOffice_App_user" WHERE username='clientuser'), 'Issued', 'Standard', 2, CURRENT_TIMESTAMP, 100.50, FALSE, 'Multibanco', 'Maria Santos', 'Av. da República, 45, 1050-001 Lisboa', '912345678'),
    ((SELECT id FROM "PostOffice_App_user" WHERE username='clientuser'), 'Paid',   'Premium',  1, CURRENT_TIMESTAMP, 200.75, TRUE,  'MB Way',      'Maria Santos', 'Av. da República, 45, 1050-001 Lisboa', '912345678'),
    (NULL, 'Pending','Standard', 3, CURRENT_TIMESTAMP, 50.00, FALSE, 'Numerário', 'Cliente Ocasional', 'N/D', '000000000');

-- -------------------------------------------------------------------------
-- INVOICE ITEMS
-- -------------------------------------------------------------------------
INSERT INTO "postoffice_app_invoice_items"
    (invoice_id, shipment_type, weight, delivery_speed, quantity, unit_price, notes)
VALUES
    ((SELECT id_invoice FROM "PostOffice_App_invoice" WHERE name='Maria Santos' AND invoice_status='Issued'), 'Encomenda Standard', 1.50, 'Normal', 2, 50.25, 'Livros técnicos'),
    ((SELECT id_invoice FROM "PostOffice_App_invoice" WHERE name='Maria Santos' AND invoice_status='Paid'), 'Encomenda Express', 2.00, 'Urgente', 1, 200.75, 'Documentação importante'),
    ((SELECT id_invoice FROM "PostOffice_App_invoice" WHERE name='Cliente Ocasional'), 'Carta Registada', 0.05, 'Normal', 3, 16.67, 'Correspondência');

-- -------------------------------------------------------------------------
-- ROUTES
-- -------------------------------------------------------------------------
INSERT INTO "PostOffice_App_route"
    (description, delivery_status, delivery_date, delivery_start_time,
     delivery_end_time, expected_duration, kms_travelled, driver_notes,
     driver_id, vehicle_id, origin_name, origin_address, origin_contact,
     destination_name, destination_address, destination_contact)
VALUES
    ('Rota manhã - Lisboa Centro', 'In Transit', CURRENT_DATE,
     '09:00:00', '12:00:00', '03:00:00', 45.0, '',
     (SELECT id FROM "PostOffice_App_employee" WHERE position='Driver'),
     (SELECT id FROM "PostOffice_App_vehicle" WHERE plate_number='AB-12-CD'),
     'Armazém Central Lisboa', 'Zona Industrial de Alcântara, 1300-001 Lisboa', '211234567',
     'Escritórios Avenida', 'Av. da Liberdade, 200, 1250-001 Lisboa', '213456789'),
    ('Rota tarde - Grande Porto', 'Pending', CURRENT_DATE + INTERVAL '1 day',
     '14:00:00', '17:00:00', '03:00:00', 60.0, '',
     (SELECT id FROM "PostOffice_App_employee" WHERE position='Driver'),
     (SELECT id FROM "PostOffice_App_vehicle" WHERE plate_number='EF-34-GH'),
     'Depósito Porto Norte', 'Parque Industrial da Maia, 4425-001 Maia', '229876543',
     'Empresa Gaia', 'Rua dos Mercadores, 89, 4400-001 Vila Nova de Gaia', '227654321');

-- -------------------------------------------------------------------------
-- DELIVERIES
-- -------------------------------------------------------------------------
INSERT INTO "PostOffice_App_delivery"
    (invoice_id, tracking_number, description, sender_name, sender_address,
     sender_phone, sender_email, recipient_name, recipient_address, recipient_phone,
     recipient_email, item_type, weight, dimensions, status, priority,
     registered_at, updated_at, in_transition, destination, delivery_date,
     driver_id, client_id, route_id)
VALUES
(
    (SELECT id_invoice FROM "PostOffice_App_invoice" WHERE name='Maria Santos' AND invoice_status='Issued'),
    'PT2025010001',
    'Livros técnicos',
    'Livraria Central',
    'Rua Augusta, 123, 1100-001 Lisboa',
    '213456789',
    'vendas@livrariacentral.pt',
    'Maria Santos',
    'Av. da República, 45, 1050-001 Lisboa',
    '912345678',
    'maria.santos@email.pt',
    'Encomenda',
    1500,
    '30x20x15',
    'In Transit',
    'normal',
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP,
    TRUE,
    'Av. da República, 45, 1050-001 Lisboa',
    CURRENT_DATE,
    (SELECT id FROM "PostOffice_App_employee" WHERE position='Driver'),
    (SELECT id FROM "PostOffice_App_user" WHERE username='clientuser'),
    (SELECT id FROM "PostOffice_App_route" WHERE description='Rota manhã - Lisboa Centro')
);