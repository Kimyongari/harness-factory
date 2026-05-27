# API specs / reference knowledge base

> A place for **passive knowledge** the agent reads when needed.
> Add API specs, legacy system structure, domain glossaries here freely.
> Active "how-to procedures" belong in `.skills/`.

## Example: internal API

### `GET /v1/users/{id}`
- Description: fetch a single user
- Response: `{ "id": str, "name": str, "created_at": iso8601 }`

## Domain glossary
- **Harness**: the whole system around an LLM that makes it act as an agent
- **IR**: framework-neutral Intermediate Representation
