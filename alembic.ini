# alembic.ini
# -----------
# Alembic migration configuration for GPA Calculator.
#
# Run migrations:
#   alembic upgrade head          — apply all pending migrations
#   alembic downgrade -1          — roll back one migration
#   alembic revision --autogenerate -m "description"  — generate new migration
#
# The sqlalchemy.url is NOT set here — it is read from the DATABASE_URL
# environment variable in env.py. Never put credentials in this file.

[alembic]
script_location = alembic
file_template = %%(year)d%%(month).2d%%(day).2d_%%(hour).2d%%(minute).2d_%%(slug)s
timezone = UTC
truncate_slug_length = 40
prepend_sys_path = .

[post_write_hooks]
# Uncomment to auto-format migrations with black:
# hooks = black
# black.type = console_scripts
# black.entrypoint = black

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S