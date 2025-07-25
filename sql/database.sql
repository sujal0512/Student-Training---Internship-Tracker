CREATE DATABASE stit_db;
USE stit_db;

CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    role ENUM('student', 'faculty') NOT NULL,
    batch VARCHAR(10),
    semester VARCHAR(10),
    course VARCHAR(50)
);

CREATE TABLE internships (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    title VARCHAR(100) NOT NULL,
    company VARCHAR(100) NOT NULL,
    duration VARCHAR(50) NOT NULL,
    certificate VARCHAR(200),
    status ENUM('Pending', 'Verified') DEFAULT 'Pending',
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE projects (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    title VARCHAR(100) NOT NULL,
    tools VARCHAR(200) NOT NULL,
    description TEXT NOT NULL,
    github_link VARCHAR(200),
    status ENUM('Pending', 'Verified') DEFAULT 'Pending',
    FOREIGN KEY (user_id) REFERENCES users(id)
);
ALTER USER 'sujal'@'localhost' IDENTIFIED WITH mysql_native_password BY 'your_secure_password';
FLUSH PRIVILEGES;
