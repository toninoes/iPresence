BEGIN;
CREATE TABLE "presence_empresa" (
    "id" serial NOT NULL PRIMARY KEY,
    "cif" varchar(10) NOT NULL UNIQUE,
    "nombre" varchar(100) NOT NULL UNIQUE,
    "direccion" varchar(150) NOT NULL,
    "poblacion" varchar(100) NOT NULL,
    "postal" integer CHECK ("postal" >= 0) NOT NULL,
    "telefono" integer CHECK ("telefono" >= 0) NOT NULL,
    "fax" integer CHECK ("fax" >= 0) NOT NULL,
    "email" varchar(75) NOT NULL
)
;
CREATE TABLE "presence_gerente" (
    "id" serial NOT NULL PRIMARY KEY,
    "nif" varchar(10) NOT NULL UNIQUE,
    "first_name" varchar(30) NOT NULL,
    "last_name" varchar(30) NOT NULL,
    "empresa_id" integer NOT NULL REFERENCES "presence_empresa" ("id") DEFERRABLE INITIALLY DEFERRED
)
;
CREATE TABLE "presence_centro" (
    "id" serial NOT NULL PRIMARY KEY,
    "direccion" varchar(150) NOT NULL,
    "poblacion" varchar(100) NOT NULL,
    "postal" integer CHECK ("postal" >= 0) NOT NULL,
    "telefono" integer CHECK ("telefono" >= 0) NOT NULL,
    "fax" integer CHECK ("fax" >= 0) NOT NULL,
    "email" varchar(75) NOT NULL,
    "empresa_id" integer NOT NULL REFERENCES "presence_empresa" ("id") DEFERRABLE INITIALLY DEFERRED
)
;
CREATE TABLE "presence_laboral" (
    "user_ptr_id" integer NOT NULL PRIMARY KEY REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED,
    "centro_id" integer NOT NULL REFERENCES "presence_centro" ("id") DEFERRABLE INITIALLY DEFERRED
)
;
CREATE TABLE "presence_docente" (
    "user_ptr_id" integer NOT NULL PRIMARY KEY REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED
)
;
CREATE TABLE "presence_alumno" (
    "user_ptr_id" integer NOT NULL PRIMARY KEY REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED,
    "telefono" integer CHECK ("telefono" >= 0) NOT NULL,
    "movil" integer CHECK ("movil" >= 0) NOT NULL,
    "fnac" date NOT NULL,
    "docente_id" integer REFERENCES "presence_docente" ("user_ptr_id") DEFERRABLE INITIALLY DEFERRED,
    "laboral_id" integer REFERENCES "presence_laboral" ("user_ptr_id") DEFERRABLE INITIALLY DEFERRED
)
;
CREATE TABLE "presence_curso" (
    "id" serial NOT NULL PRIMARY KEY,
    "fecha_inicio" integer CHECK ("fecha_inicio" >= 0) NOT NULL UNIQUE
)
;
CREATE TABLE "presence_aprendizaje" (
    "id" serial NOT NULL PRIMARY KEY,
    "resultado" text NOT NULL
)
;
CREATE TABLE "presence_contratoprograma_aprendizajes" (
    "id" serial NOT NULL PRIMARY KEY,
    "contratoprograma_id" integer NOT NULL,
    "aprendizaje_id" integer NOT NULL REFERENCES "presence_aprendizaje" ("id") DEFERRABLE INITIALLY DEFERRED,
    UNIQUE ("contratoprograma_id", "aprendizaje_id")
)
;
CREATE TABLE "presence_contratoprograma" (
    "id" serial NOT NULL PRIMARY KEY,
    "fecha" date NOT NULL,
    "curso_id" integer NOT NULL REFERENCES "presence_curso" ("id") DEFERRABLE INITIALLY DEFERRED,
    "alumno_id" integer NOT NULL REFERENCES "presence_alumno" ("user_ptr_id") DEFERRABLE INITIALLY DEFERRED,
    "docente_id" integer NOT NULL REFERENCES "presence_docente" ("user_ptr_id") DEFERRABLE INITIALLY DEFERRED,
    "laboral_id" integer NOT NULL REFERENCES "presence_laboral" ("user_ptr_id") DEFERRABLE INITIALLY DEFERRED,
    "gerente_id" integer NOT NULL REFERENCES "presence_gerente" ("id") DEFERRABLE INITIALLY DEFERRED,
    "modalidad" varchar(1) NOT NULL,
    "periodo" varchar(1) NOT NULL,
    "actividades" text NOT NULL,
    "criterios" text NOT NULL,
    "confirmado" boolean NOT NULL
)
;
ALTER TABLE "presence_contratoprograma_aprendizajes" ADD CONSTRAINT "contratoprograma_id_refs_id_9ad5dc3" FOREIGN KEY ("contratoprograma_id") REFERENCES "presence_contratoprograma" ("id") DEFERRABLE INITIALLY DEFERRED;
CREATE TABLE "presence_seguimiento" (
    "id" serial NOT NULL PRIMARY KEY,
    "fecha" date NOT NULL,
    "actividad" text NOT NULL,
    "tiempo" smallint NOT NULL,
    "observaciones" text NOT NULL,
    "contratoprograma_id" integer NOT NULL REFERENCES "presence_contratoprograma" ("id") DEFERRABLE INITIALLY DEFERRED
)
;
CREATE TABLE "presence_visita_aprendizajesPositivos" (
    "id" serial NOT NULL PRIMARY KEY,
    "visita_id" integer NOT NULL,
    "aprendizaje_id" integer NOT NULL REFERENCES "presence_aprendizaje" ("id") DEFERRABLE INITIALLY DEFERRED,
    UNIQUE ("visita_id", "aprendizaje_id")
)
;
CREATE TABLE "presence_visita" (
    "id" serial NOT NULL PRIMARY KEY,
    "fecha" date NOT NULL,
    "contratoprograma_id" integer NOT NULL REFERENCES "presence_contratoprograma" ("id") DEFERRABLE INITIALLY DEFERRED,
    "otro_motivo" text NOT NULL,
    "tiempo" varchar(10) NOT NULL,
    "modalidad" varchar(1) NOT NULL
)
;
ALTER TABLE "presence_visita_aprendizajesPositivos" ADD CONSTRAINT "visita_id_refs_id_5cdea502" FOREIGN KEY ("visita_id") REFERENCES "presence_visita" ("id") DEFERRABLE INITIALLY DEFERRED;
CREATE TABLE "presence_usuarioinactivo" (
    "id" serial NOT NULL PRIMARY KEY,
    "usuario_id" integer NOT NULL UNIQUE REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED,
    "key" varchar(50) NOT NULL,
    "validez" timestamp with time zone NOT NULL
)
;
CREATE INDEX "presence_gerente_empresa_id" ON "presence_gerente" ("empresa_id");
CREATE INDEX "presence_centro_empresa_id" ON "presence_centro" ("empresa_id");
CREATE INDEX "presence_laboral_centro_id" ON "presence_laboral" ("centro_id");
CREATE INDEX "presence_alumno_docente_id" ON "presence_alumno" ("docente_id");
CREATE INDEX "presence_alumno_laboral_id" ON "presence_alumno" ("laboral_id");
CREATE INDEX "presence_contratoprograma_curso_id" ON "presence_contratoprograma" ("curso_id");
CREATE INDEX "presence_contratoprograma_alumno_id" ON "presence_contratoprograma" ("alumno_id");
CREATE INDEX "presence_contratoprograma_docente_id" ON "presence_contratoprograma" ("docente_id");
CREATE INDEX "presence_contratoprograma_laboral_id" ON "presence_contratoprograma" ("laboral_id");
CREATE INDEX "presence_contratoprograma_gerente_id" ON "presence_contratoprograma" ("gerente_id");
CREATE INDEX "presence_seguimiento_contratoprograma_id" ON "presence_seguimiento" ("contratoprograma_id");
CREATE INDEX "presence_visita_contratoprograma_id" ON "presence_visita" ("contratoprograma_id");
COMMIT;
