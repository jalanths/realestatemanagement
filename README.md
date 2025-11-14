# Real Estate Management System

This is a Flask-based web application for managing a real estate business, including clients, agents, properties, contracts, and payments.

## Features

- User authentication (Admin, Agent, Client roles)
- Admin Dashboard with aggregated statistics (Total Clients, Agents, Properties, Payments)
- Property Management
- Agent and Client Management
- Contract and Payment Tracking
- Commission Management
- Database Triggers, Stored Procedures, and Functions for advanced operations

## Setup Instructions

### 1. Database Setup

This project uses MySQL.

1.  **Install MySQL Server:** If you don't have MySQL installed, download and install it from the official MySQL website.
2.  **Create Database:** The application expects a database named `real_estate_db`. You can create it manually or by running the `mysqltables.sql` script.
3.  **Configure `app.py`:** Update the `db_config` dictionary in `app.py` with your MySQL credentials:

    ```python
    db_config = {
        'host': 'localhost',
        'user': 'your_mysql_username',
        'password': 'your_mysql_password',
        'database': 'real_estate_db'
    }
    ```
4.  **Run SQL Script:** Execute the `database/mysqltables.sql` script to create the necessary tables, triggers, procedures, and seed initial data.

    ```bash
    mysql -u your_mysql_username -p real_estate_db < database/mysqltables.sql
    ```
    (You will be prompted for your MySQL password)

### 2. Python Environment Setup

1.  **Clone the repository:**

    ```bash
    git clone https://github.com/jalanths/realestatemanagement.git
    cd realestatemanagement
    ```
2.  **Create a virtual environment (recommended):**

    ```bash
    python -m venv venv
    ```
3.  **Activate the virtual environment:**
    *   **Windows:** `venv\Scripts\activate`
    *   **macOS/Linux:** `source venv/bin/activate`
4.  **Install dependencies:**

    ```bash
    pip install -r requirements.txt
    ```

### 3. Running the Application

1.  **Ensure MySQL is running** and you have completed the database setup.
2.  **Run the Flask application:**

    ```bash
    python app.py
    ```
3.  **Access the application:** Open your web browser and go to `http://127.0.0.1:5000`

## Default Credentials

- **Admin:**
    - Email: `admin@test.com`
    - Password: `admin`
- **Agent:**
    - Email: `agent@test.com`
    - Password: `agent`
- **Client:**
    - Email: `client@test.com`
    - Password: `client`
