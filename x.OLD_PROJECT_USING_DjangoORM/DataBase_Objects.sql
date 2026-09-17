--------------------------- functions.sql ---------------------------
-----------------------------
-- Export .csv for WAREHOUSES
-----------------------------
CREATE OR REPLACE FUNCTION public.export_warehouses_csv(
	)
    RETURNS TABLE(line text)
    LANGUAGE 'plpgsql'
    COST 100
    VOLATILE PARALLEL UNSAFE
    ROWS 1000
AS $BODY$
        BEGIN
            RETURN QUERY
            SELECT CONCAT_WS(',',
                id,
                name,
                address,
                contact,
                po_schedule_open,
                po_schedule_close,
                maximum_storage_capacity
            )
            FROM "PostOffice_App_warehouse"
            ORDER BY id;
        END;

$BODY$;

-----------------------------
-- Export .csv for VEHICLES
-----------------------------
CREATE OR REPLACE FUNCTION public.export_vehicles_csv(
	)
    RETURNS TABLE(line text)
    LANGUAGE 'plpgsql'
    COST 100
    VOLATILE PARALLEL UNSAFE
    ROWS 1000
AS $BODY$
    BEGIN
        RETURN QUERY
        SELECT CONCAT_WS(',',
            id,
            plate_number,
            brand,
            model,
            capacity,
            vehicle_status,
            year,
            fuel_type,
            last_maintenance_date,
            vehicle_type
        )
        FROM "PostOffice_App_vehicle"
        ORDER BY id;
    END;
$BODY$;

--------------------------
-- Export .csv for ROUTES
--------------------------
CREATE OR REPLACE FUNCTION public.export_routes_csv(
	)
    RETURNS TABLE(line text)
    LANGUAGE 'plpgsql'
    COST 100
    VOLATILE PARALLEL UNSAFE
    ROWS 1000
AS $BODY$
    BEGIN
        RETURN QUERY
        SELECT CONCAT_WS(',',
            id,
            description,
            delivery_status,
            vehicle_id,
            driver_id,
            origin_name,
            origin_address,
            origin_contact,
            destination_name,
            destination_address,
            destination_contact,
            delivery_date,
            delivery_start_time,
            delivery_end_time,
            kms_travelled,
            expected_duration,
            driver_notes
        )
        FROM "PostOffice_App_route"
        ORDER BY id;
    END;
$BODY$;

-----------------------------
-- Export .csv for DELIVERIES
-----------------------------
CREATE OR REPLACE FUNCTION public.export_deliveries_csv(
	)
    RETURNS TABLE(line text)
    LANGUAGE 'plpgsql'
    COST 100
    VOLATILE PARALLEL UNSAFE
    ROWS 1000
AS $BODY$
    BEGIN
        RETURN QUERY
        SELECT CONCAT_WS(',',
            id,
            tracking_number,
            description,
            sender_name,
            sender_address,
            sender_phone,
            sender_email,
            recipient_name,
            recipient_address,
            recipient_phone,
            recipient_email,
            item_type,
            weight,
            dimensions,
            status,
            priority,
            registered_at,
            updated_at,
            in_transition,
            destination,
            delivery_date,
            driver_id,
            invoice_id,
            route_id,
            client_id
        )
        FROM "PostOffice_App_delivery"
        ORDER BY id;
    END;
$BODY$;

-----------------------------
-- Export .csv for INVOICES
-----------------------------
CREATE OR REPLACE FUNCTION public.export_invoices_csv(
	)
    RETURNS TABLE(line text)
    LANGUAGE 'plpgsql'
    COST 100
    VOLATILE PARALLEL UNSAFE
    ROWS 1000

AS $BODY$
BEGIN
    RETURN QUERY
    SELECT
        COALESCE(id_invoice::TEXT, '') || ',' ||
        COALESCE(invoice_status, '') || ',' ||
        COALESCE(invoice_type, '') || ',' ||
        COALESCE(quantity::TEXT, '') || ',' ||
        COALESCE(TO_CHAR(invoice_datetime, 'YYYY-MM-DD HH24:MI:SS'), '') || ',' ||
        COALESCE(cost::TEXT, '') || ',' ||
        CASE WHEN paid THEN 'true' ELSE 'false' END || ',' ||
        COALESCE(payment_method, '') || ',' ||
        COALESCE(REPLACE(name, ',', ';'), '') || ',' ||
        COALESCE(REPLACE(address, ',', ';'), '') || ',' ||
        COALESCE(contact, '') || ',' ||
        COALESCE(user_id::TEXT, '')
    FROM "PostOffice_App_invoice"
    ORDER BY
        invoice_datetime DESC NULLS LAST,
        id_invoice;
END;
$BODY$;



--------------------------- materialized_views.sql ---------------------------

