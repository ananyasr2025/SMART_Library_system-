# Smart Library Management System - Flask backend
from functools import wraps
from datetime import date
from flask import Flask, render_template, request, redirect, url_for, session, flash, abort
from werkzeug.security import generate_password_hash as gph, check_password_hash as cph
from database import query
from config import Config

app = Flask(__name__)
app.secret_key = Config.SECRET_KEY

def login_required(*roles):
    """Protect a route; optionally restrict to given roles (role-based access)."""
    def deco(f):
        @wraps(f)
        def w(*a, **k):
            if 'uid' not in session:
                flash('Please log in first', 'warning'); return redirect(url_for('login'))
            if roles and session['role'] not in roles:
                flash('Access denied', 'danger'); return redirect(url_for('dashboard'))
            return f(*a, **k)
        return w
    return deco

def seed():
    """Create demo accounts with HASHED passwords the first time the app runs."""
    if query("SELECT id FROM users LIMIT 1", one=True): return
    for n, e, p, r in [("Admin", "admin@lib.com", "admin123", "admin"),
                       ("Lara Librarian", "lib@lib.com", "lib123", "librarian"),
                       ("Sam Student", "student@lib.com", "stud123", "student")]:
        uid = query("INSERT INTO users(name,email,password,role) VALUES(%s,%s,%s,%s)", (n, e, gph(p), r), commit=True)
        if r == 'student': query("INSERT INTO students(user_id,roll_no,interests) VALUES(%s,'CS001','Programming,Science')", (uid,), commit=True)
        if r == 'librarian': query("INSERT INTO librarians(user_id,employee_id) VALUES(%s,'EMP01')", (uid,), commit=True)

