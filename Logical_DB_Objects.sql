/*==============================================================*/
/* rodrigo_objects.sql                                          */
/* Database Objects: Invoice (11) + InvoiceItem (4) +           */
/*                   Dashboard (3) + Vehicle (7) + Route (7)    */
/*                                                = 32 objects  */
/*                                                              */
/* Run order: Execute top-to-bottom in pgAdmin Query Tool.      */
/* All table/column names are unquoted lowercase except "USER". */
/*==============================================================*/

-- RODRIGO

/* ============================================================ */
/*                       F U N C T I O N S                      */
/* ============================================================ */


-- 1. fn_calculate_tax
-- Calculate tax amount for a given value. Default rate 23%.
CREATE OR REPLACE FUNCTION fn_calculate_tax(
    p_amount DECIMAL(10,2),
    p_rate   DECIMAL(5,4) DEFAULT 0.23
)
RETURNS DECIMAL(10,2)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN ROUND(p_amount * p_rate, 2);
END;
$$;


-- 2. fn_calculate_item_total
-- Pure calculation: quantity * unit_price.
CREATE OR REPLACE FUNCTION fn_calculate_item_total(
    p_quantity   INT,
    p_unit_price DECIMAL(10,2)
)
RETURNS DECIMAL(10,2)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN COALESCE(p_quantity, 0) * COALESCE(p_unit_price, 0.00);
END;
$$;


-- 3. fn_invoice_subtotal
-- Sum of all total_item_cost for a given invoice.
CREATE OR REPLACE FUNCTION fn_invoice_subtotal(p_invoice_id INT)
RETURNS DECIMAL(10,2)
LANGUAGE plpgsql
AS $$
DECLARE
    v_subtotal DECIMAL(10,2);
BEGIN
    SELECT COALESCE(SUM(total_item_cost), 0.00)
    INTO v_subtotal
    FROM invoice_item
    WHERE inv_id = p_invoice_id;

    RETURN v_subtotal;
END;
$$;


-- 4. fn_invoice_total
-- Subtotal + 23% tax for a given invoice.
-- Depends on: fn_invoice_subtotal, fn_calculate_tax
CREATE OR REPLACE FUNCTION fn_invoice_total(p_invoice_id INT)
RETURNS DECIMAL(10,2)
LANGUAGE plpgsql
AS $$
DECLARE
    v_subtotal DECIMAL(10,2);
BEGIN
    v_subtotal := fn_invoice_subtotal(p_invoice_id);
    RETURN ROUND(v_subtotal + fn_calculate_tax(v_subtotal), 2);
END;
$$;


-- 5. fn_is_valid_year
-- Check that a vehicle year is between 1900 and current year + 1.
CREATE OR REPLACE FUNCTION fn_is_valid_year(p_year INT)
RETURNS BOOLEAN
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN p_year IS NOT NULL
       AND p_year >= 1900
       AND p_year <= EXTRACT(YEAR FROM CURRENT_DATE)::INT + 1;
END;
$$;



/* ============================================================ */
/*                          V I E W S                           */
/* ============================================================ */


-- 6. v_invoices_with_items
-- Invoices joined with aggregated item counts and totals, plus warehouse/staff/client names.
CREATE OR REPLACE VIEW v_invoices_with_items AS
SELECT
    i.id,
    i.war_id,
    w.name                                              AS warehouse_name,
    i.staff_id,
    u_staff.first_name || ' ' || u_staff.last_name      AS staff_name,
    i.client_id,
    u_client.first_name || ' ' || u_client.last_name    AS client_name,
    i.status,
    i.type,
    i.quantity,
    i.cost,
    i.paid,
    i.pay_method,
    i.name,
    i.address,
    i.contact,
    i.created_at,
    i.updated_at,
    COALESCE(agg.item_count, 0)              AS item_count
FROM invoice i
LEFT JOIN warehouse w           ON w.id = i.war_id
LEFT JOIN employee_staff es     ON es.id = i.staff_id
LEFT JOIN "USER" u_staff        ON u_staff.id = es.id
LEFT JOIN client c              ON c.id = i.client_id
LEFT JOIN "USER" u_client       ON u_client.id = c.id
LEFT JOIN LATERAL (
    SELECT COUNT(*) AS item_count
    FROM invoice_item ii
    WHERE ii.inv_id = i.id
) agg ON true
ORDER BY i.created_at DESC;


-- 7. v_invoices_export
-- Flat view formatted for JSON/CSV export.
CREATE OR REPLACE VIEW v_invoices_export AS
SELECT
    i.id,
    i.war_id,
    i.staff_id,
    i.client_id,
    i.status,
    i.type,
    i.quantity,
    i.cost,
    i.paid,
    i.pay_method,
    i.name,
    i.address,
    i.contact,
    i.created_at,
    i.updated_at
FROM invoice i
ORDER BY i.id;


-- 8. v_vehicles_full
-- All vehicle data for list pages.
CREATE OR REPLACE VIEW v_vehicles_full AS
SELECT
    v.id,
    v.vehicle_type,
    v.plate_number,
    v.capacity,
    v.brand,
    v.model,
    v.vehicle_status,
    v.year,
    v.fuel_type,
    v.last_maintenance_date,
    v.is_active,
    v.created_at,
    v.updated_at
FROM vehicle v
ORDER BY v.id;


-- 9. v_vehicles_export
-- Flat view formatted for JSON/CSV export.
CREATE OR REPLACE VIEW v_vehicles_export AS
SELECT
    v.id,
    v.vehicle_type,
    v.plate_number,
    v.capacity,
    v.brand,
    v.model,
    v.vehicle_status,
    v.year,
    v.fuel_type,
    v.last_maintenance_date,
    v.is_active,
    v.created_at,
    v.updated_at
FROM vehicle v
ORDER BY v.id;


-- 10. v_routes_full
-- Routes joined with driver, vehicle, and warehouse info.
CREATE OR REPLACE VIEW v_routes_full AS
SELECT
    r.id,
    r.driver_id,
    u_driver.first_name || ' ' || u_driver.last_name AS driver_name,
    ed.license_number,
    ed.license_category,
    r.vehicle_id,
    v.plate_number,
    v.brand || ' ' || v.model                        AS vehicle_name,
    r.war_id,
    w.name                                            AS warehouse_name,
    r.description,
    r.delivery_status,
    r.delivery_date,
    r.delivery_start_time,
    r.delivery_end_time,
    r.expected_duration,
    r.kms_travelled,
    r.driver_notes,
    r.is_active,
    r.created_at,
    r.updated_at
FROM route r
LEFT JOIN employee_driver ed    ON ed.id = r.driver_id
LEFT JOIN "USER" u_driver       ON u_driver.id = ed.id
LEFT JOIN vehicle v             ON v.id = r.vehicle_id
LEFT JOIN warehouse w           ON w.id = r.war_id
ORDER BY r.delivery_date DESC NULLS LAST, r.id;


-- 11. v_routes_export
-- Flat view formatted for JSON/CSV export.
CREATE OR REPLACE VIEW v_routes_export AS
SELECT
    r.id,
    r.driver_id,
    r.vehicle_id,
    r.war_id,
    r.description,
    r.delivery_status,
    r.delivery_date,
    r.delivery_start_time,
    r.delivery_end_time,
    r.expected_duration,
    r.kms_travelled,
    r.driver_notes,
    r.is_active,
    r.created_at,
    r.updated_at
FROM route r
ORDER BY r.id;



-- 12. v_invoice_totals
-- Per-invoice cost (already includes tax via trigger), item count, and total quantity.
CREATE OR REPLACE VIEW v_invoice_totals AS
SELECT
    i.id                                    AS invoice_id,
    i.cost,
    i.quantity,
    COALESCE(agg.item_count, 0)             AS item_count
FROM invoice i
LEFT JOIN LATERAL (
    SELECT COUNT(*) AS item_count
    FROM invoice_item ii
    WHERE ii.inv_id = i.id
) agg ON true
ORDER BY i.id;


-- 13. v_dashboard_stats
-- Cached aggregate counts for the admin dashboard.
CREATE OR REPLACE VIEW v_dashboard_stats AS
SELECT
    (SELECT COUNT(*) FROM vehicle WHERE is_active = true)                                   AS total_vehicles,
    (SELECT COUNT(*) FROM delivery)                                                         AS total_deliveries,
    (SELECT COUNT(*) FROM "USER" WHERE role = 'client')                                     AS total_clients,
    (SELECT COUNT(*) FROM employee WHERE is_active = true)                                  AS total_employees,
    (SELECT COUNT(*) FROM route WHERE delivery_status NOT IN ('finished', 'cancelled'))     AS active_routes,
    (SELECT COUNT(*) FROM delivery WHERE status IN ('registered', 'ready', 'pending', 'in_transit'))    AS pending_deliveries,
    (SELECT COUNT(*) FROM invoice)                                                          AS total_invoices;

-- 14. fn_get_dashboard_stats
-- Returns role-specific dashboard data as key-value pairs.
-- Depends on: v_dashboard_stats
CREATE OR REPLACE FUNCTION fn_get_dashboard_stats(
    p_user_id INT,
    p_role    VARCHAR(20)
)
RETURNS TABLE (
    stat_name  TEXT,
    stat_value BIGINT
)
LANGUAGE plpgsql
AS $$
BEGIN
    IF p_role IN ('admin', 'manager') THEN
        RETURN QUERY
        SELECT 'total_vehicles'::TEXT,      ds.total_vehicles      FROM v_dashboard_stats ds
        UNION ALL
        SELECT 'total_deliveries'::TEXT,    ds.total_deliveries    FROM v_dashboard_stats ds
        UNION ALL
        SELECT 'total_clients'::TEXT,       ds.total_clients       FROM v_dashboard_stats ds
        UNION ALL
        SELECT 'total_employees'::TEXT,     ds.total_employees     FROM v_dashboard_stats ds
        UNION ALL
        SELECT 'active_routes'::TEXT,       ds.active_routes       FROM v_dashboard_stats ds
        UNION ALL
        SELECT 'pending_deliveries'::TEXT,  ds.pending_deliveries  FROM v_dashboard_stats ds
        UNION ALL
        SELECT 'total_invoices'::TEXT,      ds.total_invoices      FROM v_dashboard_stats ds;

    ELSIF p_role = 'driver' THEN
        RETURN QUERY
        SELECT 'my_deliveries'::TEXT, COUNT(*)::BIGINT
        FROM delivery
        WHERE driver_id = p_user_id;

    ELSIF p_role = 'client' THEN
        RETURN QUERY
        SELECT 'my_deliveries'::TEXT, COUNT(*)::BIGINT
        FROM delivery
        WHERE client_id = p_user_id;

    ELSE  -- staff or other
        RETURN QUERY
        SELECT 'total_deliveries'::TEXT, COUNT(*)::BIGINT
        FROM delivery;
    END IF;
END;
$$;