-----------------------------------------------------------
-- Number of INVOICES and total revenue grouped by day
-----------------------------------------------------------
CREATE MATERIALIZED VIEW mv_daily_sales AS
    SELECT
        DATE(invoice_datetime) AS day,
        COUNT(*) AS total_invoices,
        SUM(cost) AS total_revenue
    FROM public."PostOffice_App_invoice"
    GROUP BY day
    ORDER BY day;

-----------------------------------------------------------
-- All-time number of INVOICES and total revenue grouped by payment method
-----------------------------------------------------------
CREATE MATERIALIZED VIEW mv_payment_methods_stats AS
    SELECT
        payment_method,
        COUNT(*) AS total_invoices,
        SUM(cost) AS total_value
    FROM public."PostOffice_App_invoice"
    GROUP BY payment_method;

-----------------------------------------------------------
-- Top 10 customers by spending (all-time)
-----------------------------------------------------------
CREATE MATERIALIZED VIEW mv_top_customers AS
    SELECT
        name AS customer_name,
        COUNT(*) AS total_invoices,
        SUM(cost) AS total_spent
    FROM public."PostOffice_App_invoice"
    GROUP BY name
    ORDER BY total_spent DESC
    LIMIT 10;

-----------------------------------------------------------
-- Number of INVOICES and total revenue grouped by month
-----------------------------------------------------------
CREATE MATERIALIZED VIEW mv_monthly_sales AS
    SELECT
        DATE_TRUNC('month', invoice_datetime) AS month,
        COUNT(*) AS total_invoices,
        SUM(cost) AS total_revenue
    FROM public."PostOffice_App_invoice"
    GROUP BY month
    ORDER BY month;



--------------------------- procedures ---------------------------

-- check_driver_vehicle_availability
CREATE OR REPLACE FUNCTION check_driver_vehicle_availability(
    p_driver_id INT,
    p_vehicle_id INT,
    p_delivery_date DATE
) RETURNS BOOLEAN AS $$
DECLARE
    conflicting_routes INT;
BEGIN
    SELECT COUNT(*) INTO conflicting_routes
    FROM "PostOffice_App_route"
    WHERE delivery_date = p_delivery_date
      AND (driver_id = p_driver_id OR vehicle_id = p_vehicle_id);

    IF conflicting_routes > 0 THEN
        RAISE EXCEPTION 'Driver or Vehicle is already assigned on %', p_delivery_date;
        RETURN FALSE;
    ELSE
        RETURN TRUE;
    END IF;
END;
$$ LANGUAGE plpgsql;


-- validate_delivery_status_transition
CREATE OR REPLACE FUNCTION validate_delivery_status_transition(
    p_delivery_id INT,
    p_new_status VARCHAR
) RETURNS BOOLEAN AS $$
DECLARE
    current_status VARCHAR;
BEGIN
    SELECT status INTO current_status
    FROM "PostOffice_App_delivery"
    WHERE id = p_delivery_id;

    IF current_status IS NULL THEN
        RAISE EXCEPTION 'Delivery not found';
    END IF;

    CASE current_status
        WHEN 'Registered' THEN
            IF p_new_status NOT IN ('Ready', 'Cancelled') THEN
                RAISE EXCEPTION 'Invalid transition from Registered to %', p_new_status;
            END IF;
        WHEN 'Ready' THEN
            IF p_new_status NOT IN ('In Transit', 'Cancelled') THEN
                RAISE EXCEPTION 'Invalid transition from Ready to %', p_new_status;
            END IF;
        WHEN 'In Transit' THEN
            IF p_new_status NOT IN ('Completed', 'Cancelled') THEN
                RAISE EXCEPTION 'Invalid transition from In Transit to %', p_new_status;
            END IF;
        WHEN 'Completed' THEN
            RAISE EXCEPTION 'Completed deliveries cannot change status';
        WHEN 'Cancelled' THEN
            RAISE EXCEPTION 'Cancelled deliveries cannot change status';
    END CASE;

    RETURN TRUE;
END;
$$ LANGUAGE plpgsql;

--------------------------- simple_views ---------------------------

-----------------------------------------------------------
-- INVOICES listing (all-time)
-----------------------------------------------------------
CREATE OR REPLACE VIEW vw_all_invoices AS
    SELECT
        id_invoice,
        name AS customer_name,
        invoice_type,
        invoice_status,
        quantity,
        cost,
        paid,
        payment_method,
        invoice_datetime
    FROM public."PostOffice_App_invoice";

-----------------------------------------------------------
-- All unpaid INVOICES (all-time)
-----------------------------------------------------------
CREATE OR REPLACE VIEW vw_unpaid_invoices AS
    SELECT *
    FROM public."PostOffice_App_invoice"
    WHERE paid = FALSE;

-----------------------------------------------------------
-- All-time number of INVOICES and total revenue grouped by invoice
-- status (Pending, Completed, Cancelled or Refunded)
-----------------------------------------------------------
CREATE OR REPLACE VIEW vw_invoices_totals_by_status AS
    SELECT
        invoice_status,
        COUNT(*) AS total_invoices,
        SUM(cost) AS total_value
    FROM public."PostOffice_App_invoice"
    GROUP BY invoice_status
    ORDER BY total_invoices DESC;

