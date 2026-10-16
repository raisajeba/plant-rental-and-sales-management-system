ALTER TABLE users
    ADD COLUMN approval_status VARCHAR(20) NOT NULL DEFAULT 'approved',
    ADD CONSTRAINT ck_users_approval_status
        CHECK (approval_status IN ('pending', 'approved', 'rejected'));
