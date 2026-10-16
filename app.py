from flask import Flask,request,redirect,url_for,render_template_string
import mysql.connector
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from datetime import datetime
import os

app=Flask(__name__)

# MySQL Configuration
DB_CONFIG={
    "host":"localhost",
    "user":"root",
    "password":"Dhanush@1234"
}

# Create database and tables
def setup_database():
    con=mysql.connector.connect(**DB_CONFIG)
    cur=con.cursor()
    cur.execute("CREATE DATABASE IF NOT EXISTS expense_tracker")
    cur.execute("USE expense_tracker")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS categories(
        category_id INT AUTO_INCREMENT PRIMARY KEY,
        category_name VARCHAR(50) UNIQUE NOT NULL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS expenses(
        expense_id INT AUTO_INCREMENT PRIMARY KEY,
        expense_date DATE NOT NULL,
        category_id INT NOT NULL,
        amount DECIMAL(12,2) NOT NULL,
        description VARCHAR(255),
        payment_method VARCHAR(50),
        FOREIGN KEY(category_id) REFERENCES categories(category_id)
    )
    """)

    categories=[
        "Food","Travel","Education","Shopping",
        "Bills","Entertainment","Health","Other"
    ]

    for category in categories:
        cur.execute(
            "INSERT IGNORE INTO categories(category_name) VALUES(%s)",
            (category,)
        )

    con.commit()
    cur.close()
    con.close()

def get_connection():
    return mysql.connector.connect(
        **DB_CONFIG,
        database="expense_tracker"
    )

def get_expenses(start_date=None,end_date=None,category=None):
    con=get_connection()
    query="""
    SELECT e.expense_id,e.expense_date,c.category_name,
           e.amount,e.description,e.payment_method
    FROM expenses e
    JOIN categories c ON e.category_id=c.category_id
    WHERE 1=1
    """
    values=[]

    if start_date:
        query+=" AND e.expense_date >= %s"
        values.append(start_date)

    if end_date:
        query+=" AND e.expense_date <= %s"
        values.append(end_date)

    if category:
        query+=" AND c.category_name = %s"
        values.append(category)

    query+=" ORDER BY e.expense_date DESC,e.expense_id DESC"

    cur=con.cursor()
    cur.execute(query,tuple(values))
    rows=cur.fetchall()
    cur.close()
    con.close()
    return rows

def get_categories():
    con=get_connection()
    cur=con.cursor()
    cur.execute("SELECT category_name FROM categories ORDER BY category_name")
    rows=cur.fetchall()
    cur.close()
    con.close()
    return [row[0] for row in rows]

def generate_charts():
    os.makedirs("static",exist_ok=True)
    rows=get_expenses()

    if not rows:
        for filename in ["category_pie.png","monthly_bar.png"]:
            path=os.path.join("static",filename)
            if os.path.exists(path):
                os.remove(path)
        return

    df=pd.DataFrame(rows,columns=[
        "id","date","category","amount","description","payment"
    ])

    df["amount"]=pd.to_numeric(df["amount"])
    df["date"]=pd.to_datetime(df["date"])

    # Category pie chart
    category_totals=df.groupby("category")["amount"].sum()

    plt.figure(figsize=(7,5))
    plt.pie(
        category_totals,
        labels=category_totals.index,
        autopct="%1.1f%%",
        startangle=90
    )
    plt.title("Category-wise Expense Distribution")
    plt.tight_layout()
    plt.savefig("static/category_pie.png")
    plt.close()

    # Monthly bar chart
    df["month"]=df["date"].dt.to_period("M").astype(str)
    monthly_totals=df.groupby("month")["amount"].sum()

    plt.figure(figsize=(8,5))
    monthly_totals.plot(kind="bar")
    plt.title("Monthly Expenses")
    plt.xlabel("Month")
    plt.ylabel("Amount")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig("static/monthly_bar.png")
    plt.close()

# HTML Interface
HTML="""
<!DOCTYPE html>
<html>
<head>
<title>Personal Expense Tracker</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
body{
    margin:0;
    font-family:Arial,sans-serif;
    background:#f1f5f9;
    color:#1e293b;
}
header{
    background:#1d4ed8;
    color:white;
    padding:25px;
    text-align:center;
}
.container{
    max-width:1100px;
    margin:25px auto;
    padding:15px;
}
.card{
    background:white;
    padding:20px;
    margin-bottom:20px;
    border-radius:12px;
    box-shadow:0 3px 12px #0001;
}
.grid{
    display:grid;
    grid-template-columns:repeat(auto-fit,minmax(200px,1fr));
    gap:15px;
}
input,select,button{
    box-sizing:border-box;
    width:100%;
    padding:11px;
    margin:6px 0;
    border:1px solid #cbd5e1;
    border-radius:6px;
}
button,.btn{
    background:#2563eb;
    color:white;
    border:0;
    cursor:pointer;
    text-decoration:none;
    padding:10px;
    border-radius:6px;
    display:inline-block;
}
.delete{
    background:#dc2626;
}
.edit{
    background:#059669;
}
table{
    width:100%;
    border-collapse:collapse;
    background:white;
}
th,td{
    padding:11px;
    text-align:left;
    border-bottom:1px solid #e2e8f0;
}
th{
    background:#dbeafe;
}
.table-wrap{
    overflow-x:auto;
}
.stat{
    font-size:25px;
    font-weight:bold;
    color:#2563eb;
}
.charts{
    display:grid;
    grid-template-columns:repeat(auto-fit,minmax(280px,1fr));
    gap:20px;
}
.charts img{
    width:100%;
}
.error{
    background:#fee2e2;
    padding:12px;
    border-radius:6px;
}
@media(max-width:600px){
    header{padding:15px}
    .container{padding:10px}
}
</style>
</head>
<body>

<header>
<h1>Personal Expense Tracker</h1>
<p>Track spending. Understand your expenses. Plan better.</p>
</header>

<div class="container">

{% if message %}
<div class="card">{{message}}</div>
{% endif %}

<div class="grid">
<div class="card">
<h3>Total Expenses</h3>
<div class="stat">₹{{"%.2f"|format(total)}}</div>
</div>
<div class="card">
<h3>This Month</h3>
<div class="stat">₹{{"%.2f"|format(month_total)}}</div>
</div>
<div class="card">
<h3>Total Records</h3>
<div class="stat">{{count}}</div>
</div>
<div class="card">
<h3>Highest Spending</h3>
<div class="stat" style="font-size:19px">{{highest}}</div>
</div>
</div>

<div class="card">
<h2>{{"Edit Expense" if edit else "Add New Expense"}}</h2>

<form method="POST" action="{{url_for('save_expense')}}">
<input type="hidden" name="expense_id"
value="{{edit[0] if edit else ''}}">

<div class="grid">
<div>
<label>Date</label>
<input type="date" name="expense_date"
value="{{edit[1] if edit else today}}" required>
</div>

<div>
<label>Category</label>
<select name="category" required>
{% for c in categories %}
<option value="{{c}}"
{% if edit and edit[2]==c %}selected{% endif %}>
{{c}}
</option>
{% endfor %}
</select>
</div>

<div>
<label>Amount (₹)</label>
<input type="number" name="amount" min="0.01"
step="0.01"
value="{{edit[3] if edit else ''}}" required>
</div>

<div>
<label>Payment Method</label>
<select name="payment_method" required>
{% for p in ["Cash","UPI","Card","Net Banking","Other"] %}
<option value="{{p}}"
{% if edit and edit[5]==p %}selected{% endif %}>
{{p}}
</option>
{% endfor %}
</select>
</div>
</div>

<label>Description</label>
<input type="text" name="description"
placeholder="Enter expense details"
maxlength="255"
value="{{edit[4] if edit else ''}}">

<button type="submit">
{{"Update Expense" if edit else "Add Expense"}}
</button>

{% if edit %}
<a class="btn delete" href="{{url_for('home')}}">Cancel</a>
{% endif %}
</form>
</div>

<div class="card">
<h2>Filter Expenses</h2>
<form method="GET" action="/">
<div class="grid">
<div>
<label>Start Date</label>
<input type="date" name="start_date" value="{{start_date}}">
</div>
<div>
<label>End Date</label>
<input type="date" name="end_date" value="{{end_date}}">
</div>
<div>
<label>Category</label>
<select name="category">
<option value="">All Categories</option>
{% for c in categories %}
<option value="{{c}}"
{% if selected_category==c %}selected{% endif %}>
{{c}}
</option>
{% endfor %}
</select>
</div>
<div>
<label>&nbsp;</label>
<button type="submit">Apply Filters</button>
<a class="btn" href="{{url_for('home')}}">Clear Filters</a>
</div>
</div>
</form>
</div>

<div class="card">
<h2>Expense Records</h2>
<div class="table-wrap">
<table>
<tr>
<th>ID</th>
<th>Date</th>
<th>Category</th>
<th>Amount</th>
<th>Description</th>
<th>Payment</th>
<th>Actions</th>
</tr>

{% for e in expenses %}
<tr>
<td>{{e[0]}}</td>
<td>{{e[1]}}</td>
<td>{{e[2]}}</td>
<td>₹{{"%.2f"|format(e[3]|float)}}</td>
<td>{{e[4] or "-"}}</td>
<td>{{e[5]}}</td>
<td>
<a class="btn edit"
href="{{url_for('home',edit_id=e[0])}}">Edit</a>
<form method="POST"
action="{{url_for('delete_expense',expense_id=e[0])}}"
onsubmit="return confirm('Delete this expense?')">
<button class="delete" type="submit">Delete</button>
</form>
</td>
</tr>
{% endfor %}

{% if not expenses %}
<tr><td colspan="7">No expenses found.</td></tr>
{% endif %}
</table>
</div>

<h3>Filtered Total: ₹{{"%.2f"|format(filtered_total)}}</h3>
</div>

<div class="card">
<h2>Category-wise Analysis</h2>
<div class="table-wrap">
<table>
<tr><th>Category</th><th>Total Spending</th><th>Share</th></tr>
{% for c in analysis %}
<tr>
<td>{{c[0]}}</td>
<td>₹{{"%.2f"|format(c[1])}}</td>
<td>{{"%.1f"|format(c[2])}}%</td>
</tr>
{% endfor %}
</table>
</div>
</div>

<div class="card">
<h2>Expense Charts</h2>
<div class="charts">
<div>
<h3>Category Pie Chart</h3>
{% if chart_exists %}
<img src="{{url_for('static',filename='category_pie.png')}}?v={{chart_version}}">
{% else %}
<p>Add an expense to generate the chart.</p>
{% endif %}
</div>
<div>
<h3>Monthly Bar Chart</h3>
{% if chart_exists %}
<img src="{{url_for('static',filename='monthly_bar.png')}}?v={{chart_version}}">
{% else %}
<p>Add an expense to generate the chart.</p>
{% endif %}
</div>
</div>
</div>

<div class="card">
<h2>Monthly Expense Report</h2>
<form method="GET" action="/">
<label>Select Month</label>
<input type="month" name="report_month" value="{{report_month}}">
<button type="submit">Generate Report</button>
</form>
<h3>Report for {{report_month}}</h3>
<p>Total: <b>₹{{"%.2f"|format(report_total)}}</b></p>
<p>Number of records: <b>{{report_count}}</b></p>
{% for c in report_categories %}
<p>{{c[0]}}: ₹{{"%.2f"|format(c[1])}}</p>
{% endfor %}
</div>

</div>
</body>
</html>
"""

@app.route("/")
def home():
    try:
        today=datetime.today().strftime("%Y-%m-%d")
        current_month=datetime.today().strftime("%Y-%m")

        start_date=request.args.get("start_date","")
        end_date=request.args.get("end_date","")
        selected_category=request.args.get("category","")
        report_month=request.args.get("report_month",current_month)
        edit_id=request.args.get("edit_id","")

        if start_date and end_date and start_date>end_date:
            return "Error: Start date cannot be after end date.",400

        # All expense records
        all_rows=get_expenses()

        # Filtered records
        expenses=get_expenses(
            start_date or None,
            end_date or None,
            selected_category or None
        )

        total=float(sum(float(e[3]) for e in all_rows))
        filtered_total=float(sum(float(e[3]) for e in expenses))

        month_rows=[
            e for e in all_rows
            if str(e[1])[:7]==current_month
        ]
        month_total=float(sum(float(e[3]) for e in month_rows))

        count=len(all_rows)

        # Category analysis
        category_totals={}
        for e in all_rows:
            category_totals[e[2]]=category_totals.get(e[2],0)+float(e[3])

        analysis=[]
        for name,amount in sorted(
            category_totals.items(),
            key=lambda item:item[1],
            reverse=True
        ):
            share=(amount/total*100) if total else 0
            analysis.append((name,amount,share))

        highest=analysis[0][0] if analysis else "None"

        # Monthly report
        report_rows=[
            e for e in all_rows
            if str(e[1])[:7]==report_month
        ]

        report_total=float(sum(float(e[3]) for e in report_rows))
        report_count=len(report_rows)
        report_data={}

        for e in report_rows:
            report_data[e[2]]=report_data.get(e[2],0)+float(e[3])

        report_categories=sorted(
            report_data.items(),
            key=lambda item:item[1],
            reverse=True
        )

        # Optional edit record
        edit=None
        if edit_id:
            con=get_connection()
            cur=con.cursor()
            cur.execute("""
                SELECT e.expense_id,e.expense_date,c.category_name,
                       e.amount,e.description,e.payment_method
                FROM expenses e
                JOIN categories c ON e.category_id=c.category_id
                WHERE e.expense_id=%s
            """,(edit_id,))
            edit=cur.fetchone()
            cur.close()
            con.close()

        generate_charts()

        return render_template_string(
            HTML,
            expenses=expenses,
            categories=get_categories(),
            total=total,
            month_total=month_total,
            count=count,
            highest=highest,
            analysis=analysis,
            today=today,
            edit=edit,
            start_date=start_date,
            end_date=end_date,
            selected_category=selected_category,
            filtered_total=filtered_total,
            report_month=report_month,
            report_total=report_total,
            report_count=report_count,
            report_categories=report_categories,
            chart_exists=bool(all_rows),
            chart_version=datetime.now().timestamp(),
            message=request.args.get("message","")
        )

    except mysql.connector.Error as e:
        return (
            "<h2>Database Error</h2>"
            "<p>"+str(e)+"</p>"
            "<p>Check your MySQL password and ensure MySQL Server is running.</p>",
            500
        )

@app.route("/save",methods=["POST"])
def save_expense():
    try:
        expense_id=request.form.get("expense_id","").strip()
        expense_date=request.form.get("expense_date","").strip()
        category=request.form.get("category","").strip()
        description=request.form.get("description","").strip()
        payment_method=request.form.get("payment_method","").strip()

        try:
            amount=float(request.form.get("amount",""))
            parsed_date=datetime.strptime(expense_date,"%Y-%m-%d")
        except (ValueError,TypeError):
            return "Invalid amount or date.",400

        if not np.isfinite(amount) or amount<=0:
            return "Amount must be a positive number.",400

        if not category or not payment_method:
            return "Category and payment method are required.",400

        con=get_connection()
        cur=con.cursor()

        cur.execute(
            "SELECT category_id FROM categories WHERE category_name=%s",
            (category,)
        )
        result=cur.fetchone()

        if not result:
            cur.close()
            con.close()
            return "Invalid category.",400

        category_id=result[0]

        if expense_id:
            cur.execute("""
                UPDATE expenses
                SET expense_date=%s,category_id=%s,amount=%s,
                    description=%s,payment_method=%s
                WHERE expense_id=%s
            """,(
                parsed_date.date(),category_id,amount,
                description,payment_method,expense_id
            ))
        else:
            cur.execute("""
                INSERT INTO expenses(
                    expense_date,category_id,amount,
                    description,payment_method
                )
                VALUES(%s,%s,%s,%s,%s)
            """,(
                parsed_date.date(),category_id,amount,
                description,payment_method
            ))

        con.commit()
        cur.close()
        con.close()

        return redirect(url_for("home",message="Expense saved successfully!"))

    except mysql.connector.Error as e:
        return "Database Error: "+str(e),500

@app.route("/delete/<int:expense_id>",methods=["POST"])
def delete_expense(expense_id):
    try:
        con=get_connection()
        cur=con.cursor()
        cur.execute(
            "DELETE FROM expenses WHERE expense_id=%s",
            (expense_id,)
        )
        con.commit()
        cur.close()
        con.close()
        return redirect(url_for("home",message="Expense deleted successfully!"))

    except mysql.connector.Error as e:
        return "Database Error: "+str(e),500

if __name__=="__main__":
    try:
        setup_database()
        print("Database initialized successfully.")
        print("Open http://127.0.0.1:5000 in your browser.")
        app.run(debug=False)
    except mysql.connector.Error as e:
        print("Could not connect to MySQL.")
        print("Check your MySQL username, password and server.")
        print("Details:",e)