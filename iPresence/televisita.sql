BEGIN;
CREATE TABLE "televisita_room" (
    "id" serial NOT NULL PRIMARY KEY,
    "owner_id" integer NOT NULL UNIQUE REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED,
    "nombre" varchar(70) NOT NULL,
    "salaId" text NOT NULL,
    "salaIdWebrtc" text NOT NULL,
    "autorizado_id" integer REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED
)
;
CREATE INDEX "televisita_room_autorizado_id" ON "televisita_room" ("autorizado_id");
COMMIT;