/* ============================================================ */
/*                       T R I G G E R S                        */
/* ============================================================ */


-- 15. trg_invoice_item_calc_total
-- BEFORE INSERT/UPDATE on invoice_item: auto-calculate total_item_cost = quantity * unit_price.
CREATE OR REPLACE FUNCTION fn_trg_invoice_item_calc_total()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.total_item_cost := fn_calculate_item_total(NEW.quantity, NEW.unit_price);
    NEW.updated_at      := NOW();
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_invoice_item_calc_total ON invoice_item;

CREATE TRIGGER trg_invoice_item_calc_total
    BEFORE INSERT OR UPDATE ON invoice_item
    FOR EACH ROW
    EXECUTE FUNCTION fn_trg_invoice_item_calc_total();


-- 16. trg_invoice_update_cost
-- AFTER INSERT/UPDATE/DELETE on invoice_item: recalculate the parent invoice cost and quantity.
CREATE OR REPLACE FUNCTION fn_trg_invoice_update_cost()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    v_inv_id INT;
BEGIN
    -- Determine which invoice was affected
    IF TG_OP = 'DELETE' THEN
        v_inv_id := OLD.inv_id;
    ELSE
        v_inv_id := NEW.inv_id;
    END IF;

    -- Recalculate invoice cost (subtotal + tax) and quantity using fn_invoice_total
    UPDATE invoice
    SET cost       = fn_invoice_total(v_inv_id),
        quantity   = (SELECT COALESCE(SUM(quantity), 0) FROM invoice_item WHERE inv_id = v_inv_id),
        updated_at = NOW()
    WHERE id = v_inv_id;

    RETURN NULL;  -- AFTER trigger, return value is ignored
END;
$$;

DROP TRIGGER IF EXISTS trg_invoice_update_cost ON invoice_item;

CREATE TRIGGER trg_invoice_update_cost
    AFTER INSERT OR UPDATE OR DELETE ON invoice_item
    FOR EACH ROW
    EXECUTE FUNCTION fn_trg_invoice_update_cost();


-- 17. trg_invoice_soft_delete
-- BEFORE DELETE on invoice: set status='cancelled' instead of hard-deleting.
CREATE OR REPLACE FUNCTION fn_trg_invoice_soft_delete()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    UPDATE invoice
    SET status     = 'cancelled',
        updated_at = NOW()
    WHERE id = OLD.id;

    -- Cancel the DELETE so the row stays in the table
    RETURN NULL;
END;
$$;

DROP TRIGGER IF EXISTS trg_invoice_soft_delete ON invoice;

CREATE TRIGGER trg_invoice_soft_delete
    BEFORE DELETE ON invoice
    FOR EACH ROW
    EXECUTE FUNCTION fn_trg_invoice_soft_delete();


-- 18. trg_route_time_check
-- BEFORE INSERT/UPDATE on route: ensure delivery_end_time > delivery_start_time (when both set).
CREATE OR REPLACE FUNCTION fn_trg_route_time_check()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF NEW.delivery_start_time IS NOT NULL
       AND NEW.delivery_end_time IS NOT NULL
       AND NEW.delivery_end_time <= NEW.delivery_start_time
    THEN
        RAISE EXCEPTION 'Route end time (%) must be after start time (%)',
            NEW.delivery_end_time, NEW.delivery_start_time;
    END IF;

    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_route_time_check ON route;

CREATE TRIGGER trg_route_time_check
    BEFORE INSERT OR UPDATE ON route
    FOR EACH ROW
    EXECUTE FUNCTION fn_trg_route_time_check();



/* ============================================================ */
/*                     P R O C E D U R E S                      */
/* ============================================================ */


/* ---------- INVOICE ---------- */

-- 19. sp_create_invoice
-- Create a new invoice header row.
CREATE OR REPLACE PROCEDURE sp_create_invoice(
    p_war_id        INT,
    p_staff_id      INT,
    p_client_id     INT,
    p_status        VARCHAR(30),
    p_type          VARCHAR(30),
    p_quantity      INT,
    p_cost          DECIMAL(10,2),
    p_paid          BOOL,
    p_pay_method    VARCHAR(30),
    p_name          TEXT,
    p_address       TEXT,
    p_contact       TEXT,
    INOUT p_id      INT DEFAULT NULL
)
LANGUAGE plpgsql
AS $$
BEGIN
    INSERT INTO invoice (
        war_id, staff_id, client_id,
        status, type, quantity, cost,
        paid, pay_method,
        name, address, contact,
        created_at, updated_at
    ) VALUES (
        p_war_id, p_staff_id, p_client_id,
        COALESCE(p_status, 'pending'), p_type, p_quantity, COALESCE(p_cost, 0.00),
        COALESCE(p_paid, false), p_pay_method,
        p_name, p_address, p_contact,
        NOW(), NOW()
    )
    RETURNING id INTO p_id;
END;
$$;


-- 20. sp_update_invoice
-- Update an existing invoice's mutable fields.
CREATE OR REPLACE PROCEDURE sp_update_invoice(
    p_id            INT,
    p_war_id        INT         DEFAULT NULL,
    p_staff_id      INT         DEFAULT NULL,
    p_client_id     INT         DEFAULT NULL,
    p_status        VARCHAR(30) DEFAULT NULL,
    p_type          VARCHAR(30) DEFAULT NULL,
    p_quantity      INT         DEFAULT NULL,
    p_cost          DECIMAL(10,2) DEFAULT NULL,
    p_paid          BOOL        DEFAULT NULL,
    p_pay_method    VARCHAR(30) DEFAULT NULL,
    p_name          TEXT        DEFAULT NULL,
    p_address       TEXT        DEFAULT NULL,
    p_contact       TEXT        DEFAULT NULL
)
LANGUAGE plpgsql
AS $$
BEGIN
    UPDATE invoice
    SET war_id      = COALESCE(p_war_id,     war_id),
        staff_id    = COALESCE(p_staff_id,   staff_id),
        client_id   = COALESCE(p_client_id,  client_id),
        status      = COALESCE(p_status,     status),
        type        = COALESCE(p_type,       type),
        quantity    = COALESCE(p_quantity,    quantity),
        cost        = COALESCE(p_cost,       cost),
        paid        = COALESCE(p_paid,       paid),
        pay_method  = COALESCE(p_pay_method, pay_method),
        name        = COALESCE(p_name,       name),
        address     = COALESCE(p_address,    address),
        contact     = COALESCE(p_contact,    contact),
        updated_at  = NOW()
    WHERE id = p_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Invoice with id % not found', p_id;
    END IF;
END;
$$;


-- 21. sp_delete_invoice
-- Soft-delete an invoice (triggers trg_invoice_soft_delete).
CREATE OR REPLACE PROCEDURE sp_delete_invoice(p_id INT)
LANGUAGE plpgsql
AS $$
BEGIN
    -- The BEFORE DELETE trigger converts this into a soft delete
    DELETE FROM invoice WHERE id = p_id;

    -- After the trigger fires, the row still exists — verify the status was set
    IF NOT EXISTS (SELECT 1 FROM invoice WHERE id = p_id AND status = 'cancelled') THEN
        RAISE EXCEPTION 'Invoice with id % not found', p_id;
    END IF;
END;
$$;


-- 22. sp_import_invoices
-- Bulk-import invoices (with optional nested items) from a JSONB array.
CREATE OR REPLACE PROCEDURE sp_import_invoices(p_data JSONB)
LANGUAGE plpgsql
AS $$
DECLARE
    v_rec       JSONB;
    v_item      JSONB;
    v_inv_id    INT;
BEGIN
    FOR v_rec IN SELECT jsonb_array_elements(p_data)
    LOOP
        INSERT INTO invoice (
            war_id, staff_id, client_id,
            status, type, quantity, cost,
            paid, pay_method,
            name, address, contact,
            created_at, updated_at
        ) VALUES (
            (v_rec->>'war_id')::INT,
            (v_rec->>'staff_id')::INT,
            (v_rec->>'client_id')::INT,
            COALESCE(v_rec->>'status', 'pending'),
            v_rec->>'type',
            (v_rec->>'quantity')::INT,
            COALESCE((v_rec->>'cost')::DECIMAL, 0.00),
            COALESCE((v_rec->>'paid')::BOOL, false),
            v_rec->>'pay_method',
            v_rec->>'name',
            v_rec->>'address',
            v_rec->>'contact',
            NOW(), NOW()
        )
        RETURNING id INTO v_inv_id;

        -- If the JSON object has an "items" array, import each item too
        IF v_rec ? 'items' AND jsonb_typeof(v_rec->'items') = 'array' THEN
            FOR v_item IN SELECT jsonb_array_elements(v_rec->'items')
            LOOP
                INSERT INTO invoice_item (
                    inv_id, shipment_type, weight, delivery_speed,
                    quantity, unit_price, total_item_cost,
                    notes, created_at, updated_at
                ) VALUES (
                    v_inv_id,
                    v_item->>'shipment_type',
                    (v_item->>'weight')::DECIMAL,
                    v_item->>'delivery_speed',
                    (v_item->>'quantity')::INT,
                    (v_item->>'unit_price')::DECIMAL,
                    COALESCE((v_item->>'quantity')::INT, 0) * COALESCE((v_item->>'unit_price')::DECIMAL, 0),
                    v_item->>'notes',
                    NOW(), NOW()
                );
            END LOOP;
        END IF;
    END LOOP;
END;
$$;


/* ---------- INVOICE ITEM ---------- */

-- 23. sp_add_invoice_item
-- Add a single item to an invoice.
-- The trigger will auto-calculate total_item_cost and update the invoice cost.
CREATE OR REPLACE PROCEDURE sp_add_invoice_item(
    p_inv_id          INT,
    p_shipment_type   VARCHAR(50),
    p_weight          DECIMAL(10,2),
    p_delivery_speed  VARCHAR(50),
    p_quantity        INT,
    p_unit_price      DECIMAL(10,2),
    p_notes           TEXT DEFAULT NULL,
    INOUT p_id        INT DEFAULT NULL
)
LANGUAGE plpgsql
AS $$
BEGIN
    -- Validate that the parent invoice exists
    IF NOT EXISTS (SELECT 1 FROM invoice WHERE id = p_inv_id) THEN
        RAISE EXCEPTION 'Invoice with id % not found', p_inv_id;
    END IF;

    INSERT INTO invoice_item (
        inv_id, shipment_type, weight, delivery_speed,
        quantity, unit_price,
        notes, created_at, updated_at
    ) VALUES (
        p_inv_id, p_shipment_type, p_weight, p_delivery_speed,
        p_quantity, p_unit_price,
        p_notes, NOW(), NOW()
    )
    RETURNING id INTO p_id;

    -- total_item_cost is set by trg_invoice_item_calc_total
    -- invoice.cost is recalculated by trg_invoice_update_cost
END;
$$;


/* ---------- VEHICLE ---------- */

