from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class User(AbstractUser):
    """
    Single "USER" works for both Django auth and SQL database objects business logic

    Django ORM handles: registration, login, sessions, permissions.
    DB objects handle:  business reads (views), writes (procedures),
                        validation (triggers), aggregations (mat. views).

    Django AbstractUser provides:
        id, password(128), username(150), first_name(150), last_name(150),
        email(254), is_superuser, is_staff, is_active, last_login, date_joined

    NOTE: If populating data via raw SQL, reset the serial sequence after:
        SELECT setval(pg_get_serial_sequence('"USER"', 'id'), (SELECT MAX(id) FROM "USER"));
        Through DJANGO ORM it's always correctly serialized automatically
    """

    # Override PK to int4 (serial) — matches INT4 FKs in CLIENT, EMPLOYEE, etc.
    id = models.AutoField(primary_key=True)

    # Override date_joined so the DB column is named 'created_at'
    # for stored procedures / views to reference
    date_joined = models.DateTimeField(default=timezone.now, db_column='created_at')

    # Business fields
    contact = models.CharField(max_length=20, null=True, blank=True)
    address = models.CharField(max_length=255, null=True, blank=True)
    role = models.CharField(
        max_length=16,
        choices=[
            ("admin", "Admin"),
            ("client", "Client"),
            ("driver", "Driver"),
            ("staff", "Staff"),
            ("manager", "Manager"),
        ],
        default="client",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = '"USER"'
