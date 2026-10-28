USE estoque_inteligente;

CREATE TABLE IF NOT EXISTS notification_reads (
    user_id INT NOT NULL,
    notification_key VARCHAR(120) NOT NULL,
    read_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, notification_key),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