-- 24. sp_create_vehicle
-- Create a new vehicle with validation.
CREATE OR REPLACE PROCEDURE sp_create_vehicle(
    p_vehicle_type          VARCHAR(50),
    p_plate_number          VARCHAR(20),
    p_capacity              DECIMAL(10,2),
    p_brand                 VARCHAR(50),
    p_model                 VARCHAR(50),
    p_vehicle_status        VARCHAR(20),
    p_year                  INT,
    p_fuel_type             VARCHAR(30),
    p_last_maintenance_date DATE DEFAULT NULL,
    INOUT p_id              INT DEFAULT NULL
)
LANGUAGE plpgsql
AS $$
BEGIN
    -- Validate year
    IF NOT fn_is_valid_year(p_year) THEN
        RAISE EXCEPTION 'Invalid year: %. Must be between 1900 and %.', p_year, EXTRACT(YEAR FROM CURRENT_DATE)::INT + 1;
    END IF;

    INSERT INTO vehicle (
        vehicle_type, plate_number, capacity,
        brand, model, vehicle_status,
        year, fuel_type, last_maintenance_date,
        is_active, created_at, updated_at
    ) VALUES (
        p_vehicle_type, p_plate_number, p_capacity,
        p_brand, p_model, COALESCE(p_vehicle_status, 'available'),
        p_year, p_fuel_type, p_last_maintenance_date,
        true, NOW(), NOW()
    )
    RETURNING id INTO p_id;
END;
$$;


-- 25. sp_update_vehicle
-- Update an existing vehicle's mutable fields.
CREATE OR REPLACE PROCEDURE sp_update_vehicle(
    p_id                     INT,
    p_vehicle_type           VARCHAR(50)    DEFAULT NULL,
    p_plate_number           VARCHAR(20)    DEFAULT NULL,
    p_capacity               DECIMAL(10,2)  DEFAULT NULL,
    p_brand                  VARCHAR(50)    DEFAULT NULL,
    p_model                  VARCHAR(50)    DEFAULT NULL,
    p_vehicle_status         VARCHAR(20)    DEFAULT NULL,
    p_year                   INT            DEFAULT NULL,
    p_fuel_type              VARCHAR(30)    DEFAULT NULL,
    p_last_maintenance_date  DATE           DEFAULT NULL,
    p_is_active              BOOL           DEFAULT NULL
)
LANGUAGE plpgsql
AS $$
BEGIN
    -- Validate year if provided
    IF p_year IS NOT NULL AND NOT fn_is_valid_year(p_year) THEN
        RAISE EXCEPTION 'Invalid year: %. Must be between 1900 and %.', p_year, EXTRACT(YEAR FROM CURRENT_DATE)::INT + 1;
    END IF;

    UPDATE vehicle
    SET vehicle_type          = COALESCE(p_vehicle_type,          vehicle_type),
        plate_number          = COALESCE(p_plate_number,          plate_number),
        capacity              = COALESCE(p_capacity,              capacity),
        brand                 = COALESCE(p_brand,                 brand),
        model                 = COALESCE(p_model,                 model),
        vehicle_status        = COALESCE(p_vehicle_status,        vehicle_status),
        year                  = COALESCE(p_year,                  year),
        fuel_type             = COALESCE(p_fuel_type,             fuel_type),
        last_maintenance_date = COALESCE(p_last_maintenance_date, last_maintenance_date),
        is_active             = COALESCE(p_is_active,             is_active),
        updated_at            = NOW()
    WHERE id = p_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Vehicle with id % not found', p_id;
    END IF;
END;
$$;


-- 26. sp_delete_vehicle
-- Delete a vehicle. Prevents deletion if assigned to active routes.
CREATE OR REPLACE PROCEDURE sp_delete_vehicle(p_id INT)
LANGUAGE plpgsql
AS $$
BEGIN
    -- Check for active routes using this vehicle
    IF EXISTS (
        SELECT 1 FROM route
        WHERE vehicle_id = p_id
          AND delivery_status IN ('not_started', 'on_going')
    ) THEN
        RAISE EXCEPTION 'Cannot delete vehicle %: it is assigned to active routes.', p_id;
    END IF;

    DELETE FROM vehicle WHERE id = p_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Vehicle with id % not found', p_id;
    END IF;
END;
$$;


-- 27. sp_import_vehicles
-- Bulk-import vehicles from a JSONB array.
-- Depends on: fn_is_valid_year (year validation, same as sp_create_vehicle)
CREATE OR REPLACE PROCEDURE sp_import_vehicles(p_data JSONB)
LANGUAGE plpgsql
AS $$
DECLARE
    v_rec  JSONB;
    v_year INT;
BEGIN
    FOR v_rec IN SELECT jsonb_array_elements(p_data)
    LOOP
        v_year := (v_rec->>'year')::INT;

        -- Validate year (consistent with sp_create_vehicle)
        IF NOT fn_is_valid_year(v_year) THEN
            RAISE EXCEPTION 'Invalid year: %. Must be between 1900 and %.', v_year, EXTRACT(YEAR FROM CURRENT_DATE)::INT + 1;
        END IF;

        INSERT INTO vehicle (
            vehicle_type, plate_number, capacity,
            brand, model, vehicle_status,
            year, fuel_type, last_maintenance_date,
            is_active, created_at, updated_at
        ) VALUES (
            v_rec->>'vehicle_type',
            v_rec->>'plate_number',
            (v_rec->>'capacity')::DECIMAL,
            v_rec->>'brand',
            v_rec->>'model',
            COALESCE(v_rec->>'vehicle_status', 'available'),
            v_year,
            v_rec->>'fuel_type',
            (v_rec->>'last_maintenance_date')::DATE,
            COALESCE((v_rec->>'is_active')::BOOL, true),
            NOW(), NOW()
        );
    END LOOP;
END;
$$;


/* ---------- ROUTE ---------- */

-- 28. sp_create_route
-- Create a new route.
CREATE OR REPLACE PROCEDURE sp_create_route(
    p_driver_id           INT,
    p_vehicle_id          INT,
    p_war_id              INT,
    p_description         TEXT,
    p_delivery_status     VARCHAR(20),
    p_delivery_date       DATE,
    p_delivery_start_time TIMESTAMPTZ DEFAULT NULL,
    p_delivery_end_time   TIMESTAMPTZ DEFAULT NULL,
    p_expected_duration   TIME        DEFAULT NULL,
    p_kms_travelled       DECIMAL(8,2) DEFAULT NULL,
    p_driver_notes        TEXT        DEFAULT NULL,
    INOUT p_id            INT         DEFAULT NULL
)
LANGUAGE plpgsql
AS $$
BEGIN
    INSERT INTO route (
        driver_id, vehicle_id, war_id,
        description, delivery_status,
        delivery_date, delivery_start_time, delivery_end_time,
        expected_duration, kms_travelled, driver_notes,
        is_active, created_at, updated_at
    ) VALUES (
        p_driver_id, p_vehicle_id, p_war_id,
        p_description, COALESCE(p_delivery_status, 'not_started'),
        p_delivery_date, p_delivery_start_time, p_delivery_end_time,
        p_expected_duration, p_kms_travelled, p_driver_notes,
        true, NOW(), NOW()
    )
    RETURNING id INTO p_id;

    -- trg_route_time_check validates start/end times automatically
END;
$$;


-- 29. sp_update_route
-- Update an existing route's mutable fields.
CREATE OR REPLACE PROCEDURE sp_update_route(
    p_id                   INT,
    p_driver_id            INT            DEFAULT NULL,
    p_vehicle_id           INT            DEFAULT NULL,
    p_war_id               INT            DEFAULT NULL,
    p_description          TEXT           DEFAULT NULL,
    p_delivery_status      VARCHAR(20)    DEFAULT NULL,
    p_delivery_date        DATE           DEFAULT NULL,
    p_delivery_start_time  TIMESTAMPTZ    DEFAULT NULL,
    p_delivery_end_time    TIMESTAMPTZ    DEFAULT NULL,
    p_expected_duration    TIME           DEFAULT NULL,
    p_kms_travelled        DECIMAL(8,2)   DEFAULT NULL,
    p_driver_notes         TEXT           DEFAULT NULL,
    p_is_active            BOOL           DEFAULT NULL
)
LANGUAGE plpgsql
AS $$
BEGIN
    UPDATE route
    SET driver_id           = COALESCE(p_driver_id,           driver_id),
        vehicle_id          = COALESCE(p_vehicle_id,          vehicle_id),
        war_id              = COALESCE(p_war_id,              war_id),
        description         = COALESCE(p_description,         description),
        delivery_status     = COALESCE(p_delivery_status,     delivery_status),
        delivery_date       = COALESCE(p_delivery_date,       delivery_date),
        delivery_start_time = COALESCE(p_delivery_start_time, delivery_start_time),
        delivery_end_time   = COALESCE(p_delivery_end_time,   delivery_end_time),
        expected_duration   = COALESCE(p_expected_duration,   expected_duration),
        kms_travelled       = COALESCE(p_kms_travelled,       kms_travelled),
        driver_notes        = COALESCE(p_driver_notes,        driver_notes),
        is_active           = COALESCE(p_is_active,           is_active),
        updated_at          = NOW()
    WHERE id = p_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Route with id % not found', p_id;
    END IF;

    -- trg_route_time_check validates start/end times automatically
END;
$$;


-- 30. sp_delete_route
-- Delete a route. Prevents deletion if it has active deliveries.
CREATE OR REPLACE PROCEDURE sp_delete_route(p_id INT)
LANGUAGE plpgsql
AS $$
BEGIN
    -- Check for active deliveries on this route
    IF EXISTS (
        SELECT 1 FROM delivery
        WHERE route_id = p_id
          AND status NOT IN ('completed', 'cancelled')
    ) THEN
        RAISE EXCEPTION 'Cannot delete route %: it has active deliveries.', p_id;
    END IF;

    DELETE FROM route WHERE id = p_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Route with id % not found', p_id;
    END IF;
END;
$$;


-- 31. sp_import_routes
-- Bulk-import routes from a JSONB array.
CREATE OR REPLACE PROCEDURE sp_import_routes(p_data JSONB)
LANGUAGE plpgsql
AS $$
DECLARE
    v_rec JSONB;
BEGIN
    FOR v_rec IN SELECT jsonb_array_elements(p_data)
    LOOP
        INSERT INTO route (
            driver_id, vehicle_id, war_id,
            description, delivery_status,
            delivery_date, delivery_start_time, delivery_end_time,
            expected_duration, kms_travelled, driver_notes,
            is_active, created_at, updated_at
        ) VALUES (
            (v_rec->>'driver_id')::INT,
            (v_rec->>'vehicle_id')::INT,
            (v_rec->>'war_id')::INT,
            v_rec->>'description',
            COALESCE(v_rec->>'delivery_status', 'not_started'),
            (v_rec->>'delivery_date')::DATE,
            (v_rec->>'delivery_start_time')::TIMESTAMPTZ,
            (v_rec->>'delivery_end_time')::TIMESTAMPTZ,
            (v_rec->>'expected_duration')::TIME,
            (v_rec->>'kms_travelled')::DECIMAL,
            v_rec->>'driver_notes',
            COALESCE((v_rec->>'is_active')::BOOL, true),
            NOW(), NOW()
        );
    END LOOP;
