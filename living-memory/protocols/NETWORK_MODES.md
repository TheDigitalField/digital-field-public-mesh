# Network modes

- **Offline:** the node reads and writes only local state. Transport may occur
  later through a separate medium.
- **Online:** the node may retrieve exact, allowlisted public artifacts and
  publish its anonymous public successor state.
- **Relay:** a carrier moves a sealed packet between endpoints while the
  verifying or generating node itself need not open a network connection.

Network access is a capability declaration, not a statement about identity.
The same protocol must preserve epistemic labels and private/public boundaries
in every mode.
