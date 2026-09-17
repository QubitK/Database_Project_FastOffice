# Do this configuration before running the django project:

1. PgAdmin > Select server 'PostGreSQL 17' >

   * In DBs, recreate new DB called: PostOffice\_DB
   * In 'PostOffice\\PostOffice\\PostOffice\_Proj\\PostOffice\_Proj\\settings.py' : "PASSWORD": "postgres",
     Set your own server 'PostGreSQL 17' password

2. Post_Office\\PostOffice\\PostOffice\\PostOffice_Proj > run the commands:
   pip install -r requirements.txt

   * Run Django migrations first (enable django login handling):
     python manage.py makemigrations PostOffice\_App
     py manage.py migrate

3. Run the DDL.sql in pgadmin QueryTool:

   * to create all the data structure (expect USER)

4. Add the CRUD logical objects

   * pgsql Query tool run: final\_logic\_db\_objects.sql

5. Populate BD with data:

   * Inside PgAdmin query tool run: populate\_data.sql to load test data into the DB

6. Run
   py manage.py runserver

# Users to test from populate\_data.sql:

Admin:    gabriel.rodrigues / testpass123  (Gabriel Rodrigues)
Client:   ana.silva         / testpass123  (Ana Silva) --- X
Client:   bruno.santos      / testpass123  (Bruno Santos)
Driver:   carlos.ferreira   / testpass123  (Carlos Ferreira)
Driver:   diana.costa       / testpass123  (Diana Costa)
Staff:    eduardo.lopes     / testpass123  (Eduardo Lopes)
Staff:    filipa.mendes     / testpass123  (Filipa Mendes)