END;
$$;



-- DIEGO

/*==============================================================*/
/* diego_objects.sql                                            */
/* Database Objects: User (5) + Employee (5) +                  */
/*                   EmployeeDriver (2) + EmployeeStaff (1) +   */
/*                   Warehouse (7)                              */
/*                                                = 20 objects  */
/*                                                              */
/* Run order: Execute top-to-bottom in pgAdmin Query Tool.      */
/* All table/column names are unquoted lowercase except "USER". */
/*==============================================================*/


/* ============================================================ */
/*                       F U N C T I O N S                      */
/* ============================================================ */

CREATE OR REPLACE FUNCTION export_warehouses_csv()
RETURNS TABLE (
    id INT,
    name TEXT,
    contact TEXT,
    address TEXT,
    schedule_open TIME,
    schedule_close TIME,
    schedule TEXT,
    maximum_storage_capacity INT,
    is_active BOOLEAN,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
)
LANGUAGE sql
AS $$
    SELECT
        id,
        name,
        contact,
        address,
        schedule_open,
        schedule_close,
        schedule,
        maximum_storage_capacity,
        is_active,
        created_at,
        updated_at
    FROM v_warehouses_export
    ORDER BY id;
$$;

-- 1. fn_is_license_valid  [EmployeeDriver]
-- Check if a driver license has not expired.
CREATE OR REPLACE FUNCTION fn_is_license_valid(p_expiry_date DATE)
RETURNS BOOLEAN
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN p_expiry_date IS NOT NULL AND p_expiry_date > CURRENT_DATE;
END;
$$;



/* ============================================================ */
/*                          V I E W S                           */
/* ============================================================ */


-- 2. v_clients  [User]
-- All users with role='client', joined with client table for tax_id.
CREATE OR REPLACE VIEW v_clients AS
SELECT
    u.id,
    u.username,
    u.email,
    u.first_name,
    u.last_name,
    u.first_name || ' ' || u.last_name  AS full_name,
    u.contact,
    u.address,
    u.role,
    u.is_active,
    u.created_at,
    u.updated_at,
    c.tax_id
FROM "USER" u
JOIN client c ON c.id = u.id
WHERE u.role = 'client'
ORDER BY u.first_name, u.last_name;


-- 3. v_potential_employees  [User]
-- Users eligible to become employees (not admin/client, not already an employee).
CREATE OR REPLACE VIEW v_potential_employees AS
SELECT
    u.id,
    u.username,
    u.email,
    u.first_name,
    u.last_name,
    u.first_name || ' ' || u.last_name  AS full_name,
    u.contact,
    u.address,
    u.role,
    u.is_active,
    u.created_at
FROM "USER" u
WHERE u.role NOT IN ('admin', 'client')
  AND u.is_active = true
  AND NOT EXISTS (SELECT 1 FROM employee e WHERE e.id = u.id)
ORDER BY u.first_name, u.last_name;


-- 4. v_employees_full  [Employee]
-- Employees joined with user info, driver info, and staff info.
-- All joins use shared-PK (id = id).
CREATE OR REPLACE VIEW v_employees_full AS
SELECT
    e.id,
    e.emp_position,
    e.schedule,
    e.wage,
    e.is_active,
    e.hire_date,
    e.war_id,
    w.name                                  AS warehouse_name,
    u.username,
    u.email,
    u.first_name,
    u.last_name,
    u.first_name || ' ' || u.last_name     AS full_name,
    u.contact,
    u.address,
    u.role,
    -- Driver info (NULL if not driver)
    ed.license_number,
    ed.license_category,
    ed.license_expiry_date,
    ed.driving_experience_years,
    ed.driver_status,
    -- Staff info (NULL if not staff)
    es.department
FROM employee e
JOIN "USER" u               ON u.id  = e.id        -- shared PK
LEFT JOIN employee_driver ed ON ed.id = e.id        -- shared PK
LEFT JOIN employee_staff es  ON es.id = e.id        -- shared PK
LEFT JOIN warehouse w        ON w.id  = e.war_id
WHERE e.is_active = true
ORDER BY u.first_name, u.last_name;


-- 5. v_warehouses_full  [Warehouse]
-- All warehouse data with employee count for list pages.
CREATE OR REPLACE VIEW v_warehouses_full AS
SELECT
    w.id,
    w.name,
    w.contact,
    w.address,
    w.schedule_open,
    w.schedule_close,
    w.schedule,
    w.maximum_storage_capacity,
    w.is_active,
    w.created_at,
    w.updated_at,
    COALESCE(emp_count.cnt, 0)  AS employee_count
FROM warehouse w
LEFT JOIN LATERAL (
    SELECT COUNT(*) AS cnt
    FROM employee e
    WHERE e.war_id = w.id AND e.is_active = true
) emp_count ON true
ORDER BY w.name;


-- 6. v_warehouses_export  [Warehouse]
-- Flat view formatted for JSON/CSV export.
CREATE OR REPLACE VIEW v_warehouses_export AS
SELECT
    w.id,
    w.name,
    w.contact,
    w.address,
    w.schedule_open,
    w.schedule_close,
    w.schedule,
    w.maximum_storage_capacity,
    w.is_active,
    w.created_at,
    w.updated_at
FROM warehouse w
ORDER BY w.id;



-- 7. v_users_admin  [User]
-- Simplified administrative view of system users.
-- Exposes core identification and status fields for admin dashboards
-- and user management pages (read-only).
CREATE OR REPLACE VIEW v_users_admin AS
SELECT
    id,
    username,
    email,
    role,
    is_active,
    created_at
FROM "USER"
ORDER BY username;



/* ============================================================ */
/*                       T R I G G E R S                        */
/* ============================================================ */


-- 7. trg_employee_sync_user_role  [Employee]
-- AFTER INSERT/UPDATE OF emp_position on employee:
-- auto-update "USER".role to match the employee position.
CREATE OR REPLACE FUNCTION fn_sync_employee_user_role()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF NEW.emp_position = 'driver' THEN
        UPDATE "USER"
        SET role = 'driver', updated_at = NOW()
        WHERE id = NEW.id;
    ELSIF NEW.emp_position = 'staff' THEN
        UPDATE "USER"
        SET role = 'staff', updated_at = NOW()
        WHERE id = NEW.id;
    END IF;

    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_employee_sync_user_role ON employee;

CREATE TRIGGER trg_employee_sync_user_role
    AFTER INSERT OR UPDATE OF emp_position ON employee
    FOR EACH ROW
    EXECUTE FUNCTION fn_sync_employee_user_role();


-- 8. trg_warehouse_schedule_check  [Warehouse]
-- BEFORE INSERT/UPDATE on warehouse: ensure schedule_close > schedule_open (when both set).
CREATE OR REPLACE FUNCTION fn_trg_warehouse_schedule_check()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF NEW.schedule_open IS NOT NULL
       AND NEW.schedule_close IS NOT NULL
       AND NEW.schedule_close <= NEW.schedule_open
    THEN
        RAISE EXCEPTION 'Warehouse close time (%) must be after open time (%)',
            NEW.schedule_close, NEW.schedule_open;
    END IF;

    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_warehouse_schedule_check ON warehouse;

CREATE TRIGGER trg_warehouse_schedule_check
    BEFORE INSERT OR UPDATE ON warehouse
    FOR EACH ROW
    EXECUTE FUNCTION fn_trg_warehouse_schedule_check();



/* ============================================================ */
/*                     P R O C E D U R E S                      */
/* ============================================================ */


/* ---------- USER ---------- */

-- 9. sp_create_user  [User]
-- Create a new user. Password must be pre-hashed by Django (make_password).
-- If role is 'client', also creates the client record.
CREATE OR REPLACE PROCEDURE sp_create_user(
    p_username      VARCHAR(150),
    p_email         VARCHAR(254),
    p_password      VARCHAR(128),
    p_first_name    VARCHAR(150),
    p_last_name     VARCHAR(150),
    p_contact       VARCHAR(20),
    p_address       VARCHAR(255),
    p_role          VARCHAR(20) DEFAULT 'client',
    INOUT p_id      INT DEFAULT NULL
)
LANGUAGE plpgsql
AS $$
BEGIN
    INSERT INTO "USER" (
        username, email, password, first_name, last_name,
        contact, address, role,
        is_superuser, is_staff, is_active, created_at, updated_at
    ) VALUES (
        p_username, p_email, p_password, p_first_name, p_last_name,
        p_contact, p_address, COALESCE(p_role, 'client'),
        FALSE, FALSE, TRUE, NOW(), NOW()
    )
    RETURNING id INTO p_id;

    -- If role is client, create the client record (shared PK)
    IF COALESCE(p_role, 'client') = 'client' THEN
        INSERT INTO client (id, tax_id) VALUES (p_id, NULL);
    END IF;
END;
$$;


-- 10. sp_update_user  [User]
-- Update a user's profile fields. Does NOT update password (use Django for that).
CREATE OR REPLACE PROCEDURE sp_update_user(
    p_id            INT,
    p_email         VARCHAR(254)  DEFAULT NULL,
    p_first_name    VARCHAR(150)  DEFAULT NULL,
    p_last_name     VARCHAR(150)  DEFAULT NULL,
    p_contact       VARCHAR(20)   DEFAULT NULL,
    p_address       VARCHAR(255)  DEFAULT NULL,
    p_role          VARCHAR(20)   DEFAULT NULL,
    p_is_active     BOOL          DEFAULT NULL
)
LANGUAGE plpgsql
AS $$
BEGIN
    UPDATE "USER"
    SET email      = COALESCE(p_email,      email),
        first_name = COALESCE(p_first_name, first_name),
        last_name  = COALESCE(p_last_name,  last_name),
        contact    = COALESCE(p_contact,    contact),
        address    = COALESCE(p_address,    address),
        role       = COALESCE(p_role,       role),
        is_active  = COALESCE(p_is_active,  is_active),
        updated_at = NOW()
    WHERE id = p_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'User with id % not found', p_id;
    END IF;
END;
$$;


-- 11. sp_delete_user  [User]
-- Soft-delete a user (set is_active = false).
CREATE OR REPLACE PROCEDURE sp_delete_user(p_id INT)
LANGUAGE plpgsql
AS $$
BEGIN
    UPDATE "USER"
    SET is_active  = false,
        updated_at = NOW()
    WHERE id = p_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'User with id % not found', p_id;
    END IF;
END;
$$;


/* ---------- EMPLOYEE (+ EMPLOYEE_DRIVER + EMPLOYEE_STAFF) ---------- */

