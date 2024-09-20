import sqlite3
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText

# Database connection
conn = sqlite3.connect('rent_collection.db')
cursor = conn.cursor()

# Create tables
cursor.execute('''
CREATE TABLE IF NOT EXISTS tenants (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    rent_due_date TEXT NOT NULL,
    rent_amount REAL NOT NULL,
    last_payment_date TEXT,
    late_fee REAL DEFAULT 0
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS payments (
    id INTEGER PRIMARY KEY,
    tenant_id INTEGER,
    payment_date TEXT NOT NULL,
    amount REAL NOT NULL,
    FOREIGN KEY (tenant_id) REFERENCES tenants(id)
)
''')

conn.commit()

# Function to send email notifications
def send_email(to_address, subject, message):
    from_address = "your_email@example.com"
    password = "your_email_password"

    msg = MIMEText(message)
    msg['Subject'] = subject
    msg['From'] = from_address
    msg['To'] = to_address

    with smtplib.SMTP('smtp.example.com', 587) as server:
        server.starttls()
        server.login(from_address, password)
        server.sendmail(from_address, to_address, msg.as_string())

# Function to send payment reminders
def send_payment_reminders():
    cursor.execute("SELECT id, name, email, rent_due_date, rent_amount FROM tenants")
    tenants = cursor.fetchall()

    for tenant in tenants:
        tenant_id, name, email, rent_due_date, rent_amount = tenant
        rent_due_date = datetime.strptime(rent_due_date, '%Y-%m-%d')

        # Check if the rent is due soon
        if rent_due_date - datetime.now() <= timedelta(days=3):
            message = f"Dear {name},\n\nThis is a reminder that your rent of ${rent_amount:.2f} is due on {rent_due_date.strftime('%Y-%m-%d')}.\n\nPlease ensure that the payment is made on time to avoid any late fees."
            send_email(email, "Rent Payment Reminder", message)

# Function to process rent payments
def process_rent_payment(tenant_id, amount):
    payment_date = datetime.now().strftime('%Y-%m-%d')

    cursor.execute("INSERT INTO payments (tenant_id, payment_date, amount) VALUES (?, ?, ?)", (tenant_id, payment_date, amount))
    cursor.execute("UPDATE tenants SET last_payment_date = ?, late_fee = 0 WHERE id = ?", (payment_date, tenant_id))

    conn.commit()

    cursor.execute("SELECT name, email FROM tenants WHERE id = ?", (tenant_id,))
    tenant = cursor.fetchone()
    name, email = tenant

    message = f"Dear {name},\n\nWe have received your rent payment of ${amount:.2f} on {payment_date}.\n\nThank you for your timely payment."
    send_email(email, "Rent Payment Confirmation", message)

# Function to apply late fees
def apply_late_fees():
    cursor.execute("SELECT id, name, email, rent_due_date, rent_amount, last_payment_date, late_fee FROM tenants")
    tenants = cursor.fetchall()

    for tenant in tenants:
        tenant_id, name, email, rent_due_date, rent_amount, last_payment_date, late_fee = tenant
        rent_due_date = datetime.strptime(rent_due_date, '%Y-%m-%d')

        # Check if the rent is overdue and late fee has not been applied
        if not last_payment_date or datetime.strptime(last_payment_date, '%Y-%m-%d') > rent_due_date:
            overdue_days = (datetime.now() - rent_due_date).days
            if overdue_days > 0:
                new_late_fee = rent_amount * 0.05 * overdue_days
                cursor.execute("UPDATE tenants SET late_fee = ? WHERE id = ?", (new_late_fee, tenant_id))
                conn.commit()

                message = f"Dear {name},\n\nYour rent payment is overdue by {overdue_days} days. A late fee of ${new_late_fee:.2f} has been applied to your account.\n\nPlease make the payment as soon as possible to avoid further charges."
                send_email(email, "Overdue Rent Payment Notice", message)

# Example usage
def main():
    # Send payment reminders
    send_payment_reminders()

    # Process a rent payment (Example: tenant with ID 1 pays $1200)
    process_rent_payment(1, 1200.00)

    # Apply late fees to overdue accounts
    apply_late_fees()

if __name__ == "__main__":
    main()

# Close the database connection when done
conn.close()