-----------------------------------------------------------
-- INVOICES from the last 7 days (rolling weekly window)
-----------------------------------------------------------
CREATE OR REPLACE VIEW vw_recent_invoices AS
SELECT *
FROM public."PostOffice_App_invoice"
WHERE invoice_datetime >= NOW() - INTERVAL '7 days';


--------------------------- triggers ---------------------------

-----------------------------------------------------------
-- Update timestamp for DELIVERY
-----------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_update_delivery_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_update_delivery_timestamp
BEFORE UPDATE ON "PostOffice_App_delivery"
FOR EACH ROW
EXECUTE FUNCTION fn_update_delivery_timestamp();

-----------------------------------------------------------
-- Shows in pgadmin4 logs that a DELIVERY was created
-----------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_log_delivery_created()
RETURNS TRIGGER AS $$
BEGIN
    RAISE NOTICE 'Delivery % created with status %', NEW.id, NEW.status;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_delivery_created
AFTER INSERT ON "PostOffice_App_delivery"
FOR EACH ROW
EXECUTE FUNCTION fn_log_delivery_created();

-----------------------------------------------------------
-- Shows in pgadmin4 logs that a DELIVERY status has changed
-----------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_log_delivery_status_change()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.status IS DISTINCT FROM OLD.status THEN
        RAISE NOTICE 'Delivery % changed status from % to %', NEW.id,
        OLD.status, NEW.status;
    END IF;
RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_status_change
AFTER UPDATE ON "PostOffice_App_delivery"
FOR EACH ROW
EXECUTE FUNCTION fn_log_delivery_status_change();

-----------------------------------------------------------
-- Shows in pgadmin4 error in case of DELIVERY fields are not being updated properly
-----------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_validate_delivery()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.status = 'Completed' AND NEW.delivery_date IS NULL THEN
        RAISE EXCEPTION 'Cannot mark delivery as Completed without
        delivery_date';
    END IF;

    IF NEW.weight <= 0 THEN
        RAISE EXCEPTION 'Weight must be greater than 0';
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_validate_delivery
BEFORE INSERT OR UPDATE ON "PostOffice_App_delivery"
FOR EACH ROW
EXECUTE FUNCTION fn_validate_delivery();

-----------------------------------------------------------
-- Shows in pgadmin4 error in case of INVOICE fields are not being updated properly
-----------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_validate_invoice()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.cost < 0 THEN
        RAISE EXCEPTION 'Invoice cost cannot be negative';
    END IF;

    IF NEW.quantity IS NOT NULL AND NEW.quantity <= 0 THEN
        RAISE EXCEPTION 'Invoice quantity must be greater than zero';
    END IF;

    IF NEW.paid = TRUE THEN
        NEW.invoice_status = 'Paid';
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_validate_invoice
BEFORE INSERT OR UPDATE ON "PostOffice_App_invoice"
FOR EACH ROW
EXECUTE FUNCTION fn_validate_invoice();

-----------------------------------------------------------
-- Shows in pgadmin4 error in case of driver license expires or is insert incorrectly
-----------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_validate_driver()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.license_expiry_date < CURRENT_DATE THEN
        RAISE EXCEPTION 'Driver license expired';
    END IF;

    IF NEW.driving_experience_years < 0 THEN
        RAISE EXCEPTION 'Driving experience cannot be negative';
    END IF;
RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_validate_driver
BEFORE INSERT OR UPDATE ON "PostOffice_App_employeedriver"
FOR EACH ROW
EXECUTE FUNCTION fn_validate_driver();

-----------------------------------------------------------
-- Updates all DELIVERies of a route as completed when the route is completed
-----------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_route_status()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.delivery_status = 'Completed' THEN
        UPDATE "PostOffice_App_delivery"
        SET status='Completed', delivery_date = CURRENT_DATE
        WHERE route_id = NEW.id;
    END IF;
RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_route_completed
AFTER UPDATE ON "PostOffice_App_route"
FOR EACH ROW
EXECUTE FUNCTION fn_route_status();

-----------------------------------------------------------
-- Updates INVOICES total cost adding the item costs
-----------------------------------------------------------
CREATE OR REPLACE FUNCTION update_invoice_cost()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE "PostOffice_App_invoice"
    SET cost = (
        SELECT COALESCE(SUM(quantity * unit_price), 0)
        FROM postoffice_app_invoice_items
        WHERE invoice_id = COALESCE(NEW.invoice_id, OLD.invoice_id)
    )
    WHERE id_invoice = COALESCE(NEW.invoice_id, OLD.invoice_id);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_invoice_cost ON postoffice_app_invoice_items;

CREATE TRIGGER trigger_invoice_cost
AFTER INSERT OR UPDATE OR DELETE ON postoffice_app_invoice_items
FOR EACH ROW EXECUTE FUNCTION update_invoice_cost();