-- 12. sp_create_employee  [Employee + EmployeeDriver + EmployeeStaff]
-- Creates USER + EMPLOYEE + driver/staff sub-type in a single atomic transaction.
-- Password must be pre-hashed by Django (make_password).
-- The trigger trg_employee_sync_user_role auto-updates "USER".role after the employee INSERT.
CREATE OR REPLACE PROCEDURE sp_create_employee(
    -- User params (inserted into "USER")
    p_username          VARCHAR(150),
    p_email             VARCHAR(254),
    p_password          VARCHAR(128),
    p_first_name        VARCHAR(150),
    p_last_name         VARCHAR(150),
    p_contact           VARCHAR(20),
    p_address           VARCHAR(255),
    -- Employee params (inserted into employee)
    p_war_id            INT,
    p_emp_position      VARCHAR(32),
    p_schedule          VARCHAR(255),
    p_wage              DECIMAL(10,2),
    p_hire_date         DATE,
    -- Driver params (nullable — only used when emp_position = 'driver')
    p_license_number    VARCHAR(50)   DEFAULT NULL,
    p_license_category  VARCHAR(20)   DEFAULT NULL,
    p_license_expiry    DATE          DEFAULT NULL,
    p_driving_experience INT          DEFAULT NULL,
    p_driver_status     VARCHAR(20)   DEFAULT NULL,
    -- Staff params (nullable — only used when emp_position = 'staff')
    p_department        VARCHAR(32)   DEFAULT NULL,
    -- Output
    INOUT o_user_id     INT           DEFAULT NULL
)
LANGUAGE plpgsql
AS $$
BEGIN
    -- Validate position
    IF p_emp_position NOT IN ('driver', 'staff') THEN
        RAISE EXCEPTION 'Invalid position: %. Must be driver or staff', p_emp_position;
    END IF;

    -- Validate driver has required fields
    IF p_emp_position = 'driver' AND (p_license_number IS NULL OR p_license_expiry IS NULL) THEN
        RAISE EXCEPTION 'Driver position requires license_number and license_expiry';
    END IF;

    -- Validate license not expired
    IF p_emp_position = 'driver' AND NOT fn_is_license_valid(p_license_expiry) THEN
        RAISE EXCEPTION 'License expiry date must be in the future';
    END IF;

    -- Validate staff has department
    IF p_emp_position = 'staff' AND p_department IS NULL THEN
        RAISE EXCEPTION 'Staff position requires department';
    END IF;

    -- Validate wage
    IF p_wage < 0 THEN
        RAISE EXCEPTION 'Wage cannot be negative';
    END IF;

    -- 1) Create user in "USER" (role set temporarily; trigger will sync after employee insert)
    INSERT INTO "USER" (
        username, email, password, first_name, last_name,
        contact, address, role,
        is_superuser, is_staff, is_active, created_at, updated_at
    ) VALUES (
        p_username, p_email, p_password, p_first_name, p_last_name,
        p_contact, p_address, 'client',    -- temp role; trigger fixes it
        FALSE, FALSE, TRUE, NOW(), NOW()
    ) RETURNING id INTO o_user_id;

    -- 2) Create employee (shared PK = same id as "USER")
    --    This fires trg_employee_sync_user_role -> updates "USER".role
    INSERT INTO employee (
        id, war_id, emp_position, schedule, wage, is_active, hire_date
    ) VALUES (
        o_user_id, p_war_id, p_emp_position, p_schedule, p_wage, TRUE, p_hire_date
    );

    -- 3) Create driver-specific record (shared PK = same id as employee)
    IF p_emp_position = 'driver' THEN
        INSERT INTO employee_driver (
            id, license_number, license_category,
            license_expiry_date, driving_experience_years, driver_status
        ) VALUES (
            o_user_id, p_license_number, p_license_category,
            p_license_expiry, p_driving_experience,
            COALESCE(p_driver_status, 'available')
        );
    END IF;

    -- 4) Create staff-specific record (shared PK = same id as employee)
    IF p_emp_position = 'staff' THEN
        INSERT INTO employee_staff (
            id, department
        ) VALUES (
            o_user_id, p_department
        );
    END IF;
END;
$$;


