
-- TYPE ckan_entity_type

CREATE TYPE public.ckan_entity_type AS ENUM (
    'package',
    'resource'
);
ALTER TYPE public.ckan_entity_type OWNER TO postgres;

-- FUNCTION get_doi_sequence_name

CREATE FUNCTION public.get_doi_sequence_name(prefix text) RETURNS text
    LANGUAGE sql
    AS $$
select'prefix_' || replace(prefix, '.', '_') || '_seq'
$$;

ALTER FUNCTION public.get_doi_sequence_name(prefix text) OWNER TO postgres;

-- TABLE ckan_site

CREATE TABLE public.ckan_site (
    site_pk SERIAL PRIMARY KEY,
    site_id text NOT NULL,
    url text,
    description text
);

ALTER TABLE public.ckan_site OWNER TO postgres;
ALTER TABLE ONLY public.ckan_site
    ADD CONSTRAINT unique_ckan_site_id UNIQUE (site_id);

-- TABLE doi_prefix

CREATE TABLE public.doi_prefix (
    prefix_pk SERIAL PRIMARY KEY,
    prefix_id text NOT NULL,
    description text
);

ALTER TABLE public.doi_prefix OWNER TO postgres;
ALTER TABLE ONLY public.doi_prefix
    ADD CONSTRAINT unique_ckan_prefix_id UNIQUE (prefix_id);


-- FUNCTION create_doi_sequences
-- Creates all not existing sequences from doi_prefixes.sequence

CREATE FUNCTION public.create_doi_sequences() RETURNS void
    LANGUAGE plpgsql
    AS $$

DECLARE
    r doi_prefix%rowtype;
    available varchar;
BEGIN
    FOR r IN SELECT * FROM doi_prefix 
    LOOP
    SELECT c.relname INTO available FROM pg_class c WHERE c.relname=get_doi_sequence_name(r.prefix_id);
	IF AVAILABLE IS NOT NULL THEN
       RAISE NOTICE 'Sequence % already exists', get_doi_sequence_name(r.prefix_id);
       CONTINUE;
    END IF;
    RAISE NOTICE 'Create sequence %', get_doi_sequence_name(r.prefix_id);
    EXECUTE 'CREATE SEQUENCE ' || get_doi_sequence_name(r.prefix_id);
    END LOOP;
EXCEPTION WHEN others THEN
	RAISE NOTICE '% %', SQLERRM, SQLSTATE;
END;

$$;

ALTER FUNCTION public.create_doi_sequences() OWNER TO postgres;

COMMENT ON FUNCTION public.create_doi_sequences() IS 'Creates all not existing sequences from doi_prefixes.sequence';


-- FUNCTION get_next_doi_suffix

CREATE FUNCTION public.get_next_doi_suffix(prefix_id text, tag text) RETURNS text
    LANGUAGE sql
    AS $$
select 
tag||cast (nextval(get_doi_sequence_name(prefix_id)) as text);

$$;

ALTER FUNCTION public.get_next_doi_suffix(prefix_id text, tag text) OWNER TO postgres;

-- FUNCTION insert_doi_suffix_fn

CREATE FUNCTION public.insert_doi_suffix_fn() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
     BEGIN
         NEW.suffix_id := get_next_doi_suffix(NEW.prefix_id, NEW.tag_id);
         RETURN NEW;
     END;
 $$;

ALTER FUNCTION public.insert_doi_suffix_fn() OWNER TO postgres;

-- FUNCTION update_doi_modified_fn()

CREATE FUNCTION public.update_doi_modified_fn() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.date_modified := now();
    RETURN NEW;
END; $$;

ALTER FUNCTION public.update_doi_modified_fn() OWNER TO postgres;

-- TABLE doi_realisation

CREATE TABLE public.doi_realisation (
    doi_pk SERIAL PRIMARY KEY,
    prefix_id text NOT NULL,
    suffix_id text NOT NULL,
    ckan_id uuid NOT NULL,
    ckan_name text NOT NULL,
    site_id text NOT NULL,
    tag_id text DEFAULT 'envidat.' NOT NULL,
    ckan_user text DEFAULT 'admin' NOT NULL,
    metadata text NOT NULL,
    metadata_format text DEFAULT 'ckan'::text,
    ckan_entity public.ckan_entity_type DEFAULT 'package'::public.ckan_entity_type NOT NULL,
    date_created timestamp without time zone DEFAULT now() NOT NULL,
    date_modified timestamp without time zone DEFAULT now() NOT NULL
);

ALTER TABLE public.doi_realisation OWNER TO postgres;

ALTER TABLE ONLY public.doi_realisation
    ADD CONSTRAINT unique_ckan_id_site_entity UNIQUE (ckan_id, site_id, ckan_entity);

ALTER TABLE ONLY public.doi_realisation
    ADD CONSTRAINT unique_doi_site UNIQUE (prefix_id, suffix_id, site_id);

CREATE TRIGGER doi_inserted_tr BEFORE INSERT ON public.doi_realisation FOR EACH ROW WHEN ((new.suffix_id IS NULL)) EXECUTE PROCEDURE public.insert_doi_suffix_fn();
CREATE TRIGGER doi_modified_tr BEFORE UPDATE ON public.doi_realisation FOR EACH ROW EXECUTE PROCEDURE public.update_doi_modified_fn();

ALTER TABLE ONLY public.doi_realisation
    ADD CONSTRAINT prefix_fk FOREIGN KEY (prefix_id) REFERENCES public.doi_prefix(prefix_id);

ALTER TABLE ONLY public.doi_realisation
    ADD CONSTRAINT site_id_fk FOREIGN KEY (site_id) REFERENCES public.ckan_site(site_id);

-- access rights
REVOKE ALL ON SCHEMA public FROM PUBLIC;
REVOKE ALL ON SCHEMA public FROM postgres;
GRANT ALL ON SCHEMA public TO postgres;
GRANT ALL ON SCHEMA public TO PUBLIC;

REVOKE ALL ON TABLE public.doi_realisation FROM PUBLIC;
REVOKE ALL ON TABLE public.doi_realisation FROM postgres;
GRANT ALL ON TABLE public.doi_realisation TO postgres;
GRANT SELECT ON TABLE public.doi_realisation TO ckan_default;
GRANT INSERT, UPDATE ON TABLE public.doi_realisation TO ckan_default;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO ckan_default;

-- Edit the lines below to add prefixes and create the sequences
-- INSERT INTO public.doi_prefix(prefix_id, description) VALUES ('10.16904', 'WSL prefix');
-- INSERT INTO public.doi_prefix(prefix_id, description) VALUES ('10.12345', 'test prefix');

-- INSERT INTO public.ckan_site VALUES (1, 'localhost', 'http://localhost:5000', 'local test instance');

-- SELECT public.create_doi_sequences()

-- INSERT INTO public.doi_realisation(prefix_id, ckan_id, ckan_name, site_id, metadata) VALUES ('10.12345', 'b5e52b1a-cc8f-46a6-ad94-2c309f6d7fe7', 'horse-breeds', 'localhost', 'pending');
