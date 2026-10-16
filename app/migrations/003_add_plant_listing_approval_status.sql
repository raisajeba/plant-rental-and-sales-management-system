ALTER TABLE plants
    ADD COLUMN approval_status VARCHAR(20) NOT NULL DEFAULT 'approved',
    ADD CONSTRAINT ck_plants_approval_status
        CHECK (approval_status IN ('pending', 'approved', 'rejected'));
