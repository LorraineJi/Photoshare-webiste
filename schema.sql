CREATE DATABASE photoshare;
USE photoshare;

CREATE TABLE users
(
  user_id INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
  first_name VARCHAR(255) NOT NULL,
  last_name VARCHAR(255) NOT NULL,
  dob VARCHAR(255) NOT NULL,
  profile_pic LONGBLOB, bio TEXT,
  hometown VARCHAR(255),
  email VARCHAR(255) NOT NULL unique,
  gender ENUM('M','F','O'),
  score INT NOT NULL,
  password VARCHAR(255) NOT NULL
);
ALTER TABLE users ALTER score SET DEFAULT 0;

CREATE TABLE albums
(
  aid INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
  name VARCHAR(255) NOT NULL,
  user_id INT NOT NULL,
  date_cr VARCHAR(255) NOT NULL
);

ALTER TABLE albums ADD FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE;
ALTER TABLE albums MODIFY name SET DEFAULT ‘untitled’;

CREATE TABLE tags
(
  description VARCHAR(255) NOT NULL unique
);

CREATE TABLE friends
(
  user_id INT NOT NULL,
  fri_id INT NOT NULL,
  PRIMARY KEY(user_id, fri_id)
);
ALTER TABLE friends ADD FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE;
ALTER TABLE friends ADD FOREIGN KEY (fri_id) REFERENCES users(user_id) ON DELETE CASCADE;
ALTER TABLE friends ADD CONSTRAINT chk_fri CHECK(fri_id != user_id);

CREATE TABLE tag_associate
(
  description VARCHAR(255) NOT NULL,
  pid INT NOT NULL,
  PRIMARY KEY(description, pid)
);
ALTER TABLE tag_associate ADD FOREIGN KEY (description) REFERENCES tags(description) ON DELETE CASCADE;
ALTER TABLE tag_associate ADD FOREIGN KEY (pid) REFERENCES photo(pid) ON DELETE CASCADE;

CREATE TABLE photo
(
  pid INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
  caption TEXT,
  data LONGBLOB NOT NULL,
  aid INT NOT NULL
);
ALTER TABLE photo ADD FOREIGN KEY (aid) REFERENCES albums(aid) ON DELETE CASCADE;

CREATE TABLE comment_on
(
  cid INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
  date VARCHAR(255) NOT NULL,
  text TEXT NOT NULL,
  user_id INT,
  pid INT NOT NULL
);
ALTER TABLE comment_on ADD FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE;
ALTER TABLE comment_on ADD FOREIGN KEY (pid) REFERENCES photo(pid) ON DELETE CASCADE;

CREATE TABLE likes
(
  user_id INT NOT NULL,
  pid INT NOT NULL,
  PRIMARY KEY(user_id, pid)
);
ALTER TABLE likes ADD FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE;
ALTER TABLE likes ADD FOREIGN KEY (pid) REFERENCES photo(pid) ON DELETE CASCADE;


CREATE trigger add_photo
AFTER INSERT ON photo
FOR EACH ROW
UPDATE users SET score=score+1
WHERE users.user_id=(
  SELECT users.user_id FROM albums,photo
  WHERE users.user_id=albums.user_id AND albums.aid=photo.aid AND photo.pid=(SELECT MAX(p. pid) from photo p));

CREATE trigger add_comment
AFTER INSERT ON comment_on
FOR EACH ROW UPDATE users SET score=score+1
WHERE user_id = (SELECT user_id FROM comment_on c WHERE c.cid =(SELECT MAX(co.cid)FROM comment_on co));

INSERT INTO users (user_id, first_name,last_name,dob,email,password) VALUES (0,'Mr/Ms','Anonymous','unknown','unknown','unknown');
UPDATE users SET user_id = 0 WHERE first_name='Mr/Ms';
