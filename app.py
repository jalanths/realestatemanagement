from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import mysql.connector
import os

from werkzeug.security import generate_password_hash, check_password_hash

# --- Flask App Setup ---
app = Flask(__name__)
app.secret_key = os.urandom(24) # Required for sessions

# --- Flask-Login Setup ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login' # Redirect to login page if not authenticated

# --- Database Configuration ---
# !!! IMPORTANT: Update these with your MySQL details !!!
db_config = {
    'host': 'localhost',
    'user': 'root',               # Your MySQL username
    'password': '123456789',        # Your MySQL password
    'database': 'real_estate_db'
}

# --- User Model for Flask-Login ---
class User(UserMixin):
    def __init__(self, id, username, role, password_hash=None):
        self.id = id
        self.username = username
        self.role = role
        self.password_hash = password_hash

@login_manager.user_loader
def load_user(user_id):
    conn = get_db_connection()
    if not conn:
        return None
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT USER_ID, Email, Role, PasswordHash FROM user WHERE USER_ID = %s", (user_id,))
    user_data = cursor.fetchone()
    cursor.close()
    conn.close()
    if user_data:
        return User(id=user_data['USER_ID'], username=user_data['Email'], role=user_data['Role'], password_hash=user_data['PasswordHash'])
    return None

# --- Database Helper Function ---
def get_db_connection():
    try:
        conn = mysql.connector.connect(**db_config)
        return conn
    except mysql.connector.Error as err:
        print(f"Error connecting to database: {err}")
        return None

# --- Main Login/Logout Routes ---
@app.route("/")
def index():
    """Serves the login page."""
    return render_template('login.html')

@app.route("/login", methods=['POST'])
def login():
    name = request.form['name']
    password = request.form['password']

    conn = get_db_connection()
    if not conn:
        return "Database connection failed", 500
    cursor = conn.cursor(dictionary=True)

    query = "SELECT * FROM user WHERE Email = %s"
    cursor.execute(query, (name,))
    user_data = cursor.fetchone()
    
    if user_data and check_password_hash(user_data['PasswordHash'], password):
        user = User(id=user_data['USER_ID'], username=user_data['Email'], role=user_data['Role'], password_hash=user_data['PasswordHash'])
        login_user(user)
        
        if user.role == 'Admin':
            return redirect(url_for('admin_dashboard'))
        elif user.role == 'Agent':
            return redirect(url_for('agent_dashboard'))
        else:
            return redirect(url_for('client_dashboard'))
    else:
        flash("Invalid name or password.", "error")
        return redirect(url_for('index'))
    
    cursor.close()
    conn.close()

@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "success")
    return redirect(url_for('index'))

