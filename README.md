# Arctic Unfrozen

Arctic Unfrozen maintains the MongoDB-backed `arctic` Python package originally
developed by Man Group. The original authors moved active development to
[ArcticDB](https://github.com/man-group/ArcticDB), a ground-up successor with a
new storage engine. ArcticDB is the appropriate choice for many new projects,
but it is not storage-compatible with Arctic.

This project keeps Arctic useful for existing deployments and for teams that
prefer MongoDB. It remains a practical option when:

- existing Arctic data must remain readable without a migration;
- MongoDB is already part of the application stack and operating model;
- existing code depends on the established `arctic` imports and APIs;
- a Python implementation is useful for inspection, debugging, or extension;
- the LGPL-licensed Arctic codebase better fits the deployment requirements.

The project is being modernized conservatively: current Python and dependency
support should improve without breaking the existing interface or stored data.

## Documentation

The original setup and usage guide remains available in
[README-arctic.md](README-arctic.md). It is still the primary reference while
the documentation is refreshed for Arctic Unfrozen.

## Development

Install the package and development tools:

```bash
python -m pip install -e ".[test,dev]"
```

Run unit tests:

```bash
python -m nox -s unit
```

Integration tests erase all non-system databases on their target MongoDB
server. Never point them at a server containing valuable data. To run them
against an isolated ephemeral MongoDB container:

```bash
docker run --rm -d --name arctic-unfrozen-test \
  -p 127.0.0.1:27018:27017 \
  mongodb/mongodb-community-server:8.3.2-ubi9-slim
ARCTIC_TEST_MONGO_HOST=localhost:27018 python -m nox -s integration
docker stop arctic-unfrozen-test
```
