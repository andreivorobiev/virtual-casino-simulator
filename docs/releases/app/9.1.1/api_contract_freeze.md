# API contract freeze policy

The `/api/v1` endpoints are frozen as compatibility contracts.

## Compatible changes

- New optional request fields.
- New optional response fields.
- New endpoints that do not alter existing endpoint behavior.
- New error codes only when old clients safely ignore them.

## Breaking changes

- Removing an endpoint.
- Renaming a field.
- Adding a required request field to an existing endpoint.
- Changing the meaning of an existing field.
- Changing money movement timing.
- Changing ledger or history schema incompatibly.

Breaking changes require `/api/v2` or an explicit compatibility shim.
