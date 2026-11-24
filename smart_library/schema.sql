CREATE DATABASE IF NOT EXISTS smart_library;
USE smart_library;
CREATE TABLE users(id INT AUTO_INCREMENT PRIMARY KEY, name VARCHAR(100) NOT NULL, email VARCHAR(120) UNIQUE NOT NULL,
  password VARCHAR(255) NOT NULL, role ENUM('admin','librarian','student') NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE students(id INT AUTO_INCREMENT PRIMARY KEY, user_id INT NOT NULL, roll_no VARCHAR(30), interests VARCHAR(255),
  FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE);
CREATE TABLE librarians(id INT AUTO_INCREMENT PRIMARY KEY, user_id INT NOT NULL, employee_id VARCHAR(30),
  FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE);
CREATE TABLE categories(id INT AUTO_INCREMENT PRIMARY KEY, name VARCHAR(60) UNIQUE NOT NULL);
CREATE TABLE books(id INT AUTO_INCREMENT PRIMARY KEY, title VARCHAR(200) NOT NULL, author VARCHAR(120) NOT NULL,
  isbn VARCHAR(20) UNIQUE NOT NULL, category_id INT NOT NULL, total_copies INT NOT NULL DEFAULT 1,
  available_copies INT NOT NULL DEFAULT 1, cover_url VARCHAR(255), FOREIGN KEY(category_id) REFERENCES categories(id));
CREATE TABLE book_issues(id INT AUTO_INCREMENT PRIMARY KEY, book_id INT NOT NULL, user_id INT NOT NULL,
  request_date DATE DEFAULT (CURRENT_DATE), issue_date DATE, due_date DATE,
  status ENUM('requested','issued','returned','rejected') DEFAULT 'requested',
  FOREIGN KEY(book_id) REFERENCES books(id) ON DELETE CASCADE, FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE);
CREATE TABLE book_returns(id INT AUTO_INCREMENT PRIMARY KEY, issue_id INT NOT NULL, return_date DATE, fine INT DEFAULT 0,
  FOREIGN KEY(issue_id) REFERENCES book_issues(id) ON DELETE CASCADE);
CREATE TABLE notifications(id INT AUTO_INCREMENT PRIMARY KEY, user_id INT NOT NULL, message VARCHAR(255),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE);
CREATE TABLE recommendations(id INT AUTO_INCREMENT PRIMARY KEY, student_id INT NOT NULL, book_id INT NOT NULL, reason VARCHAR(200),
  FOREIGN KEY(student_id) REFERENCES users(id) ON DELETE CASCADE, FOREIGN KEY(book_id) REFERENCES books(id) ON DELETE CASCADE);

INSERT INTO categories(name) VALUES('Programming'),('Science'),('Fiction'),('History'),('Self-Help');
INSERT INTO books(title,author,isbn,category_id,total_copies,available_copies) VALUES
('Clean Code','Robert C. Martin','9780132350884',1,5,5),('Python Crash Course','Eric Matthes','9781593279288',1,4,4),
('Introduction to Algorithms','Thomas Cormen','9780262046305',1,3,3),('A Brief History of Time','Stephen Hawking','9780553380163',2,4,4),
('Cosmos','Carl Sagan','9780345539434',2,3,3),('1984','George Orwell','9780451524935',3,5,5),
('The Alchemist','Paulo Coelho','9780062315007',3,4,4),('Sapiens','Yuval Noah Harari','9780062316110',4,4,4),
('Atomic Habits','James Clear','9781847941831',5,5,5);
-- Default users (admin/librarian/student) are created automatically by app.py on first run.
