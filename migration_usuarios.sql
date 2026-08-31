USE estoque_inteligente;

ALTER TABLE users
ADD COLUMN email VARCHAR(150) NULL UNIQUE AFTER name;

UPDATE users
SET email = CONCAT(login, '@arb.local')
WHERE email IS NULL;

ALTER TABLE users
MODIFY email VARCHAR(150) NOT NULL;