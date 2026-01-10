
# App Structure 
```
app/
    main.py
    core/
    db/
    api/v1/
    modules/
    auth/
    users/
    businesses/
    orders/
    reviews/
    shared/
    tests/
```



```
app/
  main.py

  core/
    config.py          # settings/env
    logging.py         # optional
    security.py        # auth utils (jwt, hashing)

  db/
    engine.py          # create_async_engine
    session.py         # AsyncSession dependency
    base.py            # SQLModel metadata import aggregator
    init_db.py         # create_all (dev only) / startup checks

  api/
    v1/
      router.py        # include all routers here
      deps.py          # common dependencies (current user, session, etc.)

  modules/
    auth/
      router.py
      schemas.py
      service.py

    users/
      models.py
      schemas.py
      service.py
      router.py

    businesses/
      models.py
      schemas.py
      service.py
      router.py

    orders/
      models.py
      schemas.py
      service.py
      router.py

    reviews/
      models.py
      schemas.py
      service.py
      router.py

  shared/
    exceptions.py
    responses.py
    pagination.py
    utils.py

tests/
  test_users.py
  conftest.py

```