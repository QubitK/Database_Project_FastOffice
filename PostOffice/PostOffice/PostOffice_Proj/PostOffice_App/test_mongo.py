import pytest
from pymongo import MongoClient
from datetime import datetime

# ------------------------------
# Connect to your real MongoDB
# ------------------------------
client = MongoClient("mongodb://localhost:27017")
db = client["postoffice"]

deliveries = db["deliveries"]
notifications = db["notifications"]
postoffice_col = db["postoffice"]
routes = db["routes"]
users = db["users"]
vehicles = db["vehicles"]

# ------------------------------
# Deliveries CRUD
# ------------------------------
def test_deliveries_crud():
    result = deliveries.insert_one({
        "recipient": "Test User",
        "address": "123 Test St",
        "status": "Pending",
        "delivery_date": datetime.now()
    })
    doc_id = result.inserted_id
    print(f"Inserted delivery ID: {doc_id}")

    # READ
    doc = deliveries.find_one({"_id": doc_id})
    assert doc is not None
    assert doc["recipient"] == "Test User"

    # UPDATE
    deliveries.update_one({"_id": doc_id}, {"$set": {"status": "Delivered"}})
    updated_doc = deliveries.find_one({"_id": doc_id})
    assert updated_doc["status"] == "Delivered"

    # DELETE
    deliveries.delete_one({"_id": doc_id})
    assert deliveries.find_one({"_id": doc_id}) is None
    print("Delivery CRUD verified.")


# ------------------------------
# Notifications CRUD
# ------------------------------
def test_notifications_crud():
    result = notifications.insert_one({
        "title": "Test Notification",
        "message": "This is a test notification.",
        "date": datetime.now()
    })
    doc_id = result.inserted_id
    print(f"Inserted notification ID: {doc_id}")

    # READ
    doc = notifications.find_one({"_id": doc_id})
    assert doc is not None
    assert doc["title"] == "Test Notification"

    # UPDATE
    notifications.update_one({"_id": doc_id}, {"$set": {"title": "Updated Notification"}})
    updated_doc = notifications.find_one({"_id": doc_id})
    assert updated_doc["title"] == "Updated Notification"

    # DELETE
    notifications.delete_one({"_id": doc_id})
    assert notifications.find_one({"_id": doc_id}) is None
    print("Notifications CRUD verified.")


# ------------------------------
# Postoffice CRUD
# ------------------------------
def test_postoffice_crud():
    result = postoffice_col.insert_one({
        "name": "Test Postoffice",
        "address": "456 Main St",
        "contact": "555-5678",
        "po_schedule_open": "08:00",
        "po_schedule_close": "17:00",
        "maximum_storage_capacity": 500
    })
    doc_id = result.inserted_id
    print(f"Inserted postoffice ID: {doc_id}")

    # READ
    doc = postoffice_col.find_one({"_id": doc_id})
    assert doc is not None
    assert doc["name"] == "Test Postoffice"

    # UPDATE
    postoffice_col.update_one({"_id": doc_id}, {"$set": {"maximum_storage_capacity": 600}})
    updated_doc = postoffice_col.find_one({"_id": doc_id})
    assert updated_doc["maximum_storage_capacity"] == 600

    # DELETE
    postoffice_col.delete_one({"_id": doc_id})
    assert postoffice_col.find_one({"_id": doc_id}) is None
    print("Postoffice CRUD verified.")


# ------------------------------
# Routes CRUD
# ------------------------------
def test_routes_crud():
    result = routes.insert_one({
        "route_name": "Test Route",
        "origin": "Origin A",
        "destination": "Destination B",
        "distance_km": 25
    })
    doc_id = result.inserted_id
    print(f"Inserted route ID: {doc_id}")

    # READ
    doc = routes.find_one({"_id": doc_id})
    assert doc is not None
    assert doc["route_name"] == "Test Route"

    # UPDATE
    routes.update_one({"_id": doc_id}, {"$set": {"distance_km": 30}})
    updated_doc = routes.find_one({"_id": doc_id})
    assert updated_doc["distance_km"] == 30

    # DELETE
    routes.delete_one({"_id": doc_id})
    assert routes.find_one({"_id": doc_id}) is None
    print("Routes CRUD verified.")


# ------------------------------
# Users CRUD
# ------------------------------
def test_users_crud():
    result = users.insert_one({
        "username": "testuser",
        "role": "client",
        "email": "test@example.com",
        "password": "hashed_password"
    })
    doc_id = result.inserted_id
    print(f"Inserted user ID: {doc_id}")

    # READ
    doc = users.find_one({"_id": doc_id})
    assert doc is not None
    assert doc["username"] == "testuser"

    # UPDATE
    users.update_one({"_id": doc_id}, {"$set": {"role": "admin"}})
    updated_doc = users.find_one({"_id": doc_id})
    assert updated_doc["role"] == "admin"

    # DELETE
    users.delete_one({"_id": doc_id})
    assert users.find_one({"_id": doc_id}) is None
    print("Users CRUD verified.")


# ------------------------------
# Vehicles CRUD
# ------------------------------
def test_vehicles_crud():
    result = vehicles.insert_one({
        "vehicle_type": "Van",
        "plate_number": "TEST123",
        "capacity": 1000,
        "brand": "TestBrand",
        "model": "TB1",
        "vehicle_status": "Active",
        "year": 2025,
        "fuel_type": "Electric",
        "last_maintenance_date": datetime.now()
    })
    doc_id = result.inserted_id
    print(f"Inserted vehicle ID: {doc_id}")

    # READ
    doc = vehicles.find_one({"_id": doc_id})
    assert doc is not None
    assert doc["plate_number"] == "TEST123"

    # UPDATE
    vehicles.update_one({"_id": doc_id}, {"$set": {"vehicle_status": "Inactive"}})
    updated_doc = vehicles.find_one({"_id": doc_id})
    assert updated_doc["vehicle_status"] == "Inactive"

    # DELETE
    vehicles.delete_one({"_id": doc_id})
    assert vehicles.find_one({"_id": doc_id}) is None
    print("Vehicles CRUD verified.")