# ---------- Public pages & auth ----------
@app.route('/')
def index():
    books = query("SELECT b.*,c.name cat FROM books b JOIN categories c ON c.id=b.category_id ORDER BY b.id DESC LIMIT 4")
    cats = query("SELECT c.*,COUNT(b.id) n FROM categories c LEFT JOIN books b ON b.category_id=c.id GROUP BY c.id")
    return render_template('index.html', books=books, cats=cats)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        f = request.form
        name, email, pw = f['name'].strip(), f['email'].strip().lower(), f['password']
        if not name or '@' not in email or len(pw) < 6:
            flash('Fill all fields. Password needs 6+ characters.', 'danger')
        elif query("SELECT id FROM users WHERE email=%s", (email,), one=True):
            flash('Email already registered', 'danger')
        else:
            uid = query("INSERT INTO users(name,email,password,role) VALUES(%s,%s,%s,'student')", (name, email, gph(pw)), commit=True)
            query("INSERT INTO students(user_id,roll_no,interests) VALUES(%s,%s,%s)",
                  (uid, f['roll_no'].strip(), ','.join(f.getlist('interests'))), commit=True)
            flash('Registered! Please log in.', 'success'); return redirect(url_for('login'))
    return render_template('register.html', cats=query("SELECT * FROM categories"))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u = query("SELECT * FROM users WHERE email=%s", (request.form['email'].strip().lower(),), one=True)
        if u and cph(u['password'], request.form['password']):
            session.update(uid=u['id'], name=u['name'], role=u['role'])
            return redirect(url_for('dashboard'))
        flash('Invalid email or password', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear(); return redirect(url_for('index'))

# ---------- Dashboards ----------
def recommend(uid):
    """Smart feature 4: recommend by interests + categories already borrowed."""
    st = query("SELECT interests FROM students WHERE user_id=%s", (uid,), one=True)
    names = [x for x in (st['interests'] or '').split(',') if x] if st else []
    names += [h['name'] for h in query("SELECT DISTINCT c.name FROM book_issues i JOIN books b ON b.id=i.book_id JOIN categories c ON c.id=b.category_id WHERE i.user_id=%s", (uid,))]
    names = names or ['']
    ph = ','.join(['%s'] * len(names))
    books = query(f"SELECT b.*,c.name cat FROM books b JOIN categories c ON c.id=b.category_id WHERE c.name IN ({ph}) "
                  "AND b.available_copies>0 AND b.id NOT IN (SELECT book_id FROM book_issues WHERE user_id=%s) LIMIT 4", tuple(names) + (uid,))
    query("DELETE FROM recommendations WHERE student_id=%s", (uid,), commit=True)
    for b in books:
        query("INSERT INTO recommendations(student_id,book_id,reason) VALUES(%s,%s,%s)", (uid, b['id'], 'Matches your interest in ' + b['cat']), commit=True)
    return books

@app.route('/dashboard')
@login_required()
def dashboard():
    uid = session['uid']
    if session['role'] == 'student':
        mine = query("SELECT i.*,b.title FROM book_issues i JOIN books b ON b.id=i.book_id WHERE i.user_id=%s AND i.status='issued'", (uid,))
        query("DELETE FROM notifications WHERE user_id=%s", (uid,), commit=True)   # Smart feature 3: due-date alerts
        for i in mine:
            d = (i['due_date'] - date.today()).days
            if d < 0: m = f"OVERDUE: '{i['title']}' by {-d} day(s). Fine so far: Rs {-d * Config.FINE_PER_DAY}"
            elif d <= 3: m = f"Due soon: '{i['title']}' in {d} day(s)"
            else: continue
            query("INSERT INTO notifications(user_id,message) VALUES(%s,%s)", (uid, m), commit=True)
        return render_template('dashboard.html', mine=mine, recs=recommend(uid), today=date.today(),
                               notes=query("SELECT * FROM notifications WHERE user_id=%s", (uid,)))
    s = query("""SELECT (SELECT COALESCE(SUM(total_copies),0) FROM books) total,
        (SELECT COALESCE(SUM(available_copies),0) FROM books) avail,
        (SELECT COUNT(*) FROM book_issues WHERE status='issued') issued,
        (SELECT COUNT(*) FROM users WHERE role='student') students,
        (SELECT COUNT(*) FROM book_issues WHERE status='issued' AND due_date<CURDATE()) overdue""", one=True)
    monthly = query("SELECT CONCAT(YEAR(issue_date),'-',LPAD(MONTH(issue_date),2,'0')) m,COUNT(*) n FROM book_issues WHERE issue_date IS NOT NULL GROUP BY m ORDER BY m")
    bycat = query("SELECT c.name,COALESCE(SUM(b.total_copies),0) n FROM categories c LEFT JOIN books b ON b.category_id=c.id GROUP BY c.id")
    recent = query("SELECT i.*,b.title,u.name FROM book_issues i JOIN books b ON b.id=i.book_id JOIN users u ON u.id=i.user_id ORDER BY i.id DESC LIMIT 6")
    return render_template('dashboard.html', s=s, monthly=monthly, bycat=bycat, recent=recent)

# ---------- Books (CRUD + smart search) ----------
@app.route('/books')
def books():
    q, cat = request.args.get('q', '').strip(), request.args.get('cat', '')
    sql = "SELECT b.*,c.name cat FROM books b JOIN categories c ON c.id=b.category_id WHERE (b.title LIKE %s OR b.author LIKE %s OR b.isbn LIKE %s)"
    a = [f'%{q}%'] * 3
    if cat: sql += " AND b.category_id=%s"; a.append(cat)
    return render_template('books.html', books=query(sql + " ORDER BY b.title", tuple(a)),
                           cats=query("SELECT * FROM categories"), q=q, cat=cat)

@app.route('/books/save', defaults={'id': None}, methods=['GET', 'POST'])
@app.route('/books/save/<int:id>', methods=['GET', 'POST'])
@login_required('admin', 'librarian')
def book_save(id):
    b = query("SELECT * FROM books WHERE id=%s", (id,), one=True) if id else None
    if request.method == 'POST':
        f = request.form
        try:
            t = int(f['total']); assert t >= 0 and f['title'].strip() and f['isbn'].strip()
            data = (f['title'].strip(), f['author'].strip(), f['isbn'].strip(), f['category_id'], t, f['cover'].strip() or None)
            if id:   # keep availability correct: available = total - currently issued
                out = b['total_copies'] - b['available_copies']
                query("UPDATE books SET title=%s,author=%s,isbn=%s,category_id=%s,total_copies=%s,cover_url=%s,available_copies=GREATEST(%s-%s,0) WHERE id=%s",
                      data + (t, out, id), commit=True)
            else:
                query("INSERT INTO books(title,author,isbn,category_id,total_copies,cover_url,available_copies) VALUES(%s,%s,%s,%s,%s,%s,%s)", data + (t,), commit=True)
            flash('Book saved', 'success'); return redirect(url_for('books'))
        except Exception as e:
            flash(f'Could not save (check fields / duplicate ISBN): {e}', 'danger')
    return render_template('book_form.html', b=b, cats=query("SELECT * FROM categories"))

@app.route('/books/<int:id>/delete', methods=['POST'])
@login_required('admin', 'librarian')
def book_delete(id):
    query("DELETE FROM books WHERE id=%s", (id,), commit=True); flash('Book deleted', 'info')
    return redirect(url_for('books'))

# ---------- Issue / return workflow ----------
@app.route('/request/<int:id>', methods=['POST'])
@login_required('student')
def request_book(id):
    if query("SELECT id FROM book_issues WHERE user_id=%s AND book_id=%s AND status IN ('requested','issued')", (session['uid'], id), one=True):
        flash('You already requested/borrowed this book', 'warning')
    else:
        query("INSERT INTO book_issues(book_id,user_id) VALUES(%s,%s)", (id, session['uid']), commit=True)
        flash('Request sent to the librarian', 'success')
    return redirect(url_for('books'))

@app.route('/transactions')
@login_required()
def transactions():
    sql = "SELECT i.*,b.title,u.name,r.fine FROM book_issues i JOIN books b ON b.id=i.book_id JOIN users u ON u.id=i.user_id LEFT JOIN book_returns r ON r.issue_id=i.id"
    rows = query(sql + " WHERE i.user_id=%s ORDER BY i.id DESC", (session['uid'],)) if session['role'] == 'student' \
        else query(sql + " ORDER BY i.id DESC")
    return render_template('transactions.html', rows=rows, today=date.today())

@app.route('/issue/<int:id>/<act>', methods=['POST'])
@login_required('admin', 'librarian')
def issue_action(id, act):
    i = query("SELECT * FROM book_issues WHERE id=%s", (id,), one=True) or abort(404)
    if act == 'approve' and i['status'] == 'requested':
        if query("SELECT available_copies a FROM books WHERE id=%s", (i['book_id'],), one=True)['a'] < 1:
            flash('No copies available', 'danger')
        else:   # automatic availability update + due date
            query("UPDATE books SET available_copies=available_copies-1 WHERE id=%s", (i['book_id'],), commit=True)
            query("UPDATE book_issues SET status='issued',issue_date=CURDATE(),due_date=DATE_ADD(CURDATE(),INTERVAL %s DAY) WHERE id=%s", (Config.LOAN_DAYS, id), commit=True)
            flash('Book issued', 'success')
    elif act == 'reject' and i['status'] == 'requested':
        query("UPDATE book_issues SET status='rejected' WHERE id=%s", (id,), commit=True); flash('Request rejected', 'info')
    elif act == 'return' and i['status'] == 'issued':
        late = max((date.today() - i['due_date']).days, 0)
        query("UPDATE book_issues SET status='returned' WHERE id=%s", (id,), commit=True)
        query("INSERT INTO book_returns(issue_id,return_date,fine) VALUES(%s,CURDATE(),%s)", (id, late * Config.FINE_PER_DAY), commit=True)
        query("UPDATE books SET available_copies=available_copies+1 WHERE id=%s", (i['book_id'],), commit=True)
        flash(f'Returned. Fine: Rs {late * Config.FINE_PER_DAY}', 'success')
    return redirect(url_for('transactions'))

# ---------- Admin: users ----------
@app.route('/users', methods=['GET', 'POST'])
@login_required('admin')
def users():
    if request.method == 'POST':
        f = request.form
        try:
            assert len(f['password']) >= 6 and '@' in f['email']
            uid = query("INSERT INTO users(name,email,password,role) VALUES(%s,%s,%s,'librarian')", (f['name'].strip(), f['email'].strip().lower(), gph(f['password'])), commit=True)
            query("INSERT INTO librarians(user_id,employee_id) VALUES(%s,%s)", (uid, f['emp']), commit=True)
            flash('Librarian added', 'success')
        except Exception as e:
            flash(f'Could not add (duplicate email / short password): {e}', 'danger')
    return render_template('users.html', users=query("SELECT * FROM users ORDER BY role,name"))

@app.route('/users/<int:id>/delete', methods=['POST'])
@login_required('admin')
def user_delete(id):
    if id == session['uid']: flash("You can't delete yourself", 'danger')
    else: query("DELETE FROM users WHERE id=%s", (id,), commit=True); flash('User deleted', 'info')
    return redirect(url_for('users'))

if __name__ == '__main__':
    seed()
    app.run(debug=True)
