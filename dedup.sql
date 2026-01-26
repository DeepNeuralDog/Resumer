
WITH ranked AS (
  SELECT id, ROW_NUMBER() OVER (PARTITION BY text, "user" ORDER BY id) AS rn
  FROM summaries
)
DELETE FROM summaries WHERE id IN (SELECT id FROM ranked WHERE rn > 1);

WITH ranked AS (
  SELECT id, ROW_NUMBER() OVER (PARTITION BY skill_name, "user" ORDER BY id) AS rn
  FROM skills
)
DELETE FROM skills WHERE id IN (SELECT id FROM ranked WHERE rn > 1);

WITH ranked AS (
  SELECT id, ROW_NUMBER() OVER (PARTITION BY text, skill ORDER BY id) AS rn
  FROM skill_bullets
)
DELETE FROM skill_bullets WHERE id IN (SELECT id FROM ranked WHERE rn > 1);

WITH ranked AS (
  SELECT id, ROW_NUMBER() OVER (
    PARTITION BY experience_name, start_year, end_year, ongoing, "user"
    ORDER BY id
  ) AS rn
  FROM experiences
)
DELETE FROM experiences WHERE id IN (SELECT id FROM ranked WHERE rn > 1);

WITH ranked AS (
  SELECT id, ROW_NUMBER() OVER (PARTITION BY text, experience ORDER BY id) AS rn
  FROM experience_bullets
)
DELETE FROM experience_bullets WHERE id IN (SELECT id FROM ranked WHERE rn > 1);

WITH ranked AS (
  SELECT id, ROW_NUMBER() OVER (PARTITION BY project_name, github_link, "user" ORDER BY id) AS rn
  FROM projects
)
DELETE FROM projects WHERE id IN (SELECT id FROM ranked WHERE rn > 1);

WITH ranked AS (
  SELECT id, ROW_NUMBER() OVER (PARTITION BY text, project ORDER BY id) AS rn
  FROM project_bullets
)
DELETE FROM project_bullets WHERE id IN (SELECT id FROM ranked WHERE rn > 1);

WITH ranked AS (
  SELECT id, ROW_NUMBER() OVER (
    PARTITION BY education_name, institution, start, "end", grade, "user"
    ORDER BY id
  ) AS rn
  FROM education
)
DELETE FROM education WHERE id IN (SELECT id FROM ranked WHERE rn > 1);

WITH ranked AS (
  SELECT id, ROW_NUMBER() OVER (
    PARTITION BY referer_name, referer_institute, position, "user"
    ORDER BY id
  ) AS rn
  FROM "references"
)
DELETE FROM "references" WHERE id IN (SELECT id FROM ranked WHERE rn > 1);

ALTER TABLE summaries
  ADD CONSTRAINT summaries_unique_text_user UNIQUE (text, "user");

ALTER TABLE skills
  ADD CONSTRAINT skills_unique_skill_user UNIQUE (skill_name, "user");

ALTER TABLE skill_bullets
  ADD CONSTRAINT skill_bullets_unique_text_skill UNIQUE (text, skill);

ALTER TABLE experiences
  ADD CONSTRAINT experiences_unique_fields UNIQUE (experience_name, start_year, end_year, ongoing, "user");

ALTER TABLE experience_bullets
  ADD CONSTRAINT experience_bullets_unique_text_experience UNIQUE (text, experience);

ALTER TABLE projects
  ADD CONSTRAINT projects_unique_fields UNIQUE (project_name, github_link, "user");

ALTER TABLE project_bullets
  ADD CONSTRAINT project_bullets_unique_text_project UNIQUE (text, project);

ALTER TABLE education
  ADD CONSTRAINT education_unique_fields UNIQUE (education_name, institution, start, "end", grade, "user");

ALTER TABLE "references"
  ADD CONSTRAINT references_unique_fields UNIQUE (referer_name, referer_institute, position, "user");