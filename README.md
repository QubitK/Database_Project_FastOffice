# Fast Office - Post Office Logistics Management System

### Hybrid Multi-database Architecture
Combination of PostgreSQL, MongoDB, and Django ORM, with each technology being used according to the type of data and functionality it is best suited for.
      * PostgreSQL stores all structured, transactional data that needs strict consistency and relationships between entities
   * MongoDB, on the other hand, fits better for semi-structured notifications, which are event-driven and don't need relationship constraints
   * Django ORM is implemented alongside PostGreSQL specifically for user identity and authentication, taking advantage of Django's built-in security framework

### Database-level Business Logic
Core business logic is enforced directly at the database level using PostgreSQL, which is a central focus of the project.
- CRUD operations are implemented through stored procedures and database functions written in PL/pgSQL, rather than relying on direct table manipulation
- Relational data is protected by integrity constraints, ensuring consistency across related data
- Centralizing business rules within the database makes the system less dependent on the specific client or frontend implementation

### Data Modeling and Database Design
A comprehensive data model was designed and implemented to provide a structured foundation for the system
- Development of both Conceptual Data Model (CDM) and Physical Data Model (PDM)
- Definition of entity relationships, cardinalities, and integrity rules to ensure a consistent and robust database structure

### Data Integrity and Validation
Data integrity is enforced at the database level through constraints and triggers, preventing invalid data from being persisted
- Triggers implement automatic validation and enforce business rules that depend on changes to stored data
- Constraints enforce structural and relational consistency 
- This approach ensures that invalid data is rejected at the source rather than relying exclusively on frontend validation

### Other Features
- Soft Delete strategy to prevent loss of information that may be relevant to the system's operational history
- Database Views and Query Optimization
   * UI-oriented database views to provide enriched and application-ready data for frontend consumption
   * Flat views provide simplified structures suitable for data export, such as JSON or CSV
   * Materialized views are used for frequently accessed or computationally expensive queries, reducing the cost of repeated data retrieval

#### Setup to run:
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

#### Users to test from populate\_data.sql:

| Role   | Username          | Password    | Name              |
|--------|-------------------|-------------|-------------------|
| Admin  | gabriel.rodrigues | testpass123 | Gabriel Rodrigues |
| Client | ana.silva         | testpass123 | Ana Silva         |
| Client | bruno.santos      | testpass123 | Bruno Santos      |
| Driver | carlos.ferreira   | testpass123 | Carlos Ferreira   |
| Driver | diana.costa       | testpass123 | Diana Costa       |
| Staff  | eduardo.lopes     | testpass123 | Eduardo Lopes     |
| Staff  | filipa.mendes     | testpass123 | Filipa Mendes     |