@app.route("/signup", methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form['name']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        role = request.form['role']

        if password != confirm_password:
            flash('Passwords do not match.', 'error')
            return redirect(url_for('signup'))

        conn = get_db_connection()
        if not conn:
            flash('Database connection failed.', 'error')
            return redirect(url_for('signup'))
        cursor = conn.cursor(dictionary=True)

        # Check if user already exists
        cursor.execute("SELECT * FROM user WHERE Email = %s", (name,))
        if cursor.fetchone():
            flash('Name already registered.', 'error')
            cursor.close()
            conn.close()
            return redirect(url_for('signup'))

        # Hash the password and insert new user
        password_hash = generate_password_hash(password)
        cursor.execute("INSERT INTO user (Email, PasswordHash, Role) VALUES (%s, %s, %s)", (name, password_hash, role))
        conn.commit()
        
        # Also need to add to client or agent table
        user_id = cursor.lastrowid
        if role == 'Client':
            cursor.execute("INSERT INTO client (CLIENT_ID, Name) VALUES (%s, %s)", (user_id, name))
            conn.commit()
            
            # Create a new MySQL user for the client with read-only privileges
            try:
                # Use a separate cursor without dictionary=True for this
                nondict_cursor = conn.cursor()
                nondict_cursor.execute(f"CREATE USER '{name}'@'localhost' IDENTIFIED BY '{password}'")
                nondict_cursor.execute(f"GRANT SELECT ON real_estate_db.* TO '{name}'@'localhost'")
                conn.commit()
                flash(f"MySQL user for client '{name}' created with read-only privileges.", "info")
                nondict_cursor.close()
            except mysql.connector.Error as err:
                flash(f"Could not create MySQL user for client '{name}': {err}", "error")
        elif role == 'Agent':
            commission_perc = request.form.get('commission_perc')
            cursor.execute("INSERT INTO agent (AGENT_ID, Name, CommissionPerc) VALUES (%s, %s, %s)", (user_id, name, commission_perc))
            conn.commit()
            
            # Create a new MySQL user for the agent with limited privileges
            try:
                # Use a separate cursor without dictionary=True for this
                nondict_cursor = conn.cursor()
                nondict_cursor.execute(f"CREATE USER '{name}'@'localhost' IDENTIFIED BY '{password}'")
                nondict_cursor.execute(f"GRANT SELECT, INSERT, UPDATE ON real_estate_db.property TO '{name}'@'localhost'")
                nondict_cursor.execute(f"GRANT SELECT, INSERT, UPDATE ON real_estate_db.client TO '{name}'@'localhost'")
                nondict_cursor.execute(f"GRANT SELECT, INSERT, UPDATE ON real_estate_db.contract TO '{name}'@'localhost'")
                conn.commit()
                flash(f"MySQL user for agent '{name}' created with limited privileges.", "info")
                nondict_cursor.close()
            except mysql.connector.Error as err:
                flash(f"Could not create MySQL user for agent '{name}': {err}", "error")


        cursor.close()
        conn.close()

        flash('Account created successfully! Please log in.', 'success')
        return redirect(url_for('index'))

    return render_template('signup.html')


# --- Helper Function to Check for Admin ---
def is_admin():
    return current_user.is_authenticated and current_user.role == 'Admin'

def is_agent():
    return current_user.is_authenticated and current_user.role == 'Agent'

# -----------------------------------------------------------------
# REQUIREMENT 1: 1 Aggregate Query with GUI
# -----------------------------------------------------------------
@app.route("/admin_dashboard")
@login_required
def admin_dashboard():
    if not is_admin():
        return redirect(url_for('index'))
        
    conn = get_db_connection()
    if not conn:
        flash("Database connection failed.", "error")
        return redirect(url_for('index'))
    cursor = conn.cursor(dictionary=True)
    
    # Aggregate Query 1: Total Clients
    cursor.execute("SELECT COUNT(*) AS client_count FROM client")
    stat_clients = cursor.fetchone()

    # Aggregate Query 2: Total Agents
    cursor.execute("SELECT COUNT(*) AS agent_count FROM agent")
    stat_agents = cursor.fetchone()

    # Aggregate Query 3: Total Properties
    cursor.execute("SELECT COUNT(*) AS property_count FROM property")
    stat_properties = cursor.fetchone()
    
    # Aggregate Query 4: SUM of Payments
    cursor.execute("SELECT SUM(Amount) AS total_payment FROM payment")
    stat_payment = cursor.fetchone()
    
    stats = {
        'client_count': stat_clients['client_count'],
        'agent_count': stat_agents['agent_count'],
        'property_count': stat_properties['property_count'],
        'total_payment': stat_payment['total_payment']
    }
    
    cursor.close()
    conn.close()
    
    return render_template('admin_dashboard.html', stats=stats)

# -----------------------------------------------------------------
# REQUIREMENT 2: 1 Join Query with GUI
# -----------------------------------------------------------------
@app.route("/properties")
@login_required
def properties():
    if not is_admin():
        return redirect(url_for('index'))
        
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # This is a 3-table JOIN query
    query = """
        SELECT 
            p.PROPERTY_ID, p.Street, p.PRICE, 
            a.Name AS AgentName, 
            c.Name AS ClientName
        FROM property p
        JOIN agent a ON p.AGENT_ID = a.AGENT_ID
        JOIN client c ON p.CLIENT_ID = c.CLIENT_ID
        ORDER BY p.PRICE DESC
    """
    cursor.execute(query)
    properties = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('property_list.html', properties=properties)

# -----------------------------------------------------------------
# REQUIREMENT 3: 1 Nested Query with GUI
# -----------------------------------------------------------------
@app.route("/agent_search", methods=['GET', 'POST'])
@login_required
def agent_search():
    if not is_admin():
        return redirect(url_for('index'))
    
    agents = []
    city = ""
    if request.method == 'POST':
        city = request.form['city']
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # This is a NESTED query
        query = """
            SELECT * FROM agent 
            WHERE OFFICE_ID IN (
                SELECT OFFICE_ID FROM office WHERE City = %s
            )
        """
        cursor.execute(query, (city,))
        agents = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
    return render_template('agent_search.html', agents=agents, city=city)

# -----------------------------------------------------------------
# REQUIREMENT 4: Triggers with GUI
# -----------------------------------------------------------------
@app.route("/edit_property/<int:id>", methods=['GET', 'POST'])
@login_required
def edit_property(id):
    if not is_admin():
        return redirect(url_for('index'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        new_price = request.form['price']
        
        # This UPDATE will fire the 'trg_PropertyPriceAudit' trigger
        # This is the "Triggers with GUI" part.
        cursor.execute("UPDATE property SET PRICE = %s WHERE PROPERTY_ID = %s", (new_price, id))
        conn.commit()
        flash(f"Property {id} price updated. Trigger fired!", "success")
        
        cursor.close()
        conn.close()
        return redirect(url_for('properties'))

    # GET request: Show the edit form
    cursor.execute("SELECT * FROM property WHERE PROPERTY_ID = %s", (id,))
    prop = cursor.fetchone()
    cursor.close()
    conn.close()
    return render_template('edit_property.html', prop=prop)

# -----------------------------------------------------------------
# REQUIREMENT 5: Procedures/Functions with GUI
# -----------------------------------------------------------------
@app.route("/payments")
@login_required
def payments():
    if not is_admin():
        return redirect(url_for('index'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Get payments that haven't had commission calculated yet
    query = """
        SELECT p.* FROM payment p
        LEFT JOIN commission comm ON comm.COMMISSION_ID IN (
            SELECT e.COMMISSION_ID FROM earns e WHERE e.AGENT_ID IN (
                SELECT c.AGENT_ID FROM contract c WHERE c.CONTRACT_ID = p.CONTRACT_ID
            )
        )
        WHERE comm.COMMISSION_ID IS NULL
    """ # This is a complex query, a simple "SELECT * FROM payment" also works
    
    cursor.execute("SELECT * FROM payment")
    payments = cursor.fetchall()
    
    cursor.close()
    conn.close()
    return render_template('payments.html', payments=payments)

@app.route("/add_payment", methods=['GET', 'POST'])
@login_required
def add_payment():
    if not is_admin():
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    if not conn:
        flash("Database connection failed.", "error")
        return redirect(url_for('admin_dashboard'))
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        contract_id = request.form['contract_id']
        payment_date = request.form['payment_date']
        amount = request.form['amount']
        
        query = "INSERT INTO payment (Payment_Date, Amount, CONTRACT_ID) VALUES (%s, %s, %s)"
        cursor.execute(query, (payment_date, amount, contract_id))
        conn.commit()

        cursor.close()
        conn.close()

        flash('Payment added successfully!', 'success')
        return redirect(url_for('payments'))

    # For GET request, we need to fetch contracts to populate a dropdown
    cursor.execute("""
        SELECT c.CONTRACT_ID, cl.Name AS ClientName, a.Name AS AgentName
        FROM contract c
        JOIN client cl ON c.CLIENT_ID = cl.CLIENT_ID
        JOIN agent a ON c.AGENT_ID = a.AGENT_ID
    """)
    contracts = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return render_template('add_payment.html', contracts=contracts)

# -----------------------------------------------------------------
# REQUIREMENT 7: Functions with GUI
# -----------------------------------------------------------------
@app.route("/agent_sales_report", methods=['GET', 'POST'])
@login_required
def agent_sales_report():
    if not is_admin():
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    if not conn:
        flash("Database connection failed.", "error")
        return redirect(url_for('admin_dashboard')) # Or an appropriate error page
    cursor = conn.cursor(dictionary=True)
    
    total_sales = None
    agent_id_selected = None

    try:
        if request.method == 'POST':
            agent_id_selected = request.form['agent_id']
            
            # This is the "Function with GUI" part.
            # We call the function 'fn_GetAgentTotalSales'
            query = "SELECT fn_GetAgentTotalSales(%s) AS sales"
            
            cursor.execute(query, (agent_id_selected,))
            result = cursor.fetchone()
            if result:
                total_sales = result['sales']
            flash(f"Total sales calculated for Agent ID {agent_id_selected}.", "success")
            
    except mysql.connector.Error as err:
        flash(f"Error calculating sales: {err}", "error")
    finally:
        # GET or POST: We always need the list of agents for the dropdown
        cursor.execute("SELECT AGENT_ID, Name FROM agent")
        agents = cursor.fetchall()
        
        cursor.close()
        conn.close()
    
    return render_template(
        'agent_sales_report.html', 
        agents=agents, 
        total_sales=total_sales, 
        agent_id_selected=int(agent_id_selected) if agent_id_selected else None
    )



@app.route('/high_value_clients')
@login_required
def high_value_clients():
    if not is_admin():
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('index'))

    conn = get_db_connection()
    if not conn:
        flash("Database connection failed.", "error")
        return redirect(url_for('admin_dashboard'))
    cursor = conn.cursor(dictionary=True)

    query = """
        SELECT
            cl.CLIENT_ID,
            cl.Name,
            COUNT(p.Payment_No) AS NumPayments,
            SUM(p.Amount) AS TotalPayments
        FROM client cl
        JOIN contract c ON cl.CLIENT_ID = c.CLIENT_ID
        JOIN payment p ON c.CONTRACT_ID = p.CONTRACT_ID
        GROUP BY cl.CLIENT_ID, cl.Name
        ORDER BY TotalPayments DESC
        LIMIT 10
    """
    cursor.execute(query)
    clients = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template('high_value_clients.html', clients=clients)

@app.route('/delete_user/<int:user_id>')
@login_required
def delete_user(user_id):
    if not is_admin():
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('index'))

    conn = get_db_connection()
    if not conn:
        flash("Database connection failed.", "error")
        return redirect(url_for('admin_dashboard'))
    cursor = conn.cursor(dictionary=True)

    try:
        # Get user role before deleting
        cursor.execute("SELECT Role, CLIENT_ID, AGENT_ID FROM user WHERE USER_ID = %s", (user_id,))
        user = cursor.fetchone()

        if user:
            # Delete from user table
            cursor.execute("DELETE FROM user WHERE USER_ID = %s", (user_id,))

            # Delete from client or agent table
            if user['Role'] == 'Client' and user['CLIENT_ID']:
                cursor.execute("DELETE FROM client WHERE CLIENT_ID = %s", (user['CLIENT_ID'],))
            elif user['Role'] == 'Agent' and user['AGENT_ID']:
                cursor.execute("DELETE FROM agent WHERE AGENT_ID = %s", (user['AGENT_ID'],))
            
            conn.commit()
            flash(f"User ID {user_id} has been deleted.", "success")
        else:
            flash(f"User ID {user_id} not found.", "warning")

    except mysql.connector.Error as err:
        conn.rollback()
        flash(f"Error deleting user: {err}. This user might be referenced in other records (e.g., properties, contracts).", "error")
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('admin_dashboard'))

@app.route('/add_commission', methods=['GET', 'POST'])
@login_required
def add_commission():
    if not is_admin():
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    if not conn:
        flash("Database connection failed.", "error")
        return redirect(url_for('admin_dashboard'))
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        agent_id = request.form['agent_id']
        amount = request.form['amount']
        percentage = request.form.get('percentage') # Optional
        earned_date = request.form['earned_date']
        
        try:
            # Insert into commission table
            cursor.execute("INSERT INTO commission (Amount, Percentage) VALUES (%s, %s)", (amount, percentage))
            commission_id = cursor.lastrowid

            # Insert into earns table
            cursor.execute("INSERT INTO earns (AGENT_ID, COMMISSION_ID, Earned_Date) VALUES (%s, %s, %s)", (agent_id, commission_id, earned_date))
            
            conn.commit()
            flash('Commission added successfully!', 'success')
        except mysql.connector.Error as err:
            conn.rollback()
            flash(f"Database error: {err}", "error")
        
        return redirect(url_for('admin_dashboard'))

    # For GET request, we need to fetch agents to populate a dropdown
    cursor.execute("SELECT AGENT_ID, Name FROM agent")
    agents = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('add_commission.html', agents=agents)

# --- Placeholder Dashboards for Agent/Client ---
@app.route("/agent_dashboard")
@login_required
def agent_dashboard():
    if current_user.role != 'Agent':
        return redirect(url_for('index'))

    conn = get_db_connection()
    if not conn:
        flash("Database connection failed.", "error")
        return redirect(url_for('index'))
    cursor = conn.cursor(dictionary=True)

    # Fetch earnings for the logged-in agent
    query = """
        SELECT c.Amount, c.Percentage, e.Earned_Date
        FROM commission c
        JOIN earns e ON c.COMMISSION_ID = e.COMMISSION_ID
        WHERE e.AGENT_ID = %s
    """
    cursor.execute(query, (current_user.id,))
    earnings = cursor.fetchall()

    total_earnings = sum(item['Amount'] or 0 for item in earnings)

    cursor.close()
    conn.close()

    return render_template('agent_dashboard.html', earnings=earnings, total_earnings=total_earnings)

@app.route("/client_dashboard")
@login_required
def client_dashboard():
    if current_user.role != 'Client':
        return redirect(url_for('index'))

    conn = get_db_connection()
    if not conn:
        flash("Database connection failed.", "error")
        return redirect(url_for('index'))
    cursor = conn.cursor(dictionary=True)

    # Fetch payments for the logged-in client
    query_payments = """
        SELECT p.Payment_Date, p.CONTRACT_ID, p.Amount
        FROM payment p
        JOIN contract c ON p.CONTRACT_ID = c.CONTRACT_ID
        WHERE c.CLIENT_ID = %s
    """
    cursor.execute(query_payments, (current_user.id,))
    payments = cursor.fetchall()

    # Fetch properties for the logged-in client
    query_properties = "SELECT * FROM property WHERE CLIENT_ID = %s"
    cursor.execute(query_properties, (current_user.id,))
    properties = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template('client_dashboard.html', payments=payments, properties=properties)

@app.route("/add_client", methods=['GET', 'POST'])
@login_required
def add_client():
    if not is_agent():
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    if not conn:
        flash("Database connection failed.", "error")
        return redirect(url_for('agent_dashboard'))
    cursor = conn.cursor(dictionary=True)

    client_selected = None
    if request.method == 'POST':
        client_id = request.form['client_id']
        fname = request.form['fname']
        lname = request.form['lname']
        phone = request.form['phone']
        street = request.form['street']
        city = request.form['city']
        state = request.form['state']
        zip_code = request.form['zip']
        
        # Update client details
        try:
            cursor.execute("""
                UPDATE client 
                SET Fname = %s, Lname = %s, AddressStreet = %s, City = %s, State = %s, ZIPCode = %s 
                WHERE CLIENT_ID = %s
            """, (fname, lname, street, city, state, zip_code, client_id))
            
            # Update or insert phone number
            cursor.execute("SELECT * FROM clientphone WHERE CLIENT_ID = %s", (client_id,))
            if cursor.fetchone():
                if phone:
                    cursor.execute("UPDATE clientphone SET PhoneNumber = %s WHERE CLIENT_ID = %s", (phone, client_id))
                else:
                    cursor.execute("DELETE FROM clientphone WHERE CLIENT_ID = %s", (client_id,))
            elif phone:
                cursor.execute("INSERT INTO clientphone (CLIENT_ID, PhoneNumber) VALUES (%s, %s)", (client_id, phone))
            
            conn.commit()
            flash(f"Client details for ID {client_id} updated successfully!", "success")
        except mysql.connector.Error as err:
            flash(f"Database error: {err}. Please ensure the client table has address columns (AddressStreet, City, State, ZIPCode).", "error")
        
        return redirect(url_for('agent_dashboard'))
    else: # GET request
        client_id_param = request.args.get('client_id')
        if client_id_param:
            try:
                cursor.execute("""
                    SELECT c.CLIENT_ID, c.Name, c.Fname, c.Lname, c.AddressStreet, c.City, c.State, c.ZIPCode, cp.PhoneNumber
                    FROM client c
                    LEFT JOIN clientphone cp ON c.CLIENT_ID = cp.CLIENT_ID
                    WHERE c.CLIENT_ID = %s
                """, (client_id_param,))
                client_selected = cursor.fetchone()
            except mysql.connector.Error as err:
                flash(f"Database error: {err}. The client table may be missing address columns.", "error")


    # Fetch all clients for the dropdown
    cursor.execute("SELECT CLIENT_ID, Name FROM client")
    clients = cursor.fetchall()
    
    cursor.close()
    conn.close()

    return render_template('add_client.html', clients=clients, client_selected=client_selected)

@app.route("/add_property", methods=['GET', 'POST'])
@login_required
def add_property():
    if not is_agent():
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        street = request.form['street']
        city = request.form['city']
        state = request.form['state']
        zip_code = request.form['zip']
        price = request.form['price']
        prop_type = request.form['type']
        size = request.form['size']
        client_id = request.form['client_id']
        
        conn = get_db_connection()
        if not conn:
            flash("Database connection failed.", "error")
            return redirect(url_for('agent_dashboard'))
        cursor = conn.cursor()

        query = "INSERT INTO property (Street, City, State, ZIP, PRICE, TYPE, SIZE, CLIENT_ID, AGENT_ID) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"
        cursor.execute(query, (street, city, state, zip_code, price, prop_type, size, client_id, current_user.id))
        conn.commit()

        cursor.close()
        conn.close()

        flash('Property added successfully!', 'success')
        return redirect(url_for('agent_dashboard'))

    # For GET request, we need to fetch clients to populate a dropdown
    conn = get_db_connection()
    if not conn:
        flash("Database connection failed.", "error")
        return redirect(url_for('agent_dashboard'))
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT CLIENT_ID, Name FROM client")
    clients = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return render_template('add_property.html', clients=clients)

@app.route("/add_contract", methods=['GET', 'POST'])
@login_required
def add_contract():
    if not is_agent():
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    if not conn:
        flash("Database connection failed.", "error")
        return redirect(url_for('agent_dashboard'))
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        client_id = request.form['client_id']
        start_date = request.form['start_date']
        end_date = request.form['end_date']
        amount = request.form['amount']
        
        query = "INSERT INTO contract (Start_Date, End_Date, Amount, CLIENT_ID, AGENT_ID) VALUES (%s, %s, %s, %s, %s)"
        cursor.execute(query, (start_date, end_date, amount, client_id, current_user.id))
        conn.commit()

        cursor.close()
        conn.close()

        flash('Contract added successfully!', 'success')
        return redirect(url_for('agent_dashboard'))

    # For GET request, we need to fetch clients to populate a dropdown
    cursor.execute("SELECT CLIENT_ID, Name FROM client")
    clients = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return render_template('add_contract.html', clients=clients)

# --- Run the App ---
if __name__ == '__main__':
    with app.app_context():
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor(dictionary=True)
            # Check if admin user exists
            cursor.execute("SELECT * FROM user WHERE Email = 'admin@test.com' AND Role = 'Admin'")
            admin_user = cursor.fetchone()

            hashed_password = generate_password_hash('admin')

            if not admin_user:
                # Create a default admin user with a hashed password
                cursor.execute("INSERT INTO user (Email, PasswordHash, Role) VALUES (%s, %s, %s)", ('admin@test.com', hashed_password, 'Admin'))
                conn.commit()
                print("Default admin user created: admin@test.com / admin")
            else:
                # If user exists, check if password needs updating
                if not check_password_hash(admin_user['PasswordHash'], 'admin'):
                    cursor.execute("UPDATE user SET PasswordHash = %s WHERE USER_ID = %s", (hashed_password, admin_user['USER_ID']))
                    conn.commit()
                    print("Admin user password updated.")
                else:
                    print("Admin user already exists with correct password.")
            
            cursor.close()
            conn.close()
        else:
            print("Could not connect to database to check/create default admin user.")
    app.run(debug=True)