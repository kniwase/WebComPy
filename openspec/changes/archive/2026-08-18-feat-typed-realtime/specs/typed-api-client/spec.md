# Typed API Client Specification (delta)

## ADDED Requirements

### Requirement: Already-typed values shall pass through from_json unchanged

`from_json` SHALL return a value that is already an instance of the target type unchanged, without re-validation, including when `strict=True`. Strict validation (unknown-key rejection, missing-required-field rejection, and type-mismatch errors) SHALL apply to JSON-derived values (dict/list/scalar inputs) only; a value that is already the target type is not a mismatch. This covers values restored from transfer metadata by registered type decoders (e.g., allowlist-registered custom types), which are reconstructed before schema-driven conversion and must survive it unchanged.

#### Scenario: Dataclass instance passes through in strict mode

- **WHEN** `from_json(User, user_instance, strict=True)` is called for a dataclass `User(id: int, name: str)` and an existing `User` instance `user_instance`
- **THEN** the same `user_instance` SHALL be returned unchanged

#### Scenario: Nested instance field is preserved

- **WHEN** `from_json(Team, {"name": "core", "members": [user_instance]}, strict=True)` is called for `Team(name: str, members: list[User])` and an existing `User` instance `user_instance`
- **THEN** the result SHALL contain the same `user_instance` at `members[0]`

#### Scenario: Dict inputs remain strictly validated

- **WHEN** `from_json(User, {"id": 1, "name": "ada", "extra": true}, strict=True)` is called
- **THEN** a `TypeError` SHALL be raised for the unknown key `extra`