-- 13. sp_update_employee  [Employee]
-- Update employee, user, and driver/staff sub-type records.
-- Handles position changes (e.g. driver -> staff) by deleting old sub-type and creating new.
CREATE OR REPLACE PROCEDURE sp_update_employee(
    p_id                 INT,
    -- User fields
    p_email              VARCHAR(254)  DEFAULT NULL,
    p_first_name         VARCHAR(150)  DEFAULT NULL,
    p_last_name          VARCHAR(150)  DEFAULT NULL,
    p_contact            VARCHAR(20)   DEFAULT NULL,
    p_address            VARCHAR(255)  DEFAULT NULL,
    -- Employee fields
    p_war_id             INT           DEFAULT NULL,
    p_emp_position       VARCHAR(32)   DEFAULT NULL,
    p_schedule           VARCHAR(255)  DEFAULT NULL,
    p_wage               DECIMAL(10,2) DEFAULT NULL,
    p_is_active          BOOL          DEFAULT NULL,
    -- Driver fields (if position is/becomes driver)
    p_license_number     VARCHAR(50)   DEFAULT NULL,
    p_license_category   VARCHAR(20)   DEFAULT NULL,
    p_license_expiry     DATE          DEFAULT NULL,
    p_driving_experience INT           DEFAULT NULL,
    p_driver_status      VARCHAR(20)   DEFAULT NULL,
    -- Staff fields (if position is/becomes staff)
    p_department         VARCHAR(32)   DEFAULT NULL
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_current_position VARCHAR(32);
BEGIN
    -- Get current position
    SELECT emp_position INTO v_current_position FROM employee WHERE id = p_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Employee with id % not found', p_id;
    END IF;

    -- Validate wage if provided
    IF p_wage IS NOT NULL AND p_wage < 0 THEN
        RAISE EXCEPTION 'Wage cannot be negative';
    END IF;

    -- Validate license if switching to driver
    IF p_emp_position = 'driver' AND v_current_position != 'driver' THEN
        IF p_license_number IS NULL OR p_license_expiry IS NULL THEN
            RAISE EXCEPTION 'Driver position requires license_number and license_expiry';
        END IF;
        IF NOT fn_is_license_valid(p_license_expiry) THEN
            RAISE EXCEPTION 'License expiry date must be in the future';
        END IF;
    END IF;

    -- Validate department if switching to staff
    IF p_emp_position = 'staff' AND v_current_position != 'staff' AND p_department IS NULL THEN
        RAISE EXCEPTION 'Staff position requires department';
    END IF;

    -- Update user fields
    UPDATE "USER"
    SET email      = COALESCE(p_email,      email),
        first_name = COALESCE(p_first_name, first_name),
        last_name  = COALESCE(p_last_name,  last_name),
        contact    = COALESCE(p_contact,    contact),
        address    = COALESCE(p_address,    address),
        updated_at = NOW()
    WHERE id = p_id;

    -- Update employee fields
    -- The trigger trg_employee_sync_user_role will update "USER".role if emp_position changes
    UPDATE employee
    SET war_id       = COALESCE(p_war_id,       war_id),
        emp_position = COALESCE(p_emp_position, emp_position),
        schedule     = COALESCE(p_schedule,     schedule),
        wage         = COALESCE(p_wage,         wage),
        is_active    = COALESCE(p_is_active,    is_active)
    WHERE id = p_id;

    -- Handle position change: delete old sub-type, create new
    IF p_emp_position IS NOT NULL AND p_emp_position != v_current_position THEN
        -- Remove old sub-type record
        IF v_current_position = 'driver' THEN
            DELETE FROM employee_driver WHERE id = p_id;
        ELSIF v_current_position = 'staff' THEN
            DELETE FROM employee_staff WHERE id = p_id;
        END IF;

        -- Create new sub-type record
        IF p_emp_position = 'driver' THEN
            INSERT INTO employee_driver (
                id, license_number, license_category,
                license_expiry_date, driving_experience_years, driver_status
            ) VALUES (
                p_id, p_license_number, p_license_category,
                p_license_expiry, p_driving_experience,
                COALESCE(p_driver_status, 'available')
            );
        ELSIF p_emp_position = 'staff' THEN
            INSERT INTO employee_staff (id, department)
            VALUES (p_id, p_department);
        END IF;
    ELSE
        -- Same position: update existing sub-type record
        IF COALESCE(p_emp_position, v_current_position) = 'driver' THEN
            UPDATE employee_driver
            SET license_number           = COALESCE(p_license_number,     license_number),
                license_category         = COALESCE(p_license_category,   license_category),
                license_expiry_date      = COALESCE(p_license_expiry,     license_expiry_date),
                driving_experience_years = COALESCE(p_driving_experience, driving_experience_years),
                driver_status            = COALESCE(p_driver_status,      driver_status)
            WHERE id = p_id;
        ELSIF COALESCE(p_emp_position, v_current_position) = 'staff' THEN
            UPDATE employee_staff
            SET department = COALESCE(p_department, department)
            WHERE id = p_id;
        END IF;
    END IF;
END;
$$;


-- 14. sp_delete_employee  [Employee]
-- Delete employee and sub-type records. Soft-deletes the user.
-- Prevents deletion if driver has active routes or deliveries.
CREATE OR REPLACE PROCEDURE sp_delete_employee(p_id INT)
LANGUAGE plpgsql
AS $$
DECLARE
    v_position VARCHAR(32);
BEGIN
    -- Get position to know which sub-type to delete
    SELECT emp_position INTO v_position FROM employee WHERE id = p_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Employee with id % not found', p_id;
    END IF;

    -- Check for active routes (if driver)
    IF v_position = 'driver' THEN
        IF EXISTS (
            SELECT 1 FROM route
            WHERE driver_id = p_id
              AND delivery_status IN ('not_started', 'on_going')
        ) THEN
            RAISE EXCEPTION 'Cannot delete driver %: assigned to active routes', p_id;
        END IF;

        IF EXISTS (
            SELECT 1 FROM delivery
            WHERE driver_id = p_id
              AND status NOT IN ('completed', 'cancelled')
        ) THEN
            RAISE EXCEPTION 'Cannot delete driver %: has active deliveries', p_id;
        END IF;
    END IF;

    -- Delete sub-type record first (FK constraint: child before parent)
    IF v_position = 'driver' THEN
        DELETE FROM employee_driver WHERE id = p_id;
    ELSIF v_position = 'staff' THEN
        DELETE FROM employee_staff WHERE id = p_id;
    END IF;

    -- Delete employee record
    DELETE FROM employee WHERE id = p_id;

    -- Soft-delete the user (don't hard-delete, keep for audit trail)
    UPDATE "USER"
    SET is_active  = false,
        updated_at = NOW()
    WHERE id = p_id;
END;
$$;


/* ---------- WAREHOUSE ---------- */

-- 15. sp_create_warehouse  [Warehouse]
-- Create a new warehouse.
-- trg_warehouse_schedule_check validates open/close times automatically.
CREATE OR REPLACE PROCEDURE sp_create_warehouse(
    p_name                      VARCHAR(100),
    p_contact                   VARCHAR(20),
    p_address                   VARCHAR(255),
    p_maximum_storage_capacity  INT,
    p_schedule_open             TIME    DEFAULT NULL,
    p_schedule_close            TIME    DEFAULT NULL,
    p_schedule                  TEXT    DEFAULT NULL,
    INOUT p_id                  INT     DEFAULT NULL
)
LANGUAGE plpgsql
AS $$
BEGIN
    INSERT INTO warehouse (
        name, contact, address,
        schedule_open, schedule_close, schedule,
        maximum_storage_capacity,
        is_active, created_at, updated_at
    ) VALUES (
        p_name, p_contact, p_address,
        p_schedule_open, p_schedule_close, p_schedule,
        p_maximum_storage_capacity,
        true, NOW(), NOW()
    )
    RETURNING id INTO p_id;
END;
$$;


-- 16. sp_update_warehouse  [Warehouse]
-- Update an existing warehouse's mutable fields.
CREATE OR REPLACE PROCEDURE sp_update_warehouse(
    p_id                        INT,
    p_name                      VARCHAR(100)  DEFAULT NULL,
    p_contact                   VARCHAR(20)   DEFAULT NULL,
    p_address                   VARCHAR(255)  DEFAULT NULL,
    p_schedule_open             TIME          DEFAULT NULL,
    p_schedule_close            TIME          DEFAULT NULL,
    p_schedule                  TEXT          DEFAULT NULL,
    p_maximum_storage_capacity  INT           DEFAULT NULL,
    p_is_active                 BOOL          DEFAULT NULL
)
LANGUAGE plpgsql
AS $$
BEGIN
    UPDATE warehouse
    SET name                     = COALESCE(p_name,                      name),
        contact                  = COALESCE(p_contact,                   contact),
        address                  = COALESCE(p_address,                   address),
        schedule_open            = COALESCE(p_schedule_open,             schedule_open),
        schedule_close           = COALESCE(p_schedule_close,            schedule_close),
        schedule                 = COALESCE(p_schedule,                  schedule),
        maximum_storage_capacity = COALESCE(p_maximum_storage_capacity,  maximum_storage_capacity),
        is_active                = COALESCE(p_is_active,                 is_active),
        updated_at               = NOW()
    WHERE id = p_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Warehouse with id % not found', p_id;
    END IF;
END;
$$;


-- 17. sp_delete_warehouse  [Warehouse]
-- Delete a warehouse. Prevents deletion if it has active employees or routes.
CREATE OR REPLACE PROCEDURE sp_delete_warehouse(p_id INT)
LANGUAGE plpgsql
AS $$
BEGIN
    -- Check for active employees assigned to this warehouse
    IF EXISTS (
        SELECT 1 FROM employee
        WHERE war_id = p_id AND is_active = true
    ) THEN
        RAISE EXCEPTION 'Cannot delete warehouse %: it has active employees assigned.', p_id;
    END IF;

    -- Check for active routes dispatched from this warehouse
    IF EXISTS (
        SELECT 1 FROM route
        WHERE war_id = p_id
          AND delivery_status IN ('not_started', 'on_going')
    ) THEN
        RAISE EXCEPTION 'Cannot delete warehouse %: it has active routes.', p_id;
    END IF;

    DELETE FROM warehouse WHERE id = p_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Warehouse with id % not found', p_id;
    END IF;
END;
$$;


-- 18. sp_import_warehouses  [Warehouse]
-- Bulk-import warehouses from a JSONB array.
CREATE OR REPLACE PROCEDURE sp_import_warehouses(p_data JSONB)
LANGUAGE plpgsql
AS $$
DECLARE
    v_rec JSONB;
BEGIN
    FOR v_rec IN SELECT jsonb_array_elements(p_data)
    LOOP
        INSERT INTO warehouse (
            name, contact, address,
            schedule_open, schedule_close, schedule,
            maximum_storage_capacity,
            is_active, created_at, updated_at
        ) VALUES (
            v_rec->>'name',
            v_rec->>'contact',
            v_rec->>'address',
            (v_rec->>'schedule_open')::TIME,
            (v_rec->>'schedule_close')::TIME,
            v_rec->>'schedule',
            (v_rec->>'maximum_storage_capacity')::INT,
            COALESCE((v_rec->>'is_active')::BOOL, true),
            NOW(), NOW()
        );
    END LOOP;
END;
$$;


/*==============================================================*/
/* END OF diego_objects.sql                                      */
/* Total: 18 standalone SQL blocks (20 objects counting         */
/*        driver/staff logic inside sp_create_employee)         */
/*==============================================================*/


-- DAVID
/* ============================================================ */
/*                       F U N C T I O N S                      */
/* ============================================================ */


-- 1. fn_is_valid_status_transition  [Delivery]
-- Validate delivery status transitions.
-- Allowed transitions:
--   registered -> ready, cancelled
--   ready      -> pending, cancelled
--   pending    -> in_transit, cancelled
--   in_transit -> completed, cancelled
--   completed  -> (terminal, no transitions)
--   cancelled  -> (terminal, no transitions)
CREATE OR REPLACE FUNCTION fn_is_valid_status_transition(
    p_old_status VARCHAR(20),
    p_new_status VARCHAR(20)
)
RETURNS BOOLEAN
LANGUAGE plpgsql
AS $$
BEGIN
    -- Same status is always allowed (no-op update)
    IF p_old_status = p_new_status THEN
        RETURN TRUE;
    END IF;

    RETURN CASE p_old_status
        WHEN 'registered' THEN p_new_status IN ('ready', 'cancelled')
        WHEN 'ready'      THEN p_new_status IN ('pending', 'cancelled')
        WHEN 'pending'    THEN p_new_status IN ('in_transit', 'cancelled')
        WHEN 'in_transit' THEN p_new_status IN ('completed', 'cancelled')
        ELSE FALSE  -- completed and cancelled are terminal
    END;
END;
$$;


-- 2. fn_get_client_deliveries  [Delivery]
-- Return all deliveries for a specific client, with driver/route info.
CREATE OR REPLACE FUNCTION fn_get_client_deliveries(p_client_id INT)
RETURNS TABLE (
    id                INT,
    tracking_number   VARCHAR(50),
    description       TEXT,
    sender_name       VARCHAR(100),
    recipient_name    VARCHAR(100),
    recipient_address TEXT,
    item_type         VARCHAR(20),
    weight            INT,
    dimensions        VARCHAR(50),
    status            VARCHAR(20),
    priority          VARCHAR(20),
    in_transition     BOOL,
    delivery_date     TIMESTAMPTZ,
    driver_name       TEXT,
    route_id          INT,
    warehouse_name    VARCHAR(100),
    created_at        TIMESTAMPTZ,
    updated_at        TIMESTAMPTZ
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        d.id,
        d.tracking_number,
        d.description,
        d.sender_name,
        d.recipient_name,
        d.recipient_address,
        d.item_type,
        d.weight,
        d.dimensions,
        d.status,
        d.priority,
        d.in_transition,
        d.delivery_date,
        u_driver.first_name || ' ' || u_driver.last_name  AS driver_name,
        d.route_id,
        w.name                                              AS warehouse_name,
        d.created_at,
        d.updated_at
    FROM delivery d
    LEFT JOIN employee_driver ed   ON ed.id = d.driver_id
    LEFT JOIN "USER" u_driver      ON u_driver.id = ed.id
    LEFT JOIN warehouse w          ON w.id = d.war_id
    WHERE d.client_id = p_client_id
    ORDER BY d.created_at DESC;
END;
$$;


-- 3. fn_get_driver_deliveries  [Delivery]
-- Return all deliveries for a specific driver, with client/route info.
CREATE OR REPLACE FUNCTION fn_get_driver_deliveries(p_driver_id INT)
RETURNS TABLE (
    id                INT,
    tracking_number   VARCHAR(50),
    description       TEXT,
    sender_name       VARCHAR(100),
    recipient_name    VARCHAR(100),
    recipient_address TEXT,
    item_type         VARCHAR(20),
    weight            INT,
    dimensions        VARCHAR(50),
    status            VARCHAR(20),
    priority          VARCHAR(20),
    in_transition     BOOL,
    delivery_date     TIMESTAMPTZ,
    client_name       TEXT,
    route_id          INT,
    warehouse_name    VARCHAR(100),
    created_at        TIMESTAMPTZ,
    updated_at        TIMESTAMPTZ
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        d.id,
        d.tracking_number,
        d.description,
        d.sender_name,
        d.recipient_name,
        d.recipient_address,
        d.item_type,
        d.weight,
        d.dimensions,
        d.status,
        d.priority,
        d.in_transition,
        d.delivery_date,
        u_client.first_name || ' ' || u_client.last_name  AS client_name,
        d.route_id,
        w.name                                              AS warehouse_name,
        d.created_at,
        d.updated_at
    FROM delivery d
    LEFT JOIN client c             ON c.id = d.client_id
    LEFT JOIN "USER" u_client      ON u_client.id = c.id
    LEFT JOIN warehouse w          ON w.id = d.war_id
    WHERE d.driver_id = p_driver_id
    ORDER BY d.created_at DESC;
END;
$$;


-- 4. fn_get_delivery_tracking  [DeliveryTracking]
-- Return the full tracking timeline for a delivery by tracking number.
-- Joins delivery_tracking with delivery, employee_staff, warehouse.
CREATE OR REPLACE FUNCTION fn_get_delivery_tracking(p_tracking_number VARCHAR(50))
RETURNS TABLE (
    tracking_id       INT,
    delivery_id       INT,
    tracking_number   VARCHAR(50),
    status            VARCHAR(20),
    notes             TEXT,
    changed_by_name   TEXT,
    warehouse_name    VARCHAR(100),
    event_timestamp   TIMESTAMPTZ
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        dt.id              AS tracking_id,
        dt.del_id          AS delivery_id,
        d.tracking_number,
        dt.status,
        dt.notes,
        u_staff.first_name || ' ' || u_staff.last_name  AS changed_by_name,
        w.name                                            AS warehouse_name,
        dt.created_at      AS event_timestamp
    FROM delivery_tracking dt
    JOIN delivery d             ON d.id  = dt.del_id
    LEFT JOIN employee_staff es ON es.id = dt.staff_id
    LEFT JOIN "USER" u_staff    ON u_staff.id = es.id
    LEFT JOIN warehouse w       ON w.id  = dt.war_id
    WHERE d.tracking_number = p_tracking_number
    ORDER BY dt.created_at ASC;
END;
$$;



/* ============================================================ */
/*                          V I E W S                           */
/* ============================================================ */


-- 5. v_deliveries_full  [Delivery]
-- Deliveries joined with driver, client, route, and warehouse info.
CREATE OR REPLACE VIEW v_deliveries_full AS
SELECT
    d.id,
    d.tracking_number,
    d.description,
    d.sender_name,
    d.sender_address,
    d.sender_phone,
    d.sender_email,
    d.recipient_name,
    d.recipient_address,
    d.recipient_phone,
    d.recipient_email,
    d.item_type,
    d.weight,
    d.dimensions,
    d.status,
    d.priority,
    d.in_transition,
    d.delivery_date,
    d.created_at,
    d.updated_at,
    -- FKs
    d.driver_id,
    d.route_id,
    d.inv_id,
    d.client_id,
    d.war_id,
    -- Driver info
    u_driver.first_name || ' ' || u_driver.last_name  AS driver_name,
    -- Client info
    u_client.first_name || ' ' || u_client.last_name  AS client_name,
    -- Route info
    r.delivery_status                                   AS route_status,
    r.delivery_date                                     AS route_date,
    -- Warehouse info
    w.name                                              AS warehouse_name
FROM delivery d
LEFT JOIN employee_driver ed   ON ed.id = d.driver_id
LEFT JOIN "USER" u_driver      ON u_driver.id = ed.id
LEFT JOIN client c             ON c.id = d.client_id
LEFT JOIN "USER" u_client      ON u_client.id = c.id
LEFT JOIN route r              ON r.id = d.route_id
LEFT JOIN warehouse w          ON w.id = d.war_id
ORDER BY d.created_at DESC;


-- 6. v_deliveries_export  [Delivery]
-- Flat view formatted for JSON/CSV export.
CREATE OR REPLACE VIEW v_deliveries_export AS
SELECT
    d.id,
    d.driver_id,
    d.route_id,
    d.inv_id,
    d.client_id,
    d.war_id,
    d.tracking_number,
    d.description,
    d.sender_name,
    d.sender_address,
    d.sender_phone,
    d.sender_email,
    d.recipient_name,
    d.recipient_address,
    d.recipient_phone,
    d.recipient_email,
    d.item_type,
    d.weight,
    d.dimensions,
    d.status,
    d.priority,
    d.in_transition,
    d.delivery_date,
    d.created_at,
    d.updated_at
FROM delivery d
ORDER BY d.id;


-- 7. v_delivery_tracking  [DeliveryTracking]
-- Full tracking timeline view joining delivery_tracking with delivery, employee_staff, warehouse.
CREATE OR REPLACE VIEW v_delivery_tracking AS
SELECT
    dt.id              AS tracking_id,
    dt.del_id          AS delivery_id,
    d.tracking_number,
    dt.status,
    dt.notes,
    dt.staff_id,
    u_staff.first_name || ' ' || u_staff.last_name  AS staff_name,
    dt.war_id,
    w.name                                            AS warehouse_name,
    dt.created_at      AS event_timestamp
FROM delivery_tracking dt
JOIN delivery d             ON d.id  = dt.del_id
LEFT JOIN employee_staff es ON es.id = dt.staff_id
LEFT JOIN "USER" u_staff    ON u_staff.id = es.id
LEFT JOIN warehouse w       ON w.id  = dt.war_id
ORDER BY dt.del_id, dt.created_at ASC;



/* ============================================================ */
/*                       T R I G G E R S                        */
/* ============================================================ */


-- 8. trg_delivery_soft_delete  [Delivery]
-- BEFORE DELETE on delivery: set status='cancelled' instead of hard-deleting.
CREATE OR REPLACE FUNCTION fn_trg_delivery_soft_delete()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    UPDATE delivery
    SET status     = 'cancelled',
        updated_at = NOW()
    WHERE id = OLD.id;

    -- Cancel the DELETE so the row stays in the table
    RETURN NULL;
END;
$$;

DROP TRIGGER IF EXISTS trg_delivery_soft_delete ON delivery;

CREATE TRIGGER trg_delivery_soft_delete
    BEFORE DELETE ON delivery
    FOR EACH ROW
    EXECUTE FUNCTION fn_trg_delivery_soft_delete();


-- 9. trg_delivery_status_workflow  [Delivery]
-- BEFORE UPDATE on delivery: enforce valid status transitions.
-- Depends on: fn_is_valid_status_transition
CREATE OR REPLACE FUNCTION fn_trg_delivery_status_workflow()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    -- Only check when status is actually changing
    IF OLD.status IS DISTINCT FROM NEW.status THEN
        IF NOT fn_is_valid_status_transition(OLD.status, NEW.status) THEN
            RAISE EXCEPTION 'Invalid status transition: % -> %. Allowed from %: %',
                OLD.status, NEW.status, OLD.status,
                CASE OLD.status
                    WHEN 'registered' THEN 'ready, cancelled'
                    WHEN 'ready'      THEN 'pending, cancelled'
                    WHEN 'pending'    THEN 'in_transit, cancelled'
                    WHEN 'in_transit' THEN 'completed, cancelled'
                    ELSE '(none — terminal status)'
                END;
        END IF;
    END IF;

    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_delivery_status_workflow ON delivery;

CREATE TRIGGER trg_delivery_status_workflow
    BEFORE UPDATE ON delivery
    FOR EACH ROW
    EXECUTE FUNCTION fn_trg_delivery_status_workflow();


-- 10. trg_delivery_timestamp_check  [Delivery]
-- BEFORE INSERT/UPDATE on delivery: ensure updated_at >= created_at.
-- Also auto-sets updated_at = NOW() on UPDATE.
CREATE OR REPLACE FUNCTION fn_trg_delivery_timestamp_check()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    -- On INSERT: set timestamps if not provided
    IF TG_OP = 'INSERT' THEN
        NEW.created_at := COALESCE(NEW.created_at, NOW());
        NEW.updated_at := COALESCE(NEW.updated_at, NOW());
    END IF;

    -- On UPDATE: always bump updated_at
    IF TG_OP = 'UPDATE' THEN
        NEW.updated_at := NOW();
    END IF;

    -- Validate updated_at >= created_at
    IF NEW.updated_at < NEW.created_at THEN
        RAISE EXCEPTION 'updated_at (%) cannot be before created_at (%)',
            NEW.updated_at, NEW.created_at;
    END IF;

    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_delivery_timestamp_check ON delivery;

CREATE TRIGGER trg_delivery_timestamp_check
    BEFORE INSERT OR UPDATE ON delivery
    FOR EACH ROW
    EXECUTE FUNCTION fn_trg_delivery_timestamp_check();


-- 11. trg_delivery_tracking_log  [DeliveryTracking]
-- AFTER INSERT OR UPDATE OF status ON delivery:
-- Automatically insert a row into delivery_tracking to record the status change.
-- The staff_id and war_id are taken from the delivery row itself
-- (set by sp_update_delivery_status before the trigger fires).
CREATE OR REPLACE FUNCTION fn_trg_delivery_tracking_log()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    -- On INSERT: log the initial status
    -- On UPDATE of status: log the new status
    IF TG_OP = 'INSERT' OR (TG_OP = 'UPDATE' AND OLD.status IS DISTINCT FROM NEW.status) THEN
        INSERT INTO delivery_tracking (
            del_id, staff_id, war_id,
            status, notes, created_at
        ) VALUES (
            NEW.id,
            NULL,       -- staff_id set to NULL on auto-log; sp_update_delivery_status handles it
            NEW.war_id,
            NEW.status,
            CASE
                WHEN TG_OP = 'INSERT' THEN 'Delivery registered'
                ELSE 'Status changed to ' || NEW.status
            END,
            NOW()
        );
    END IF;

    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_delivery_tracking_log ON delivery;

CREATE TRIGGER trg_delivery_tracking_log
    AFTER INSERT OR UPDATE OF status ON delivery
    FOR EACH ROW
    EXECUTE FUNCTION fn_trg_delivery_tracking_log();



/* ============================================================ */
/*                     P R O C E D U R E S                      */
/* ============================================================ */


/* ---------- DELIVERY ---------- */

-- 12. sp_create_delivery  [Delivery]
-- Create a new delivery with validation.
-- Auto-generates tracking_number if not provided.
-- Triggers trg_delivery_timestamp_check (timestamps) and trg_delivery_tracking_log (initial event).
CREATE OR REPLACE PROCEDURE sp_create_delivery(
    p_driver_id          INT         DEFAULT NULL,
    p_route_id           INT         DEFAULT NULL,
    p_inv_id             INT         DEFAULT NULL,
    p_client_id          INT         DEFAULT NULL,
    p_war_id             INT         DEFAULT NULL,
    p_tracking_number    VARCHAR(50) DEFAULT NULL,
    p_description        TEXT        DEFAULT NULL,
    p_sender_name        VARCHAR(100) DEFAULT NULL,
    p_sender_address     TEXT        DEFAULT NULL,
    p_sender_phone       VARCHAR(20) DEFAULT NULL,
    p_sender_email       VARCHAR(100) DEFAULT NULL,
    p_recipient_name     VARCHAR(100) DEFAULT NULL,
    p_recipient_address  TEXT        DEFAULT NULL,
    p_recipient_phone    VARCHAR(20) DEFAULT NULL,
    p_recipient_email    VARCHAR(100) DEFAULT NULL,
    p_item_type          VARCHAR(20) DEFAULT NULL,
    p_weight             INT         DEFAULT NULL,
    p_dimensions         VARCHAR(50) DEFAULT NULL,
    p_status             VARCHAR(20) DEFAULT 'registered',
    p_priority           VARCHAR(20) DEFAULT 'normal',
    p_delivery_date      TIMESTAMPTZ DEFAULT NULL,
    INOUT p_id           INT         DEFAULT NULL
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_tracking VARCHAR(50);
BEGIN
    -- Validate weight if provided
    IF p_weight IS NOT NULL AND p_weight < 1 THEN
        RAISE EXCEPTION 'Weight must be >= 1, got %', p_weight;
    END IF;

    -- Validate FK: client exists (if provided)
    IF p_client_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM client WHERE id = p_client_id) THEN
        RAISE EXCEPTION 'Client with id % not found', p_client_id;
    END IF;

    -- Validate FK: driver exists (if provided)
    IF p_driver_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM employee_driver WHERE id = p_driver_id) THEN
        RAISE EXCEPTION 'Driver with id % not found', p_driver_id;
    END IF;

    -- Validate FK: route exists (if provided)
    IF p_route_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM route WHERE id = p_route_id) THEN
        RAISE EXCEPTION 'Route with id % not found', p_route_id;
    END IF;

    -- Auto-generate tracking number if not provided: PO-YYYYMMDD-XXXXX
    IF p_tracking_number IS NULL OR p_tracking_number = '' THEN
        v_tracking := 'PO-' || TO_CHAR(NOW(), 'YYYYMMDD') || '-' ||
                      LPAD(nextval(pg_get_serial_sequence('delivery', 'id'))::TEXT, 5, '0');
    ELSE
        v_tracking := p_tracking_number;
    END IF;

    INSERT INTO delivery (
        driver_id, route_id, inv_id, client_id, war_id,
        tracking_number, description,
        sender_name, sender_address, sender_phone, sender_email,
        recipient_name, recipient_address, recipient_phone, recipient_email,
        item_type, weight, dimensions,
        status, priority, in_transition,
        delivery_date, created_at, updated_at
    ) VALUES (
        p_driver_id, p_route_id, p_inv_id, p_client_id, p_war_id,
        v_tracking, p_description,
        p_sender_name, p_sender_address, p_sender_phone, p_sender_email,
        p_recipient_name, p_recipient_address, p_recipient_phone, p_recipient_email,
        p_item_type, p_weight, p_dimensions,
        COALESCE(p_status, 'registered'), COALESCE(p_priority, 'normal'), false,
        p_delivery_date, NOW(), NOW()
    )
    RETURNING id INTO p_id;

    -- trg_delivery_timestamp_check validates timestamps
    -- trg_delivery_tracking_log inserts the initial tracking event
END;
$$;


-- 13. sp_update_delivery  [Delivery]
-- Update a delivery's mutable fields (NOT status — use sp_update_delivery_status for that).
CREATE OR REPLACE PROCEDURE sp_update_delivery(
    p_id                 INT,
    p_driver_id          INT          DEFAULT NULL,
    p_route_id           INT          DEFAULT NULL,
    p_inv_id             INT          DEFAULT NULL,
    p_client_id          INT          DEFAULT NULL,
    p_war_id             INT          DEFAULT NULL,
    p_tracking_number    VARCHAR(50)  DEFAULT NULL,
    p_description        TEXT         DEFAULT NULL,
    p_sender_name        VARCHAR(100) DEFAULT NULL,
    p_sender_address     TEXT         DEFAULT NULL,
    p_sender_phone       VARCHAR(20)  DEFAULT NULL,
    p_sender_email       VARCHAR(100) DEFAULT NULL,
    p_recipient_name     VARCHAR(100) DEFAULT NULL,
    p_recipient_address  TEXT         DEFAULT NULL,
    p_recipient_phone    VARCHAR(20)  DEFAULT NULL,
    p_recipient_email    VARCHAR(100) DEFAULT NULL,
    p_item_type          VARCHAR(20)  DEFAULT NULL,
    p_weight             INT          DEFAULT NULL,
    p_dimensions         VARCHAR(50)  DEFAULT NULL,
    p_priority           VARCHAR(20)  DEFAULT NULL,
    p_in_transition      BOOL         DEFAULT NULL,
    p_delivery_date      TIMESTAMPTZ  DEFAULT NULL
)
LANGUAGE plpgsql
AS $$
BEGIN
    -- Validate weight if provided
    IF p_weight IS NOT NULL AND p_weight < 1 THEN
        RAISE EXCEPTION 'Weight must be >= 1, got %', p_weight;
    END IF;

    UPDATE delivery
    SET driver_id         = COALESCE(p_driver_id,         driver_id),
        route_id          = COALESCE(p_route_id,          route_id),
        inv_id            = COALESCE(p_inv_id,            inv_id),
        client_id         = COALESCE(p_client_id,         client_id),
        war_id            = COALESCE(p_war_id,            war_id),
        tracking_number   = COALESCE(p_tracking_number,   tracking_number),
        description       = COALESCE(p_description,       description),
        sender_name       = COALESCE(p_sender_name,       sender_name),
        sender_address    = COALESCE(p_sender_address,    sender_address),
        sender_phone      = COALESCE(p_sender_phone,      sender_phone),
        sender_email      = COALESCE(p_sender_email,      sender_email),
        recipient_name    = COALESCE(p_recipient_name,    recipient_name),
        recipient_address = COALESCE(p_recipient_address, recipient_address),
        recipient_phone   = COALESCE(p_recipient_phone,   recipient_phone),
        recipient_email   = COALESCE(p_recipient_email,   recipient_email),
        item_type         = COALESCE(p_item_type,         item_type),
        weight            = COALESCE(p_weight,            weight),
        dimensions        = COALESCE(p_dimensions,        dimensions),
        priority          = COALESCE(p_priority,          priority),
        in_transition     = COALESCE(p_in_transition,     in_transition),
        delivery_date     = COALESCE(p_delivery_date,     delivery_date),
        updated_at        = NOW()
    WHERE id = p_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Delivery with id % not found', p_id;
    END IF;

    -- trg_delivery_timestamp_check validates timestamps
END;
$$;


-- 14. sp_update_delivery_status  [Delivery]
-- Update ONLY the delivery status, with staff/warehouse context for tracking.
-- This fires trg_delivery_status_workflow (validates transition)
-- and trg_delivery_tracking_log (inserts tracking event).
-- After the auto-logged event, we update it with the staff_id and notes.
CREATE OR REPLACE PROCEDURE sp_update_delivery_status(
    p_delivery_id    INT,
    p_new_status     VARCHAR(20),
    p_staff_id       INT          DEFAULT NULL,
    p_warehouse_id   INT          DEFAULT NULL,
    p_notes          TEXT         DEFAULT NULL
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_tracking_id INT;
BEGIN
    -- Validate delivery exists
    IF NOT EXISTS (SELECT 1 FROM delivery WHERE id = p_delivery_id) THEN
        RAISE EXCEPTION 'Delivery with id % not found', p_delivery_id;
    END IF;

    -- Update the delivery status
    -- trg_delivery_status_workflow validates the transition
    -- trg_delivery_tracking_log auto-inserts a tracking row
    UPDATE delivery
    SET status     = p_new_status,
        updated_at = NOW()
    WHERE id = p_delivery_id;

    -- Now update the most recent tracking event with staff/warehouse/notes context
    SELECT id INTO v_tracking_id
    FROM delivery_tracking
    WHERE del_id = p_delivery_id
    ORDER BY created_at DESC
    LIMIT 1;

    IF v_tracking_id IS NOT NULL THEN
        UPDATE delivery_tracking
        SET staff_id = COALESCE(p_staff_id, staff_id),
            war_id   = COALESCE(p_warehouse_id, war_id),
            notes    = COALESCE(p_notes, notes)
        WHERE id = v_tracking_id;
    END IF;
END;
$$;


-- 15. sp_delete_delivery  [Delivery]
-- Soft-delete a delivery (triggers trg_delivery_soft_delete -> sets status='cancelled').
CREATE OR REPLACE PROCEDURE sp_delete_delivery(p_id INT)
LANGUAGE plpgsql
AS $$
BEGIN
    -- The BEFORE DELETE trigger converts this into a soft delete
    DELETE FROM delivery WHERE id = p_id;

    -- After the trigger fires, the row still exists — verify the status was set
    IF NOT EXISTS (SELECT 1 FROM delivery WHERE id = p_id AND status = 'cancelled') THEN
        RAISE EXCEPTION 'Delivery with id % not found', p_id;
    END IF;
END;
$$;


-- 16. sp_import_deliveries  [Delivery]
-- Bulk-import deliveries from a JSONB array.
-- Auto-generates tracking_number for each if not provided.
-- Triggers fire per row (timestamp check + tracking log).
CREATE OR REPLACE PROCEDURE sp_import_deliveries(p_data JSONB)
LANGUAGE plpgsql
AS $$
DECLARE
    v_rec       JSONB;
    v_tracking  VARCHAR(50);
    v_del_id    INT;
BEGIN
    FOR v_rec IN SELECT jsonb_array_elements(p_data)
    LOOP
        -- Auto-generate tracking number if not provided
        IF (v_rec->>'tracking_number') IS NULL OR (v_rec->>'tracking_number') = '' THEN
            v_tracking := 'PO-' || TO_CHAR(NOW(), 'YYYYMMDD') || '-' ||
                          LPAD(nextval(pg_get_serial_sequence('delivery', 'id'))::TEXT, 5, '0');
        ELSE
            v_tracking := v_rec->>'tracking_number';
        END IF;

        INSERT INTO delivery (
            driver_id, route_id, inv_id, client_id, war_id,
            tracking_number, description,
            sender_name, sender_address, sender_phone, sender_email,
            recipient_name, recipient_address, recipient_phone, recipient_email,
            item_type, weight, dimensions,
            status, priority, in_transition,
            delivery_date, created_at, updated_at
        ) VALUES (
            (v_rec->>'driver_id')::INT,
            (v_rec->>'route_id')::INT,
            (v_rec->>'inv_id')::INT,
            (v_rec->>'client_id')::INT,
            (v_rec->>'war_id')::INT,
            v_tracking,
            v_rec->>'description',
            v_rec->>'sender_name',
            v_rec->>'sender_address',
            v_rec->>'sender_phone',
            v_rec->>'sender_email',
            v_rec->>'recipient_name',
            v_rec->>'recipient_address',
            v_rec->>'recipient_phone',
            v_rec->>'recipient_email',
            v_rec->>'item_type',
            (v_rec->>'weight')::INT,
            v_rec->>'dimensions',
            COALESCE(v_rec->>'status', 'registered'),
            COALESCE(v_rec->>'priority', 'normal'),
            COALESCE((v_rec->>'in_transition')::BOOL, false),
            (v_rec->>'delivery_date')::TIMESTAMPTZ,
            NOW(), NOW()
        )
        RETURNING id INTO v_del_id;

        -- trg_delivery_timestamp_check and trg_delivery_tracking_log fire per row
    END LOOP;
END;
$$;



DROP MATERIALIZED VIEW IF EXISTS mv_delivery_tracking;

CREATE MATERIALIZED VIEW mv_delivery_tracking AS
SELECT
  d.id              AS delivery_id,
  d.tracking_number AS tracking_number,
  dt.id             AS tracking_id,
  dt.status         AS status,
  dt.notes          AS notes,
  dt.created_at     AS event_timestamp,
  dt.staff_id       AS staff_id,
  u.username        AS staff_username,
  dt.war_id         AS warehouse_id,
  w.name            AS warehouse_name
FROM delivery_tracking dt
JOIN delivery d ON d.id = dt.del_id
LEFT JOIN "USER" u ON u.id = dt.staff_id
LEFT JOIN warehouse w ON w.id = dt.war_id;


CREATE UNIQUE INDEX IF NOT EXISTS ux_mv_delivery_tracking_tracking_id
ON mv_delivery_tracking (tracking_id);

CREATE INDEX IF NOT EXISTS ix_mv_delivery_tracking_lookup
ON mv_delivery_tracking (tracking_number, event_timestamp);



REFRESH MATERIALIZED VIEW mv_delivery_tracking;
-- o si quieres concurrente:
-- REFRESH MATERIALIZED VIEW CONCURRENTLY mv_delivery_tracking;

/*==============================================================*/
/* END OF david_objects.sql                                      */
/* Total: 16 objects                                            */
/*   Delivery: 2 views + 3 triggers + 3 functions + 5 procs    */
/*   DeliveryTracking: 1 view + 1 trigger + 1 function         */
/*==============================================================*/